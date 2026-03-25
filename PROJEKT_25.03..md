# Projekt: Full Voice Conversation Agent -- Whisper STT + Agent + TTS

**Datum:** Mittwoch, 25.03.2026
**Zeit:** 09:00 - 12:00 (3 Stunden)
**Modus:** Selbststaendige Arbeit -- ihr arbeitet ALLEIN
**Treffpunkt:** Um 12:00 treffen wir uns im Zoom-Raum. Bringt eine lauffaehige Demo mit.

---

## Was ihr heute baut

Gestern habt ihr TTS gebaut: Text rein, Audio raus.
Heute baut ihr die UMKEHRUNG: Audio rein, Text raus (Whisper STT).
Dann verbindet ihr beides zu einem vollstaendigen Voice Agent:

```
User spricht --> [Whisper STT] --> Text --> [Claude Agent] --> Text --> [TTS] --> Agent spricht zurueck
```

Das ist eine Pipeline aus DREI verschiedenen Architekturen:
- Whisper: Encoder-Decoder (Audio --> Text)
- Claude: Decoder-Only (Text --> Text)
- SpeechT5/Bark: Encoder-Decoder bzw. Decoder-Only (Text --> Audio)

---

## Setup

```bash
pip install sounddevice soundfile openai anthropic transformers torch numpy librosa
```

Testet, dass euer Mikrofon funktioniert:

```python
import sounddevice as sd
print(sd.query_devices())
```

Falls kein Input-Device angezeigt wird: Systemeinstellungen pruefen, Mikrofon-Zugriff erlauben.

---

## Teil 1: Homework Review (09:00 - 09:15)

Checkt eure Dienstag-Homework. Jeder fuer sich, ehrlich:

| Aufgabe | Erledigt? | Notizen |
|---------|-----------|---------|
| Bark TTS (Decoder-Only) laeuft | | |
| Speaker Embedding Vergleich (5 Stimmen) | | |
| Mel-Spectrogram Visualisierung mit librosa | | |
| OpenAI vs SpeechT5 vs Bark Benchmark | | |
| TTS_ARCHITECTURES.md geschrieben | | |

Was NICHT fertig ist, wird HEUTE ABEND nachgeholt. Kein Aufschub.

Bereitet eine kurze Demo vor (2-3 Minuten pro Person), die ihr um 12:00 zeigt.

---

## Teil 2: Whisper STT -- Die Umkehrung von TTS (09:15 - 10:00)

### Theorie: Warum Whisper das Spiegelbild von TTS ist

Gestern habt ihr gelernt:

```
TTS:  Text ----> [Encoder] ----> [Decoder] ----> Audio
                                  ^
                                  | Cross-Attention: Decoder schaut auf Text-Features
```

Heute das Gegenstueck:

```
STT:  Audio ----> [Encoder] ----> [Decoder] ----> Text
                                   ^
                                   | Cross-Attention: Decoder schaut auf Audio-Features
```

Die Architektur ist IDENTISCH -- nur die Richtung ist umgedreht.

### Der Mel-Spectrogram-Zusammenhang

Erinnert euch: Gestern habt ihr Mel-Spectrograms VISUALISIERT -- die Ausgabe eures TTS-Systems.
Genau dieses Format ist die EINGABE fuer Whisper.

```
TTS Output:  Text --> ... --> Mel-Spectrogram --> Vocoder --> WAV-Datei
Whisper Input: WAV-Datei --> Mel-Spectrogram --> Encoder --> Decoder --> Text
```

Das Mel-Spectrogram ist die Bruecke zwischen beiden Welten. Whisper konvertiert das Audio
zurueck in ein 80-Kanal Mel-Spectrogram (30 Sekunden Fenster) und fuettert es in den Encoder.

### Cross-Attention in Whisper

Beim TTS (SpeechT5) hat der Decoder auf Text-Features geschaut, um Audio-Tokens zu generieren.
Bei Whisper schaut der Decoder auf Audio-Features, um Text-Tokens zu generieren.

Gleicher Mechanismus, umgekehrte Daten:
- SpeechT5 Cross-Attention: Query=Audio-Position, Key/Value=Text-Features
- Whisper Cross-Attention: Query=Text-Position, Key/Value=Audio-Features

### Praktisch: Zwei Ansaetze

Ihr implementiert BEIDE Ansaetze und vergleicht sie -- genau wie gestern mit TTS.

