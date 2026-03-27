# HAUSAUFGABE -- Donnerstag 26.03.2026 (Advanced)

## Deployment-Abend | Abgabe: Freitag 27.03.2026 vor Unterrichtsbeginn

Heute habt ihr den Voice Agent auf Railway deployed. Jetzt deployed ihr EUREN eigenen.

Diese Hausaufgabe hat ein Ziel: Euer deployed Voice Agent wird besser.
Kein Portfolio, kein CV, keine Slides. Nur Code, Docker, Endpoints.

Referenz-Repo: https://github.com/OthmanAdi/voice-agent-deploy
Live: https://deployvoiceagent-production.up.railway.app

---

## Teil 1: EUER Repo deployment-ready machen (45 min)

Ihr habt diese Woche euren eigenen Voice Agent gebaut. Der lebt in EUREM Repo.
Jetzt bekommt EUER Repo: Docker, FastAPI, Railway.

### Schritt fuer Schritt

**1. server.py in EUER Repo kopieren und anpassen**

```python
"""FastAPI Server fuer den Voice Agent."""

from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timezone
from agent import think  # <-- euer agent.py importieren
import os

app = FastAPI(title="Voice Agent API")
START_TIME = datetime.now(timezone.utc)
conversation_history = []


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    history_length: int


@app.get("/health")
async def health():
    uptime = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    return {
        "status": "healthy",
        "uptime_seconds": round(uptime, 2),
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    response = think(req.message, conversation_history)
    return ChatResponse(
        response=response,
        history_length=len(conversation_history)
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

WICHTIG: Der Import `from agent import think` muss zu EUREM Code passen.
Wenn eure Funktion anders heisst oder in einer anderen Datei liegt: anpassen.

**2. Dockerfile in EUER Repo**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "server.py"]
```

**3. docker-compose.yml in EUER Repo**

```yaml
services:
  voice-agent:
    build: .
    container_name: voice-agent
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - ENVIRONMENT=development
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

**4. .dockerignore in EUER Repo**

```
.git
.gitignore
.env
__pycache__
*.pyc
*.mp3
*.wav
.venv
venv
node_modules
*.md
.vscode
```

Warum .dockerignore? Ohne sie kopiert `COPY . .` alles in das Image.
Euer .env mit den API-Keys landet dann IM Container-Image.
Das .env darf nie ins Image. Die Keys kommen via Environment Variables von Railway.

**5. Lokal testen**

```bash
docker compose build && docker compose up
```

In einem zweiten Terminal:

```bash
curl http://localhost:8000/health
```

Erwartete Antwort:

```json
{"status": "healthy", "uptime_seconds": 5.23, "environment": "development"}
```

```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "Was ist Docker?"}'
```

Wenn beides funktioniert: weiter.
Wenn nicht: Docker-Logs lesen. `docker compose logs -f` zeigt euch den Fehler.

**6. Push zu GitHub**

```bash
git add server.py Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: add Docker + FastAPI deployment"
git push
```

**7. Deploy auf Railway**

```bash
railway login
railway init
railway up
```

Railway erkennt das Dockerfile automatisch und baut den Container.

**8. Environment Variables setzen**

```bash
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set OPENAI_API_KEY=sk-...
railway variables set ENVIRONMENT=production
```

OHNE die Environment Variables startet der Container, aber Claude und TTS schlagen fehl.
Railway injiziert die Variables als echte Environment Variables in den Container.
Deshalb funktioniert `os.getenv("ANTHROPIC_API_KEY")` im Code.

**9. Domain holen**

```bash
railway domain
```

Railway gibt euch eine URL wie: `dein-projekt-production.up.railway.app`

**10. Live testen**

```bash
curl https://EURE-URL.up.railway.app/health
curl -X POST https://EURE-URL.up.railway.app/chat -H "Content-Type: application/json" -d '{"message": "Hallo"}'
```

Beide muessen funktionieren. Wenn der Health Check geht aber /chat nicht:
`railway logs` zeigt euch die Fehlermeldung im Container.

---

## Teil 2: /voices Endpoint + /chat-with-voice (30 min)

OpenAI TTS hat 6 Stimmen. Im Moment ist "nova" hardcoded.
Jetzt wird die Stimme waehlbar.

### Neue Pydantic Models

Fuegt das zu eurem server.py hinzu:

```python
from typing import Optional
import base64
from openai import OpenAI

openai_client = OpenAI()

