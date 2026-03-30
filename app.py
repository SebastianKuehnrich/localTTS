"""
Voice Agent API — FastAPI-App.
Endpoints fuer Health Check, Chat (Claude Streaming), TTS und Confidence Scoring.
Graceful Shutdown + Structured JSON Logging.
"""

import os
import sys
import json
import time
import asyncio
import logging
import tempfile
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from dataclasses import asdict

from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import base64

from pydantic import BaseModel, Field
from typing import Optional
from anthropic import Anthropic
from openai import OpenAI

from confidence import analyze_confidence
from sliding_window import SlidingContextWindow
from context_hub import voice_hub


# ── Structured JSON Logging ─────────────────────────────────

class JSONFormatter(logging.Formatter):
    """Formatiert Log-Eintraege als JSON fuer Log-Aggregatoren."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


logger = logging.getLogger("voice_agent")
_handler = logging.StreamHandler()
_handler.setFormatter(JSONFormatter())
logger.addHandler(_handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())


# ── Konfiguration ───────────────────────────────────────────

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Du bist ein hilfreicher Sprachassistent. Antworte kurz auf Deutsch. Maximal 3 Saetze.",
)
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
MAX_AUDIO_LENGTH_SECONDS = int(os.getenv("MAX_AUDIO_LENGTH_SECONDS", "30"))
STT_MODEL = os.getenv("STT_MODEL", "whisper-small")  # "whisper-small" (lokal) oder "whisper-api" (OpenAI)

# TTS-Stimmen
AVAILABLE_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
CURRENT_VOICE = os.getenv("TTS_VOICE", "nova")
TTS_MODEL = "tts-1"


# ── Globaler State ──────────────────────────────────────────

START_TIME = datetime.now(timezone.utc)
active_requests = 0
shutting_down = False
anthropic_client: Anthropic | None = None
openai_client = None
whisper_pipeline = None
context_window: SlidingContextWindow | None = None
REQUEST_LOG: list[dict] = []


# ── Lifespan (Startup / Shutdown) ───────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: Clients initialisieren. Shutdown: Graceful drain."""
    global anthropic_client, openai_client

    logger.info("Voice Agent API starting up...")

    # Anthropic API Key pruefen
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        logger.warning(
            "ANTHROPIC_API_KEY nicht gesetzt. /chat und /analyze Endpoints sind deaktiviert."
        )
    else:
        anthropic_client = Anthropic(api_key=api_key)
        logger.info("Anthropic Client initialisiert.")

        global context_window
        context_window = SlidingContextWindow(
            client=anthropic_client,
            model=CLAUDE_MODEL,
            max_recent=10,
            summary_threshold=20,
        )
        logger.info("SlidingContextWindow initialisiert (max_recent=10, threshold=20).")

    # OpenAI API Key pruefen (fuer TTS + optionales API-STT)
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not openai_key:
        logger.warning(
            "OPENAI_API_KEY nicht gesetzt. /tts Endpoint ist deaktiviert."
        )
    else:
        openai_client = OpenAI(api_key=openai_key)
        logger.info("OpenAI Client initialisiert (TTS).")

    # Lokales Whisper laden
    global whisper_pipeline
    if STT_MODEL.startswith("whisper-") and STT_MODEL != "whisper-api":
        try:
            from transformers import pipeline as hf_pipeline
            model_name = f"openai/{STT_MODEL}"
            logger.info(f"Lade lokales Whisper-Modell: {model_name}...")
            whisper_pipeline = hf_pipeline(
                "automatic-speech-recognition",
                model=model_name,
                chunk_length_s=30,
                ignore_warning=True,
            )
            logger.info(f"Whisper-Modell geladen: {model_name}")
        except Exception as e:
            logger.error(f"Whisper-Modell konnte nicht geladen werden: {e}")
    elif STT_MODEL == "whisper-api":
        logger.info("STT: OpenAI Whisper API")
    logger.info(f"Modell: {CLAUDE_MODEL}, STT: {STT_MODEL}, Version: {APP_VERSION}")

    yield

    # Graceful Shutdown
    global shutting_down
    shutting_down = True
    logger.info(f"Shutting down. Warte auf {active_requests} aktive Requests...")

    for _ in range(30):
        if active_requests == 0:
            break
        await asyncio.sleep(1)

    logger.info("Shutdown abgeschlossen.")


# ── FastAPI App ─────────────────────────────────────────────

app = FastAPI(
    title="Voice Agent API",
    description="Pipeline: STT -> Claude Agent -> TTS mit Confidence Scoring",
    version=APP_VERSION,
    lifespan=lifespan,
)

# Statische Dateien (UI)
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    """Liefert die Web-UI aus."""
    index_path = STATIC_DIR / "index.html"
    if index_path.is_file():
        return FileResponse(str(index_path))
    return JSONResponse({"message": "Voice Agent API", "docs": "/docs"})