**Ansatz A: OpenAI Whisper API (Cloud, bezahlt, einfach)**

```python
from openai import OpenAI
import time

client = OpenAI()

start = time.time()
with open("audio.wav", "rb") as f:
    result = client.audio.transcriptions.create(
        model="whisper-1",
        file=f,
        language="de"
    )
elapsed = time.time() - start

print(f"Transkription: {result.text}")
print(f"Dauer: {elapsed:.2f}s")
```

**Ansatz B: HuggingFace Whisper (lokal, kostenlos, langsamer)**

```python
from transformers import pipeline
import time

transcriber = pipeline(
    "automatic-speech-recognition",
    model="openai/whisper-small",
    device="cpu"  # oder "cuda" falls GPU vorhanden
)

start = time.time()
result = transcriber("audio.wav")
elapsed = time.time() - start

print(f"Transkription: {result['text']}")
print(f"Dauer: {elapsed:.2f}s")
```

**Vergleichs-Aufgabe:**

Nehmt einen Satz auf (z.B. "Kuenstliche Intelligenz veraendert die Arbeitswelt"),
transkribiert ihn mit BEIDEN Ansaetzen, und notiert:

| Kriterium | OpenAI API | HuggingFace lokal |
|-----------|------------|-------------------|
| Geschwindigkeit | | |
| Genauigkeit (deutsch) | | |
| Genauigkeit (englisch) | | |
| Kosten | ~$0.006/min | kostenlos |
| Offline moeglich? | Nein | Ja |

Tipp: Testet auch mit englischen Saetzen. Whisper ist multilingual,
aber die Qualitaet variiert je nach Sprache und Modellgroesse.

---

## Teil 3: Voice Conversation Loop (10:00 - 11:30)

### Audio aufnehmen vom Mikrofon

Basis-Code fuer alle Tiers:

```python
import sounddevice as sd
import numpy as np
import soundfile as sf

def record_audio(duration: int = 5, sample_rate: int = 16000) -> str:
    """Nimmt Audio vom Mikrofon auf und speichert als WAV."""
    filepath = "input.wav"
    print(f"Sprich jetzt... ({duration} Sekunden)")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    sf.write(filepath, audio, sample_rate)
    print("Aufnahme gespeichert.")
    return filepath
```

---

### BRONZE: Record + Transcribe

Nimm Audio auf, transkribiere es mit Whisper, gib den Text aus.

```python
import sounddevice as sd
import soundfile as sf
from openai import OpenAI

client = OpenAI()

def record_audio(duration: int = 5, sample_rate: int = 16000) -> str:
    filepath = "input.wav"
    print(f"Sprich jetzt... ({duration} Sekunden)")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    sf.write(filepath, audio, sample_rate)
    print("Aufnahme gespeichert.")
    return filepath

def transcribe(filepath: str) -> str:
    with open(filepath, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="de"
        )
    return result.text

# --- Main ---
filepath = record_audio(duration=5)
text = transcribe(filepath)
print(f"\nDu hast gesagt: {text}")
```

**Erfolgskriterium:** Ihr sprecht einen Satz, und der korrekte Text erscheint in der Konsole.

---

### SILVER: Full Voice Loop -- Record + Whisper + Claude + TTS + Playback

Die komplette Schleife: User spricht, Agent antwortet mit Stimme.

```python
import sounddevice as sd
import soundfile as sf
import numpy as np
from openai import OpenAI
from anthropic import Anthropic
from pathlib import Path

openai_client = OpenAI()
anthropic_client = Anthropic()

def record_audio(duration: int = 5, sample_rate: int = 16000) -> str:
    filepath = "input.wav"
    print(f"\nSprich jetzt... ({duration} Sekunden)")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    sf.write(filepath, audio, sample_rate)
    return filepath

def transcribe(filepath: str) -> str:
    """Whisper STT: Audio --> Text"""
    with open(filepath, "rb") as f:
        result = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="de"
        )
    return result.text

def ask_agent(user_text: str, history: list) -> str:
    """Claude Agent: Text --> Text"""
    history.append({"role": "user", "content": user_text})

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system="Du bist ein hilfreicher Assistent. Antworte kurz und praezise auf Deutsch.",
        messages=history
    )

    assistant_text = response.content[0].text
    history.append({"role": "assistant", "content": assistant_text})
    return assistant_text

def speak(text: str) -> None:
    """TTS: Text --> Audio --> Playback"""
    response = openai_client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text
    )

    output_path = "response.wav"
    with open(output_path, "wb") as f:
        f.write(response.content)

    # Audio abspielen
    data, samplerate = sf.read(output_path)
    sd.play(data, samplerate)
    sd.wait()

# --- Main ---
print("=== Voice Conversation Agent ===")
print("Pipeline: Mikrofon --> Whisper(STT) --> Claude(Agent) --> TTS --> Lautsprecher\n")

conversation_history = []

filepath = record_audio(duration=5)

user_text = transcribe(filepath)
print(f"[USER]  {user_text}")

agent_text = ask_agent(user_text, conversation_history)
print(f"[AGENT] {agent_text}")

speak(agent_text)
print("\n[Fertig]")
```