AVAILABLE_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
CURRENT_VOICE = "nova"
TTS_MODEL = "tts-1"


class ChatWithVoiceRequest(BaseModel):
    message: str
    voice: Optional[str] = "nova"
```

### /voices Endpoint

```python
@app.get("/voices")
async def voices():
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
        }
    }
```

### /chat-with-voice Endpoint

```python
@app.post("/chat-with-voice")
async def chat_with_voice(req: ChatWithVoiceRequest):
    # Voice validieren
    voice = req.voice if req.voice in AVAILABLE_VOICES else CURRENT_VOICE

    # Claude antwortet
    text_response = think(req.message, conversation_history)

    # TTS generiert Audio mit gewaehlter Stimme
    tts_response = openai_client.audio.speech.create(
        model=TTS_MODEL,
        voice=voice,
        input=text_response
    )

    # Audio als Base64 kodieren
    audio_bytes = tts_response.content
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    return {
        "response": text_response,
        "voice_used": voice,
        "audio_format": "mp3",
        "audio_base64": audio_base64,
        "audio_size_bytes": len(audio_bytes),
        "history_length": len(conversation_history)
    }
```

### Testen

```bash
# Verfuegbare Stimmen abfragen
curl https://EURE-URL.up.railway.app/voices

# Chat mit Stimmenauswahl
curl -X POST https://EURE-URL.up.railway.app/chat-with-voice \
  -H "Content-Type: application/json" \
  -d '{"message": "Sag mir was ueber Docker", "voice": "onyx"}'
```

Die Antwort enthaelt `audio_base64` -- das ist das MP3 als Base64-String.
Ein Frontend koennte das dekodieren und abspielen. Fuer jetzt reicht es,
dass der Endpoint funktioniert und die Groesse (`audio_size_bytes`) sinnvoll ist.

Warum Base64? HTTP-Responses sind text-basiert. Binaere Audio-Daten muessen
kodiert werden. Base64 macht aus 3 Bytes Binaerdaten 4 ASCII-Zeichen.
Das ist ~33% Overhead, aber universell kompatibel mit JSON.

---

## Teil 3: /stream Endpoint mit Server-Sent Events (30 min)

Claude kann Token fuer Token streamen. Das habt ihr in streaming_voice.py gesehen.
Jetzt bringt ihr das Streaming in den FastAPI Server.

SSE (Server-Sent Events) ist ein HTTP-Protokoll fuer Einweg-Streaming vom Server zum Client.
Der Client oeffnet eine Verbindung, der Server schickt Daten Stueck fuer Stueck.
Jede Nachricht hat das Format `data: {...}\n\n`.

### /stream Endpoint

```python
import json
import anthropic
from fastapi.responses import StreamingResponse

claude_client = anthropic.Anthropic()


@app.post("/stream")
async def stream_chat(req: ChatRequest):
    async def generate():
        full_response = ""
        conversation_history.append({"role": "user", "content": req.message})

        with claude_client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system="Du bist ein hilfreicher deutscher Assistent. Antworte kurz und praezise auf Deutsch.",
            messages=conversation_history
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield f"data: {json.dumps({'token': text})}\n\n"

        conversation_history.append({"role": "assistant", "content": full_response})
        yield f"data: {json.dumps({'done': True, 'full_response': full_response})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Testen

```bash
curl -N -X POST https://EURE-URL.up.railway.app/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Was ist Docker?"}'
```

Das `-N` Flag ist entscheidend. Ohne `-N` buffert curl die Ausgabe und ihr seht
alles erst am Ende. Mit `-N` seht ihr jeden Token einzeln ankommen:

```
data: {"token": "Docker"}
data: {"token": " ist"}
data: {"token": " eine"}
data: {"token": " Container"}
data: {"token": "-Platt"}
data: {"token": "form"}
...
data: {"done": true, "full_response": "Docker ist eine Container-Plattform..."}
```

Das ist der Unterschied zwischen 5 Sekunden warten und sofort lesen.
ChatGPT, Claude.ai -- alle nutzen SSE fuer ihre Chat-Interfaces.

---

## Teil 4: Request Logging Middleware (20 min)

Jeder Request wird geloggt: Zeitpunkt, Methode, Pfad, Status, Dauer.
Kein externer Service noetig -- eine Python-Liste reicht.

### Middleware + /logs Endpoint

Fuegt das zu eurem server.py hinzu, VOR den Endpoint-Definitionen:

