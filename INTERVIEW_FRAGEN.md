# Interview-Fragen — Schriftliche Antworten
## Sebastian | 01.04.2026

---

## Frage 1: "Erklaer mir den Unterschied zwischen Fine-Tuning und Prompting. Wann nutzt du was?"

**Prompting** aendert den Input — die Modellgewichte bleiben identisch. Ich formuliere
Anweisungen, Beispiele (Few-Shot) oder Kontext so, dass das Modell die gewuenschte
Antwort generiert. Das ist schnell, kostet nichts extra und funktioniert fuer die
meisten allgemeinen Aufgaben.

**Fine-Tuning** aendert die Gewichte des Modells selbst. Man trainiert auf einem
spezialisierten Datensatz weiter, sodass das Modell neues Verhalten lernt. Mit QLoRA
(wie in Woche 1 mit Qwen 7B) werden nur ~1-2% der Parameter trainiert — effizient,
aber trotzdem aufwendiger als Prompting.

**Wann was?**

| Kriterium | Prompting | Fine-Tuning |
|-----------|-----------|-------------|
| Aufgabe ist allgemein | Ja | Uebertrieben |
| Spezifischer Stil/Ton noetig | Begrenzt | Ja |
| Domain-spezifisches Wissen | RAG + Prompting | Ja, wenn RAG nicht reicht |
| Latenz-kritisch | Ja (kein Training) | Ja (kleineres Modell moeglich) |
| Budget begrenzt | Ja ($0) | Nein (GPU-Kosten) |
| Wenige Beispiele vorhanden | Few-Shot Prompting | Nein (braucht Daten) |

**Konkretes Beispiel aus meinem Projekt:** Fuer den Voice Agent nutze ich Prompting
(System Prompt auf Deutsch, max 3 Saetze). Fine-Tuning waere hier Overkill — Claude
kann Deutsch und kurze Antworten generieren ohne Gewichtsaenderung. Fine-Tuning
wuerde ich einsetzen wenn ich z.B. einen spezialisierten medizinischen Assistenten
braeuchte, der konsistent in Fachsprache antwortet und Prompting allein nicht reicht.

**Knowledge Distillation** ist eine Erweiterung: Ein grosses Modell (Teacher, z.B. Claude)
generiert Trainingsdaten, ein kleines Modell (Student, z.B. Qwen 7B) wird darauf
fine-getuned. So bekommt man die Qualitaet des grossen Modells in einem kleinen,
guenstigen Modell. Genau das haben wir in Woche 1 gemacht.

---

## Frage 2: "Du hast einen Voice Agent gebaut. Was kostet es, 1.000 Conversations zu fuehren?"

**Annahmen:**
- Durchschnittliche Conversation: 5 Austausche (User fragt, Agent antwortet)
- Pro Austausch: ~50 Woerter User-Input (~75 Tokens), ~100 Woerter Agent-Output (~150 Tokens)
- Whisper laeuft lokal (whisper-small) → $0
- Claude Sonnet: $3/1M Input-Tokens, $15/1M Output-Tokens
- OpenAI TTS (tts-1): $15/1M Characters
- Railway: $5/Monat (Fix)

**Rechnung pro Conversation (5 Austausche):**

| Komponente | Berechnung | Kosten |
|-----------|-----------|--------|
| Whisper (lokal) | CPU-Zeit, kein API-Call | $0 |
| Claude Input | ~750 Tokens * ($3/1M) | $0.00225 |
| Claude Output | ~750 Tokens * ($15/1M) | $0.01125 |
| Sliding Window Overhead | ~300 Tokens System + Summary | ~$0.005 |
| OpenAI TTS | ~2500 Chars * ($15/1M) | $0.0375 |
| **Summe pro Conversation** | | **~$0.056** |

**Pro 1.000 Conversations:** ~$56 + $5 Railway = **~$61/Monat**

**Optimierungshebel:**
1. Claude Haiku statt Sonnet: Output-Kosten sinken um ~10x → ~$15 statt $56
2. Lokales TTS (SpeechT5): $0 statt $37.50 (aber robotischere Stimme)
3. Sliding Window spart ~60% Input-Tokens bei langen Conversations
4. Caching haeufiger Antworten (z.B. Begruessung) → weniger API-Calls

