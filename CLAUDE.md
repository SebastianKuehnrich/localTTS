# CLAUDE.md

## Projekt
Voice Agent — Sprachbasierter Assistent mit Whisper STT, Claude LLM, OpenAI TTS.
Deployed auf Railway: https://localtts-production.up.railway.app

## Stack
- Python 3.11 (Docker) / 3.12 (lokal)
- FastAPI (Web-Framework + API Server)
- Docker + docker-compose
- Anthropic SDK (Claude claude-sonnet-4-20250514 fuer Chat + Streaming)
- OpenAI SDK (Whisper API fuer STT, TTS fuer Sprachausgabe)
- HuggingFace Transformers (lokales Whisper-small, SpeechT5, Bark)
- Railway (Cloud Deployment)

## Architektur

### API-Pipeline (app.py)
```
User -> /chat oder /stream Endpoint
     -> Claude API Call (Streaming oder Standard)
     -> Confidence Scoring (confidence.py)
     -> Response zurueck an User (JSON oder SSE)
```

### Voice-Pipeline (main.py)
```
Mikrofon -> Whisper STT -> Claude Agent (Streaming)
         -> OpenAI TTS (satzweise) -> Lautsprecher
```

### Chat-with-Voice Pipeline
```
User -> /chat-with-voice Endpoint
     -> Claude API -> Text-Response
     -> OpenAI TTS -> Audio als Base64
     -> Response mit Text + Audio + Confidence
```

## Dateien

### Kern-Applikation
- `app.py` — FastAPI Server mit allen Endpoints (Health, Chat, Stream, Voice, STT, TTS, Logs)
- `confidence.py` — Confidence Scoring Modul (Hedging-Analyse, sprachliche Indikatoren)
- `sliding_window.py` — Sliding Context Window (ersetzt naive conversation_history)
- `context_hub.py` — Deklarativer Context Manager (welche Dateien bei welchem Task)

### Voice Agent Stufen
- `main.py` — Streaming Voice Agent mit Timing-Messung
- `voice_agent_bronze.py` — Bronze: Record + Transcribe (nur Whisper STT)
- `voice_agent_silver.py` — Silver: Full Voice Loop (ein Austausch)
- `voice_agent_gold.py` — Gold: Continuous Conversation (Endlos-Schleife)
- `voice_agent_diamond.py` — Diamond: Streaming TTS (satzweise Ausgabe)

### TTS/STT Vergleich
- `bark_tts.py` — Bark TTS (Deutsch, Englisch, kreativ)
- `speaker_compare.py` — 5 Speaker Embeddings im Vergleich
- `mel_visualize.py` — Mel-Spectrogram + Wellenform Visualisierung
- `tts_benchmark.py` — Benchmark: OpenAI vs SpeechT5 vs Bark
- `whisper_compare.py` — Whisper API vs HuggingFace lokal

### Infrastruktur
- `Dockerfile` — Container-Definition (python:3.11-slim + ffmpeg)
- `docker-compose.yml` — Lokale Entwicklung mit Health Check
- `requirements.txt` — Python Dependencies
- `.dockerignore` — Schuetzt .env und Audio-Dateien vor dem Image
- `.gitignore` — Standard Python + Audio + IDE

### Dokumentation
- `README.md` — Setup, Ausfuehrung, Endpoints
- `TTS_ARCHITECTURES.md` — Architektur-Vergleiche, Pipeline-Diagramme, Deployment

## Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| /health | GET | Status + Uptime + Services |
| /chat | POST | Text rein -> Claude Antwort + Confidence raus |
| /chat/stream | POST | SSE Streaming, Token fuer Token |
| /stream | POST | SSE Streaming (Alias) |
| /voices | GET | Verfuegbare TTS-Stimmen (6 Stimmen) |
| /chat-with-voice | POST | Chat + TTS mit Stimmenwahl (Base64 Audio) |
| /confidence | POST | Confidence-Analyse eines beliebigen Texts |
| /analyze | POST | CORTANA-Style Analyse mit Eskalations-Logik |
| /stt | POST | Speech-to-Text via Whisper (lokal oder API) |
| /tts | POST | Text-to-Speech via OpenAI TTS (Stimme waehlbar) |
| /logs | GET | Letzte 20 Requests mit Timing |
| /context | GET | Sliding Window Stats + ContextHub Info |

## Environment Variables

| Variable | Wofuer | Wo gesetzt |
|----------|-------|-----------|
| ANTHROPIC_API_KEY | Claude API | Railway + .env lokal |
| OPENAI_API_KEY | Whisper + TTS | Railway + .env lokal |
| ENVIRONMENT | development/production | Railway |
| PORT | Server-Port | Railway (automatisch) |
| CLAUDE_MODEL | Claude Modell (default: claude-sonnet-4-20250514) | Railway |
| STT_MODEL | whisper-small (lokal) oder whisper-api | Railway |
| LOG_LEVEL | debug/info/warning/error | Railway |
| TTS_VOICE | Default-Stimme (default: nova) | Railway |

## Context Engineering
- **SlidingContextWindow** (`sliding_window.py`): Ersetzt die naive `conversation_history = []`.
  Letzte 10 Messages werden behalten, aeltere zusammengefasst. Token-Kosten bleiben stabil.
- **ContextHub** (`context_hub.py`): Bestimmt deklarativ welche Dateien/Module fuer
  eine User-Anfrage relevant sind. Regelbasiert mit Regex-Triggern.

## Bekannte Einschraenkungen
- Conversation History ist jetzt SlidingWindow, aber nur serverseitig (kein Session-Management per User)
- Lokales Whisper-small ist langsamer als die API, aber kostenlos
- TTS braucht OpenAI API Key (kein lokales Fallback)
- Kein Rate Limiting implementiert
- Keine User-Authentifizierung

## Code-Konventionen
- Python Type Hints verwenden
- Docstrings fuer Funktionen
- Keine API Keys im Code (nur .env / Railway Variables)
- Structured JSON Logging (kein print())
- Defensive Coding: Input-Validierung, Error Handling, Graceful Shutdown
