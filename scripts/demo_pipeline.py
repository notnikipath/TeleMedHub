from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import httpx


async def run_demo() -> None:
    payload = {
        "appointment": {
            "patient_id": "PAT-0001",
            "doctor_id": "DOC-001",
            "consultation_type": "cardiology",
            "scheduled_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "symptoms": "Высокое давление и учащенный пульс",
            "language": "ru",
            "actor_role": "patient",
        },
        "payment_amount": 2500.0,
        "diagnosis": "Артериальная гипертензия, плановый контроль",
        "recommendations": "Ежедневный мониторинг давления, контроль у кардиолога",
        "prescriptions": ["Лозартан 50мг 1 раз в день"],
        "consent_recording": True,
        "device_payload": [
            {"device_type": "blood_pressure_monitor", "values": {"systolic": 165, "diastolic": 101}},
            {"device_type": "holter", "values": {"heart_rate": 105}},
        ],
        "transcript": "Пациент жалуется на давление. Пульс повышен. Назначен контроль и терапия.",
        "actor_id": "PAT-0001",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post("http://localhost:8180/workflow/consultation", json=payload)
        response.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    asyncio.run(run_demo())
