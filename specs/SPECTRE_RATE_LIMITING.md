# SPECTRE Spec: Rate Limiting fuer Voice Agent API

## S — Situation (Was ist der aktuelle Zustand?)

Der Voice Agent laeuft auf Railway ohne jegliches Rate Limiting.
Jeder kann unbegrenzt Requests an `/chat`, `/stream`, `/chat-with-voice` senden.

**Probleme:**
- Ein einzelner Client kann die API ueberlasten (DoS)
- Claude API Kosten sind nicht gedeckelt ($3/1M Input Tokens)
- OpenAI TTS Kosten sind nicht gedeckelt ($15/1M Zeichen)
- Kein Schutz gegen API-Key-Missbrauch wenn URL bekannt ist

## P — Problem (Was genau soll geloest werden?)

Es braucht ein Rate Limiting das:
1. Requests pro IP/Client begrenzt (z.B. 10 Requests/Minute)
2. Token-Kosten pro Session begrenzt (z.B. 5000 Tokens/Stunde)
3. Bei Ueberschreitung sinnvolle Fehlermeldungen liefert (429 Too Many Requests)
4. Health Check und statische Dateien nicht begrenzt

## E — Evidence (Was wissen wir?)

- Railway hat kein eingebautes Rate Limiting
- FastAPI hat `slowapi` (basiert auf Flask-Limiter) als gaengige Loesung
- In-Memory Rate Limiting reicht fuer einen einzelnen Container
- Redis waere noetig fuer Multi-Container (nicht unser Use Case)
- Aktuelle Request-Frequenz: ~5-20 Requests/Tag (Demo-Traffic)

## C — Constraints (Was sind die Einschraenkungen?)

- Kein Redis verfuegbar (Railway Free Tier)
- In-Memory Storage geht bei Container-Restart verloren (akzeptabel)
- Health Check muss immer erreichbar bleiben (Docker HEALTHCHECK)
- Kein User-Management vorhanden (nur IP-basiert moeglich)

## T — Technical Design (Wie wird es gebaut?)

### Implementierung mit slowapi

```python
# In requirements.txt ergaenzen:
# slowapi>=0.1.9

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Auf Endpoints anwenden:
@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, chat_req: ChatRequest):
    ...

@app.post("/chat-with-voice")
@limiter.limit("5/minute")   # Teurer wegen TTS
async def chat_with_voice(request: Request, chat_req: ChatWithVoiceRequest):
    ...

# Health Check OHNE Limit:
@app.get("/health")
async def health():
    ...
```

### Rate Limits pro Endpoint

| Endpoint | Limit | Begruendung |
|----------|-------|-------------|
| /chat | 10/min | Standard-Chat, moderate Kosten |
| /chat/stream | 10/min | Gleich wie /chat |
| /stream | 10/min | Alias fuer /chat/stream |
| /chat-with-voice | 5/min | Teuer (Claude + TTS) |
| /analyze | 10/min | Gleich wie /chat |
| /stt | 5/min | Audio-Upload, CPU-intensiv |
| /tts | 10/min | Nur TTS, moderate Kosten |
| /health | kein Limit | Monitoring muss immer funktionieren |
| /voices | kein Limit | Nur statische Daten |
| /logs | kein Limit | Nur lesen |
| /context | kein Limit | Nur lesen |

### Response bei Ueberschreitung

```json
{
    "error": "Rate limit exceeded",
    "detail": "10 per 1 minute",
    "retry_after": 42
}
```

HTTP Status: 429 Too Many Requests
Header: `Retry-After: 42`

## R — Risks (Was kann schiefgehen?)

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Legitime User werden geblockt | Niedrig | Mittel | Grosszuegige Limits (10/min reicht fuer Demo) |
| IP-Spoofing umgeht Limit | Niedrig | Niedrig | Railway Proxy liefert echte IP |
| Container-Restart loescht Limits | Mittel | Niedrig | Akzeptabel fuer Demo/Schulung |
| Shared IP (NAT) blockt mehrere User | Niedrig | Mittel | Limit pro IP hoch genug setzen |

## E — Execution Plan (Wie wird umgesetzt?)

1. `pip install slowapi` + requirements.txt ergaenzen
2. Limiter in app.py initialisieren (vor den Endpoints)
3. Rate Limits auf alle kostenintensiven Endpoints setzen
4. 429-Error-Handler registrieren
5. Lokal testen mit `curl` in schneller Folge
6. Docker Image neu bauen
7. Push zu GitHub + Railway Redeploy
8. Verifizieren dass Health Check weiter funktioniert

### Geschaetzter Aufwand: 30 Minuten
### Abhaengigkeiten: slowapi Paket
### Breaking Changes: Keine (nur neues Verhalten bei Ueberlast)
