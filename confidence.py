"""
Confidence Scoring Modul.
Analysiert Claude-Antworten und berechnet einen Konfidenz-Score basierend auf
sprachlichen Indikatoren (Hedging, Unsicherheitsausdruecke, Antwortlaenge).
"""

import re
from dataclasses import dataclass, field

# Hedging-Ausdruecke die auf Unsicherheit hindeuten
HEDGING_MARKERS_DE = [
    "vielleicht", "moeglicherweise", "eventuell", "wahrscheinlich",
    "vermutlich", "koennte", "duerfte", "wuerde", "scheint",
    "ich bin nicht sicher", "ich bin mir nicht sicher",
    "soweit ich weiss", "meines wissens", "ich glaube",
    "es ist moeglich", "unter umstaenden", "gewissermassen",
]

HEDGING_MARKERS_EN = [
    "maybe", "perhaps", "possibly", "probably", "likely",
    "might", "could be", "i think", "i believe",
    "i'm not sure", "not certain", "as far as i know",
    "it seems", "it appears", "arguably", "presumably",
]

# Starke Aussagen die auf hohe Konfidenz hindeuten
CONFIDENCE_MARKERS = [
    "definitiv", "sicher", "auf jeden fall", "zweifellos",
    "definitely", "certainly", "absolutely", "clearly",
    "ohne zweifel", "eindeutig", "tatsaechlich", "offensichtlich",
]

# Wenn das Modell zugibt, etwas nicht zu wissen
REFUSAL_MARKERS = [
    "ich weiss nicht", "ich kann nicht", "keine ahnung",
    "i don't know", "i cannot", "i'm unable",
    "das liegt ausserhalb", "dazu habe ich keine informationen",
]

# Idealer Antwortbereich (zu kurz = unsicher, zu lang = ausschweifend)
MIN_IDEAL_LENGTH = 20
MAX_IDEAL_LENGTH = 500


@dataclass
class ConfidenceResult:
    """Ergebnis der Konfidenz-Analyse."""
    score: float  # 0.0 - 1.0
    label: str  # "high", "medium", "low"
    hedging_count: int
    confidence_marker_count: int
    has_refusal: bool
    response_length: int
    details: dict = field(default_factory=dict)


def _count_markers(text: str, markers: list[str]) -> int:
    """Zaehlt wie viele Marker im Text vorkommen."""
    text_lower = text.lower()
    return sum(1 for marker in markers if marker in text_lower)


def _length_score(length: int) -> float:
    """Bewertet die Antwortlaenge. Sehr kurz oder sehr lang = niedrigerer Score."""
    if length < 5:
        return 0.3
    if length < MIN_IDEAL_LENGTH:
        return 0.6
    if length <= MAX_IDEAL_LENGTH:
        return 1.0
    # Ueber MAX_IDEAL_LENGTH: langsam abfallend
    return max(0.5, 1.0 - (length - MAX_IDEAL_LENGTH) / 2000)


def _sentence_count(text: str) -> int:
    """Zaehlt die Anzahl der Saetze."""
    return len(re.findall(r"[.!?]+", text)) or 1


def analyze_confidence(response_text: str) -> ConfidenceResult:
    """
    Analysiert eine Claude-Antwort und berechnet einen Konfidenz-Score.

    Der Score basiert auf:
    - Hedging-Ausdruecke (senken den Score)
    - Konfidenz-Marker (erhoehen den Score)
    - Verweigerungen / "Ich weiss nicht" (senken den Score stark)
    - Antwortlaenge (zu kurz oder zu lang senkt den Score)

    Returns:
        ConfidenceResult mit Score (0.0-1.0) und Details
    """
    if not response_text or not response_text.strip():
        return ConfidenceResult(
            score=0.0,
            label="low",
            hedging_count=0,
            confidence_marker_count=0,
            has_refusal=True,
            response_length=0,
            details={"reason": "Leere Antwort"},
        )

    text = response_text.strip()
    length = len(text)
    sentences = _sentence_count(text)

    # Marker zaehlen
    hedging_de = _count_markers(text, HEDGING_MARKERS_DE)
    hedging_en = _count_markers(text, HEDGING_MARKERS_EN)
    hedging_total = hedging_de + hedging_en

    confidence_markers = _count_markers(text, CONFIDENCE_MARKERS)
    has_refusal = _count_markers(text, REFUSAL_MARKERS) > 0

    # Score berechnen: Start bei 0.8 (Baseline)
    score = 0.8

    # Hedging: -0.1 pro Marker, normalisiert auf Satzanzahl
    hedging_penalty = min(0.5, (hedging_total / max(sentences, 1)) * 0.15)
    score -= hedging_penalty

    # Konfidenz-Marker: +0.05 pro Marker (max +0.2)
    confidence_bonus = min(0.2, confidence_markers * 0.05)
    score += confidence_bonus

    # Refusal: -0.3
    if has_refusal:
        score -= 0.3

    # Laengen-Faktor
    l_score = _length_score(length)
    score *= l_score

    # Clamp auf [0.0, 1.0]
    score = max(0.0, min(1.0, score))

    # Label bestimmen
    if score >= 0.7:
        label = "high"
    elif score >= 0.4:
        label = "medium"
    else:
        label = "low"

    return ConfidenceResult(
        score=round(score, 3),
        label=label,
        hedging_count=hedging_total,
        confidence_marker_count=confidence_markers,
        has_refusal=has_refusal,
        response_length=length,
        details={
            "hedging_penalty": round(hedging_penalty, 3),
            "confidence_bonus": round(confidence_bonus, 3),
            "length_factor": round(l_score, 3),
            "sentence_count": sentences,
        },
    )
