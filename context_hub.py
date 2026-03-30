"""context_hub.py — Deklarativer Context Manager fuer den Voice Agent.

Entscheidet basierend auf der User-Frage, welche Dateien relevant sind.
Inspiriert vom ContextHub-Pattern aus der Lecture (03_context_hub.ts).
"""

import re
import logging

logger = logging.getLogger("voice_agent")


class ContextHub:
    """Deklarativer Context Manager: Task -> relevante Dateien."""

    def __init__(
        self,
        always_include: list[str],
        rules: list[dict],
        exclude_patterns: list[str] | None = None,
    ):
        """
        Args:
            always_include: Dateien die IMMER geladen werden.
            rules: Liste von Regeln mit 'trigger' (Regex), 'files' (Liste), 'description'.
            exclude_patterns: Regex-Patterns fuer Dateien die NIE geladen werden.
        """
        if not always_include:
            raise ValueError("always_include darf nicht leer sein.")

        self.always_include = list(always_include)
        self.rules = list(rules)
        self.exclude_patterns = [
            re.compile(p) for p in (exclude_patterns or [])
        ]

    def resolve(self, task: str) -> dict:
        """Gibt relevante Dateien + matched Rules fuer einen Task zurueck.

        Args:
            task: User-Anfrage oder Task-Beschreibung.

        Returns:
            Dict mit 'files' (Liste), 'matched_rules' (Liste), 'always' (Liste).
        """
        if not task or not task.strip():
            return {
                "files": list(self.always_include),
                "matched_rules": [],
                "always": list(self.always_include),
            }

        files = set(self.always_include)
        matched_rules = []

        for rule in self.rules:
            trigger = rule.get("trigger", "")
            if re.search(trigger, task, re.IGNORECASE):
                rule_files = rule.get("files", [])
                files.update(rule_files)
                matched_rules.append({
                    "description": rule.get("description", trigger),
                    "files": rule_files,
                })

        # Exclude-Filter anwenden
        filtered = [
            f for f in sorted(files)
            if not any(p.search(f) for p in self.exclude_patterns)
        ]

        return {
            "files": filtered,
            "matched_rules": matched_rules,
            "always": list(self.always_include),
        }


# ── Konfiguration fuer UNSEREN Voice Agent ─────────────────

voice_hub = ContextHub(
    always_include=["app.py", "confidence.py", "requirements.txt"],
    rules=[
        {
            "trigger": r"tts|voice|audio|speech|stimme|sprechen|lautsprecher",
            "files": ["app.py", "bark_tts.py", "speaker_compare.py"],
            "description": "TTS / Audio / Sprachsynthese",
        },
        {
            "trigger": r"whisper|stt|transkription|sprache.zu.text|mikrofon|aufnahme",
            "files": ["app.py", "whisper_compare.py"],
            "description": "STT / Whisper / Transkription",
        },
        {
            "trigger": r"deploy|docker|railway|server|container|image",
            "files": ["Dockerfile", "docker-compose.yml", ".dockerignore"],
            "description": "Deployment / Docker / Railway",
        },
        {
            "trigger": r"stream|sse|echtzeit|live|token",
            "files": ["app.py", "main.py"],
            "description": "Streaming / SSE",
        },
        {
            "trigger": r"history|kontext|context|memory|gespraech|window|zusammenfassung",
            "files": ["sliding_window.py"],
            "description": "Context / History / Sliding Window",
        },
        {
            "trigger": r"confidence|konfidenz|score|bewertung|eskalat|analyse",
            "files": ["confidence.py", "app.py"],
            "description": "Confidence Scoring / Analyse",
        },
        {
            "trigger": r"benchmark|vergleich|latenz|performance|test",
            "files": ["tts_benchmark.py", "whisper_compare.py", "mel_visualize.py"],
            "description": "Benchmark / Vergleich / Performance",
        },
        {
            "trigger": r"architektur|pipeline|diagramm|design|dokumentation",
            "files": ["TTS_ARCHITECTURES.md", "CLAUDE.md", "README.md"],
            "description": "Architektur / Dokumentation",
        },
    ],
    exclude_patterns=[r"\.env$", r"__pycache__", r"\.git/", r"\.venv/"],
)


if __name__ == "__main__":
    # Tests — fuehre dieses File direkt aus: python context_hub.py
    test_queries = [
        "TTS Audio Bug fixen",
        "Railway Deployment ist kaputt",
        "Whisper erkennt keine Sprache",
        "SSE Streaming bricht ab",
        "Conversation History wird zu lang",
        "Confidence Score ist zu niedrig",
        "Benchmark aller TTS Modelle",
        "Wie ist die Architektur aufgebaut?",
        "",
    ]

    print("=" * 60)
    print("ContextHub Test")
    print("=" * 60)

    for query in test_queries:
        result = voice_hub.resolve(query)
        display = query if query else "(leere Anfrage)"
        print(f"\nQuery: '{display}'")
        if result["matched_rules"]:
            for rule in result["matched_rules"]:
                print(f"  Regel: {rule['description']}")
        else:
            print("  Keine Regel gematched (nur always_include)")
        print(f"  Dateien: {result['files']}")

    print(f"\n{'=' * 60}")
    print("Alle Tests abgeschlossen.")
