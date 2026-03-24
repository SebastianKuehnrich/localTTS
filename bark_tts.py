"""
Teil 1: Bark — Decoder-Only TTS
Generiert Deutsch, Englisch und kreatives Audio mit Bark.
"""

import sys
import time

try:
    from transformers import AutoProcessor, BarkModel
    import scipy.io.wavfile
except ImportError as e:
    print(f"Fehlende Abhaengigkeit: {e}")
    print("Installiere mit: pip install transformers scipy")
    sys.exit(1)


def generate_audio(model, processor, text: str, voice_preset: str, filename: str) -> float:
    """Generiert Audio und speichert als WAV. Gibt die Dauer in Sekunden zurueck."""
    inputs = processor(text, voice_preset=voice_preset)

    start = time.time()
    audio = model.generate(**inputs)
    duration = time.time() - start

    audio_np = audio.cpu().numpy().squeeze()

    if audio_np.size == 0:
        print(f"WARNUNG: Leeres Audio fuer '{filename}' — uebersprungen.")
        return duration

    scipy.io.wavfile.write(filename, rate=24000, data=audio_np)
    print(f"Gespeichert: {filename} ({duration:.1f}s Generierung)")
    return duration


def main():
    print("Lade Bark-Modell (kann beim ersten Mal dauern)...")
    processor = AutoProcessor.from_pretrained("suno/bark-small")
    model = BarkModel.from_pretrained("suno/bark-small")
    print("Modell geladen.\n")

    # --- Test 1: Deutsch ---
    generate_audio(
        model, processor,
        text="Hallo, ich bin ein KI-Agent und ich lerne gerade Text-to-Speech.",
        voice_preset="v2/de_speaker_3",
        filename="bark_deutsch.wav",
    )

    # --- Test 2: Englisch ---
    generate_audio(
        model, processor,
        text="Hello, I am an AI agent and I am learning text to speech.",
        voice_preset="v2/en_speaker_6",
        filename="bark_english.wav",
    )

    # --- Test 3: Kreativ (Bark kann lachen!) ---
    generate_audio(
        model, processor,
        text="Das ist witzig! [laughs] Nein, wirklich. [sighs] Okay, zurueck zur Arbeit.",
        voice_preset="v2/de_speaker_5",
        filename="bark_creative.wav",
    )

    print("\nHoert euch alle drei Dateien an.")
    print("Bark kann [laughs], [sighs], [clears throat], [gasps] und Musik.")
    print("Das kann SpeechT5 NICHT — weil SpeechT5 nur Mel-Spectrograms fuer Sprache generiert.")
    print("Bark generiert allgemeine Audio-Tokens, nicht nur Sprache.")


if __name__ == "__main__":
    main()
