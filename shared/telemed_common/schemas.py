from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Role(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"
    INSURER = "insurance_representative"


class ConsultationType(str, Enum):
    THERAPY = "therapy"
    PEDIATRICS = "pediatrics"
    CARDIOLOGY = "cardiology"
    DERMATOLOGY = "dermatology"
    PSYCHOLOGY = "psychology"


class AppointmentStatus(str, Enum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class SessionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"


class DeviceType(str, Enum):
    BLOOD_PRESSURE = "blood_pressure_monitor"
    GLUCOSE = "glucometer"
    PULSE_OXIMETER = "pulse_oximeter"
    HOLTER = "holter"


class FileAttachment(BaseModel):
    filename: str
    content_type: str
    url: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AppointmentRequest(BaseModel):
    patient_id: str
    doctor_id: str
    consultation_type: ConsultationType
    scheduled_at: datetime
    symptoms: str = ""
    language: str = Field(default="ru", pattern="^(ru|en|kk)$")
    insurance_id: str | None = None
    actor_role: Role = Role.PATIENT


class Appointment(BaseModel):
    appointment_id: str
    patient_id: str
    doctor_id: str
    consultation_type: ConsultationType
    scheduled_at: datetime
    status: AppointmentStatus
    language: str = Field(default="ru", pattern="^(ru|en|kk)$")
    symptoms: str = ""
    payment_required: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VideoSessionRequest(BaseModel):
    appointment_id: str
    patient_id: str
    doctor_id: str
    consent_recording: bool = False
    actor_role: Role


class VideoSession(BaseModel):
    session_id: str
    appointment_id: str
    status: SessionStatus = SessionStatus.PENDING
    webrtc_offer: str | None = None
    webrtc_answer: str | None = None
    selected_media_node: str = "janus-node-1"
    consent_recording: bool = False
    started_at: datetime | None = None
    ended_at: datetime | None = None


class ConnectionQuality(BaseModel):
    session_id: str
    latency_ms: int = Field(ge=0)
    jitter_ms: int = Field(ge=0)
    packet_loss_pct: float = Field(ge=0, le=100)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EMREntry(BaseModel):
    entry_id: str
    patient_id: str
    doctor_id: str
    consultation_type: ConsultationType
    diagnosis: str
    recommendations: str
    prescriptions: list[str] = Field(default_factory=list)
    attachments: list[FileAttachment] = Field(default_factory=list)
    fhir_resource_type: str = "ClinicalImpression"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeviceReading(BaseModel):
    reading_id: str
    patient_id: str
    device_type: DeviceType
    values: dict[str, float]
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = "device"


class CriticalAlert(BaseModel):
    alert_id: str
    patient_id: str
    severity: str = Field(pattern="^(medium|high|critical)$")
    reason: str
    reading: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PaymentRequest(BaseModel):
    appointment_id: str
    patient_id: str
    amount: float = Field(gt=0)
    currency: str = Field(default="RUB", pattern="^(RUB|USD|KZT)$")
    provider: str = "demo-pay"
    actor_role: Role = Role.PATIENT


class PaymentResult(BaseModel):
    transaction_id: str
    appointment_id: str
    status: str = Field(pattern="^(pending|paid|failed|refunded)$")
    amount: float
    currency: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ComplaintAnalysis(BaseModel):
    patient_id: str
    complaint_text: str
    keywords: list[str] = Field(default_factory=list)
    urgency_score: float = Field(ge=0, le=1)
    suggested_specialties: list[ConsultationType] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)


class DoctorRecommendation(BaseModel):
    patient_id: str
    recommended_doctor_id: str
    consultation_type: ConsultationType
    score: float = Field(ge=0, le=1)
    reason: str


class AuditEvent(BaseModel):
    event_id: str
    actor_id: str
    actor_role: Role | str
    action: str
    object_type: str
    object_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConsultationPipelineRequest(BaseModel):
    appointment: AppointmentRequest
    payment: PaymentRequest
    consent_recording: bool = False
    diagnosis: str
    recommendations: str
    prescriptions: list[str] = Field(default_factory=list)
    device_payload: list[DeviceReading] = Field(default_factory=list)
    actor_id: str


class ConsultationPipelineResult(BaseModel):
    appointment: dict[str, Any]
    payment: dict[str, Any]
    session: dict[str, Any]
    emr_entry: dict[str, Any]
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