```python
import time
from datetime import datetime

REQUEST_LOG = []


@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round(duration * 1000, 1)
    }

    REQUEST_LOG.append(log_entry)

    # Maximal 100 Eintraege behalten (Memory-Schutz)
    if len(REQUEST_LOG) > 100:
        REQUEST_LOG.pop(0)

    return response


@app.get("/logs")
async def get_logs():
    return {
        "total_requests": len(REQUEST_LOG),
        "logs": REQUEST_LOG[-20:]
    }
```

### Warum Middleware?

Middleware sitzt ZWISCHEN dem eingehenden Request und eurem Endpoint.
Jeder Request -- egal welcher Endpoint -- geht durch die Middleware.
Ihr muesst nicht jeden Endpoint einzeln loggen.

### Testen

```bash
# 5 Requests machen
curl https://EURE-URL.up.railway.app/health
curl https://EURE-URL.up.railway.app/voices
curl -X POST https://EURE-URL.up.railway.app/chat -H "Content-Type: application/json" -d '{"message": "Hallo"}'
curl -X POST https://EURE-URL.up.railway.app/chat -H "Content-Type: application/json" -d '{"message": "Was ist Python?"}'
curl https://EURE-URL.up.railway.app/health

# Logs pruefen
curl https://EURE-URL.up.railway.app/logs
```

Erwartete Antwort:

```json
{
  "total_requests": 5,
  "logs": [
    {"timestamp": "2026-03-26T20:15:03.123", "method": "GET", "path": "/health", "status": 200, "duration_ms": 1.2},
    {"timestamp": "2026-03-26T20:15:04.456", "method": "GET", "path": "/voices", "status": 200, "duration_ms": 0.8},
    {"timestamp": "2026-03-26T20:15:05.789", "method": "POST", "path": "/chat", "status": 200, "duration_ms": 2341.5},
    {"timestamp": "2026-03-26T20:15:10.012", "method": "POST", "path": "/chat", "status": 200, "duration_ms": 1823.7},
    {"timestamp": "2026-03-26T20:15:12.345", "method": "GET", "path": "/health", "status": 200, "duration_ms": 1.0}
  ]
}
```

Beachtet die duration_ms: /health braucht ~1ms, /chat braucht ~2000ms.
Das ist die Claude API Latenz. In Production wuerdet ihr darauf Alerts setzen.

---

## Teil 5: ARCHITECTURE.md erweitern (15 min)

Euer ARCHITECTURE.md bekommt einen Deployment-Abschnitt.

### Deployment-Diagramm hinzufuegen

```markdown
## Deployment

### Pipeline

    GitHub Repo
         |
         | git push
         v
    Railway (Build)
         |
         | docker build
         v
    Docker Image
         |
         | docker run
         v
    Container (port 8000)
         |
         | railway domain
         v
    Public URL: https://xxx-production.up.railway.app

### Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| /health | GET | Status + Uptime. Fuer Monitoring und Healthchecks. |
| /chat | POST | Text rein, Claude-Antwort raus. JSON Request/Response. |
| /voices | GET | Verfuegbare TTS-Stimmen auflisten. |
| /chat-with-voice | POST | Chat + TTS. Antwort als Text + Base64-Audio. |
| /stream | POST | Chat mit SSE-Streaming. Token fuer Token. |
| /logs | GET | Letzte 20 Requests mit Timing. |

### Environment Variables

| Variable | Wofuer | Wo gesetzt |
|----------|--------|------------|
| ANTHROPIC_API_KEY | Claude API Zugang | Railway Variables |
| OPENAI_API_KEY | TTS API Zugang | Railway Variables |
| ENVIRONMENT | development/production | Railway Variables |
| PORT | Server-Port (Railway setzt das automatisch) | Railway (automatisch) |

### Warum Docker

- **Isolation:** Der Container hat seine eigene Python-Version, eigene Dependencies.
  Kein "aber bei mir geht es" mehr.
- **Reproduzierbarkeit:** Dockerfile ist die einzige Wahrheit. Was drin steht, wird gebaut.
  Egal ob auf deinem Laptop oder auf Railway.
- **Portabilitaet:** Railway, AWS, Google Cloud, dein eigener Server -- egal.
  Docker laeuft ueberall gleich.
- **Kein Dependency-Chaos:** pip install auf dem Host-System kann alles kaputt machen.
  Im Container ist es isoliert.
```