**Wichtig im Interview:** Nicht nur die Zahl nennen, sondern zeigen dass man die
Kostenstruktur versteht und Optimierungsmoeglichkeiten kennt.

---

## Frage 3: "Was ist Context Engineering und warum ist es wichtig?"

Context Engineering ist **die Architektur des gesamten Informationsflusses** zu einem
LLM. Es geht NICHT nur um "gute Prompts schreiben" — es geht darum, WELCHE Information
das Modell WANN sieht und in WELCHER Form.

**Die vier Operationen (nach Andrej Karpathy):**

1. **Write:** Informationen persistent speichern — Conversation History, User-Praeferenzen,
   Zusammenfassungen. In meinem Projekt: `sliding_window.py` speichert und komprimiert
   die Chat-Historie automatisch.

2. **Select:** Die RICHTIGEN Informationen fuer die aktuelle Aufgabe waehlen.
   In meinem Projekt: `context_hub.py` mit 8 Regex-Regeln bestimmt welche Dateien
   bei welcher Frage relevant sind. "TTS Latenz?" → lade `bark_tts.py`, `tts_benchmark.py`.
   "Docker Problem?" → lade `Dockerfile`, `docker-compose.yml`. NICHT alles auf einmal.

3. **Compress:** Token-Kosten kontrollieren. Mein Sliding Window komprimiert aeltere
   Nachrichten zu einer Zusammenfassung. Statt linear wachsender Token-Kosten
   (~100 * N Nachrichten) bleiben die Kosten stabil bei ~1300 Tokens.

4. **Isolate:** Verschiedene Kontexte trennen. System Prompt, User-Historie und
   Tool-Ergebnisse sind getrennte Bereiche — sie vermischen sich nicht.

**Warum ist das wichtig?**

Ohne Context Engineering passiert Folgendes:
- Token-Kosten explodieren (jede Nachricht schickt die GESAMTE Historie mit)
- Das Modell bekommt irrelevante Informationen (Noise → schlechtere Antworten)
- Das Token-Limit wird irgendwann erreicht → Fehler
- Keine Kontrolle darueber was das Modell "weiss" und was nicht

**Konkretes Beispiel:** Nach Einfuehrung des Sliding Window sanken meine Token-Kosten
von linear wachsend auf stabil ~1300 Tokens — bei BESSERER Antwortqualitaet, weil
der Kontext fokussierter ist.

---

## Frage 4: "Erklaer mir den Unterschied zwischen deiner Voice Pipeline und Full-Duplex Systemen wie Moshi."

**Meine Pipeline (Half-Duplex):**
```
Mikrofon → [Whisper STT] → Text → [Claude LLM] → Text → [OpenAI TTS] → Lautsprecher
```
Drei separate Modelle, sequentiell. Der Agent ist TAUB waehrend er spricht.
Latenz: 1-3 Sekunden bis zur ersten hoerbaren Antwort.

**Moshi (True Full-Duplex):**
```
Mikrofon ──→ [EIN Modell] ←── hoert UND spricht GLEICHZEITIG
Lautsprecher ←─┘
```
Ein Modell mit Dual-Stream Architektur. ~200ms Latenz. Erkennt Unterbrechungen.

**Vergleich:**

| Aspekt | Meine Pipeline | Moshi/Full-Duplex |
|--------|---------------|-------------------|
| Modelle | 3 (Whisper + Claude + TTS) | 1 |
| Latenz | 1-3 Sekunden | ~200-300ms |
| Prosodie | Verloren (Text-Zwischenschritt) | Erhalten (Audio-zu-Audio) |
| Unterbrechungen | Unmoeglich | Ja |
| Reasoning | Bestes (Claude Sonnet) | Begrenzt (7B Parameter) |
| Modularitaet | Hoch (Komponenten austauschbar) | Niedrig (Monolith) |
| Debugging | Einfach (Text-Logs zwischen Stufen) | Schwer (Black Box) |
| Moderation | Text filterbar vor Sprachausgabe | Schwieriger |

