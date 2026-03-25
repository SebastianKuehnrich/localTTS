"""
Streaming Voice Agent — Haupteinstiegspunkt.
Pipeline: Mikrofon -> Whisper STT -> Claude Agent (Streaming) -> OpenAI TTS -> Lautsprecher.
Jeder Satz wird sofort ausgesprochen, bevor die vollstaendige Antwort fertig ist.
Timing-Messung fuer jede Pipeline-Stufe.
"""

import sys
import os
import time

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
SYSTEM_PROMPT = (
    "Du bist ein hilfreicher Sprachassistent. Antworte kurz auf Deutsch. "
    "Maximal 3 Saetze."
)
STOP_WORDS = ["stop", "stopp", "ende", "aufhoeren", "tschuess", "quit", "beenden"]


def check_requirements() -> None:
    """Prueft API-Keys und Mikrofon vor dem Start."""
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
        print("FEHLER: Kein Mikrofon gefunden. Pruefe Systemeinstellungen.")
        sys.exit(1)


def record_audio(duration: int = DURATION_SECONDS, sample_rate: int = SAMPLE_RATE) -> str:
    """Nimmt Audio vom Mikrofon auf und speichert als WAV."""
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
        print("WARNUNG: Aufnahme sehr leise. Mikrofon stumm geschaltet?")

    sf.write(INPUT_PATH, audio, sample_rate)
    return INPUT_PATH


def listen(openai_client: OpenAI, filepath: str) -> str:
    """Whisper STT: Audio --> Text."""
    with open(filepath, "rb") as f:
        result = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="de",
        )
    return result.text


def speak(openai_client: OpenAI, text: str) -> None:
    """TTS: Text --> Audio --> Playback fuer einen einzelnen Satz."""
    text = text.strip()
    if not text:
        return

    response = openai_client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
    )

    with open(CHUNK_PATH, "wb") as f:
        f.write(response.content)

    data, samplerate = sf.read(CHUNK_PATH)
    sd.play(data, samplerate)
    sd.wait()


def stream_and_speak(
    openai_client: OpenAI,
    anthropic_client: Anthropic,
    user_input: str,
    history: list,
) -> str:
    """Streamt Claude-Antwort und spricht jeden Satz sofort aus."""
    history.append({"role": "user", "content": user_input})

    current_sentence = ""
    full_response = ""

    with anthropic_client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=history,
    ) as stream:
        for text in stream.text_stream:
            current_sentence += text
            full_response += text
            print(text, end="", flush=True)

            if text.rstrip().endswith((".", "!", "?")):
                speak(openai_client, current_sentence.strip())
                current_sentence = ""

    if current_sentence.strip():
        speak(openai_client, current_sentence.strip())

    print()
    history.append({"role": "assistant", "content": full_response})
    return full_response


def is_stop_command(text: str) -> bool:
    """Prueft ob der User das Gespraech beenden will."""
    text_lower = text.lower().strip()
    return any(word in text_lower for word in STOP_WORDS)


def main() -> None:
    print("=== Streaming Voice Agent ===")
    print("Pipeline: Mikrofon -> Whisper(STT) -> Claude(Streaming) -> TTS -> Lautsprecher")
    print("Sage 'stop' oder 'ende' zum Beenden.\n")

    check_requirements()

    openai_client = OpenAI()
    anthropic_client = Anthropic()
    conversation_history = []
    exchange_count = 0
    timing_log = []

    while True:
        t_start = time.time()

        # STT
        filepath = record_audio()
        t_stt_start = time.time()
        user_text = listen(openai_client, filepath)
        t_stt = time.time() - t_stt_start

        print(f"[USER] {user_text}")

        if not user_text.strip():
            print("Keine Sprache erkannt. Nochmal versuchen...")
            continue

        if is_stop_command(user_text):
            print("\n[Agent beendet. Tschuess!]")
            speak(openai_client, "Tschuess! Bis zum naechsten Mal.")
            break

        # LLM + TTS (Streaming)
        t_llm_start = time.time()
        print("[AGENT] ", end="", flush=True)
        agent_text = stream_and_speak(
            openai_client, anthropic_client, user_text, conversation_history
        )
        t_llm_tts = time.time() - t_llm_start

        t_total = time.time() - t_start
        exchange_count += 1

        timing_log.append({
            "exchange": exchange_count,
            "stt": t_stt,
            "llm_tts": t_llm_tts,
            "total": t_total,
            "response_len": len(agent_text),
        })

        print(f"[Timing] STT: {t_stt:.1f}s | LLM+TTS: {t_llm_tts:.1f}s | Total: {t_total:.1f}s")

    # Timing-Zusammenfassung
    if timing_log:
        print(f"\n{'='*60}")
        print("TIMING-ZUSAMMENFASSUNG")
        print(f"{'='*60}")
        print(f"{'Austausch':<12} {'STT (s)':<10} {'LLM+TTS (s)':<14} {'Total (s)':<12} {'Zeichen'}")
        print("-" * 60)
        for entry in timing_log:
            print(
                f"{entry['exchange']:<12} {entry['stt']:<10.1f} {entry['llm_tts']:<14.1f} "
                f"{entry['total']:<12.1f} {entry['response_len']}"
            )

        avg_stt = sum(e["stt"] for e in timing_log) / len(timing_log)
        avg_llm = sum(e["llm_tts"] for e in timing_log) / len(timing_log)
        avg_total = sum(e["total"] for e in timing_log) / len(timing_log)
        print("-" * 60)
        print(f"{'Schnitt':<12} {avg_stt:<10.1f} {avg_llm:<14.1f} {avg_total:<12.1f}")

    print(f"\nGespraech beendet. {exchange_count} Austausche.")


if __name__ == "__main__":
    main()
