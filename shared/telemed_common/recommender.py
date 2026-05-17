from __future__ import annotations

from collections import Counter

from .schemas import ConsultationType, DoctorRecommendation


def recommend_doctor_by_symptoms(
    patient_id: str,
    symptom_tags: list[str],
    doctors: list[dict],
) -> DoctorRecommendation:
    if not doctors:
        return DoctorRecommendation(
            patient_id=patient_id,
            recommended_doctor_id="unassigned",
            consultation_type=ConsultationType.THERAPY,
            score=0.0,
            reason="No doctors registered",
        )

    tag_counter = Counter(symptom_tags)
    best_score = -1.0
    best = doctors[0]

    for doctor in doctors:
        specialties = doctor.get("specialties", [])
        experience = float(doctor.get("experience_years", 1))
        rating = float(doctor.get("rating", 4.0))
        online = bool(doctor.get("online", True))
        base = 0.1 if online else -0.2
        specialty_bonus = sum(tag_counter.get(tag, 0) for tag in specialties) * 0.1
        score = base + specialty_bonus + min(experience / 50.0, 0.2) + min(rating / 10.0, 0.5)
        if score > best_score:
            best_score = score
            best = doctor

    consultation_type = ConsultationType(best.get("consultation_type", ConsultationType.THERAPY.value))
    return DoctorRecommendation(
        patient_id=patient_id,
        recommended_doctor_id=str(best.get("doctor_id", "unknown")),
        consultation_type=consultation_type,
        score=round(min(1.0, max(0.0, best_score)), 2),
        reason=f"Matched by tags {symptom_tags[:5]} and doctor rating/availability",
    )
