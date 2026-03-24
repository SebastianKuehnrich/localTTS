# TTS Architektur-Vergleich

## 1. Pipeline-Diagramme (ASCII)

### SpeechT5 (Encoder-Decoder mit Cross-Attention)

```
Text-Input
    |
    v
[Tokenizer] --> Token-IDs
    |
    v
+-------------------+
|     ENCODER       |  (Self-Attention ueber Text-Tokens)
| Text -> Kontext-  |
|    Vektoren        |
+-------------------+
    |
    |  Encoder-Output (Key + Value fuer Cross-Attention)
    v
+-------------------+     +-------------------+
|     DECODER       | <-- | Speaker Embedding |
| (Autoregressive)  |     | (512-dim Vektor)  |
| Cross-Attention:  |     +-------------------+
| Query=Decoder     |
| Key/Value=Encoder |
+-------------------+
    |
    v
Mel-Spectrogram (80 Frequenzbaender x T Frames)
    |
    v
+-------------------+
|   HiFi-GAN        |  (Separater Vocoder)
|   (Vocoder)       |
+-------------------+
    |
    v
Audio-Wellenform (.wav, 16kHz)
```

### Bark (3x Decoder-Only, KEINE Cross-Attention)

```
Text-Input
    |
    v
+---------------------------+
| SEMANTIC DECODER (GPT)    |  Text -> Semantic Tokens
| Autoregressive, kein      |  (Kodiert WAS gesagt wird
|  Encoder, keine Cross-Att |   und REIHENFOLGE der Woerter)
+---------------------------+
    |
    v
Semantic Tokens
    |
    v
+---------------------------+
| COARSE ACOUSTIC DECODER   |  Semantic Tokens -> Coarse Tokens
| (GPT-artig)               |  (Grobe Klangstruktur)
+---------------------------+
    |
    v
Coarse Audio Tokens
    |
    v
+---------------------------+
| FINE ACOUSTIC DECODER     |  Coarse -> Fine Tokens
| (GPT-artig)               |  (Feine Audio-Details)
+---------------------------+
    |
    v
Fine Audio Tokens
    |
    v
[EnCodec Decoder] --> Audio-Wellenform (.wav, 24kHz)

Kein separater Vocoder noetig!
```

### OpenAI TTS API (Closed Source)

```
Text-Input
    |
    v
+---------------------------+
|    OpenAI API             |
|    (Black Box)            |
|    model="tts-1"          |  Architektur unbekannt
|    voice="nova"           |  Vermutlich Encoder-Decoder
+---------------------------+
    |
    v
Audio-Stream (MP3/WAV)

Alles serverseitig. Kein lokales Modell.
Keine Kontrolle ueber Pipeline.
```

---

## 2. Fragen und Antworten

### Frage 1: Wie loest Bark das Alignment-Problem ohne Cross-Attention?

SpeechT5 benutzt Cross-Attention, um bei jedem Decoder-Schritt auf den richtigen Teil
des Encoder-Outputs zu "schauen" (= welches Wort gerade gesprochen wird).

Bark hat keinen Encoder und keine Cross-Attention. Stattdessen kodiert der Semantic
Decoder die Reihenfolge der Woerter direkt IN die Semantic Tokens — aehnlich wie GPT
die Reihenfolge der Woerter im generierten Text kodiert. Die Position ist implizit
in der Sequenz enthalten. Der Coarse Decoder bekommt diese Sequenz und "weiss" durch
die Token-Reihenfolge, welches Wort wann dran ist.

Kurz: Bei SpeechT5 ist Alignment EXPLIZIT (Cross-Attention). Bei Bark ist Alignment
IMPLIZIT (in der Token-Reihenfolge kodiert).

### Frage 2: Warum braucht SpeechT5 einen separaten Vocoder, Bark aber nicht?

SpeechT5 generiert ein Mel-Spectrogram — ein 2D-Bild (80 Frequenzen x Zeit-Frames).
Das ist KEIN Audio, sondern eine Frequenz-Darstellung. Deshalb braucht es HiFi-GAN
als separaten Vocoder, der dieses 2D-Bild in eine 1D-Wellenform umwandelt.

Bark generiert direkt Audio-Tokens (via EnCodec). Diese Tokens SIND bereits eine
Audio-Darstellung. Der EnCodec-Decoder ist in die Pipeline integriert und wandelt
die Tokens direkt in Audio um. Kein separater Vocoder noetig.

