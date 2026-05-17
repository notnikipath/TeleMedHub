from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.telemed_common import (
    Appointment,
    AppointmentRequest,
    AppointmentStatus,
    ConsultationType,
    Role,
    Settings,
    build_audit_event,
    has_permission,
)

settings = Settings(service_name="appointment-service", service_port=8101)
app = FastAPI(title="TeleMedHub Appointment Service", version="1.0.0")

appointments: dict[str, Appointment] = {}
audit_log: list[dict] = []
doctor_slots: dict[str, list[str]] = defaultdict(list)

for doctor_num in range(1, 16):
    doctor_id = f"DOC-{doctor_num:03d}"
    base = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
    doctor_slots[doctor_id] = [(base + timedelta(minutes=30 * idx)).isoformat() for idx in range(12)]


class ConfirmRequest(BaseModel):
    actor_id: str
    actor_role: Role


class CancelRequest(BaseModel):
    actor_id: str
    actor_role: Role
    reason: str = ""


class SymptomQuestionnaireRequest(BaseModel):
    patient_id: str
    answers: dict[str, str]
    actor_role: Role = Role.PATIENT


ConfirmRequest.model_rebuild()
CancelRequest.model_rebuild()
SymptomQuestionnaireRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _append_audit(
    actor_id: str,
    actor_role: Role,
    action: str,
    object_type: str,
    object_id: str,
    details: dict | None = None,
) -> None:
    event = build_audit_event(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        object_type=object_type,
        object_id=object_id,
        details=details or {},
    )
    audit_log.append(event.model_dump(mode="json"))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/doctors/{doctor_id}/calendar")
async def doctor_calendar(doctor_id: str, day: date | None = None) -> dict:
    slots = doctor_slots.get(doctor_id, [])
    if day is None:
        return {"doctor_id": doctor_id, "slots": slots}
    day_prefix = day.isoformat()
    return {"doctor_id": doctor_id, "slots": [slot for slot in slots if slot.startswith(day_prefix)]}


@app.post("/appointments")
async def create_appointment(request: AppointmentRequest) -> dict:
    _assert_permission(request.actor_role, "appointment:create")
    if request.scheduled_at.isoformat() not in doctor_slots.get(request.doctor_id, []):
        raise HTTPException(status_code=409, detail="Requested timeslot is unavailable")

    appointment_id = str(uuid4())
    item = Appointment(
        appointment_id=appointment_id,
        patient_id=request.patient_id,
        doctor_id=request.doctor_id,
        consultation_type=request.consultation_type,
        scheduled_at=request.scheduled_at,
        status=AppointmentStatus.REQUESTED,
        language=request.language,
        symptoms=request.symptoms,
    )
    appointments[appointment_id] = item
    _append_audit(
        actor_id=request.patient_id,
        actor_role=request.actor_role,
        action="appointment.create",
        object_type="appointment",
        object_id=appointment_id,
        details={"doctor_id": request.doctor_id, "scheduled_at": request.scheduled_at.isoformat()},
    )
    return item.model_dump(mode="json")


@app.post("/appointments/{appointment_id}/confirm")
async def confirm_appointment(appointment_id: str, request: ConfirmRequest) -> dict:
    _assert_permission(request.actor_role, "appointment:manage")
    appointment = appointments.get(appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appointment.status = AppointmentStatus.CONFIRMED
    _append_audit(
        actor_id=request.actor_id,
        actor_role=request.actor_role,
        action="appointment.confirm",
        object_type="appointment",
        object_id=appointment_id,
    )
    return appointment.model_dump(mode="json")


@app.post("/appointments/{appointment_id}/cancel")
async def cancel_appointment(appointment_id: str, request: CancelRequest) -> dict:
    appointment = appointments.get(appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    own_record = appointment.patient_id == request.actor_id
    if not own_record and not has_permission(request.actor_role, "appointment:manage"):
        raise HTTPException(status_code=403, detail="Forbidden")

    appointment.status = AppointmentStatus.CANCELLED
    _append_audit(
        actor_id=request.actor_id,
        actor_role=request.actor_role,
        action="appointment.cancel",
        object_type="appointment",
        object_id=appointment_id,
        details={"reason": request.reason},
    )
    return appointment.model_dump(mode="json")


@app.get("/appointments/{appointment_id}")
async def get_appointment(appointment_id: str, actor_id: str, actor_role: Role) -> dict:
    appointment = appointments.get(appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    own_patient = appointment.patient_id == actor_id and actor_role == Role.PATIENT
    own_doctor = appointment.doctor_id == actor_id and actor_role == Role.DOCTOR
    if not (own_patient or own_doctor or actor_role in {Role.ADMIN, Role.INSURER}):
        raise HTTPException(status_code=403, detail="Forbidden")
    return appointment.model_dump(mode="json")


@app.get("/appointments")
async def list_appointments(
    actor_id: str,
    actor_role: Role,
    patient_id: str | None = None,
    doctor_id: str | None = None,
    status: AppointmentStatus | None = None,
) -> dict:
    items = []
    for appointment in appointments.values():
        if patient_id and appointment.patient_id != patient_id:
            continue
        if doctor_id and appointment.doctor_id != doctor_id:
            continue
        if status and appointment.status != status:
            continue

        if actor_role == Role.PATIENT and appointment.patient_id != actor_id:
            continue
        if actor_role == Role.DOCTOR and appointment.doctor_id != actor_id:
            continue
        items.append(appointment.model_dump(mode="json"))
    return {"items": items}


@app.get("/reminders/due")
async def reminders_due(within_minutes: int = 30) -> dict:
    now = datetime.now(UTC)
    deadline = now + timedelta(minutes=within_minutes)
    reminders = []
    for appointment in appointments.values():
        if appointment.status != AppointmentStatus.CONFIRMED:
            continue
        if now <= appointment.scheduled_at <= deadline:
            reminders.append(
                {
                    "appointment_id": appointment.appointment_id,
                    "patient_id": appointment.patient_id,
                    "doctor_id": appointment.doctor_id,
                    "scheduled_at": appointment.scheduled_at.isoformat(),
                }
            )
    return {"items": reminders}


@app.post("/symptoms/questionnaire")
async def symptoms_questionnaire(request: SymptomQuestionnaireRequest) -> dict:
    _assert_permission(request.actor_role, "appointment:create")
    pain_scale = int(request.answers.get("pain_scale", "0"))
    fever = request.answers.get("fever", "no")
    cough = request.answers.get("cough", "no")
    emergency = pain_scale >= 8 or fever == "high"
    recommended_type = ConsultationType.THERAPY
    if request.answers.get("child_age"):
        recommended_type = ConsultationType.PEDIATRICS
    if "rash" in request.answers.get("main_symptom", "").lower():
        recommended_type = ConsultationType.DERMATOLOGY
    if "anxiety" in request.answers.get("main_symptom", "").lower():
        recommended_type = ConsultationType.PSYCHOLOGY

    return {
        "patient_id": request.patient_id,
        "recommended_consultation_type": recommended_type.value,
        "risk_level": "high" if emergency else "normal",
        "summary": {"pain_scale": pain_scale, "fever": fever, "cough": cough},
    }


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
