"""
DIAMOND: Streaming Voice Agent.
Streamt Claude-Antwort satzweise und spricht jeden Satz sofort aus,
bevor die komplette Antwort fertig ist. Minimale Latenz.
"""

import sys
import os
import re

import numpy as np
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
from anthropic import Anthropic


# ── Konstanten ──────────────────────────────────────────────
SAMPLE_RATE = 16000
DURATION_SECONDS = 5
INPUT_PATH = "input.wav"
CHUNK_PATH = "chunk.wav"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
SYSTEM_PROMPT = "Du bist ein hilfreicher Sprachassistent. Antworte auf Deutsch."
STOP_WORDS = ["stop", "stopp", "ende", "aufhoeren", "tschuess", "quit", "beenden"]
SENTENCE_ENDINGS = re.compile(r"[.!?]\s")


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


def speak_sentence(client: OpenAI, text: str) -> None:
    """Spricht einen einzelnen Satz aus."""
    text = text.strip()
    if not text:
        return

    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
    )

    with open(CHUNK_PATH, "wb") as f:
        f.write(response.content)

    data, samplerate = sf.read(CHUNK_PATH)
    sd.play(data, samplerate)
    sd.wait()


def stream_agent_and_speak(
    openai_client: OpenAI,
    anthropic_client: Anthropic,
    user_text: str,
    history: list,
) -> str:
    """Streamt Claude-Antwort und spricht jeden Satz sofort aus."""
    history.append({"role": "user", "content": user_text})

    full_response = ""
    buffer = ""

    with anthropic_client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=history,
    ) as stream:
        for text_chunk in stream.text_stream:
            full_response += text_chunk
            buffer += text_chunk

            # Pruefe ob ein vollstaendiger Satz im Buffer ist
            match = SENTENCE_ENDINGS.search(buffer)
            while match:
                sentence_end = match.end()
                sentence = buffer[:sentence_end].strip()
                buffer = buffer[sentence_end:]

                if sentence:
                    print(f"  [SPRICHT] {sentence}")
                    speak_sentence(openai_client, sentence)

                match = SENTENCE_ENDINGS.search(buffer)

    # Rest-Buffer aussprechen (letzter Satz ohne Punkt)
    if buffer.strip():
        print(f"  [SPRICHT] {buffer.strip()}")
        speak_sentence(openai_client, buffer.strip())

    history.append({"role": "assistant", "content": full_response})
    return full_response


def is_stop_command(text: str) -> bool:
    """Prueft ob der User das Gespraech beenden will."""
    text_lower = text.lower().strip()
    return any(word in text_lower for word in STOP_WORDS)


def main() -> None:
    print("=== Diamond: Streaming Voice Agent ===")
    print("Sage 'stop' zum Beenden.\n")

    check_requirements()

    openai_client = OpenAI()
    anthropic_client = Anthropic()
    conversation_history = []
    exchange_count = 0

    while True:
        filepath = record_audio()

        user_text = transcribe(openai_client, filepath)
        print(f"\n[USER] {user_text}")

        if not user_text.strip():
            print("Keine Sprache erkannt. Nochmal versuchen...")
            continue

        if is_stop_command(user_text):
            speak_sentence(openai_client, "Tschuess!")
            break

        print("[AGENT streamt...]")
        agent_text = stream_agent_and_speak(
            openai_client, anthropic_client, user_text, conversation_history
        )
        print(f"[AGENT komplett] {agent_text}")
        exchange_count += 1

    print(f"\nGespraech beendet. {exchange_count} Austausche.")


if __name__ == "__main__":
    main()
