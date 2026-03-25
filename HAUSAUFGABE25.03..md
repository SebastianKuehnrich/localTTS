# HAUSAUFGABE — Mittwoch 25.03.2026
# Advanced Group: Dennis & Sebastian
# Abgabe: Donnerstag 26.03.2026 vor Unterrichtsbeginn

---

## Was ihr heute gemacht habt

| Was | Architektur |
|---|---|
| Whisper STT (Audio → Text) | Encoder-Decoder |
| Claude Agent (Text → Text) | Decoder-Only |
| OpenAI TTS (Text → Audio) | Encoder-Decoder (vermutlich) |
| Voice Loop (alles zusammen) | Pipeline: 3 Modelle orchestriert |
| Streaming TTS (Satz fuer Satz) | SSE + Satzende-Erkennung |

---

## Teil 1: Streaming in euren Voice Agent einbauen (45 min)

Ersetzt die `think()` + `speak()` Kombination in eurem `main.py` durch die Streaming-Version die wir zusammen geschrieben haben.

**VORHER (euer main.py):**
```python
agent_text = think(user_text, history)
speak(agent_text)
```

**NACHHER:**
```python
agent_text = stream_and_speak(user_text, history)
```

Die `stream_and_speak` Funktion aus der Lecture:

```python
def stream_and_speak(user_input: str, history: list) -> str:
    history.append({"role": "user", "content": user_input})

    current_sentence = ""
    full_response = ""

    with claude_client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system="Du bist ein hilfreicher Sprachassistent. Antworte kurz auf Deutsch. Maximal 3 Saetze.",
        messages=history
    ) as stream:
        for text in stream.text_stream:
            current_sentence += text
            full_response += text
            print(text, end="", flush=True)

            if text.rstrip().endswith((".", "!", "?")):
                speak(current_sentence.strip())
                current_sentence = ""

    if current_sentence.strip():
        speak(current_sentence.strip())

    history.append({"role": "assistant", "content": full_response})
    return full_response
```

### Was ihr testen muesst

- [ ] Agent streamt Text in die Konsole (Wort fuer Wort sichtbar)
- [ ] Nach jedem Satz wird Audio abgespielt
- [ ] Bei langen Antworten: erster Satz kommt DEUTLICH schneller als vorher
- [ ] History funktioniert noch (Folgefragen beziehen sich auf vorherige)
- [ ] Stop-Wort beendet die Schleife sauber

---

## Teil 2: ARCHITECTURE.md erweitern (30 min)

Fuegt zwei neue Abschnitte zu eurem ARCHITECTURE.md hinzu:

### Abschnitt: Pipeline vs End-to-End

Halbe Seite. Beantwortet:

1. Euer System ist eine Pipeline (Whisper → Claude → TTS). Was sind die Vorteile gegenueber einem End-to-End Modell das Audio direkt zu Audio verarbeitet?

2. Was sind die Nachteile eurer Pipeline? (Latenz, Kosten, Komplexitaet)

3. Wann wuerdet ihr eine Pipeline empfehlen und wann End-to-End?

4. GPT-4o hat einen Voice Mode der Audio-zu-Audio macht. Warum hat Anthropic das (noch) nicht? Was wuerde sich in eurem Code aendern wenn Claude direkt Audio verstehen koennte?

### Abschnitt: Streaming Architektur

Erklaert in eigenen Worten:

1. Was ist der Unterschied zwischen `client.messages.create()` und `client.messages.stream()`?

2. Warum benutzt die API SSE (Server-Sent Events) und nicht WebSocket?

3. Was ist ein Generator in Python und warum ist `stream.text_stream` einer?

4. Warum braucht man `with ... as` beim Streaming? Was passiert ohne?

---

## Teil 3: Timing + Observability (30 min)

Messt wie lange jede Stufe eurer Pipeline braucht:

```python
import time

# In main.py:
t_start = time.time()

# STT
t_stt_start = time.time()
user_text = listen(duration=5)
t_stt = time.time() - t_stt_start

# LLM
t_llm_start = time.time()
agent_text = stream_and_speak(user_text, history)
t_llm = time.time() - t_llm_start

# Gesamtzeit
t_total = time.time() - t_start

print(f"\n[Timing] STT: {t_stt:.1f}s | LLM+TTS: {t_llm:.1f}s | Total: {t_total:.1f}s")
```

Fuehrt 5 Gespraeche und notiert die Zeiten. Erstellt eine Tabelle:

```markdown
## Latenz-Analyse

| Austausch | STT (s) | LLM+TTS (s) | Total (s) | Antwortlaenge |
|-----------|---------|-------------|-----------|---------------|
| 1         |         |             |           |               |
| 2         |         |             |           |               |
| 3         |         |             |           |               |
| 4         |         |             |           |               |
| 5         |         |             |           |               |
| **Schnitt** |       |             |           |               |
```

Fuegt die Tabelle in ARCHITECTURE.md unter "Latenz-Analyse" ein.

---

## Teil 4: GitHub Push

- [ ] Streaming funktioniert in main.py
- [ ] ARCHITECTURE.md hat 3 neue Abschnitte (Pipeline vs E2E, Streaming, Latenz)
- [ ] Saubere Commits (nicht alles in einem)
- [ ] Keine API Keys im Repo
- [ ] README aktualisiert (Streaming erwaehnen)

---

## Ressourcen

- Anthropic Streaming Docs: https://docs.anthropic.com/en/api/streaming
- Anthropic Python SDK Streaming: https://docs.anthropic.com/en/api/client-sdks/python#streaming
- OpenAI Realtime API (End-to-End Voice): https://platform.openai.com/docs/guides/realtime
- LiveKit (Open Source Voice Infra): https://livekit.io/
- Python Context Manager (with/as): https://docs.python.org/3/reference/compound_stmts.html#the-with-statement
- Python Generators: https://docs.python.org/3/howto/functional.html#generators
- Server-Sent Events (MDN): https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

---

*Abgabe: Donnerstag 26.03.2026 vor Unterrichtsbeginn. Repo-Link per Slack.*
