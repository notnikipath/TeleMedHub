from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from .helpers import load_module

ROOT = Path(__file__).resolve().parents[2]


def test_appointment_create_and_confirm() -> None:
    module = load_module("appointment_module", ROOT / "appointment-service" / "app" / "main.py")
    client = TestClient(module.app)

    doctor_id = "DOC-001"
    slots_response = client.get(f"/doctors/{doctor_id}/calendar")
    assert slots_response.status_code == 200
    slots = slots_response.json()["slots"]
    assert slots

    payload = {
        "patient_id": "PAT-001",
        "doctor_id": doctor_id,
        "consultation_type": "therapy",
        "scheduled_at": slots[0],
        "symptoms": "Кашель и температура",
        "language": "ru",
        "actor_role": "patient",
    }
    create_response = client.post("/appointments", json=payload)
    assert create_response.status_code == 200
    appointment = create_response.json()

    confirm_response = client.post(
        f"/appointments/{appointment['appointment_id']}/confirm",
        json={"actor_id": "ADMIN-1", "actor_role": "admin"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"


def test_consultation_session_flow() -> None:
    module = load_module("consultation_module", ROOT / "consultation-service" / "app" / "main.py")
    client = TestClient(module.app)

    start_response = client.post(
        "/sessions/start",
        json={
            "appointment_id": "APP-123",
            "patient_id": "PAT-001",
            "doctor_id": "DOC-001",
            "consent_recording": True,
            "actor_role": "doctor",
        },
    )
    assert start_response.status_code == 200
    session = start_response.json()
    session_id = session["session_id"]

    quality_payload = {
        "session_id": session_id,
        "latency_ms": 150,
        "jitter_ms": 10,
        "packet_loss_pct": 0.5,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    quality_response = client.post(f"/sessions/{session_id}/quality", json=quality_payload)
    assert quality_response.status_code == 200

    end_response = client.post(
        f"/sessions/{session_id}/end",
        json={"actor_role": "doctor", "actor_id": "DOC-001"},
    )
    assert end_response.status_code == 200
    assert end_response.json()["status"] == "ended"
