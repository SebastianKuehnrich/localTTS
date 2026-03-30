# PROJEKT — Advanced Track | Montag 30.03.2026
# 11:30 – 13:00 (90 Minuten)
# Dennis | Sebastian | [Neuer Student falls Advanced]

---

## Lecture-Repo mit allen Code-Beispielen

**https://github.com/OthmanAdi/context-engineering-lecture**

Dort findet ihr alle Dateien aus der Lecture:
- `01_naive_context.ts` — der naive Ansatz (was Dennis bisher hat)
- `02_sliding_window.ts` — Sliding Context Window (was ihr heute einbaut)
- `03_context_hub.ts` — ContextHub: welche Dateien bei welchem Task
- `04_claude_md_example.md` — CLAUDE.md Vorlage
- `05_spec_example.md` — Spec-Vorlage

Klont das Repo, wenn ihr den Code direkt als Referenz wollt:

```bash
git clone https://github.com/OthmanAdi/context-engineering-lecture.git
```

---

## Was ihr gerade gelernt habt

- **Context Engineering** — vier Strategien: Write, Select, Compress, Isolate
- **Das Problem:** Naive `conversation_history` als wachsende Liste → Token-Explosion
- **Die Lösung:** Sliding Context Window (alte Messages zusammenfassen, neue behalten)
- **Context Hub:** Deklarativ bestimmen, welche Dateien für welchen Task relevant sind
- **CLAUDE.md:** Projekt-Context als Datei — jede AI (Claude Code, OpenCode, Cursor) liest sie
- **Spec-Driven Development:** Erst Spec schreiben, dann prompen → SPECTRE Workflow

---

## Was ihr jetzt tut

Ihr baut Context Engineering in EUER Projekt ein.
- **Dennis:** Voice Agent (Python, FastAPI, Railway)
- **Sebastian:** CORTANA/COGITO (Architektur + Dokumentation)

Bronze ist Pflicht. Silver baut direkt auf dem Lecture-Code auf. Gold ist die Herausforderung.

Ich bin ab 11:30 in einem Meeting. Alles steht hier. Um 13:00 treffen wir uns wieder und ihr zeigt was ihr gebaut habt.

---

## BRONZE — Pflicht (ca. 30 Min)

### Aufgabe: CLAUDE.md für euer Projekt schreiben

Ohne CLAUDE.md kommt ihr nicht in den Review um 13:00. Das ist Pflicht.

In der Lecture habt ihr gesehen, warum das wichtig ist: Eine CLAUDE.md ist wie ein Onboarding-Dokument für die AI. Jedes AI-Tool (Claude Code, OpenCode, Cursor) liest diese Datei automatisch und versteht danach euer Projekt.

Im Lecture-Repo: `04_claude_md_example.md` als Vorlage.

---

**Dennis — CLAUDE.md für deinen Voice Agent:**

Erstelle `CLAUDE.md` im Root deines Voice-Agent-Repos. Öffne parallel deine Dateien und beschreibe was WIRKLICH da ist:

