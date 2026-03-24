# localTTS — Text-to-Speech Vergleich

Vergleich verschiedener TTS-Architekturen: **SpeechT5** (Encoder-Decoder), **Bark** (Decoder-Only) und **OpenAI TTS** (API).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install transformers torch soundfile scipy numpy sentencepiece pandas pyarrow librosa matplotlib
```

## Skripte

| Datei | Beschreibung |
|---|---|
| `main.py` | SpeechT5 Basis-TTS (Hello World) |
| `bark_tts.py` | Bark TTS — Deutsch, Englisch, kreativ (mit Lachen/Seufzen) |
| `speaker_compare.py` | 5 verschiedene Speaker Embeddings im Vergleich |
| `mel_visualize.py` | Mel-Spectrogram + Wellenform Visualisierung |
| `tts_benchmark.py` | Benchmark: OpenAI vs SpeechT5 vs Bark (Latenz, Kosten) |

## Ausfuehrung

```bash
python main.py              # Basis-TTS
python bark_tts.py          # Bark (Deutsch/Englisch/Kreativ)
python speaker_compare.py   # Speaker-Vergleich
python mel_visualize.py     # Mel-Spectrogram plotten
python tts_benchmark.py     # Benchmark aller drei Modelle
```

## Architektur

Siehe [TTS_ARCHITECTURES.md](TTS_ARCHITECTURES.md) fuer detaillierte Architektur-Vergleiche, Pipeline-Diagramme und Erklaerungen.

## Modelle

- **SpeechT5** — Encoder-Decoder mit Cross-Attention + HiFi-GAN Vocoder
- **Bark** — 3x Decoder-Only (Semantic → Coarse → Fine), kein separater Vocoder
- **OpenAI TTS** — Closed-Source API (optional, braucht `OPENAI_API_KEY`)