**Warum ich mich fuer die Pipeline entschieden habe:**
Reasoning-Qualitaet war wichtiger als Latenz. Claude Sonnet gibt deutlich bessere
Antworten als ein 7B-Modell. Fuer einen Karriereberater-Agent, der durchdachte
Empfehlungen geben soll, ist die Antwortqualitaet entscheidend — nicht ob die
Antwort 200ms oder 2s braucht.

**Wann ich wechseln wuerde:** Wenn ein Open-Source Full-Duplex Modell verfuegbar ist
das (a) gutes Deutsch kann, (b) starkes Reasoning hat (30B+), und (c) auf
Consumer-Hardware laeuft.

**LiveKit als Mittelweg:** LiveKit buendelt STT + LLM + TTS hinter einem API Key
und ermoeglicht paralleles Streaming + VAD-basierte Unterbrechungserkennung.
Nicht echtes Full-Duplex wie Moshi, aber deutlich besser als meine sequentielle Pipeline.

---

## Frage 5: "Was ist der Unterschied zwischen autoregressive und Diffusion-basierter Text-Generierung?"

**Autoregressive (AR) Generierung — GPT, Claude, Qwen:**

Das Modell generiert ein Token nach dem anderen, von links nach rechts.
Jedes Token wird basierend auf ALLEN vorherigen Tokens berechnet:
P(token_n | token_1, ..., token_n-1).

```
Schritt 1: "Der"
Schritt 2: "Der" → "Hund"
Schritt 3: "Der Hund" → "rennt"
Schritt 4: "Der Hund rennt" → "schnell"
```

Die Causal Mask stellt sicher, dass jedes Token nur die vorherigen sehen kann.
Das bedeutet: **keine Parallelisierung moeglich**. Token 4 braucht Token 3 als Input.

**Diffusion-basierte Generierung — MDLM, Plaid:**

Inspiriert von Bild-Diffusion (Stable Diffusion). Das Modell startet mit einem
komplett verrauschten (maskierten) Text und verfeinert ihn iterativ:

```
Schritt 1: [MASK] [MASK] [MASK] [MASK]
Schritt 2: [MASK] Hund [MASK] [MASK]
Schritt 3: Der Hund [MASK] schnell
Schritt 4: Der Hund rennt schnell
```

Alle Positionen werden GLEICHZEITIG bearbeitet — das ist parallelisierbar.
Das Modell arbeitet bidirektional (sieht alle Positionen gleichzeitig, wie BERT).

**Vergleich:**

| Aspekt | Autoregressive | Diffusion |
|--------|---------------|-----------|
| Generierungsrichtung | Links → Rechts | Alle gleichzeitig |
| Parallelisierbar | Nein | Ja |
| Attention | Kausal (nur links) | Bidirektional (alles) |
| Reasoning-Qualitaet | Sehr gut (Chain of Thought) | Noch schwaecher |
| Latenz bei langen Texten | Linear (je laenger, desto langsamer) | Konstant (fixe Iterationen) |
| Reife | 10+ Jahre Forschung, State of the Art | Fruehes Stadium |

**A2D (Autoregressive to Diffusion):**
Ein neuer Ansatz bei dem bestehende AR-Modelle in Diffusion-Modelle konvertiert werden,
ohne komplett neu zu trainieren. Das ist vielversprechend, weil man die trainierten
Gewichte (und damit das Reasoning) behaelt, aber die Generierungsgeschwindigkeit
durch Parallelisierung steigert.

**Tradeoff:** AR hat aktuell bessere Reasoning-Qualitaet (Chain-of-Thought funktioniert
natuerlich links-nach-rechts). Diffusion hat Speed-Potential. Langfristig koennten
hybride Ansaetze beide Vorteile kombinieren.

---

## Zusammenfassung: Was diese Fragen zeigen

Diese 5 Fragen decken die Kernkompetenzen eines AI Engineers ab:

1. **Fine-Tuning vs Prompting** → Verstaendnis wann welches Tool
2. **Kosten-Analyse** → Business-Denken, nicht nur Technik
3. **Context Engineering** → Systemarchitektur, nicht nur Prompt-Schreiben
4. **Pipeline vs Full-Duplex** → Architektur-Entscheidungen begruenden
5. **AR vs Diffusion** → Verstaendnis aktueller Forschung und Trends