**Erfolgskriterium:** Ihr stellt eine Frage per Sprache, und der Agent antwortet euch per Sprache.

---

### GOLD: Continuous Conversation Loop

Die Schleife laeuft weiter, bis der User "stop" sagt.

```python
import sounddevice as sd
import soundfile as sf
import numpy as np
from openai import OpenAI
from anthropic import Anthropic

openai_client = OpenAI()
anthropic_client = Anthropic()

def record_audio(duration: int = 5, sample_rate: int = 16000) -> str:
    filepath = "input.wav"
    print(f"\n--- Sprich jetzt... ({duration}s) ---")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    sf.write(filepath, audio, sample_rate)
    return filepath

def transcribe(filepath: str) -> str:
    with open(filepath, "rb") as f:
        result = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="de"
        )
    return result.text

def ask_agent(user_text: str, history: list) -> str:
    history.append({"role": "user", "content": user_text})
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system="Du bist ein hilfreicher Sprachassistent. Antworte kurz und praezise auf Deutsch. "
               "Halte deine Antworten unter 3 Saetzen, weil sie vorgelesen werden.",
        messages=history
    )
    assistant_text = response.content[0].text
    history.append({"role": "assistant", "content": assistant_text})
    return assistant_text

def speak(text: str) -> None:
    response = openai_client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text
    )
    with open("response.wav", "wb") as f:
        f.write(response.content)
    data, samplerate = sf.read("response.wav")
    sd.play(data, samplerate)
    sd.wait()

# --- Main Loop ---
print("=== Continuous Voice Agent ===")
print("Sage 'stop' oder 'ende' zum Beenden.\n")

conversation_history = []
running = True

while running:
    filepath = record_audio(duration=5)
    user_text = transcribe(filepath)
    print(f"[USER]  {user_text}")

    # Stop-Erkennung
    stop_words = ["stop", "stopp", "ende", "aufhoeren", "tschuess", "quit"]
    if any(word in user_text.lower() for word in stop_words):
        print("\n[Agent beendet. Tschuess!]")
        speak("Tschuess! Bis zum naechsten Mal.")
        running = False
        continue

    agent_text = ask_agent(user_text, conversation_history)
    print(f"[AGENT] {agent_text}")

    speak(agent_text)

print(f"\nGespräch beendet. {len(conversation_history) // 2} Austausche.")
```

**Erfolgskriterium:** Ihr fuehrt ein Gespraech mit mindestens 5 Hin-und-Her-Austauschen,
und der Agent erinnert sich an den Kontext (z.B. "Wie heisse ich?" nach einer Vorstellung).

---

### DIAMOND: Streaming TTS -- Satzweise Ausgabe

Statt auf die komplette Agent-Antwort zu warten, streamt ihr die Antwort
und sprecht jeden Satz einzeln aus, sobald er fertig ist.

Das Problem bei Silver/Gold: Bei langen Antworten wartet der User 5-10 Sekunden
auf die komplette Antwort + TTS-Generierung. Mit Streaming hoert er den ersten Satz
nach ~1 Sekunde.

