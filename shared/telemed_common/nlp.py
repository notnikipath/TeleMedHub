from __future__ import annotations

import re

from .schemas import ComplaintAnalysis, ConsultationType

SPECIALTY_HINTS: dict[ConsultationType, list[str]] = {
    ConsultationType.THERAPY: ["температура", "кашель", "насморк", "боль", "fever", "cough"],
    ConsultationType.PEDIATRICS: ["ребенок", "ребёнок", "child", "infant", "педиатр"],
    ConsultationType.CARDIOLOGY: ["сердце", "давление", "пульс", "аритмия", "heart", "pressure", "holter"],
    ConsultationType.DERMATOLOGY: ["сыпь", "кожа", "пятно", "rash", "skin", "itch"],
    ConsultationType.PSYCHOLOGY: ["тревога", "паника", "депресс", "anxiety", "stress", "sleep"],
}

RED_FLAG_PATTERNS = [
    r"\b(потеря сознания|обморок|сильная боль в груди|удушье)\b",
    r"\b(loss of consciousness|severe chest pain|shortness of breath)\b",
]


def analyze_complaint(patient_id: str, complaint_text: str) -> ComplaintAnalysis:
    normalized = complaint_text.lower()
    tokens = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9\-]+", normalized)
    unique = sorted(set(tokens))

    specialty_scores: dict[ConsultationType, int] = {key: 0 for key in ConsultationType}
    for specialty, hints in SPECIALTY_HINTS.items():
        for hint in hints:
            if hint in normalized:
                specialty_scores[specialty] += 1

    sorted_specialties = sorted(
        [item for item in specialty_scores.items() if item[1] > 0],
        key=lambda item: item[1],
        reverse=True,
    )
    suggestions = [item[0] for item in sorted_specialties[:2]] or [ConsultationType.THERAPY]

    red_flags: list[str] = []
    for pattern in RED_FLAG_PATTERNS:
        found = re.findall(pattern, normalized)
        red_flags.extend(found)

    urgency = 0.25 + min(len(red_flags) * 0.35, 0.7)
    urgency += min(sum(score for _, score in sorted_specialties) * 0.05, 0.3)
    urgency = round(min(1.0, urgency), 2)

    return ComplaintAnalysis(
        patient_id=patient_id,
        complaint_text=complaint_text,
        keywords=unique[:20],
        urgency_score=urgency,
        suggested_specialties=suggestions,
        red_flags=red_flags,
    )


def speech_to_protocol(transcribed_text: str) -> dict[str, str]:
    lines = [part.strip() for part in transcribed_text.split(".") if part.strip()]
    subjective = lines[0] if lines else ""
    objective = lines[1] if len(lines) > 1 else ""
    plan = lines[2] if len(lines) > 2 else ""
    return {"subjective": subjective, "objective": objective, "plan": plan}
