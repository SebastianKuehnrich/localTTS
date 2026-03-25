"""
GOLD: Continuous Conversation Loop.
Endlos-Schleife: User spricht -> Agent antwortet -> User spricht -> ...
Beendet sich wenn der User 'stop', 'ende' o.ae. sagt.
"""

import sys
import os

import numpy as np
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
from anthropic import Anthropic


# ── Konstanten ──────────────────────────────────────────────
SAMPLE_RATE = 16000
DURATION_SECONDS = 5
INPUT_PATH = "input.wav"
RESPONSE_PATH = "response.wav"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
SYSTEM_PROMPT = (
    "Du bist ein hilfreicher Sprachassistent. Antworte kurz und praezise auf Deutsch. "
    "Halte deine Antworten unter 3 Saetzen, weil sie vorgelesen werden."
)
STOP_WORDS = ["stop", "stopp", "ende", "aufhoeren", "tschuess", "quit", "beenden"]


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
    """Nimmt Audio vom Mikrofon auf."""
    print(f"\n--- Sprich jetzt... ({duration}s) ---")
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
        print("WARNUNG: Aufnahme sehr leise.")

    sf.write(INPUT_PATH, audio, sample_rate)
    return INPUT_PATH


def transcribe(client: OpenAI, filepath: str) -> str:
    """Whisper STT: Audio --> Text."""
    with open(filepath, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="de",
        )
    return result.text


def ask_agent(client: Anthropic, user_text: str, history: list) -> str:
    """Claude Agent: Text --> Text."""
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


def speak(client: OpenAI, text: str) -> None:
    """TTS: Text --> Audio --> Playback."""
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


def is_stop_command(text: str) -> bool:
    """Prueft ob der User das Gespraech beenden will."""
    text_lower = text.lower().strip()
    return any(word in text_lower for word in STOP_WORDS)


def main() -> None:
    print("=== Gold: Continuous Voice Agent ===")
    print("Sage 'stop' oder 'ende' zum Beenden.\n")

    check_requirements()

    openai_client = OpenAI()
    anthropic_client = Anthropic()
    conversation_history = []
    exchange_count = 0

    while True:
        filepath = record_audio()

        user_text = transcribe(openai_client, filepath)
        print(f"[USER]  {user_text}")

        if not user_text.strip():
            print("Keine Sprache erkannt. Nochmal versuchen...")
            continue

        if is_stop_command(user_text):
            print("\n[Agent beendet. Tschuess!]")
            speak(openai_client, "Tschuess! Bis zum naechsten Mal.")
            break

        agent_text = ask_agent(anthropic_client, user_text, conversation_history)
        print(f"[AGENT] {agent_text}")

        speak(openai_client, agent_text)
        exchange_count += 1

    print(f"\nGespraech beendet. {exchange_count} Austausche.")


if __name__ == "__main__":
    main()