```python
import sounddevice as sd
import soundfile as sf
import numpy as np
import re
import io
from openai import OpenAI
from anthropic import Anthropic

openai_client = OpenAI()
anthropic_client = Anthropic()

def record_audio(duration: int = 5, sample_rate: int = 16000) -> str:
    filepath = "input.wav"
    print(f"\n--- Sprich jetzt... ({duration}s) ---")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    sf.write(filepath, audio, sample_rate)
    return filepath

def transcribe(filepath: str) -> str:
    with open(filepath, "rb") as f:
        result = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="de"
        )
    return result.text

def speak_sentence(text: str) -> None:
    """Spricht einen einzelnen Satz aus."""
    if not text.strip():
        return
    response = openai_client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text.strip()
    )
    with open("chunk.wav", "wb") as f:
        f.write(response.content)
    data, samplerate = sf.read("chunk.wav")
    sd.play(data, samplerate)
    sd.wait()

def stream_agent_and_speak(user_text: str, history: list) -> str:
    """Streamt Claude-Antwort und spricht jeden Satz sofort aus."""
    history.append({"role": "user", "content": user_text})

    full_response = ""
    buffer = ""
    sentence_endings = re.compile(r'[.!?]\s')

    with anthropic_client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system="Du bist ein hilfreicher Sprachassistent. Antworte auf Deutsch.",
        messages=history
    ) as stream:
        for text_chunk in stream.text_stream:
            full_response += text_chunk
            buffer += text_chunk

            # Pruefe ob ein vollstaendiger Satz im Buffer ist
            match = sentence_endings.search(buffer)
            while match:
                # Satz extrahieren und sofort aussprechen
                sentence_end = match.end()
                sentence = buffer[:sentence_end].strip()
                buffer = buffer[sentence_end:]

                if sentence:
                    print(f"  [SPRICHT] {sentence}")
                    speak_sentence(sentence)

                match = sentence_endings.search(buffer)

    # Rest-Buffer aussprechen (letzter Satz ohne Punkt)
    if buffer.strip():
        print(f"  [SPRICHT] {buffer.strip()}")
        speak_sentence(buffer.strip())

    history.append({"role": "assistant", "content": full_response})
    return full_response

# --- Main Loop ---
print("=== Streaming Voice Agent (Diamond) ===")
print("Sage 'stop' zum Beenden.\n")

conversation_history = []
running = True

while running:
    filepath = record_audio(duration=5)
    user_text = transcribe(filepath)
    print(f"\n[USER] {user_text}")

    stop_words = ["stop", "stopp", "ende", "aufhoeren", "tschuess"]
    if any(word in user_text.lower() for word in stop_words):
        speak_sentence("Tschuess!")
        running = False
        continue

    print("[AGENT streamt...]")
    agent_text = stream_agent_and_speak(user_text, conversation_history)
    print(f"[AGENT komplett] {agent_text}")

print("\nGespräch beendet.")
```

**Erfolgskriterium:** Bei einer langen Agent-Antwort (3+ Saetze) beginnt die Sprachausgabe
BEVOR die komplette Antwort generiert ist. Messt die Zeit bis zum ersten hoerbaren Wort
und vergleicht mit der nicht-streamenden Version.

---

## Teil 4: Architecture Document Update (11:30 - 12:00)

Erweitert eure TTS_ARCHITECTURES.md um folgende Abschnitte:

### 1. Whisper Architektur-Diagramm

```
WHISPER (Encoder-Decoder, Speech-to-Text)

Audio-Datei (WAV/MP3)
    |
    v
[Mel-Spectrogram Extraktion]   <-- 80 Frequency Bins, 30s Fenster
    |
    v
[Encoder: 12x Transformer Blocks]
    |  - Self-Attention auf Audio-Features
    |  - Lernt akustische Repraesentationen
    v
Audio-Features (Kontext-Vektoren)
    |
    v
[Decoder: 12x Transformer Blocks]
    |  - Self-Attention auf bisherige Text-Tokens
    |  - Cross-Attention auf Audio-Features   <-- Decoder "hoert" das Audio
    |  - Generiert Text Token fuer Token
    v
Text-Ausgabe ("Hallo, wie geht es dir?")
```

### 2. Mel-Spectrogram als Bruecke

Dokumentiert, wie das Mel-Spectrogram in BEIDEN Richtungen vorkommt:

```
TTS-Ausgang:     Text --> Encoder --> Decoder --> [MEL-SPECTROGRAM] --> Vocoder --> Audio
                                                        |
                                                   SELBES FORMAT
                                                        |
Whisper-Eingang: Audio --> [MEL-SPECTROGRAM] --> Encoder --> Decoder --> Text
```

### 3. Vollstaendige Voice-Pipeline

