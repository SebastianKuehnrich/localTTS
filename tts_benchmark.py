"""
Teil 4: TTS Benchmark — OpenAI vs SpeechT5 vs Bark
Vergleicht Latenz, Groesse, Kosten und Architektur.

Hinweis: OpenAI-Teil wird uebersprungen, wenn kein API-Key vorhanden ist.
"""

import sys
import time
import os

try:
    import torch
    import soundfile as sf
    import numpy as np
    import scipy.io.wavfile
    from transformers import (
        SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan,
        AutoProcessor, BarkModel,
    )
    import pandas as pd
except ImportError as e:
    print(f"Fehlende Abhaengigkeit: {e}")
    print("Installiere mit: pip install transformers torch soundfile scipy numpy huggingface_hub pandas pyarrow")
    sys.exit(1)


# Testtext — gleicher Text fuer alle drei
TEST_TEXT = "Machine Learning ist ein Teilgebiet der kuenstlichen Intelligenz. Neuronale Netze lernen Muster aus Daten."

results = []


def benchmark_openai():
    """OpenAI TTS — nur wenn API-Key vorhanden."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("[OpenAI] Uebersprungen — kein OPENAI_API_KEY gesetzt.")
        print("         Setze die Umgebungsvariable OPENAI_API_KEY, um diesen Test zu aktivieren.\n")
        return

    try:
        from openai import OpenAI
    except ImportError:
        print("[OpenAI] Uebersprungen — openai-Paket nicht installiert (pip install openai).\n")
        return

    client = OpenAI()

    start = time.time()
    response = client.audio.speech.create(model="tts-1", voice="nova", input=TEST_TEXT)
    response.stream_to_file("bench_openai.mp3")
    t_openai = time.time() - start

    size_openai = os.path.getsize("bench_openai.mp3")
    cost_openai = len(TEST_TEXT) * 0.015 / 1000
    results.append(("OpenAI tts-1", t_openai, size_openai, cost_openai, "Closed Source", "Unbekannt"))
    print(f"[OpenAI] Fertig: {t_openai:.1f}s\n")


def benchmark_speecht5():
    """SpeechT5 — Encoder-Decoder mit HiFi-GAN Vocoder."""
    print("[SpeechT5] Lade Modelle...")
    proc = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
    mdl = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
    voc = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")

    # Speaker-Embedding direkt aus Parquet laden (ohne datasets-Library)
    parquet_url = "https://huggingface.co/api/datasets/Matthijs/cmu-arctic-xvectors/parquet/default/validation/0.parquet"
    df = pd.read_parquet(parquet_url)

    idx = min(7306, len(df) - 1)
    xvector = df.iloc[idx]["xvector"]
    spk = torch.tensor(xvector, dtype=torch.float32).unsqueeze(0)

    start = time.time()
    inp = proc(text=TEST_TEXT, return_tensors="pt")
    speech = mdl.generate_speech(inp["input_ids"], spk, vocoder=voc)
    t_speecht5 = time.time() - start

    sf.write("bench_speecht5.wav", speech.numpy(), samplerate=16000)
    size_speecht5 = os.path.getsize("bench_speecht5.wav")
    results.append(("SpeechT5", t_speecht5, size_speecht5, 0.0, "Encoder-Decoder", "JA"))
    print(f"[SpeechT5] Fertig: {t_speecht5:.1f}s\n")


def benchmark_bark():
    """Bark — Decoder-Only TTS."""
    print("[Bark] Lade Modelle...")
    bproc = AutoProcessor.from_pretrained("suno/bark-small")
    bmdl = BarkModel.from_pretrained("suno/bark-small")

    start = time.time()
    binp = bproc(TEST_TEXT, voice_preset="v2/de_speaker_3")
    baudio = bmdl.generate(**binp).cpu().numpy().squeeze()
    t_bark = time.time() - start

    if baudio.size == 0:
        print("[Bark] WARNUNG: Leeres Audio generiert.")
        return

    scipy.io.wavfile.write("bench_bark.wav", rate=24000, data=baudio)
    size_bark = os.path.getsize("bench_bark.wav")
    results.append(("Bark", t_bark, size_bark, 0.0, "3x Decoder-Only", "NEIN"))
    print(f"[Bark] Fertig: {t_bark:.1f}s\n")


def print_results():
    """Gibt die Ergebnistabelle und Kostenrechnung aus."""
    if not results:
        print("Keine Ergebnisse vorhanden.")
        return

    print(f"\n{'Modell':<15} {'Latenz':<10} {'Groesse':<12} {'Kosten':<10} {'Architektur':<20} {'Cross-Att'}")
    print("=" * 85)
    for name, t, s, c, arch, ca in results:
        print(f"{name:<15} {t:.1f}s      {s/1024:.0f} KB       ${c:.4f}     {arch:<20} {ca}")

    # Kostenrechnung
    cost_openai = len(TEST_TEXT) * 0.015 / 1000
    print(f"\n--- Kosten fuer 10.000 Requests ---")
    print(f"OpenAI:   ${cost_openai * 10000:.2f}/Monat")
    print(f"SpeechT5: $0 (aber GPU-Server ~$50-150/Monat)")
    print(f"Bark:     $0 (aber GPU-Server ~$100-300/Monat, langsamer)")

    if cost_openai > 0:
        print(f"\nBreak-Even OpenAI vs Self-Hosted: ~{cost_openai * 10000 / 100:.0f} Monate bei $100/Monat GPU")


def main():
    print(f"Benchmark-Text ({len(TEST_TEXT)} Zeichen):")
    print(f'"{TEST_TEXT}"\n')

    benchmark_openai()
    benchmark_speecht5()
    benchmark_bark()
    print_results()


if __name__ == "__main__":
    main()
