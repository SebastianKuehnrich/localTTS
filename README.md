# localTTS — Voice Agent + TTS Vergleich

Full Voice Conversation Agent und Vergleich verschiedener TTS/STT-Architekturen:
**Whisper** (STT), **SpeechT5** (Encoder-Decoder), **Bark** (Decoder-Only), **OpenAI TTS** (API), **Claude** (Agent).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install transformers torch soundfile sounddevice scipy numpy sentencepiece pandas pyarrow librosa matplotlib openai anthropic requests
```

Umgebungsvariablen setzen (fuer Voice Agent und API-basierte Skripte):

```bash
set OPENAI_API_KEY=sk-...
set ANTHROPIC_API_KEY=sk-ant-...
```

## Skripte

### Voice Agent (Pipeline: Mikrofon → Whisper → Claude → TTS → Lautsprecher)

| Datei | Beschreibung |
|---|---|
| `main.py` | **Streaming Voice Agent** — Satzweise TTS-Ausgabe mit Timing-Messung |
| `voice_agent_bronze.py` | Bronze: Record + Transcribe (nur Whisper STT) |
| `voice_agent_silver.py` | Silver: Full Voice Loop (ein Austausch) |
| `voice_agent_gold.py` | Gold: Continuous Conversation (Endlos-Schleife) |
| `voice_agent_diamond.py` | Diamond: Streaming TTS (satzweise Ausgabe) |

### TTS Vergleich

| Datei | Beschreibung |
|---|---|
| `bark_tts.py` | Bark TTS — Deutsch, Englisch, kreativ (mit Lachen/Seufzen) |
| `speaker_compare.py` | 5 verschiedene Speaker Embeddings im Vergleich |
| `mel_visualize.py` | Mel-Spectrogram + Wellenform Visualisierung |
| `tts_benchmark.py` | Benchmark: OpenAI vs SpeechT5 vs Bark (Latenz, Kosten) |
| `whisper_compare.py` | Whisper Vergleich: OpenAI API vs HuggingFace lokal |

## Ausfuehrung

```bash
# Voice Agent (braucht Mikrofon + API Keys)
python main.py                # Streaming Voice Agent mit Timing

# TTS/STT Einzelskripte
python bark_tts.py            # Bark (Deutsch/Englisch/Kreativ)
python speaker_compare.py     # Speaker-Vergleich
python mel_visualize.py       # Mel-Spectrogram plotten
python tts_benchmark.py       # Benchmark aller drei Modelle
python whisper_compare.py     # Whisper API vs lokal
```

## Streaming

Der `main.py` Voice Agent nutzt **Streaming** fuer minimale Latenz:

```
User spricht -> Whisper(STT) -> Claude(Streaming) -> TTS(satzweise) -> Lautsprecher
```

Statt auf die komplette Agent-Antwort zu warten, wird jeder Satz sofort ausgesprochen
sobald er fertig generiert ist. Das reduziert die wahrgenommene Latenz bei langen
Antworten von ~4s auf ~1.5s bis zum ersten hoerbaren Satz.

## Architektur

Siehe [TTS_ARCHITECTURES.md](TTS_ARCHITECTURES.md) fuer:
- Pipeline-Diagramme (SpeechT5, Bark, Whisper, Full Voice Pipeline)
- Pipeline vs End-to-End Vergleich
- Streaming Architektur (SSE, Generatoren, Context Manager)
- Latenz-Analyse

## Modelle

- **Whisper** — Encoder-Decoder STT (Audio → Text), OpenAI API oder lokal via HuggingFace
- **Claude** — Decoder-Only LLM (Text → Text), Streaming via SSE
- **SpeechT5** — Encoder-Decoder TTS mit Cross-Attention + HiFi-GAN Vocoder
- **Bark** — 3x Decoder-Only (Semantic → Coarse → Fine), kein separater Vocoder
- **OpenAI TTS** — Closed-Source API (braucht `OPENAI_API_KEY`)
