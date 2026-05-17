from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.telemed_common import (
    AppointmentRequest,
    ConsultationPipelineResult,
    DeviceType,
    Role,
    Settings,
    analyze_complaint,
    recommend_doctor_by_symptoms,
    sign_token,
    verify_token,
)


class GatewaySettings(BaseSettings):
    service_name: str = "api-gateway"
    service_port: int = 8100
    appointment_service_url: str = "http://appointment-service:8101"
    consultation_service_url: str = "http://consultation-service:8102"
    emr_service_url: str = "http://emr-service:8103"
    device_service_url: str = "http://device-integration:8104"
    analytics_service_url: str = "http://analytics-service:8105"
    notification_service_url: str = "http://notification-service:8106"
    billing_service_url: str = "http://billing-service:8107"
    jwt_secret: str = Settings().jwt_secret
    token_exp_minutes: int = 120

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = GatewaySettings()
app = FastAPI(title="TeleMedHub API Gateway", version="1.0.0")


class AuthRequest(BaseModel):
    user_id: str
    role: Role
    language: str = Field(default="ru", pattern="^(ru|en|kk)$")


class DoctorRecommendationRequest(BaseModel):
    patient_id: str
    complaint_text: str
    actor_role: Role = Role.PATIENT


class PipelineDeviceItem(BaseModel):
    device_type: DeviceType
    values: dict[str, float]


class ConsultationPipelineRequest(BaseModel):
    appointment: AppointmentRequest
    payment_amount: float = Field(gt=0)
    diagnosis: str
    recommendations: str
    prescriptions: list[str] = Field(default_factory=list)
    consent_recording: bool = False
    device_payload: list[PipelineDeviceItem] = Field(default_factory=list)
    transcript: str | None = None
    actor_id: str


def _service_urls() -> dict[str, str]:
    return {
        "appointment": settings.appointment_service_url,
        "consultation": settings.consultation_service_url,
        "emr": settings.emr_service_url,
        "device": settings.device_service_url,
        "analytics": settings.analytics_service_url,
        "notification": settings.notification_service_url,
        "billing": settings.billing_service_url,
    }


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(url, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/auth/token")
async def issue_token(request: AuthRequest) -> dict:
    token = sign_token(
        {
            "sub": request.user_id,
            "role": request.role.value,
            "language": request.language,
        },
        settings.jwt_secret,
        exp_minutes=settings.token_exp_minutes,
    )
    return {"access_token": token, "token_type": "Bearer"}


@app.post("/auth/verify")
async def verify_auth(token: str) -> dict:
    payload = verify_token(token, settings.jwt_secret)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


@app.get("/services/health")
async def services_health() -> dict:
    urls = _service_urls()
    timeout = httpx.Timeout(6.0, connect=2.0)
    result: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=timeout) as client:
        for name, base_url in urls.items():
            try:
                response = await client.get(f"{base_url}/health")
                result[name] = {"status_code": response.status_code, "body": response.json()}
            except Exception as exc:
                result[name] = {"status": "unreachable", "error": str(exc)}
    return result


@app.post("/recommend/doctor")
async def recommend_doctor(request: DoctorRecommendationRequest) -> dict:
    if request.actor_role not in {Role.PATIENT, Role.ADMIN, Role.DOCTOR}:
        raise HTTPException(status_code=403, detail="Forbidden")

    analysis = analyze_complaint(request.patient_id, request.complaint_text)
    doctors = [
        {
            "doctor_id": "DOC-001",
            "consultation_type": "therapy",
            "specialties": ["кашель", "температура", "cough"],
            "rating": 4.9,
            "experience_years": 15,
            "online": True,
        },
        {
            "doctor_id": "DOC-002",
            "consultation_type": "cardiology",
            "specialties": ["давление", "сердце", "пульс", "heart"],
            "rating": 4.8,
            "experience_years": 18,
            "online": True,
        },
        {
            "doctor_id": "DOC-003",
            "consultation_type": "dermatology",
            "specialties": ["rash", "кожа", "сыпь"],
            "rating": 4.7,
            "experience_years": 11,
            "online": True,
        },
    ]
    recommendation = recommend_doctor_by_symptoms(request.patient_id, analysis.keywords, doctors)
    return {"analysis": analysis.model_dump(mode="json"), "recommendation": recommendation.model_dump(mode="json")}


