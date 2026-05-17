from shared.telemed_common.nlp import analyze_complaint, speech_to_protocol
from shared.telemed_common.schemas import ConsultationType


def test_complaint_analysis_cardio_keywords() -> None:
    result = analyze_complaint("PAT-1", "Сильная боль в груди и высокое давление")
    assert result.urgency_score > 0.3
    assert ConsultationType.CARDIOLOGY in result.suggested_specialties


def test_speech_to_protocol_splits_sections() -> None:
    payload = speech_to_protocol("Жалобы на слабость. Объективно состояние стабильное. Рекомендован покой и контроль.")
    assert payload["subjective"]
    assert payload["objective"]
    assert payload["plan"]
