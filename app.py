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

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from anthropic import Anthropic

from confidence import analyze_confidence


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


# ── Globaler State ──────────────────────────────────────────

active_requests = 0
shutting_down = False
anthropic_client: Anthropic | None = None


# ── Lifespan (Startup / Shutdown) ───────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: Clients initialisieren. Shutdown: Graceful drain."""
    global anthropic_client

    logger.info("Voice Agent API starting up...")

    # API Key pruefen
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning(
            "ANTHROPIC_API_KEY nicht gesetzt. /chat und /analyze Endpoints sind deaktiviert."
        )
    else:
        anthropic_client = Anthropic()
        logger.info("Anthropic Client initialisiert.")
    logger.info(f"Modell: {CLAUDE_MODEL}, Version: {APP_VERSION}")

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
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": APP_VERSION,
        "active_requests": active_requests,
        "services": {
            "llm": "claude-connected" if anthropic_client else "not-initialized",
        },
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat mit Claude Agent.
    Sendet eine Nachricht, erhaelt Antwort mit Confidence Score.
    """
    if not anthropic_client:
        raise HTTPException(status_code=503, detail="Anthropic Client nicht initialisiert.")

    t_start = time.time()

    messages = list(request.history)
    messages.append({"role": "user", "content": request.message})

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

    assistant_text = response.content[0].text
    confidence = analyze_confidence(assistant_text)
    duration = time.time() - t_start

    logger.info(
        f"Chat: {len(request.message)} Zeichen -> {len(assistant_text)} Zeichen, "
        f"Confidence: {confidence.score} ({confidence.label})"
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
    Streaming Chat mit Claude Agent.
    Gibt Tokens via Server-Sent Events (SSE) zurueck.
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
                    yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"

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