```markdown
# CLAUDE.md

## Projekt
Voice Agent — Sprachbasierter Assistent mit Whisper STT, Claude LLM, OpenAI TTS.
Deployed auf Railway: [DEINE RAILWAY URL HIER]

## Stack
- Python 3.12
- FastAPI (Web-Framework)
- Docker + docker-compose
- Anthropic SDK (Claude claude-sonnet-4-20250514 für Chat + Streaming)
- OpenAI SDK (Whisper für STT, TTS für Sprachausgabe)
- Railway (Cloud Deployment)

## Architektur
User → /chat oder /stream Endpoint
     → agent.py: think() Funktion → Claude API Call
     → Response zurück an User

User → /chat-with-voice Endpoint
     → agent.py: think() → Text-Response
     → OpenAI TTS → Audio als Base64
     → Response mit Text + Audio

## Dateien (öffne deinen Ordner und prüfe!)
- `server.py` — FastAPI Server mit allen Endpoints
- `agent.py` — think() Funktion, Claude API Call
- `Dockerfile` — Container-Definition
- `docker-compose.yml` — Lokale Entwicklung
- `requirements.txt` — Python Dependencies
- `.env.example` — Template für Environment Variables
- `ARCHITECTURE.md` — Architektur-Dokumentation
- [LISTE ALLE WEITEREN DATEIEN DIE DU HAST]

## Endpoints
| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| /health | GET | Status + Uptime |
| /chat | POST | Text rein → Claude Antwort raus |
| /voices | GET | Verfügbare TTS-Stimmen |
| /chat-with-voice | POST | Text rein → Antwort + Audio raus |
| /stream | POST | SSE Streaming, Token für Token |
| /logs | GET | Letzte 20 Requests mit Timing |

## Environment Variables
| Variable | Wofür | Wo gesetzt |
|----------|-------|-----------|
| ANTHROPIC_API_KEY | Claude API | Railway + .env lokal |
| OPENAI_API_KEY | Whisper + TTS | Railway + .env lokal |
| ENVIRONMENT | dev/production | Railway |
| PORT | Server-Port | Railway (automatisch) |

## Bekannte Einschränkungen
- conversation_history ist eine einfache Liste (wächst endlos → Token-Problem)
  [DAS FIXST DU IN SILVER]
- [Was funktioniert noch nicht? Sei ehrlich]
- [Welche Endpoints sind instabil?]

## Code-Konventionen
- Python Type Hints verwenden
- Docstrings für Funktionen
- Keine API Keys im Code (nur .env)
- Kein print() — nutze Python logging
```

---

**Sebastian — CLAUDE.md für CORTANA/COGITO:**

```markdown
# CLAUDE.md

## Projekt
CORTANA/COGITO — Intelligentes Assistenz-System mit Confidence-basierter
Eskalation und modularer Architektur.

## Status — EHRLICH
### Was als CODE existiert:
- [Liste alle .py oder .ts Dateien die tatsächlich laufen]
- [Fine-Tuning Code aus Woche 1?]
- [Evaluation Code aus Woche 2?]
- [FastAPI-Grundgerüst falls vorhanden?]

### Was als DOKUMENTATION existiert:
- ARCHITECTURE.md — Gesamtarchitektur
- EVAL_RESULTS.md — Evaluationsergebnisse
- TECH_STACK.md — Technologieentscheidungen

## Architektur-Entscheidungen
- WARUM zwei Systeme (CORTANA + COGITO)?
- WARUM Confidence Scoring?
- WARUM Jetson als Hardware-Target?
- Welche Alternativen wurden verworfen und warum?

## Confidence System
- Wie wird der Score berechnet?
- Welche Schwellenwerte gibt es? (z.B. >0.8 = antworten, <0.5 = eskalieren)
- Woran misst sich "Confidence"? (Source Count? Retrieval Relevance? Modell-Certainty?)

## Auth Design
- Token-basiert oder Session-basiert?
- Token Lifetime?
- Wie wird revoked?

## Bekannte Einschränkungen
- [Was ist nur Design, was ist tatsächlich implementiert?]
- [Der ehrlichste Abschnitt. Recruiter respektieren Ehrlichkeit mehr als Übertreibung.]
```

---

**Checkliste Bronze:**
- [ ] CLAUDE.md existiert im Repo-Root
- [ ] Ich habe meine echten Dateien geöffnet und geprüft (nicht geraten)
- [ ] Stack und Architektur sind korrekt beschrieben
- [ ] Bekannte Einschränkungen ehrlich dokumentiert
- [ ] Auf GitHub gepusht: `git add CLAUDE.md && git commit -m "docs: add CLAUDE.md" && git push`

**Bronze fertig → weiter zu Silver.**

---

## SILVER — Empfohlen (ca. 30 Min)

### Aufgabe: Context Engineering einbauen

In der Lecture habt ihr gesehen: `01_naive_context.ts` vs `02_sliding_window.ts`. Der naive Ansatz (einfache Liste) vs. Sliding Window (zusammenfassen + letzte N behalten).

---

**Dennis — Sliding Context Window in Python:**

Dein `conversation_history = []` in `server.py` ist genau das Problem aus `01_naive_context.ts`. Jetzt fixst du es.