---

## Komplettes server.py (Referenz)

Hier ist das vollstaendige server.py mit allen 5 Teilen zusammen.
Das ist die Referenz -- euer eigenes muss an euren Code angepasst sein.

```python
"""FastAPI Server fuer den Voice Agent -- alle Endpoints."""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import anthropic
from openai import OpenAI
import base64
import json
import time
import os

from agent import think  # <-- euer agent.py

app = FastAPI(title="Voice Agent API")
START_TIME = datetime.now(timezone.utc)
conversation_history = []

claude_client = anthropic.Anthropic()
openai_client = OpenAI()

AVAILABLE_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
CURRENT_VOICE = "nova"
TTS_MODEL = "tts-1"

# --- Request Logging ---

REQUEST_LOG = []


@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    REQUEST_LOG.append({
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round(duration * 1000, 1)
    })

    if len(REQUEST_LOG) > 100:
        REQUEST_LOG.pop(0)

    return response


# --- Pydantic Models ---

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    history_length: int


class ChatWithVoiceRequest(BaseModel):
    message: str
    voice: Optional[str] = "nova"


# --- Endpoints ---

@app.get("/health")
async def health():
    uptime = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    return {
        "status": "healthy",
        "uptime_seconds": round(uptime, 2),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "endpoints": ["/health", "/chat", "/voices", "/chat-with-voice", "/stream", "/logs"]
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    response = think(req.message, conversation_history)
    return ChatResponse(
        response=response,
        history_length=len(conversation_history)
    )


@app.get("/voices")
async def voices():
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
        }
    }


@app.post("/chat-with-voice")
async def chat_with_voice(req: ChatWithVoiceRequest):
    voice = req.voice if req.voice in AVAILABLE_VOICES else CURRENT_VOICE

    text_response = think(req.message, conversation_history)

    tts_response = openai_client.audio.speech.create(
        model=TTS_MODEL,
        voice=voice,
        input=text_response
    )

    audio_bytes = tts_response.content
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    return {
        "response": text_response,
        "voice_used": voice,
        "audio_format": "mp3",
        "audio_base64": audio_base64,
        "audio_size_bytes": len(audio_bytes),
        "history_length": len(conversation_history)
    }


@app.post("/stream")
async def stream_chat(req: ChatRequest):
    async def generate():
        full_response = ""
        conversation_history.append({"role": "user", "content": req.message})

        with claude_client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system="Du bist ein hilfreicher deutscher Assistent. Antworte kurz und praezise auf Deutsch.",
            messages=conversation_history
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield f"data: {json.dumps({'token': text})}\n\n"

        conversation_history.append({"role": "assistant", "content": full_response})
        yield f"data: {json.dumps({'done': True, 'full_response': full_response})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/logs")
async def get_logs():
    return {
        "total_requests": len(REQUEST_LOG),
        "logs": REQUEST_LOG[-20:]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

---

## Abgabe

**Wann:** Freitag 27.03.2026 vor Unterrichtsbeginn.

**Was:**

- [ ] EUER Repo auf Railway deployed mit oeffentlicher URL
- [ ] /health funktioniert: `curl https://EURE-URL.up.railway.app/health`
- [ ] /chat funktioniert: `curl -X POST ... -d '{"message": "Hallo"}'`
- [ ] /voices funktioniert: `curl https://EURE-URL.up.railway.app/voices`
- [ ] /chat-with-voice funktioniert mit Stimmenauswahl
- [ ] /stream funktioniert mit SSE: `curl -N -X POST ...`
- [ ] /logs zeigt Request-History mit Timing
- [ ] ARCHITECTURE.md hat Deployment-Abschnitt
- [ ] Alles auf GitHub gepusht

**Gesamtaufwand:** ca. 2.5 Stunden.

---

## Resources

- Railway CLI: https://docs.railway.com/guides/cli
- Railway Environment Variables: https://docs.railway.com/guides/variables
- FastAPI StreamingResponse: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
- FastAPI Middleware: https://fastapi.tiangolo.com/tutorial/middleware/
- Server-Sent Events: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
- Docker Compose Docs: https://docs.docker.com/compose/
- Base64 Encoding (Python): https://docs.python.org/3/library/base64.html
- OpenAI TTS API: https://platform.openai.com/docs/guides/text-to-speech
- Anthropic Streaming: https://docs.anthropic.com/en/api/streaming
