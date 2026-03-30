# Spec: Context Engineering fuer Voice Agent / CORTANA

## Zusammenfassung

Diese Spec definiert, wie die vier Context Engineering Strategien
(Write, Select, Compress, Isolate) im Voice Agent System eingesetzt werden.

---

## 1. WRITE Context — Was wird persistiert?

### Voice Agent (API Server)
- **Conversation History:** Jede User-Message und Agent-Antwort wird im
  SlidingContextWindow gespeichert (`sliding_window.py`).
- **Request Logs:** Jeder API-Request wird mit Timing und Status geloggt
  (REQUEST_LOG in `app.py`, maximal 100 Eintraege).
- **Confidence Scores:** Jede Antwort bekommt einen Confidence Score,
  der zusammen mit der Antwort zurueckgegeben wird.

### CORTANA/COGITO (Confidence System)
- **Confidence History:** Pro Anfrage wird ein ConfidenceResult persistiert
  mit Score, Label, Hedging-Count und Details.
- **Eskalations-Log:** Wenn `require_high_confidence=True` und Score < 0.7,
  wird die Eskalation geloggt (Logger Warning).
- **Entscheidungslog:** Welche Anfragen direkt beantwortet vs. eskaliert wurden.

---

## 2. SELECT Context — Was wird wann geladen?

### Context-Regeln (ContextHub)

| User fragt ueber... | Geladene Module | Relevante Dateien |
|---------------------|-----------------|-------------------|
| TTS / Audio / Stimme | OpenAI TTS Client | `app.py` (TTS-Endpoints), Voices-Config |
| STT / Whisper / Transkription | Whisper Pipeline | `app.py` (STT-Endpoint) |
| Docker / Deploy / Railway | Infrastruktur-Config | `Dockerfile`, `docker-compose.yml` |
| Streaming / SSE | Anthropic Streaming | `app.py` (Stream-Endpoints) |
| History / Context / Memory | SlidingContextWindow | `sliding_window.py` |
| Confidence / Analyse | Confidence Modul | `confidence.py`, `/analyze` Endpoint |

### Was NIEMALS geladen wird:
- `.env`-Dateien (API Keys, Secrets)
- Audio-Dateien (`.wav`, `.mp3`) — nur Metadaten
- `__pycache__/` und temporaere Dateien
- Git-History und IDE-Konfiguration

---

## 3. COMPRESS Context — Wie wird gekuerzt?

### Conversation History: Sliding Window
- **max_recent = 10:** Die letzten 10 Messages werden immer vollstaendig behalten.
- **summary_threshold = 20:** Ab 20 Messages werden aeltere zusammengefasst.
- **Zusammenfassung:** Claude fasst aeltere Messages in max. 200 Woerter zusammen.
  Die Zusammenfassung wird in den System-Prompt eingefuegt.
- **Fallback:** Wenn die Zusammenfassung fehlschlaegt, werden die aeltesten Messages
  einfach verworfen (lieber Informationsverlust als Crash).

### Token-Budget pro Request
- System Prompt: ~100 Tokens (Basis) + ~200 Tokens (Zusammenfassung wenn vorhanden)
- Recent Messages: ~10 Messages x ~100 Tokens = ~1000 Tokens
- **Gesamt Input:** max ~1300 Tokens (statt unbegrenzt wachsend)
- **Output:** max 500 Tokens (max_tokens=500)

### Priorisierung bei Ueberlauf
1. System Prompt bleibt immer
2. Letzte 2 Messages (aktueller Turn) bleiben immer
3. Zusammenfassung wird gekuerzt (aeltere Teile verworfen)
4. Aeltere Recent Messages werden verworfen

---

## 4. ISOLATE Context — Wie werden Sub-Tasks verteilt?

### Aufgabenverteilung

| Task | Modul | Eigener Context? |
|------|-------|-----------------|
| User-Anfrage verstehen | `app.py` (/chat) | Ja — SlidingWindow + System Prompt |
| Antwort generieren | Anthropic API (Claude) | Ja — nur System + Recent Messages |
| Confidence berechnen | `confidence.py` | Ja — nur den Antwort-Text (kein API Call) |
| Eskalation entscheiden | `/analyze` Endpoint | Ja — Confidence Score + Threshold |
| Zusammenfassung erstellen | `sliding_window.py` | Ja — nur aeltere Messages |
| STT durchfuehren | `/stt` Endpoint | Ja — nur Audio-Datei |
| TTS generieren | `/tts` Endpoint | Ja — nur Text + Voice |

### Context-Isolation zwischen Modulen
- **Confidence Modul** sieht NUR den Antwort-Text — keine History, keinen System Prompt.
  Das ist gewollt: Confidence misst die Qualitaet der einzelnen Antwort.
- **SlidingWindow** sieht die volle History, aber NICHT die Confidence Scores.
  Die Zusammenfassung basiert nur auf dem Inhalt der Messages.
- **STT/TTS** sind zustandslos: Jeder Request ist unabhaengig. Kein Context noetig.

---

## 5. Verbindung zum Confidence System

### Wie Context die Confidence beeinflusst
- **Mehr relevanter Context (Zusammenfassung vorhanden):** Claude kann besser auf
  Vorantworten Bezug nehmen, gibt praezisere Antworten → hoehere Confidence.
- **Zu wenig Context (nach Reset):** Claude hat keinen Kontext, antwortet allgemeiner,
  nutzt mehr Hedging-Ausdruecke → niedrigere Confidence.
- **Zu viel Context (ohne SlidingWindow):** Token-Limit wird ueberschritten,
  Claude "vergisst" den Anfang des Gespraechs → inkonsistente Antworten.

### Schwellenwerte
| Confidence Score | Aktion |
|-----------------|--------|
| >= 0.7 (high) | Direkt antworten |
| 0.4 - 0.7 (medium) | Antworten mit Disclaimer |
| < 0.4 (low) | Eskalieren (Mensch pruefen) |

### "Ich weiss nicht genug" Signal
- Wenn `has_refusal=True` im ConfidenceResult: Das Modell hat explizit zugegeben,
  etwas nicht zu wissen. Score wird um -0.3 reduziert.
- Bei `/analyze` mit `require_high_confidence=True`: Automatische Eskalation.