**Schritt 1:** Erstelle die Datei `sliding_window.py` in deinem Voice-Agent-Repo:

```python
"""sliding_window.py — Sliding Context Window für den Voice Agent.

Ersetzt die naive conversation_history Liste.
Statt alle Messages endlos zu sammeln:
- Die letzten N Messages werden immer behalten
- Ältere Messages werden zu einer Zusammenfassung komprimiert
- Token-Kosten bleiben stabil, Information bleibt erhalten
"""

import anthropic
from datetime import datetime

client = anthropic.Anthropic()


class SlidingContextWindow:
    def __init__(self, max_recent: int = 10, summary_threshold: int = 20):
        """
        Args:
            max_recent: Wie viele aktuelle Messages immer behalten werden.
            summary_threshold: Ab wie vielen Messages die älteren zusammengefasst werden.
        """
        self.full_history: list[dict] = []
        self.summary: str = ""
        self.max_recent = max_recent
        self.summary_threshold = summary_threshold

    def add_message(self, role: str, content: str) -> None:
        """Fügt eine neue Message zur History hinzu."""
        self.full_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

    def build_context(self) -> tuple[str, list[dict]]:
        """Baut den optimierten Context.

        Returns:
            Tuple von (system_context_string, recent_messages_list)
            - system_context: Zusammenfassung der älteren Messages (leer wenn keine)
            - recent_messages: Die letzten N Messages im Claude-API-Format
        """
        # Ab Threshold: ältere Messages zusammenfassen
        if len(self.full_history) > self.summary_threshold and not self.summary:
            older = self.full_history[:-self.max_recent]
            self.summary = self._summarize(older)
            print(f"[SlidingWindow] {len(older)} Messages zusammengefasst → Summary")

        system_context = ""
        if self.summary:
            system_context = f"Bisheriges Gespräch (Zusammenfassung):\n{self.summary}"

        recent = [
            {"role": m["role"], "content": m["content"]}
            for m in self.full_history[-self.max_recent:]
        ]

        return system_context, recent

    def _summarize(self, messages: list[dict]) -> str:
        """Fasst ältere Messages zu einer Zusammenfassung zusammen."""
        formatted = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=(
                "Fasse das folgende Gespräch zusammen. "
                "Behalte: wichtige Entscheidungen, offene Fragen, key Facts. "
                "Maximal 200 Wörter."
            ),
            messages=[{"role": "user", "content": formatted}],
        )

        if response.content and response.content[0].type == "text":
            return response.content[0].text
        return ""

    def get_stats(self) -> dict:
        """Gibt Statistiken über den aktuellen Window-Zustand zurück."""
        return {
            "total_messages": len(self.full_history),
            "in_context": min(len(self.full_history), self.max_recent),
            "has_summary": bool(self.summary),
        }

    def reset(self) -> None:
        """Setzt den Window zurück (z.B. bei neuer Session)."""
        self.full_history = []
        self.summary = ""
```

**Schritt 2:** Ändere deinen `server.py` — ersetze die naive Liste:

```python
# ALT (lösche oder kommentiere aus):
# conversation_history = []

# NEU:
from sliding_window import SlidingContextWindow

context_window = SlidingContextWindow(max_recent=10, summary_threshold=20)
```

**Schritt 3:** Ändere deinen `/chat` Endpoint:

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Message hinzufügen
    context_window.add_message("user", req.message)

    # Context bauen (mit Zusammenfassung falls vorhanden)
    system_context, recent_messages = context_window.build_context()

    # System Prompt + optionale Zusammenfassung
    system_prompt = "Du bist ein hilfreicher deutscher Assistent. Antworte kurz und präzise."
    if system_context:
        system_prompt += f"\n\n{system_context}"

    # Claude API Call mit optimiertem Context
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=system_prompt,
        messages=recent_messages,
    )

    assistant_text = response.content[0].text
    context_window.add_message("assistant", assistant_text)

    stats = context_window.get_stats()
    return ChatResponse(
        response=assistant_text,
        history_length=stats["total_messages"],
    )
