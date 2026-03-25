"""
Whisper STT Vergleich: OpenAI API vs. HuggingFace lokal.
Nimmt einen Satz per Mikrofon auf und transkribiert mit beiden Ansaetzen.
"""

import sys
import time
import os

import numpy as np
import sounddevice as sd
import soundfile as sf


# ── Konstanten ──────────────────────────────────────────────
SAMPLE_RATE = 16000
DURATION_SECONDS = 5
RECORDING_PATH = "test_recording.wav"


def check_microphone() -> None:
    """Prueft ob ein Mikrofon verfuegbar ist."""
    devices = sd.query_devices()
    input_devices = [d for d in devices if d["max_input_channels"] > 0]
    if not input_devices:
        print("FEHLER: Kein Mikrofon gefunden.")
        print("Verfuegbare Geraete:")
        print(devices)
        sys.exit(1)
    default = sd.query_devices(kind="input")
    print(f"Mikrofon: {default['name']} (Kanaele: {default['max_input_channels']})")


def record_audio(duration: int = DURATION_SECONDS, sample_rate: int = SAMPLE_RATE) -> str:
    """Nimmt Audio vom Mikrofon auf und speichert als WAV."""
    print(f"\nSprich jetzt... ({duration} Sekunden)")
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

    # Pruefen ob Aufnahme nicht leer/stumm ist
    peak = np.max(np.abs(audio))
    if peak < 0.01:
        print("WARNUNG: Aufnahme sehr leise. Mikrofon stumm geschaltet?")

    sf.write(RECORDING_PATH, audio, sample_rate)
    print(f"Aufnahme gespeichert: {RECORDING_PATH} (Peak: {peak:.4f})")
    return RECORDING_PATH


def transcribe_openai(filepath: str, language: str = "de") -> tuple[str, float]:
    """Transkription via OpenAI Whisper API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "FEHLER: OPENAI_API_KEY nicht gesetzt", 0.0

    from openai import OpenAI

    client = OpenAI()

    start = time.time()
    with open(filepath, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language=language,
        )
    elapsed = time.time() - start
    return result.text, elapsed


def transcribe_huggingface(filepath: str) -> tuple[str, float]:
    """Transkription via HuggingFace Whisper (lokal)."""
    from transformers import pipeline

    print("Lade HuggingFace Whisper-Modell (kann beim ersten Mal dauern)...")
    transcriber = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-small",
        device="cpu",
    )

    start = time.time()
    result = transcriber(filepath)
    elapsed = time.time() - start
    return result["text"], elapsed


def main() -> None:
    print("=== Whisper STT Vergleich ===\n")

    # Mikrofon pruefen
    check_microphone()

    # Audio aufnehmen
    filepath = record_audio()

    # ── Transkription mit beiden Ansaetzen ──
    results = {}

    # OpenAI API
    print("\n--- OpenAI Whisper API ---")
    text_api, time_api = transcribe_openai(filepath, language="de")
    results["OpenAI API"] = {"text": text_api, "time": time_api}
    print(f"Text:  {text_api}")
    print(f"Dauer: {time_api:.2f}s")

    # HuggingFace lokal
    print("\n--- HuggingFace Whisper (lokal) ---")
    text_hf, time_hf = transcribe_huggingface(filepath)
    results["HuggingFace lokal"] = {"text": text_hf, "time": time_hf}
    print(f"Text:  {text_hf}")
    print(f"Dauer: {time_hf:.2f}s")

    # ── Vergleichstabelle ──
    print("\n" + "=" * 60)
    print("VERGLEICH")
    print("=" * 60)
    print(f"{'Kriterium':<25} {'OpenAI API':<20} {'HuggingFace lokal':<20}")
    print("-" * 65)
    print(f"{'Geschwindigkeit':<25} {time_api:.2f}s{'':<15} {time_hf:.2f}s")
    print(f"{'Kosten':<25} {'~$0.006/min':<20} {'kostenlos':<20}")
    print(f"{'Offline moeglich?':<25} {'Nein':<20} {'Ja':<20}")
    print(f"\n{'OpenAI Text:':<15} {text_api}")
    print(f"{'HF Text:':<15} {text_hf}")


if __name__ == "__main__":
    main()
