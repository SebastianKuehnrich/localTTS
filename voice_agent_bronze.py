"""
BRONZE: Record + Transcribe.
Nimmt Audio per Mikrofon auf und transkribiert es mit OpenAI Whisper.
"""

import sys
import os

import numpy as np
import sounddevice as sd
import soundfile as sf


# ── Konstanten ──────────────────────────────────────────────
SAMPLE_RATE = 16000
DURATION_SECONDS = 5
RECORDING_PATH = "input.wav"


def check_requirements() -> None:
    """Prueft API-Key und Mikrofon."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("FEHLER: OPENAI_API_KEY nicht gesetzt.")
        print("Setze die Variable: export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    try:
        default_input = sd.query_devices(kind="input")
        print(f"Mikrofon: {default_input['name']}")
    except sd.PortAudioError:
        print("FEHLER: Kein Mikrofon gefunden.")
        sys.exit(1)


def record_audio(duration: int = DURATION_SECONDS, sample_rate: int = SAMPLE_RATE) -> str:
    """Nimmt Audio vom Mikrofon auf und speichert als WAV."""
    print(f"Sprich jetzt... ({duration} Sekunden)")
    try:
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()
    except sd.PortAudioError as e:
        print(f"FEHLER bei Aufnahme: {e}")
        sys.exit(1)

    peak = np.max(np.abs(audio))
    if peak < 0.01:
        print("WARNUNG: Aufnahme sehr leise. Mikrofon stumm geschaltet?")

    sf.write(RECORDING_PATH, audio, sample_rate)
    print("Aufnahme gespeichert.")
    return RECORDING_PATH


def transcribe(filepath: str) -> str:
    """Transkribiert eine Audio-Datei via OpenAI Whisper API."""
    from openai import OpenAI

    client = OpenAI()

    with open(filepath, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="de",
        )
    return result.text


def main() -> None:
    print("=== Bronze: Record + Transcribe ===\n")

    check_requirements()

    filepath = record_audio()
    text = transcribe(filepath)

    print(f"\nDu hast gesagt: {text}")


if __name__ == "__main__":
    main()