```

**Schritt 4:** Teste lokal:

```bash
# Server starten
python server.py

# 5 Requests schicken und beobachten ob Tokens stabil bleiben:
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "Hallo"}'
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "Was ist Docker?"}'
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "Erkläre mir FastAPI"}'
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "Was ist SSE?"}'
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "Wie funktioniert TTS?"}'
```

**Schritt 5:** Committen und pushen:

```bash
git add sliding_window.py server.py
git commit -m "feat: replace naive history with SlidingContextWindow"
git push
```

---

**Sebastian — Context Engineering Spec für CORTANA/COGITO:**

Du hast kein laufendes System. Du hast ein Architektur-Design. Deine Aufgabe: Wende die vier Strategien aus der Lecture auf dein System-Design an.

Erstelle `specs/CONTEXT_ENGINEERING_SPEC.md` in deinem Repo:

```markdown
# Spec: Context Engineering für CORTANA/COGITO

## Zusammenfassung
Diese Spec definiert, wie die vier Context Engineering Strategien
(Write, Select, Compress, Isolate) im CORTANA/COGITO System eingesetzt werden.

---

## 1. WRITE Context — Was wird persistiert?

### CORTANA (Frontend-Agent)
- [Welche Informationen schreibt CORTANA in ein Scratchpad?]
- [Zum Beispiel: letzte 5 User-Anfragen, aktive Session-Daten, User-Präferenzen]

### COGITO (Backend/Knowledge-Agent)
- [Wie führt COGITO seinen State?]
- [Zum Beispiel: Retrieval-Ergebnisse, Confidence-Scores pro Quelle, Entscheidungslog]

---

## 2. SELECT Context — Was wird wann geladen?

### Context-Regeln (wie der ContextHub aus der Lecture)

| User fragt über... | CORTANA lädt... | COGITO lädt... |
|--------------------|-----------------|----------------|
| [Thema 1] | [welche Wissensquellen?] | [welche Module?] |
| [Thema 2] | [...] | [...] |
| [Unbekanntes Thema] | [...] | [...] |

### Was NIEMALS geladen wird:
- [Sensible Daten?]
- [Zu große Dateien?]
- [Veraltete Quellen?]

---

## 3. COMPRESS Context — Wie wird gekürzt?

- Maximale Context-Größe pro Request: [wie viele Tokens?]
- Conversation-History: [Sliding Window? Ab wann zusammenfassen?]
- Retrieval-Ergebnisse: [Wie viele Chunks maximal?]
- Was passiert wenn der Context trotzdem zu groß ist? [Priorisierung?]

---

## 4. ISOLATE Context — Wie werden Sub-Tasks verteilt?

### Aufgabenverteilung

| Task | Wer bearbeitet es? | Eigener Context? |
|------|-------------------|-----------------|
| User-Anfrage verstehen | CORTANA | Ja — nur Conversation + User Profile |
| Wissen abrufen | COGITO | Ja — nur Knowledge Base + Retrieval |
| Confidence berechnen | [CORTANA oder COGITO?] | [Welcher Context?] |
| Eskalation entscheiden | [Wer?] | [Welcher Context?] |

### Context-Isolation zwischen CORTANA und COGITO
- Was sieht CORTANA, was COGITO NICHT sieht?
- Was sieht COGITO, was CORTANA NICHT sieht?
- Wo überschneiden sich die Contexts?

---

## 5. Verbindung zum Confidence System

- Wie beeinflusst die Menge an Context den Confidence Score?
  [Mehr relevanter Context → höhere Confidence?]
  [Zu viel Context → niedrigere Confidence wegen Noise?]