### Frage 3: Wie aendert man die Stimme bei Bark?

Bei SpeechT5 aendert man den Speaker Embedding (512-dim Vektor, z.B. Index 0 vs 7306).

Bei Bark aendert man das `voice_preset` (z.B. "v2/de_speaker_3" vs "v2/en_speaker_6").
Das Voice Preset ist ein Satz vorberechneter Audio-Tokens (Semantic + Coarse + Fine),
die als "Prompt" an die Decoder gegeben werden. Sie definieren Tonhoehe, Klangfarbe
und Sprechstil. Der Decoder generiert dann neuen Audio-Output, der zum Stil des
Prompts passt — aehnlich wie Few-Shot Prompting bei LLMs.

### Frage 4: Encoder-Decoder (SpeechT5) vs Decoder-Only (Bark) — Vor-/Nachteile?

**SpeechT5 Vorteile:**
- Schneller (Encoder verarbeitet den ganzen Text auf einmal, Decoder generiert nur Mel-Frames)
- Stabiles Alignment durch Cross-Attention
- Leichtgewichtiger (weniger Parameter)

**SpeechT5 Nachteile:**
- Nur Sprache (kein Lachen, Seufzen, Musik)
- Weniger natuerlich klingende Prosodie
- Braucht separaten Vocoder

**Bark Vorteile:**
- Kann Emotionen, Lachen, Musik, Geraeusche
- Natuerlichere Prosodie
- Kein separater Vocoder noetig
- Multilingual out-of-the-box

**Bark Nachteile:**
- Deutlich langsamer (3 Decoder sequentiell, alle autoregressive)
- Mehr Rechenleistung / VRAM noetig
- Weniger stabil (kann manchmal "halluzinieren" oder Woerter ueberspringen)

### Frage 5: Text-Token-Generierung (Qwen) vs Audio-Token-Generierung (Bark)?

Beide sind autoregressive Decoder-Only Modelle. Beide generieren "das naechste Token".

**Fundamentaler Unterschied:**
- **Qwen (LLM):** Generiert Text-Tokens aus einem Vokabular von ~150.000 Woertern/Subwoertern.
  Jeder Token ist ein diskretes Symbol. Die Ausgabe ist 1D (eine Sequenz von Tokens).
- **Bark:** Generiert Audio-Tokens aus einem EnCodec-Codebook. Diese Tokens sind
  NICHT Woerter, sondern komprimierte Audio-Fragmente. Bark generiert auf MEHREREN
  Ebenen (Semantic -> Coarse -> Fine), weil Audio viel mehr Information pro Zeiteinheit
  hat als Text. Ein Wort = 1 Token bei Qwen. Ein Wort = dutzende Audio-Tokens bei Bark.

Ausserdem: Text ist diskret (endliches Alphabet), Audio ist kontinuierlich (muss erst
durch EnCodec diskretisiert werden, bevor Bark damit arbeiten kann).

---

## 3. Vergleichstabelle

| | SpeechT5 | Bark | OpenAI TTS | Qwen LLM |
|---|---|---|---|---|
| **Architektur** | Encoder-Decoder | 3x Decoder-Only | Unbekannt (Closed) | Decoder-Only |
| **Input** | Text-Tokens + Speaker Embedding | Text + Voice Preset | Text + Voice-Name | Text-Tokens (Prompt) |
| **Output** | Mel-Spectrogram -> Vocoder -> Audio | Audio-Tokens -> EnCodec -> Audio | Audio (MP3/WAV) | Text-Tokens |
| **Cross-Attention** | JA (Decoder -> Encoder) | NEIN | Unbekannt | NEIN (Self-Attention) |
| **Vocoder noetig** | JA (HiFi-GAN) | NEIN (EnCodec integriert) | NEIN (serverseitig) | N/A |
| **Trainiert auf** | LibriTTS (Englisch, Sprache) | Multilingual Audio + Text | Unbekannt, vermutlich gross | Text-Korpora |
| **Staerke** | Schnell, stabil, leichtgewichtig | Expressiv, multilingual, Emotionen | Hohe Qualitaet, einfache API | Textverstaendnis, Reasoning |
| **Schwaeche** | Nur Englisch, nur Sprache, kuenstlich | Langsam, braucht GPU, instabil | Kostet Geld, kein Offline, Black Box | Kein Audio-Output |
