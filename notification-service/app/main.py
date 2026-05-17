from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.telemed_common import Role, Settings

settings = Settings(service_name="notification-service", service_port=8106)
app = FastAPI(title="TeleMedHub Notification Service", version="1.0.0")

messages: list[dict] = []

TEXTS = {
    "consultation_start": {
        "ru": "Консультация начинается через 10 минут",
        "en": "Consultation starts in 10 minutes",
        "kk": "Кеңес 10 минуттан кейін басталады",
    },
    "critical_alert": {
        "ru": "Критический показатель пациента",
        "en": "Critical patient indicator",
        "kk": "Пациенттің критикалық көрсеткіші",
    },
    "appointment_confirmed": {
        "ru": "Запись подтверждена",
        "en": "Appointment confirmed",
        "kk": "Жазылу расталды",
    },
}


class NotificationRequest(BaseModel):
    channel: str = Field(pattern="^(push|sms|email|webhook)$")
    recipient: str
    subject: str
    body: str
    language: str = Field(default="ru", pattern="^(ru|en|kk)$")
    actor_role: Role = Role.ADMIN


class TemplateRequest(BaseModel):
    template_key: str
    channel: str = Field(pattern="^(push|sms|email)$")
    recipient: str
    language: str = Field(default="ru", pattern="^(ru|en|kk)$")
    payload: dict = Field(default_factory=dict)
    actor_role: Role = Role.ADMIN


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/notify/send")
async def send_notification(request: NotificationRequest) -> dict:
    if request.actor_role not in {Role.ADMIN, Role.DOCTOR, Role.PATIENT}:
        raise HTTPException(status_code=403, detail="Forbidden")
    item = request.model_dump(mode="json")
    item["id"] = str(uuid4())
    item["created_at"] = datetime.now(UTC).isoformat()
    messages.append(item)
    return {"status": "queued", "id": item["id"]}


@app.post("/notify/template")
async def send_from_template(request: TemplateRequest) -> dict:
    text = TEXTS.get(request.template_key, {}).get(request.language, request.template_key)
    body = f"{text}. {request.payload}"
    item = {
        "id": str(uuid4()),
        "channel": request.channel,
        "recipient": request.recipient,
        "subject": request.template_key,
        "body": body,
        "language": request.language,
        "created_at": datetime.now(UTC).isoformat(),
    }
    messages.append(item)
    return {"status": "queued", "id": item["id"]}


@app.get("/notify/history")
async def history(limit: int = 200) -> dict:
    return {"items": messages[-limit:]}