- Ab welchem Confidence-Wert antwortet das System direkt?
- Ab welchem Wert wird eskaliert?
- Gibt es ein "ich weiß nicht genug" Signal?
```

**Checkliste Silver:**
- [ ] Dennis: `sliding_window.py` existiert und importiert ohne Fehler
- [ ] Dennis: `server.py` benutzt SlidingContextWindow statt `conversation_history = []`
- [ ] Dennis: Lokal getestet mit mindestens 5 curl-Requests
- [ ] Dennis: Auf GitHub gepusht
- [ ] Sebastian: `specs/CONTEXT_ENGINEERING_SPEC.md` ist vollständig geschrieben
- [ ] Sebastian: Alle 4 Strategien sind auf CORTANA/COGITO angewandt
- [ ] Sebastian: Verbindung zum Confidence System hergestellt
- [ ] Sebastian: Auf GitHub gepusht

---

## GOLD — Herausforderung (ca. 30 Min)

### Aufgabe: Context Hub für euer Projekt

In der Lecture habt ihr `03_context_hub.ts` gesehen. Jetzt baut ihr das für euer eigenes Projekt.

---

**Dennis — Python ContextHub:**

Erstelle `context_hub.py` in deinem Voice-Agent-Repo:

```python
"""context_hub.py — Deklarativer Context Manager für den Voice Agent.

Entscheidet basierend auf der User-Frage, welche Dateien relevant sind.
Inspiriert vom ContextHub-Pattern aus der Lecture (03_context_hub.ts).
"""

import re


class ContextHub:
    def __init__(
        self,
        always_include: list[str],
        rules: list[dict],
        exclude_patterns: list[str],
    ):
        self.always_include = always_include
        self.rules = rules
        self.exclude_patterns = [re.compile(p) for p in exclude_patterns]

    def resolve(self, task: str) -> list[str]:
        """Gibt die Liste relevanter Dateien für einen Task zurück."""
        files = set(self.always_include)

        for rule in self.rules:
            if re.search(rule["trigger"], task, re.IGNORECASE):
                files.update(rule["files"])

        return [
            f for f in files
            if not any(p.search(f) for p in self.exclude_patterns)
        ]


# Konfiguration für DEINEN Voice Agent
# PASSE DIE DATEINAMEN AN DEIN REPO AN!
voice_hub = ContextHub(
    always_include=["agent.py", "server.py", "requirements.txt"],
    rules=[
        {
            "trigger": r"tts|voice|audio|speech|stimme|sprechen",
            "files": ["tts_handler.py", "streaming_voice.py"],
        },
        {
            "trigger": r"whisper|stt|transkription|sprache.zu.text|mikrofon",
            "files": ["whisper_handler.py", "audio_utils.py"],
        },
        {
            "trigger": r"deploy|docker|railway|server|container",
            "files": ["Dockerfile", "docker-compose.yml", ".env.example"],
        },
        {
            "trigger": r"stream|sse|echtzeit|live",
            "files": ["server.py", "streaming_voice.py"],
        },
        {
            "trigger": r"history|kontext|context|memory|gespräch",
            "files": ["sliding_window.py"],
        },
    ],
    exclude_patterns=[r"\.env$", r"__pycache__", r"\.git"],
)


if __name__ == "__main__":
    # Tests — führe dieses File direkt aus: python context_hub.py
    test_queries = [
        "TTS Audio Bug fixen",
        "Railway Deployment ist kaputt",
        "Whisper erkennt keine Sprache",
        "SSE Streaming bricht ab",
        "Conversation History wird zu lang",
    ]

    for query in test_queries:
        result = voice_hub.resolve(query)
        print(f"Query: '{query}'")
        print(f"  → Dateien: {result}")
        print()
```

**Teste es:**

```bash
python context_hub.py
```

Du solltest sehen, dass verschiedene Queries verschiedene Dateien zurückgeben.

**Optional — Integration in agent.py:**

```python
from context_hub import voice_hub

def build_system_prompt(user_message: str) -> str:
    """Baut einen System-Prompt basierend auf den relevanten Dateien."""
    relevant_files = voice_hub.resolve(user_message)
    file_context = "\n".join(f"- {f}" for f in relevant_files)
    return f"""Du bist ein Voice Agent Assistent.

Relevante Dateien für diese Frage:
{file_context}

Antworte basierend auf dem Kontext dieser Dateien."""
```

---

**Sebastian — ContextHub als YAML-Config:**

Erstelle `specs/CONTEXT_HUB_CONFIG.yml` in deinem Repo:

```yaml
# cortana_context_hub.yml
# ContextHub-Konfiguration für CORTANA/COGITO
# Definiert welche Wissensquellen bei welcher User-Anfrage geladen werden.

