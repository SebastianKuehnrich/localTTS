"""
SILVER: Full Voice Loop.
Record + Whisper STT + Claude Agent + OpenAI TTS + Playback.
Komplette Pipeline: User spricht -> Agent antwortet mit Stimme.
"""

import sys
import os

import numpy as np
import sounddevice as sd
import soundfile as sf


# ── Konstanten ──────────────────────────────────────────────
SAMPLE_RATE = 16000
DURATION_SECONDS = 5
INPUT_PATH = "input.wav"
RESPONSE_PATH = "response.wav"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
SYSTEM_PROMPT = "Du bist ein hilfreicher Assistent. Antworte kurz und praezise auf Deutsch."


def check_requirements() -> None:
    """Prueft API-Keys und Mikrofon."""
    missing = []
    if not os.environ.get("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        print(f"FEHLER: Fehlende Umgebungsvariablen: {', '.join(missing)}")
        sys.exit(1)

    try:
        default_input = sd.query_devices(kind="input")
        print(f"Mikrofon: {default_input['name']}")
    except sd.PortAudioError:
        print("FEHLER: Kein Mikrofon gefunden.")
        sys.exit(1)


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

    peak = np.max(np.abs(audio))
    if peak < 0.01:
        print("WARNUNG: Aufnahme sehr leise. Mikrofon stumm geschaltet?")

    sf.write(INPUT_PATH, audio, sample_rate)
    return INPUT_PATH


def transcribe(filepath: str) -> str:
    """Whisper STT: Audio --> Text."""
    from openai import OpenAI

    client = OpenAI()
    with open(filepath, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="de",
        )
    return result.text


def ask_agent(user_text: str, history: list) -> str:
    """Claude Agent: Text --> Text."""
    from anthropic import Anthropic

    client = Anthropic()
    history.append({"role": "user", "content": user_text})

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=history,
    )

    assistant_text = response.content[0].text
    history.append({"role": "assistant", "content": assistant_text})
    return assistant_text


def speak(text: str) -> None:
    """TTS: Text --> Audio --> Playback."""
    from openai import OpenAI

    client = OpenAI()
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
    )

    with open(RESPONSE_PATH, "wb") as f:
        f.write(response.content)

    data, samplerate = sf.read(RESPONSE_PATH)
    sd.play(data, samplerate)
    sd.wait()


def main() -> None:
    print("=== Silver: Full Voice Loop ===")
    print("Pipeline: Mikrofon --> Whisper(STT) --> Claude(Agent) --> TTS --> Lautsprecher\n")

    check_requirements()

    conversation_history = []

    filepath = record_audio()

    user_text = transcribe(filepath)
    print(f"[USER]  {user_text}")

    if not user_text.strip():
        print("Keine Sprache erkannt. Bitte lauter sprechen.")
        return

    agent_text = ask_agent(user_text, conversation_history)
    print(f"[AGENT] {agent_text}")

    speak(agent_text)
    print("\n[Fertig]")


if __name__ == "__main__":
    main()
