# PROJEKT — Donnerstag 26.03.2026 (Advanced)

## 09:00 - 12:00 | Docker + Deployment des Voice Agents

**Selbststaendige Arbeit. Ahmad ist bei den Beginnern.**

---

## Kontext

**Dennis und Sebastian haben unterschiedliche Ausgangssituationen — also unterschiedliche Ziele fuer heute.**

### Dennis
Dein Voice Agent laeuft lokal. Das reicht nicht. Kein Recruiter startet dein Repo lokal.
Heute machst du ihn production-ready: Docker-Container, Health Checks, deployed mit Live-URL.
Am Ende des Tages sollst du einen Link haben, den du morgen in der Praesentation zeigen kannst.

### Sebastian
Du hast starke Dokumentation geschrieben (ARCHITECTURE.md, EVAL_RESULTS.md, TECH_STACK.md fuer CORTANA/COGITO) — aber keinen lauffaehigen Code. Kein Voice Agent, kein Streaming, kein Gradio, kein Docker, kein Deployment. Heute ist der Tag, wo du deine Architektur in Code umsetzt. Ziel: Mindestens ein lauffaehiges FastAPI-Grundgeruest mit einem funktionierenden Endpoint, das deine Architektur-Entscheidungen demonstriert. Docker und Deployment sind Bonus — Code first.

**Sebastians Prioritaeten heute:**
1. FastAPI-App mit Basis-Endpoints aufsetzen (Health Check, mindestens ein CORTANA/COGITO Endpoint)
2. Confidence Scoring Logik als Code implementieren (auch als Stub/Prototyp)
3. Wenn Zeit bleibt: Dockerfile + Docker Compose
4. Wenn noch mehr Zeit: Deployment auf Railway

---

## BRONZE — Dockerfile + Health Check (Minimum)

### Schritt 1: Dockerfile erstellen

Erstellt im Root eures Voice-Agent-Repos ein `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# System-Dependencies fuer Audio-Processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies zuerst kopieren (Docker Layer Caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Dann den Rest des Codes
COPY . .

# Port definieren
EXPOSE 8000

# Health Check im Container selbst
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Starten
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Warum diese Reihenfolge?** Docker cached jeden Layer. Wenn sich nur euer Code aendert
(nicht die requirements.txt), wird `pip install` nicht neu ausgefuehrt. Das spart Minuten.

### Schritt 2: .dockerignore erstellen

```
__pycache__/
*.pyc
.env
.git/
.venv/
*.wav
*.mp3
wandb/
```

Ohne .dockerignore kopiert Docker euer ganzes .git-Verzeichnis und alle Audio-Dateien
in den Container. Das macht das Image unnoetig gross.

### Schritt 3: Health Check Endpoint in FastAPI

Falls ihr noch keinen habt, fuegt diesen Endpoint zu eurer FastAPI-App hinzu:

```python
from fastapi import FastAPI
from datetime import datetime
import os

app = FastAPI(title="Voice Agent API")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("APP_VERSION", "0.1.0"),
        "services": {
            "stt": "whisper-loaded",
            "tts": "speecht5-loaded",
            "llm": "claude-connected"
        }
    }
```

**Warum ein Health Check?** Jede Deployment-Plattform (Railway, AWS, Kubernetes) prueft
diesen Endpoint regelmaessig. Wenn er nicht 200 zurueckgibt, wird der Container neu gestartet.
Das ist kein Nice-to-have — das ist Standard in Production.

### Schritt 4: Lokal testen

```bash
# Image bauen
docker build -t voice-agent .

# Container starten
docker run -p 8000:8000 --env-file .env voice-agent

# In einem zweiten Terminal testen
curl http://localhost:8000/health
```

Wenn der Health Check `{"status": "healthy"}` zurueckgibt: Bronze erledigt.

---

## SILVER — docker-compose.yml + Environment Management

### Schritt 5: docker-compose.yml erstellen

```yaml
version: "3.8"

services:
  voice-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - APP_VERSION=0.1.0
      - LOG_LEVEL=info
      - MAX_AUDIO_LENGTH_SECONDS=30
      - TTS_MODEL=speecht5
      - STT_MODEL=whisper-small
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Optional: Falls ihr Redis fuer Session-Management nutzt
  # redis:
  #   image: redis:7-alpine
  #   ports:
  #     - "6379:6379"
```

### Schritt 6: .env.example aktualisieren

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-xxxxx

# App Config
APP_VERSION=0.1.0
LOG_LEVEL=info

# Voice Config
MAX_AUDIO_LENGTH_SECONDS=30
TTS_MODEL=speecht5
STT_MODEL=whisper-small

# Optional
HUGGINGFACE_TOKEN=hf_xxxxx
```

**Wichtig:** Die .env.example hat Platzhalter-Werte. Die echte .env steht in .gitignore.
Das ist nicht optional — ein geleakter API-Key kostet echtes Geld.

### Schritt 7: Testen mit docker-compose

```bash
docker compose up --build
```

Wenn alles startet und der Health Check gruen ist: Silver erledigt.

---

## GOLD — Railway Deployment + Live URL

### Schritt 8: Railway Setup

