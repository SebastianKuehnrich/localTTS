# Technical Decisions — localTTS / CORTANA Voice Agent

## Warum Confidence Scoring?

Das System berechnet einen Konfidenz-Score fuer jede Antwort basierend auf
Hedging-Ausdruecken, Antwortlaenge und Verweigerungs-Markern (`confidence.py`).

### Design-Entscheidungen

**Warum Hedging-basiert statt Log-Probability-basiert?**

Die Anthropic API gibt keine Token-Level Log-Probabilities zurueck (anders als OpenAI).
Deshalb ist eine Log-Prob-basierte Confidence nicht moeglich ohne einen zweiten API-Call.
Stattdessen nutzen wir sprachliche Indikatoren:
- "vielleicht", "moeglicherweise", "ich bin nicht sicher" → niedrige Confidence
- "definitiv", "auf jeden Fall", "zweifellos" → hohe Confidence
- "ich weiss nicht" → Refusal, Score sinkt um -0.3

Das ist ein heuristischer Ansatz, kein statistischer. Er funktioniert gut fuer kurze,
klare Antworten (unser Use Case: max 3 Saetze). Bei langen, nuancierten Texten
waere er weniger zuverlaessig.

**Warum separate Marker-Listen fuer Deutsch und Englisch?**

Claude antwortet auf Deutsch (System Prompt), aber bei Fachbegriffen oder englischen
Inputs kann die Antwort teilweise englisch sein. Beide Sprachen abdecken verhindert
False Negatives (z.B. "I'm not sure" in einer ansonsten deutschen Antwort).

**Warum Baseline 0.8?**

Die meisten Claude-Antworten sind konfident formuliert — das Modell hedget selten.
Eine Baseline von 0.8 bedeutet: "Im Zweifel ist die Antwort gut." Nur explizites
Hedging oder Verweigerung senkt den Score. Eine Baseline von 0.5 wuerde fast alle
Antworten als "medium" bewerten, was nicht hilfreich ist.

**Eskalations-Schwellenwerte:**
- >= 0.7 (high): Direkt antworten
- 0.4 - 0.7 (medium): Antworten, aber als unsicher markiert
- < 0.4 (low): Eskalieren — ein Mensch sollte pruefen

## Warum Pipeline statt End-to-End?

Der Voice Agent nutzt drei separate Modelle: Whisper (STT), Claude (LLM), OpenAI TTS.

**Warum ich mich fuer die Pipeline entschieden habe:**
1. **Modularitaet:** Jede Komponente kann einzeln ausgetauscht werden. Als wir
   von Whisper-API auf lokales Whisper-small gewechselt haben, musste nur der
   STT-Teil geaendert werden — Claude und TTS blieben identisch.
2. **Reasoning-Qualitaet:** Claude Sonnet ist aktuell das beste verfuegbare LLM
   fuer deutsche Antworten. Ein End-to-End-Modell wie Moshi hat nur 7B Parameter —
   die Antwortqualitaet ist deutlich schwaecher.
3. **Debugging:** Bei einem Pipeline-Problem kann ich sofort sehen ob die Transkription,
   die Antwort oder die Sprachsynthese fehlerhaft war. Bei End-to-End ist alles eine Black Box.
4. **Text als Zwischenformat:** Ich kann den Text loggen, filtern und moderieren
   bevor er ausgesprochen wird.

**Was schlechter ist:**
- 1-3 Sekunden Latenz (statt ~300ms bei End-to-End)
- Prosodie geht verloren (Whisper macht aus Tonfall flachen Text)
- Keine Unterbrechungen moeglich (Agent ist taub waehrend er spricht)

**Wann ich auf End-to-End wechseln wuerde:**
Wenn ein Open-Source End-to-End Modell verfuegbar ist das (a) gutes Deutsch kann,
(b) starkes Reasoning hat (30B+), und (c) auf Consumer-Hardware laeuft.
Stand April 2026 gibt es das nicht.

## Warum Sliding Context Window statt naive Liste?

Der urspruengliche `conversation_history = []` wuchs mit jeder Nachricht.
Nach 50 Nachrichten waren es ~5000 Tokens Input — teuer und irgendwann
ueber dem Token-Limit.

**Token-Kosten vorher vs nachher:**
- Vorher: ~100 Tokens pro Nachricht * N Nachrichten = linear wachsend
- Nachher: ~300 Tokens (System + Summary) + ~1000 Tokens (10 Recent) = **stabil ~1300**

**Qualitaet der Antworten:**
Der Agent verliert keine wichtigen Informationen, weil aeltere Nachrichten
zusammengefasst statt geloescht werden. "Du hast gesagt du heisst Sebastian"
funktioniert auch nach 30 Nachrichten — der Name steht in der Zusammenfassung.

**Threshold-Werte:**
- `max_recent = 10`: 10 Messages = 5 Austausche (User + Agent). Das ist genug
  fuer den unmittelbaren Kontext einer Konversation.
- `summary_threshold = 20`: Erst ab 20 Messages zusammenfassen — nicht zu frueht
  (verschwendet einen API-Call), nicht zu spaet (Token-Kosten steigen).

## Warum ContextHub mit 8 Regeln?

Der ContextHub hat 8 Trigger-Regeln die bestimmen welche Dateien bei welcher
User-Anfrage relevant sind.

