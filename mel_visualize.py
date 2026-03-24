"""
Teil 3: Mel-Spectrogram Visualisierung
Plottet Wellenform und Mel-Spectrogram einer generierten Audio-Datei.
"""

import sys
import os

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interaktives Backend (kein GUI noetig)
    import matplotlib.pyplot as plt
    import numpy as np
    import librosa
    import librosa.display
except ImportError as e:
    print(f"Fehlende Abhaengigkeit: {e}")
    print("Installiere mit: pip install librosa matplotlib numpy")
    sys.exit(1)


# Moegliche Audio-Dateien (Fallback-Kette)
AUDIO_CANDIDATES = [
    "speaker_7306.wav",
    "speaker_5000.wav",
    "speaker_3000.wav",
    "speaker_0.wav",
    "output.wav",
    "bark_deutsch.wav",
]


def find_audio_file() -> str:
    """Sucht eine vorhandene Audio-Datei aus der Kandidatenliste."""
    for candidate in AUDIO_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    print("FEHLER: Keine Audio-Datei gefunden.")
    print(f"Erwartet: eine von {AUDIO_CANDIDATES}")
    print("Fuehre zuerst speaker_compare.py oder bark_tts.py aus.")
    sys.exit(1)


def main():
    audio_path = find_audio_file()
    print(f"Verwende Audio-Datei: {audio_path}")

    # --- Schritt 1: Audio laden ---
    audio, sr = librosa.load(audio_path, sr=16000)

    if len(audio) == 0:
        print("FEHLER: Audio-Datei ist leer.")
        sys.exit(1)

    print(f"Audio geladen: {len(audio)} Samples, {len(audio)/sr:.2f}s, {sr} Hz")

    # --- Schritt 2: Mel-Spectrogram berechnen ---
    mel_spec = librosa.feature.melspectrogram(
        y=audio,
        sr=sr,
        n_mels=80,       # 80 Frequenzbaender (Standard fuer TTS)
        n_fft=1024,       # FFT Fenstergroesse
        hop_length=256,   # Schrittweite zwischen Frames
    )

    # In Dezibel umrechnen (fuer bessere Visualisierung)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

    # --- Schritt 3: Plotten ---
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # Oben: Wellenform
    axes[0].set_title("Wellenform (Audio Signal)")
    librosa.display.waveshow(audio, sr=sr, ax=axes[0])
    axes[0].set_xlabel("Zeit (Sekunden)")
    axes[0].set_ylabel("Amplitude")

    # Unten: Mel-Spectrogram
    axes[1].set_title("Mel-Spectrogram (was der TTS-Decoder generiert)")
    img = librosa.display.specshow(
        mel_spec_db,
        x_axis="time",
        y_axis="mel",
        sr=sr,
        hop_length=256,
        ax=axes[1],
    )
    axes[1].set_xlabel("Zeit (Sekunden)")
    axes[1].set_ylabel("Frequenz (Mel)")
    fig.colorbar(img, ax=axes[1], format="%+2.0f dB")

    plt.tight_layout()

    output_path = "mel_spectrogram.png"
    plt.savefig(output_path, dpi=150)
    print(f"Gespeichert: {output_path}")

    # plt.show() — auskommentiert, da Agg-Backend keinen GUI-Output hat
    # Falls ihr das Bild sehen wollt, oeffnet mel_spectrogram.png manuell.


if __name__ == "__main__":
    main()
