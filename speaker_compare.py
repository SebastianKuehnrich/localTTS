"""
Teil 2: Speaker Embedding Vergleich
Vergleicht 5 verschiedene Speaker Embeddings mit SpeechT5 — ohne datasets-Library.
Die Embeddings werden direkt per huggingface_hub als Parquet geladen.
"""

import sys

try:
    from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
    import torch
    import soundfile as sf
    import numpy as np
    import requests  # fuer Parquet-Download
    import pandas as pd
except ImportError as e:
    print(f"Fehlende Abhaengigkeit: {e}")
    print("Installiere mit: pip install transformers torch soundfile numpy huggingface_hub pandas pyarrow")
    sys.exit(1)


PARQUET_URL = "https://huggingface.co/api/datasets/Matthijs/cmu-arctic-xvectors/parquet/default/validation/0.parquet"


def load_xvectors_from_parquet() -> pd.DataFrame:
    """Laedt die Speaker-Embeddings direkt aus der Parquet-Datei (ohne datasets-Library)."""
    df = pd.read_parquet(PARQUET_URL)
    return df


def main():
    print("Lade Modelle...")
    processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
    model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
    vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")

    print("Lade Speaker-Embeddings (Parquet)...")
    df = load_xvectors_from_parquet()
    total_speakers = len(df)
    print(f"{total_speakers} Speaker-Embeddings geladen.\n")

    text = "This is a test of different speaker voices using the same model."
    inputs = processor(text=text, return_tensors="pt")

    # 5 verschiedene Stimmen — Indizes an Datensatzgroesse anpassen
    speaker_ids = [0, 100, 3000, 5000, 7306]
    speaker_ids = [sid for sid in speaker_ids if sid < total_speakers]

    if not speaker_ids:
        print("FEHLER: Keine gueltigen Speaker-IDs gefunden.")
        sys.exit(1)

    for sid in speaker_ids:
        xvector = df.iloc[sid]["xvector"]
        speaker_emb = torch.tensor(xvector, dtype=torch.float32).unsqueeze(0)

        speech = model.generate_speech(inputs["input_ids"], speaker_emb, vocoder=vocoder)

        if speech.numel() == 0:
            print(f"WARNUNG: Speaker {sid} hat leeres Audio erzeugt — uebersprungen.")
            continue

        filename = f"speaker_{sid}.wav"
        sf.write(filename, speech.numpy(), samplerate=16000)
        print(f"Speaker {sid}: {filename}")

    print("\nHoert euch alle 5 an.")
    print("Gleicher Text, gleiches Modell, verschiedene Speaker Embeddings.")
    print("Der Embedding-Vektor (512 Dimensionen) kodiert NUR die Stimme.")
    print("Er veraendert den Decoder-Zustand -> anderer Query in Cross-Attention -> anderer Sound.")


if __name__ == "__main__":
    main()