# ── Middleware: Request Tracking + Shutdown Guard ───────────

@app.middleware("http")
async def track_requests(request, call_next):
    """Zaehlt aktive Requests und lehnt neue waehrend Shutdown ab."""
    global active_requests

    if shutting_down:
        return JSONResponse(
            status_code=503,
            content={"error": "Server faehrt herunter. Bitte spaeter erneut versuchen."},
        )

    active_requests += 1
    t_start = time.time()
    try:
        response = await call_next(request)
        return response
    finally:
        active_requests -= 1
        duration = time.time() - t_start
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration:.2f}s)"
        )

        # Request-Log fuer /logs Endpoint
        REQUEST_LOG.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration * 1000, 1),
        })
        if len(REQUEST_LOG) > 100:
            REQUEST_LOG.pop(0)


# ── Request/Response Modelle ────────────────────────────────

class ChatRequest(BaseModel):
    """Request fuer den /chat Endpoint."""
    message: str = Field(..., min_length=1, max_length=2000, description="User-Nachricht")
    history: list[dict] = Field(default_factory=list, description="Bisherige Konversation")


class ChatResponse(BaseModel):
    """Response vom /chat Endpoint."""
    response: str
    confidence: dict
    model: str
    duration_seconds: float


class ConfidenceRequest(BaseModel):
    """Request fuer den /confidence Endpoint."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text zum Analysieren")


class ChatWithVoiceRequest(BaseModel):
    """Request fuer den /chat-with-voice Endpoint."""
    message: str = Field(..., min_length=1, max_length=2000, description="User-Nachricht")
    voice: Optional[str] = Field(default="nova", description="TTS-Stimme (alloy, echo, fable, onyx, nova, shimmer)")


class AnalyzeRequest(BaseModel):
    """Request fuer den /analyze Endpoint (CORTANA-Style)."""
    query: str = Field(..., min_length=1, max_length=2000)
    context: str = Field(default="", max_length=5000, description="Optionaler Kontext")
    require_high_confidence: bool = Field(default=False)


class AnalyzeResponse(BaseModel):
    """Response vom /analyze Endpoint."""
    answer: str
    confidence: dict
    escalated: bool
    model: str
    duration_seconds: float


# ── Endpoints ───────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health Check — wird von Docker/Railway regelmaessig abgefragt."""
    uptime = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(uptime, 2),
        "version": APP_VERSION,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "active_requests": active_requests,
        "services": {
            "llm": "claude-connected" if anthropic_client else "not-initialized",
            "stt": f"{STT_MODEL}-loaded" if whisper_pipeline or (STT_MODEL == "whisper-api" and openai_client) else "not-initialized",
            "tts": "openai-tts-connected" if openai_client else "not-initialized",
        },
        "endpoints": ["/health", "/chat", "/chat/stream", "/stream", "/voices",
                      "/chat-with-voice", "/confidence", "/analyze", "/stt", "/tts", "/logs"],
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat mit Claude Agent + SlidingContextWindow.
    Sendet eine Nachricht, erhaelt Antwort mit Confidence Score.
    Alte Messages werden automatisch zusammengefasst.
    """
    if not anthropic_client or not context_window:
        raise HTTPException(status_code=503, detail="Anthropic Client nicht initialisiert.")

    t_start = time.time()

    # Message ins SlidingWindow eintragen
    context_window.add_message("user", request.message)

    # Context bauen (mit Zusammenfassung falls vorhanden)
    system_prompt, recent_messages = context_window.build_context(SYSTEM_PROMPT)

    try:
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=recent_messages,
        )
    except Exception as e:
        logger.error(f"Claude API Fehler: {e}")
        raise HTTPException(status_code=502, detail="Fehler bei der Claude API.")

    assistant_text = response.content[0].text
    context_window.add_message("assistant", assistant_text)

    confidence = analyze_confidence(assistant_text)
    duration = time.time() - t_start
    stats = context_window.get_stats()

    logger.info(
        f"Chat: {len(request.message)} Zeichen -> {len(assistant_text)} Zeichen, "
        f"Confidence: {confidence.score} ({confidence.label}), "
        f"Context: {stats['in_context']}/{stats['total_messages']} messages"
    )

    return ChatResponse(
        response=assistant_text,
        confidence=asdict(confidence),
        model=CLAUDE_MODEL,
        duration_seconds=round(duration, 3),
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming Chat mit Claude Agent + SlidingContextWindow.
    Gibt Tokens via Server-Sent Events (SSE) zurueck.
    """
    if not anthropic_client or not context_window:
        raise HTTPException(status_code=503, detail="Anthropic Client nicht initialisiert.")

    # Message ins SlidingWindow eintragen
    context_window.add_message("user", request.message)
    system_prompt, recent_messages = context_window.build_context(SYSTEM_PROMPT)

    async def generate():
        full_response = ""
        try:
            with anthropic_client.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=500,
                system=system_prompt,
                messages=recent_messages,
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"

            context_window.add_message("assistant", full_response)
            confidence = analyze_confidence(full_response)
            yield f"data: {json.dumps({'type': 'done', 'confidence': asdict(confidence)})}\n\n"

        except Exception as e:
            logger.error(f"Streaming Fehler: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/confidence")
