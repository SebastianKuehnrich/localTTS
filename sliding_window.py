"""sliding_window.py — Sliding Context Window fuer den Voice Agent.

Ersetzt die naive conversation_history Liste.
Statt alle Messages endlos zu sammeln:
- Die letzten N Messages werden immer behalten
- Aeltere Messages werden zu einer Zusammenfassung komprimiert
- Token-Kosten bleiben stabil, Information bleibt erhalten
"""

import logging
from datetime import datetime, timezone

from anthropic import Anthropic

logger = logging.getLogger("voice_agent")


class SlidingContextWindow:
    """Verwaltet Conversation History mit automatischer Komprimierung."""

    def __init__(
        self,
        client: Anthropic,
        model: str = "claude-sonnet-4-20250514",
        max_recent: int = 10,
        summary_threshold: int = 20,
    ):
        """
        Args:
            client: Anthropic Client fuer die Zusammenfassung.
            model: Claude Modell fuer die Zusammenfassung.
            max_recent: Wie viele aktuelle Messages immer behalten werden.
            summary_threshold: Ab wie vielen Messages die aelteren zusammengefasst werden.
        """
        if max_recent < 2:
            raise ValueError("max_recent muss mindestens 2 sein.")
        if summary_threshold <= max_recent:
            raise ValueError("summary_threshold muss groesser als max_recent sein.")

        self._client = client
        self._model = model
        self.full_history: list[dict] = []
        self.summary: str = ""
        self.max_recent = max_recent
        self.summary_threshold = summary_threshold
        self._summary_count = 0

    def add_message(self, role: str, content: str) -> None:
        """Fuegt eine neue Message zur History hinzu."""
        if role not in ("user", "assistant"):
            raise ValueError(f"Ungueltiger Role: {role}. Erlaubt: user, assistant.")
        if not content or not content.strip():
            return

        self.full_history.append({
            "role": role,
            "content": content.strip(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Automatisch zusammenfassen wenn Threshold erreicht
        if len(self.full_history) > self.summary_threshold:
            self._compress()

    def build_context(self, base_system_prompt: str = "") -> tuple[str, list[dict]]:
        """Baut den optimierten Context.

        Args:
            base_system_prompt: Der Basis-System-Prompt der erweitert wird.

        Returns:
            Tuple von (system_prompt, recent_messages)
            - system_prompt: Basis-Prompt + optionale Zusammenfassung
            - recent_messages: Die letzten N Messages im Claude-API-Format
        """
        system = base_system_prompt

        if self.summary:
            system += f"\n\nBisheriges Gespraech (Zusammenfassung):\n{self.summary}"

        recent = [
            {"role": m["role"], "content": m["content"]}
            for m in self.full_history[-self.max_recent:]
        ]

        # Claude erwartet alternating user/assistant, startet mit user
        if recent and recent[0]["role"] == "assistant":
            recent = recent[1:]

        return system, recent

    def _compress(self) -> None:
        """Fasst aeltere Messages zu einer Zusammenfassung zusammen."""
        older = self.full_history[:-self.max_recent]
        if not older:
            return

        formatted = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in older
        )

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=512,
                system=(
                    "Fasse das folgende Gespraech zusammen. "
                    "Behalte: wichtige Entscheidungen, offene Fragen, key Facts. "
                    "Maximal 200 Woerter. Antworte NUR mit der Zusammenfassung."
                ),
                messages=[{"role": "user", "content": formatted}],
            )

            if response.content and response.content[0].type == "text":
                new_summary = response.content[0].text.strip()
                # Bestehende Zusammenfassung ergaenzen
                if self.summary:
                    self.summary = f"{self.summary}\n\n{new_summary}"
                else:
                    self.summary = new_summary

                self._summary_count += 1
                # History kuerzen: nur die letzten max_recent behalten
                self.full_history = self.full_history[-self.max_recent:]
                logger.info(
                    f"[SlidingWindow] {len(older)} Messages zusammengefasst "
                    f"(Zusammenfassung #{self._summary_count})"
                )

        except Exception as e:
            logger.error(f"[SlidingWindow] Zusammenfassung fehlgeschlagen: {e}")
            # Bei Fehler: aelteste Haelfte einfach verwerfen (Fallback)
            self.full_history = self.full_history[-(self.max_recent + 5):]

    def get_stats(self) -> dict:
        """Gibt Statistiken ueber den aktuellen Window-Zustand zurueck."""
        return {
            "total_messages": len(self.full_history),
            "in_context": min(len(self.full_history), self.max_recent),
            "has_summary": bool(self.summary),
            "summary_count": self._summary_count,
            "summary_length": len(self.summary) if self.summary else 0,
        }

    def reset(self) -> None:
        """Setzt den Window zurueck (z.B. bei neuer Session)."""
        self.full_history = []
        self.summary = ""
        self._summary_count = 0
        logger.info("[SlidingWindow] Reset durchgefuehrt.")