@app.post("/workflow/consultation", response_model=ConsultationPipelineResult)
async def consultation_pipeline(request: ConsultationPipelineRequest) -> ConsultationPipelineResult:
    urls = _service_urls()
    timeout = httpx.Timeout(20.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        appointment_payload = request.appointment.model_dump(mode="json")
        appointment = await _post_json(client, f"{urls['appointment']}/appointments", appointment_payload)

        payment = await _post_json(
            client,
            f"{urls['billing']}/payments/charge",
            {
                "appointment_id": appointment["appointment_id"],
                "patient_id": request.appointment.patient_id,
                "amount": request.payment_amount,
                "currency": "RUB",
                "provider": "telemed-demo-pay",
                "actor_role": request.appointment.actor_role.value,
            },
        )

        await _post_json(
            client,
            f"{urls['appointment']}/appointments/{appointment['appointment_id']}/confirm",
            {"actor_id": "ADMIN-SYSTEM", "actor_role": Role.ADMIN.value},
        )

        session = await _post_json(
            client,
            f"{urls['consultation']}/sessions/start",
            {
                "appointment_id": appointment["appointment_id"],
                "patient_id": appointment["patient_id"],
                "doctor_id": appointment["doctor_id"],
                "consent_recording": request.consent_recording,
                "actor_role": Role.DOCTOR.value,
            },
        )

        alerts: list[dict[str, Any]] = []
        for item in request.device_payload:
            device_resp = await _post_json(
                client,
                f"{urls['device']}/devices/readings",
                {
                    "patient_id": appointment["patient_id"],
                    "device_type": item.device_type.value,
                    "values": item.values,
                    "actor_id": appointment["patient_id"],
                    "actor_role": Role.PATIENT.value,
                },
            )
            alerts.extend(device_resp.get("critical_alerts", []))

        if request.transcript:
            await _post_json(
                client,
                f"{urls['consultation']}/speech/protocol",
                {
                    "actor_id": appointment["doctor_id"],
                    "actor_role": Role.DOCTOR.value,
                    "transcript": request.transcript,
                },
            )

        await _post_json(
            client,
            f"{urls['emr']}/assignments",
            {
                "doctor_id": appointment["doctor_id"],
                "patient_id": appointment["patient_id"],
                "actor_id": "ADMIN-SYSTEM",
                "actor_role": Role.ADMIN.value,
            },
        )

        emr_entry = await _post_json(
            client,
            f"{urls['emr']}/emr/entries",
            {
                "patient_id": appointment["patient_id"],
                "doctor_id": appointment["doctor_id"],
                "consultation_type": appointment["consultation_type"],
                "diagnosis": request.diagnosis,
                "recommendations": request.recommendations,
                "prescriptions": request.prescriptions,
                "attachments": [],
                "actor_id": appointment["doctor_id"],
                "actor_role": Role.DOCTOR.value,
            },
        )

        await _post_json(
            client,
            f"{urls['consultation']}/sessions/{session['session_id']}/end",
            {"actor_role": Role.DOCTOR.value, "actor_id": appointment["doctor_id"]},
        )

        await _post_json(
            client,
            f"{urls['notification']}/notify/template",
            {
                "template_key": "appointment_confirmed",
                "channel": "push",
                "recipient": appointment["patient_id"],
                "language": appointment.get("language", "ru"),
                "payload": {"appointment_id": appointment["appointment_id"]},
                "actor_role": Role.ADMIN.value,
            },
        )

        if alerts:
            await _post_json(
                client,
                f"{urls['notification']}/notify/template",
                {
                    "template_key": "critical_alert",
                    "channel": "sms",
                    "recipient": appointment["doctor_id"],
                    "language": appointment.get("language", "ru"),
                    "payload": {"count": len(alerts)},
                    "actor_role": Role.DOCTOR.value,
                },
            )

        await _post_json(
            client,
            f"{urls['analytics']}/analytics/ingest",
            {
                "diagnosis_code": request.diagnosis[:20],
                "treatment_effectiveness": 0.8,
                "doctor_id": appointment["doctor_id"],
                "consultation_latency_ms": 130,
                "service_uptime_pct": 99.93,
            },
        )

    return ConsultationPipelineResult(
        appointment=appointment,
        payment=payment,
        session=session,
        emr_entry=emr_entry,
        alerts=alerts,
        completed_at=datetime.now(UTC),
    )