**Warum 8 und nicht 3 oder 20?**

8 Regeln decken die 8 distinktiven Themenbereiche des Projekts ab:
TTS, STT, Deployment, Streaming, Context, Confidence, Benchmark, Architektur.
3 waeren zu grob (z.B. "Audio" fuer STT und TTS zusammen — verschiedene Dateien).
20 waeren zu fein und wuerden sich staendig ueberlappen.

**Welche Regel hat am meisten Impact?**

Die Deployment-Regel (Docker/Railway). Wenn jemand ein Deployment-Problem hat,
braucht er `Dockerfile`, `docker-compose.yml` und `.dockerignore` — aber NICHT
`confidence.py` oder `bark_tts.py`. Ohne die Regel wuerde der Agent alle Dateien
laden und den Kontext verschwenden.

**Ueberlappungen:**

Ja, gewollt. "Benchmark aller TTS Modelle" matched sowohl TTS als auch Benchmark.
Das Ergebnis: Alle relevanten Dateien werden geladen. Die Union ist korrekt.

## Design vs Code — ehrliche Reflexion

CORTANA/COGITO begann als reines Architektur-Design. Im Laufe von Woche 4
wurde daraus Code: `confidence.py`, `sliding_window.py`, `context_hub.py`, `app.py`.

**Was war leichter: designen oder implementieren?**

Designen. Ein Architektur-Diagramm zeichnen dauert 30 Minuten.
`sliding_window.py` mit korrektem Error-Handling, Fallbacks und Tests hat 2 Stunden
gedauert. Die Implementierung deckt Edge Cases auf die im Design nicht sichtbar sind
(z.B. "Was passiert wenn die Zusammenfassung fehlschlaegt?" → Fallback noetig).

**Wo hat die Implementation das Design veraendert?**

Das urspruengliche CORTANA/COGITO-Design hatte zwei getrennte Agenten.
In der Praxis wurde daraus ein einzelner FastAPI-Server mit Modulen.
Der Grund: Zwei separate Services zu orchestrieren waere Overkill fuer den Scope.
Confidence Scoring als Modul statt als eigener Service war die richtige Entscheidung.

**Was ist immer noch nur Design?**

- Multi-User Session Management (aktuell teilen alle User eine History)
- Rate Limiting (SPECTRE-Spec existiert, aber nicht implementiert)
- Jetson-Hardware-Deployment (war im COGITO-Design, nie realisiert)

## Was ich anders machen wuerde

1. **Frueh deployen:** Docker und Railway in Woche 1 statt Woche 4. Jeder Code-Push
   waere sofort testbar gewesen. Stattdessen lief alles nur lokal.
2. **Tests schreiben:** Keine automatisierten Tests. `context_hub.py` hat eine
   Test-Suite im `__main__`, aber keine echten Unit Tests mit pytest.
3. **Session Management:** Von Anfang an User-Sessions einplanen statt globale
   History. Die nachtraegliche Integration ist aufwendiger.
4. **Weniger Endpoints, mehr Tiefe:** 12+ Endpoints klingt beeindruckend, aber
   lieber 5 Endpoints die perfekt funktionieren als 12 die 80% fertig sind.

## Kosten-Analyse

Was kostet das System pro 1.000 Conversations?

Annahme: Durchschnittliche Conversation = 5 Austausche, je ~50 Woerter User + ~100 Woerter Agent.

| Komponente | Einheit | Preis | Pro Conversation | Pro 1.000 |
|-----------|---------|-------|-----------------|-----------|
| Whisper (lokal) | CPU-Zeit | $0 | $0 | $0 |
| Claude Sonnet Input | $3/1M Tokens | ~750 Tokens * 5 | $0.011 | $11.25 |
| Claude Sonnet Output | $15/1M Tokens | ~500 Tokens * 5 | $0.038 | $37.50 |
| OpenAI TTS | $15/1M Chars | ~500 Chars * 5 | $0.038 | $37.50 |
| Railway | $5/Monat | Fix | ~$0.005 | $5.00 |
| **Gesamt** | | | **~$0.09** | **~$91** |

**Optimierungspotenzial:**
- Claude Haiku statt Sonnet: ~10x billiger ($3.75 statt $37.50 Output)
- Lokales TTS (SpeechT5): $0 statt $37.50 (aber schlechtere Qualitaet)
- Sliding Window reduziert Input-Tokens um ~60% bei langen Conversations

## Vergleich: TTS-Benchmarks

Aus `tts_benchmark.py`:

| Modell | Latenz | Qualitaet | Kosten | Best fuer |
|--------|--------|-----------|--------|-----------|
| **OpenAI TTS** | ~1s (API) | Sehr gut, natuerlich | $15/1M Chars | Production, beste Qualitaet |
| **SpeechT5** | ~2s (lokal) | Gut, robotisch | $0 (lokal) | Offline, Budget, Privacy |
| **Bark** | ~5-10s (lokal) | Gut, kreativ (Lachen etc.) | $0 (lokal) | Kreative Anwendungen, Emotionen |

**Empfehlung:**
- Demo/Production: OpenAI TTS (Qualitaet rechtfertigt Kosten)
- Privacy/Offline: SpeechT5 (akzeptable Qualitaet, keine API noetig)
- Forschung/Kreativ: Bark (einzigartige Faehigkeiten, aber langsam)