```
FULL VOICE CONVERSATION PIPELINE
=================================

Mikrofon
  |
  v
WAV Audio (16kHz, mono)
  |
  v
+------------------------------------------+
| WHISPER STT (Encoder-Decoder)            |
| Audio --> Mel-Spec --> Encoder --> Decoder|
| Output: Text                             |
+------------------------------------------+
  |
  v
User-Text ("Was ist Machine Learning?")
  |
  v
+------------------------------------------+
| CLAUDE AGENT (Decoder-Only)              |
| Text --> [Decoder Transformer Blocks]    |
| Autoregressive Token-Generierung         |
| Output: Text                             |
+------------------------------------------+
  |
  v
Agent-Text ("Machine Learning ist...")
  |
  v
+------------------------------------------+
| TTS ENGINE (Encoder-Decoder ODER         |
|             Decoder-Only)                |
| SpeechT5: Enc-Dec mit Cross-Attention    |
| Bark: Decoder-Only mit Audio-Tokens      |
| OpenAI TTS: API (Architektur unbekannt)  |
| Output: Audio                            |
+------------------------------------------+
  |
  v
Lautsprecher / Kopfhoerer
```

### 4. Drei Architekturen in einer Pipeline

Fuegt eine Tabelle hinzu:

| Komponente | Architektur | Input | Output | Cross-Attention? |
|------------|-------------|-------|--------|-------------------|
| Whisper | Encoder-Decoder | Audio (Mel-Spec) | Text-Tokens | Ja: Decoder auf Audio |
| Claude | Decoder-Only | Text-Tokens | Text-Tokens | Nein (nur Self-Attention) |
| SpeechT5 | Encoder-Decoder | Text-Tokens | Audio (Mel-Spec) | Ja: Decoder auf Text |
| Bark | Decoder-Only | Text+Audio-Tokens | Audio-Tokens | Nein (nur Self-Attention) |

---

## Haeufige Fehler

| Fehler | Ursache | Loesung |
|--------|---------|---------|
| `sounddevice.PortAudioError` | Kein Mikrofon gefunden | `sd.query_devices()` pruefen, richtiges Device setzen |
| `sf.write` erzeugt leere Datei | Mikrofon stumm geschaltet | Systemeinstellungen: Mikrofon-Pegel pruefen |
| Whisper gibt Unsinn aus | Zu kurze/leise Aufnahme | Mindestens 2s sprechen, `sample_rate=16000` nutzen |
| `anthropic.APIError` | Falscher API-Key | `ANTHROPIC_API_KEY` in Environment pruefen |
| TTS-Audio knackt/stottert | Sample-Rate Mismatch | Immer die Sample-Rate aus der Datei lesen mit `sf.read` |
| Streaming-Buffer haengt | Kein Satzzeichen in Antwort | Rest-Buffer am Ende aussprechen (siehe Diamond-Code) |
| Whisper erkennt falsche Sprache | `language` nicht gesetzt | Explizit `language="de"` uebergeben |
| `ModuleNotFoundError: sounddevice` | Nicht installiert | `pip install sounddevice soundfile` ausfuehren |

---

## Zeitplan Zusammenfassung

| Zeit | Block | Dauer |
|------|-------|-------|
| 09:00 - 09:15 | Homework Review + Demo vorbereiten | 15 min |
| 09:15 - 10:00 | Whisper STT Theorie + beide Ansaetze | 45 min |
| 10:00 - 10:30 | Bronze: Record + Transcribe | 30 min |
| 10:30 - 11:00 | Silver: Full Voice Loop | 30 min |
| 11:00 - 11:30 | Gold/Diamond: Continuous + Streaming | 30 min |
| 11:30 - 12:00 | Architecture Document Update | 30 min |
| 12:00 | Zoom-Raum: Demo + Besprechung | -- |

---

## Ressourcen

- Whisper auf HuggingFace: https://huggingface.co/openai/whisper-small
- OpenAI Whisper API: https://platform.openai.com/docs/guides/speech-to-text
- Whisper Paper: https://arxiv.org/abs/2212.04356
- sounddevice Docs: https://python-sounddevice.readthedocs.io/
- Anthropic Streaming: https://docs.anthropic.com/en/api/streaming

---

## Was ihr um 12:00 zeigen muesst

1. **Live-Demo:** Mindestens Silver (Full Voice Loop) -- ihr sprecht, der Agent antwortet per Stimme
2. **Vergleich:** OpenAI Whisper API vs. HuggingFace Whisper lokal (Tabelle mit Ergebnissen)
3. **TTS_ARCHITECTURES.md:** Erweitert mit Whisper-Diagramm und Full-Pipeline-Diagramm
4. **Bonus:** Gold oder Diamond lauffaehig zeigen
