"""Shared business primitives for TeleMedHub microservices."""

from .audit import build_audit_event
from .cache import TTLCache
from .nlp import analyze_complaint, speech_to_protocol
from .recommender import recommend_doctor_by_symptoms
from .schemas import (
    Appointment,
    AppointmentRequest,
    AppointmentStatus,
    AuditEvent,
    ComplaintAnalysis,
    ConnectionQuality,
    ConsultationPipelineRequest,
    ConsultationPipelineResult,
    ConsultationType,
    CriticalAlert,
    DeviceReading,
    DeviceType,
    DoctorRecommendation,
    EMREntry,
    FileAttachment,
    PaymentRequest,
    PaymentResult,
    Role,
    SessionStatus,
    VideoSession,
    VideoSessionRequest,
)
from .security import (
    can_access_patient_data,
    decrypt_field,
    encrypt_field,
    has_permission,
    sign_token,
    verify_token,
)
from .settings import Settings
from .telemetry import detect_critical_readings

__all__ = [
    "Appointment",
    "AppointmentRequest",
    "AppointmentStatus",
    "AuditEvent",
    "ComplaintAnalysis",
    "ConnectionQuality",
    "ConsultationPipelineRequest",
    "ConsultationPipelineResult",
    "ConsultationType",
    "CriticalAlert",
    "DeviceReading",
    "DeviceType",
    "DoctorRecommendation",
    "EMREntry",
    "FileAttachment",
    "PaymentRequest",
    "PaymentResult",
    "Role",
    "SessionStatus",
    "Settings",
    "TTLCache",
    "VideoSession",
    "VideoSessionRequest",
    "analyze_complaint",
    "build_audit_event",
    "can_access_patient_data",
    "decrypt_field",
    "detect_critical_readings",
    "encrypt_field",
    "has_permission",
    "recommend_doctor_by_symptoms",
    "sign_token",
    "speech_to_protocol",
    "verify_token",
]