async def confidence_check(request: ConfidenceRequest):
    """
    Analysiert einen beliebigen Text auf Konfidenz-Indikatoren.
    Nuetzlich um eigene Texte oder externe Antworten zu bewerten.
    """
    result = analyze_confidence(request.text)
    return asdict(result)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    CORTANA-Style Analyse-Endpoint.
    Beantwortet eine Frage, bewertet die Konfidenz und eskaliert bei Bedarf.

    Wenn require_high_confidence=True und der Score unter 0.7 liegt,
    wird die Antwort als 'escalated' markiert (= Mensch sollte pruefen).
    """
    if not anthropic_client:
        raise HTTPException(status_code=503, detail="Anthropic Client nicht initialisiert.")

    t_start = time.time()

    system = SYSTEM_PROMPT
    user_content = request.query
    if request.context:
        user_content = f"Kontext: {request.context}\n\nFrage: {request.query}"

    try:
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as e:
        logger.error(f"Analyze Fehler: {e}")
        raise HTTPException(status_code=502, detail="Fehler bei der Claude API.")

    answer = response.content[0].text
    confidence = analyze_confidence(answer)
    duration = time.time() - t_start

    escalated = request.require_high_confidence and confidence.label != "high"

    if escalated:
        logger.warning(
            f"Antwort eskaliert: Score {confidence.score}, Query: {request.query[:80]}"
        )

    return AnalyzeResponse(
        answer=answer,
        confidence=asdict(confidence),
        escalated=escalated,
        model=CLAUDE_MODEL,
        duration_seconds=round(duration, 3),
    )


# ── Voices + Chat-with-Voice ───────────────────────────────

@app.get("/voices")
async def voices():
    """Listet alle verfuegbaren TTS-Stimmen auf."""
    return {
        "available": AVAILABLE_VOICES,
        "current": CURRENT_VOICE,
        "model": TTS_MODEL,
        "info": {
            "alloy": "neutral, balanced",
            "echo": "warm, maennlich",
            "fable": "britisch, erzaehlend",
            "onyx": "tief, autoritaer",
            "nova": "energisch, weiblich",
            "shimmer": "sanft, weiblich",
        },
    }


@app.post("/chat-with-voice")
async def chat_with_voice(request: ChatWithVoiceRequest):
    """
    Chat mit Claude + TTS Audio-Ausgabe.
    Gibt Text-Antwort und Base64-kodiertes Audio zurueck.
    """
    if not anthropic_client:
        raise HTTPException(status_code=503, detail="Anthropic Client nicht initialisiert.")
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI Client nicht initialisiert. OPENAI_API_KEY setzen.")

    # Voice validieren
    voice = request.voice if request.voice in AVAILABLE_VOICES else CURRENT_VOICE

    t_start = time.time()

    # Claude Agent
    messages = [{"role": "user", "content": request.message}]
    try:
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
    except Exception as e:
        logger.error(f"Claude API Fehler: {e}")
        raise HTTPException(status_code=502, detail="Fehler bei der Claude API.")

    text_response = response.content[0].text

    # TTS mit gewaehlter Stimme
    try:
        tts_response = openai_client.audio.speech.create(
            model=TTS_MODEL,
            voice=voice,
            input=text_response,
        )
        audio_bytes = tts_response.content
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        logger.error(f"TTS Fehler: {e}")
        raise HTTPException(status_code=502, detail="Fehler bei der OpenAI TTS API.")

    duration = time.time() - t_start
    confidence = analyze_confidence(text_response)

    logger.info(
        f"Chat-with-Voice: voice={voice}, {len(text_response)} Zeichen, "
        f"audio={len(audio_bytes)} bytes ({duration:.1f}s)"
    )

    return {
        "response": text_response,
        "voice_used": voice,
        "audio_format": "mp3",
        "audio_base64": audio_base64,
        "audio_size_bytes": len(audio_bytes),
        "confidence": asdict(confidence),
        "duration_seconds": round(duration, 3),
    }


# ── SSE Stream Endpoint ───────────────────────────────────

@app.post("/stream")
async def stream_chat_alias(request: ChatRequest):
    """
    Streaming Chat via SSE — Alias fuer /chat/stream.
    Gibt Tokens einzeln via Server-Sent Events zurueck.
    """
    if not anthropic_client:
        raise HTTPException(status_code=503, detail="Anthropic Client nicht initialisiert.")

    messages = list(request.history)
    messages.append({"role": "user", "content": request.message})

    async def generate():
        full_response = ""
        try:
            with anthropic_client.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    yield f"data: {json.dumps({'token': text})}\n\n"

            confidence = analyze_confidence(full_response)
            yield f"data: {json.dumps({'done': True, 'full_response': full_response, 'confidence': asdict(confidence)})}\n\n"

        except Exception as e:
            logger.error(f"Streaming Fehler: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── Context Window Stats ─────────────────────────────────

@app.get("/context")
async def context_stats():
    """Zeigt den aktuellen Zustand des SlidingContextWindow."""
    if not context_window:
        return {"status": "not-initialized", "message": "Kein Anthropic Client."}

    stats = context_window.get_stats()
    return {
        "status": "active",
        "window": stats,
        "config": {
            "max_recent": context_window.max_recent,
            "summary_threshold": context_window.summary_threshold,
        },
    }


@app.post("/context/reset")
async def context_reset():
    """Setzt das SlidingContextWindow zurueck (neue Session)."""
    if not context_window:
        raise HTTPException(status_code=503, detail="Kein Anthropic Client.")
    context_window.reset()
    return {"status": "reset", "message": "Conversation History zurueckgesetzt."}


@app.get("/context/hub")
async def context_hub_resolve(task: str = ""):
    """ContextHub: Welche Dateien sind fuer einen Task relevant?"""
    result = voice_hub.resolve(task)
    return result


# ── Request Logs ──────────────────────────────────────────

@app.get("/logs")
async def get_logs():
    """Zeigt die letzten 20 Requests mit Timing-Informationen."""
    return {
        "total_requests": len(REQUEST_LOG),
        "logs": REQUEST_LOG[-20:],
    }


# ── Voice Endpoints (STT + TTS) ────────────────────────────

@app.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """Whisper STT: Audio-Datei -> Text. Nutzt lokales whisper-small oder OpenAI API."""
    if not whisper_pipeline and STT_MODEL != "whisper-api":
        raise HTTPException(status_code=503, detail="Whisper-Modell nicht geladen.")
    if STT_MODEL == "whisper-api" and not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI Client nicht initialisiert. OPENAI_API_KEY setzen.")

    allowed_types = {"audio/wav", "audio/webm", "audio/mp4", "audio/mpeg", "audio/ogg", "application/octet-stream"}
    if audio.content_type and audio.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Nicht unterstuetztes Audio-Format: {audio.content_type}")

    try:
        audio_bytes = await audio.read()
        if len(audio_bytes) > MAX_AUDIO_LENGTH_SECONDS * 16000 * 2:
            raise HTTPException(status_code=400, detail="Audio-Datei zu gross.")

        suffix = ".webm" if audio.content_type and "webm" in audio.content_type else ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            t_start = time.time()

            if STT_MODEL == "whisper-api":
                # OpenAI Whisper API
                result = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=open(tmp_path, "rb"),
                    language="de",
                )
                text = result.text
            else:
                # Lokales Whisper-Modell
                result = whisper_pipeline(
                    tmp_path,
                    generate_kwargs={"language": "de"},
                )
                text = result["text"]

            duration = time.time() - t_start
        finally:
            os.unlink(tmp_path)

        logger.info(f"STT ({STT_MODEL}): {len(audio_bytes)} bytes -> '{text[:80]}' ({duration:.1f}s)")
        return {"text": text, "model": STT_MODEL, "duration_seconds": round(duration, 3)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT Fehler: {e}")
        raise HTTPException(status_code=502, detail=f"Fehler bei Whisper ({STT_MODEL}).")


class TTSRequest(BaseModel):
    """Request fuer den /tts Endpoint."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text zum Vorlesen")
    voice: Optional[str] = Field(default="nova", description="TTS-Stimme")


@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """OpenAI TTS: Text -> Audio-Datei (MP3). Stimme waehlbar."""
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI Client nicht initialisiert. OPENAI_API_KEY setzen.")

    voice = request.voice if request.voice in AVAILABLE_VOICES else CURRENT_VOICE

    try:
        response = openai_client.audio.speech.create(
            model=TTS_MODEL,
            voice=voice,
            input=request.text,
        )

        audio_bytes = response.content
        logger.info(f"TTS: '{request.text[:60]}' -> {len(audio_bytes)} bytes")

        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"},
        )

    except Exception as e:
        logger.error(f"TTS Fehler: {e}")
        raise HTTPException(status_code=502, detail="Fehler bei der OpenAI TTS API.")