name: cortana-cogito
description: Intelligentes Assistenz-System mit Confidence Scoring

# Diese Dateien werden IMMER geladen
always_include:
  - ARCHITECTURE.md
  - src/types.ts
  - src/config.ts

# Regeln: Trigger → Dateien + Mindest-Confidence
rules:
  medical_queries:
    trigger: "medizin|gesundheit|symptom|diagnose|arzt"
    files:
      - knowledge/medical_base.md
      - src/confidence/medical_scorer.ts
    min_confidence: 0.8
    note: "Medizinische Fragen brauchen hohe Confidence wegen Verantwortung"

  legal_queries:
    trigger: "recht|gesetz|vertrag|klage|anwalt"
    files:
      - knowledge/legal_base.md
      - src/confidence/legal_scorer.ts
    min_confidence: 0.9
    note: "Rechtliche Fragen brauchen höchste Confidence"

  technical_queries:
    trigger: "code|bug|error|server|deploy|api"
    files:
      - knowledge/tech_base.md
      - src/confidence/tech_scorer.ts
    min_confidence: 0.6
    note: "Technische Fragen sind weniger riskant — niedrigerer Threshold"

  general_queries:
    trigger: ".*"
    files:
      - knowledge/general_base.md
    min_confidence: 0.5
    note: "Fallback für alles was keiner Regel entspricht"

# Diese Dateien werden NIEMALS in den Context geladen
exclude:
  - "**/*.env"
  - "**/secrets/**"
  - "**/test_data/**"
  - "**/node_modules/**"

# Eskalations-Logik
escalation:
  below_min_confidence: "route_to_human"
  no_matching_rule: "use_general_with_disclaimer"
  multiple_rules_match: "use_highest_min_confidence"
```

**Checkliste Gold:**
- [ ] Dennis: `context_hub.py` existiert und funktioniert standalone (`python context_hub.py`)
- [ ] Dennis: 5 verschiedene Queries getestet → verschiedene Dateien geladen
- [ ] Dennis: Auf GitHub gepusht
- [ ] Sebastian: `specs/CONTEXT_HUB_CONFIG.yml` ist vollständig
- [ ] Sebastian: `min_confidence` für jede Regel definiert und begründet
- [ ] Sebastian: Escalation-Logik ist definiert
- [ ] Sebastian: Auf GitHub gepusht

---

## DIAMOND — Extra (falls Zeit)

### Aufgabe: Spec für euer nächstes Feature + SPECTRE-Workflow

Schreibt eine Spec für ein Feature, das euer Projekt noch NICHT hat:

**Dennis:** z.B. "Rate Limiting für /chat Endpoint" oder "Conversation Reset Endpoint"
**Sebastian:** z.B. "Prototyp: FastAPI Endpoint der eine Frage entgegennimmt und einen Confidence Score zurückgibt"

Durchlauft alle 7 SPECTRE-Schritte und dokumentiert sie (wie im Lecture-Repo `05_spec_example.md`).

**Warum das für eure Karriere zählt:**

Context Engineering + Spec-Driven Development sind 2026 die Skills, die AI Engineers von Prompt-Kopierern unterscheiden:
- AI Engineer mit Agent-Erfahrung (DACH): 85–130k EUR
- Senior AI Engineer mit Context Engineering + Evaluation: 100–160k EUR
- Freelance-Tagessatz für Agent-Architektur: 1.200–2.000 EUR/Tag

---

## Abgabe um 13:00

| Tier | Was muss fertig sein |
|------|---------------------|
| **Bronze (Pflicht)** | CLAUDE.md im Repo, auf GitHub |
| **Silver** | + SlidingContextWindow (Dennis) / Context Engineering Spec (Sebastian) |
| **Gold** | + ContextHub (Dennis) / YAML-Config (Sebastian) |
| **Diamond** | + eigene Spec mit SPECTRE-Workflow |

**Um 13:00 treffen wir uns. Bildschirm teilen, Code zeigen, Entscheidungen erklären.**