1. Geht zu [railway.app](https://railway.app) und loggt euch mit GitHub ein
2. "New Project" -> "Deploy from GitHub Repo"
3. Waehlt euer Voice-Agent-Repo aus
4. Railway erkennt das Dockerfile automatisch

### Schritt 9: Environment Variables in Railway setzen

Im Railway Dashboard:
- Klickt auf euren Service
- Tab "Variables"
- Fuegt alle Variablen aus .env.example hinzu (mit echten Werten)

**ANTHROPIC_API_KEY** muss gesetzt sein, sonst crashed der Container beim Start.

### Schritt 10: Domain zuweisen

- Tab "Settings" -> "Networking" -> "Generate Domain"
- Railway gibt euch eine URL wie: `voice-agent-production.up.railway.app`

### Schritt 11: Deployment verifizieren

```bash
# Health Check gegen die Live-URL
curl https://euer-service.up.railway.app/health

# Voice Agent testen (falls ihr einen Text-Endpoint habt)
curl -X POST https://euer-service.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hallo, wie geht es dir?"}'
```

Wenn der Health Check auf der Railway-URL funktioniert: Gold erledigt.

### Schritt 12: README aktualisieren

Fuegt einen Deployment-Abschnitt zu eurer README.md hinzu:

```markdown
## Deployment

### Live Demo
[voice-agent.up.railway.app](https://voice-agent.up.railway.app)

### Local Development
```bash
git clone https://github.com/EUER-NAME/voice-agent.git
cd voice-agent
cp .env.example .env
# Fill in your API keys in .env
docker compose up --build
```

### Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| ANTHROPIC_API_KEY | Claude API key | Yes |
| TTS_MODEL | TTS model to use (speecht5/bark) | No |
| STT_MODEL | STT model to use (whisper-small/whisper-base) | No |
```

---

## DIAMOND — Graceful Shutdown + Structured Logging

### Schritt 13: Graceful Shutdown implementieren

Wenn Railway einen Container stoppt (bei Redeployment), schickt es SIGTERM.
Euer Server muss laufende Requests fertig bearbeiten, bevor er sich beendet.

```python
import signal
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Globaler State fuer aktive Requests
active_requests = 0
shutting_down = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Voice Agent starting up...")
    # Modelle laden
    load_whisper_model()
    load_tts_model()
    print("All models loaded.")

    yield

    # Shutdown
    global shutting_down
    shutting_down = True
    print(f"Shutting down. Waiting for {active_requests} active requests...")

    # Maximal 30 Sekunden warten
    for _ in range(30):
        if active_requests == 0:
            break
        await asyncio.sleep(1)

    print("Shutdown complete.")

app = FastAPI(title="Voice Agent API", lifespan=lifespan)

@app.middleware("http")
async def track_requests(request, call_next):
    global active_requests
    if shutting_down:
        return JSONResponse(
            status_code=503,
            content={"error": "Server is shutting down"}
        )
    active_requests += 1
    try:
        response = await call_next(request)
        return response
    finally:
        active_requests -= 1
```

### Schritt 14: Structured Logging

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
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

# Logger konfigurieren
logger = logging.getLogger("voice_agent")
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Verwendung
logger.info("STT processing started", extra={"request_id": "abc-123"})
```

**Warum JSON-Logs?** Railway, Datadog, Grafana — alle Log-Aggregatoren parsen JSON automatisch.
Plain-Text-Logs muss man mit Regex parsen. Das macht niemand freiwillig.

Wenn Graceful Shutdown und Structured Logging implementiert sind: Diamond erledigt.

---

## Abgabe-Checkliste

Bevor ihr um 12:00 in die Lecture kommt, prueft:

### Dennis — Deployment-Checkliste
- [ ] Dockerfile existiert und baut erfolgreich
- [ ] docker-compose.yml existiert und startet den Service
- [ ] Health Check Endpoint gibt 200 zurueck
- [ ] .env.example ist vollstaendig
- [ ] .dockerignore ist vorhanden
- [ ] (Gold) Live-URL auf Railway funktioniert
- [ ] (Diamond) Graceful Shutdown + JSON Logging implementiert
- [ ] Alles committet und gepusht

### Sebastian — Code-Implementierung-Checkliste
- [ ] FastAPI-App laeuft lokal (uvicorn main:app)
- [ ] Mindestens ein funktionierender Endpoint (z.B. /health, /analyze, /confidence)
- [ ] Confidence Scoring Logik ist als Code implementiert (auch als Prototyp)
- [ ] ARCHITECTURE.md ist im Repo und beschreibt, was implementiert ist vs. was geplant ist
- [ ] requirements.txt und .env.example sind vorhanden
- [ ] Alles committet und gepusht
- [ ] (Bonus) Dockerfile erstellt
- [ ] (Bonus) Deployment auf Railway

---

## Troubleshooting

**Docker Build schlaegt fehl wegen ffmpeg:**
-> `apt-get install -y ffmpeg` muss VOR `pip install` kommen.

**Container startet, aber Health Check failed:**
-> Start-Period pruefen. Whisper-Modell braucht Zeit zum Laden. `start_period: 60s` setzen.

**Railway zeigt "Build Failed":**
-> Prueft die Build-Logs im Dashboard. Meistens fehlt eine System-Dependency im Dockerfile.

**Port-Fehler auf Railway:**
-> Railway setzt die PORT-Variable automatisch. Aendert euren CMD zu:
```dockerfile
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

**Audio-Files zu gross fuer Railway Free Tier:**
-> Speichert keine Audio-Dateien permanent. Streamt sie oder loescht sie nach Verarbeitung.
