from __future__ import annotations

import time
from collections import defaultdict
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.telemed_common import (
    EMREntry,
    FileAttachment,
    Role,
    Settings,
    TTLCache,
    build_audit_event,
    can_access_patient_data,
    decrypt_field,
    encrypt_field,
    has_permission,
)

settings = Settings(service_name="emr-service", service_port=8103)
app = FastAPI(title="TeleMedHub EMR Service", version="1.0.0")

emr_by_patient: dict[str, list[EMREntry]] = defaultdict(list)
audit_log: list[dict] = []
access_log: list[dict] = []
assigned_patients: dict[str, set[str]] = defaultdict(set)
emr_cache = TTLCache(ttl_seconds=120)


class SaveEMRRequest(BaseModel):
    patient_id: str
    doctor_id: str
    consultation_type: str
    diagnosis: str
    recommendations: str
    prescriptions: list[str] = Field(default_factory=list)
    attachments: list[FileAttachment] = Field(default_factory=list)
    actor_id: str
    actor_role: Role


class ReadEMRRequest(BaseModel):
    actor_id: str
    actor_role: Role
    reveal_sensitive: bool = False


class AssignDoctorRequest(BaseModel):
    doctor_id: str
    patient_id: str
    actor_id: str
    actor_role: Role


def _log_access(actor_id: str, actor_role: Role, patient_id: str, action: str, allowed: bool) -> None:
    access_log.append(
        {
            "access_id": str(uuid4()),
            "actor_id": actor_id,
            "actor_role": actor_role.value,
            "patient_id": patient_id,
            "action": action,
            "allowed": allowed,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/assignments")
async def assign_doctor(request: AssignDoctorRequest) -> dict:
    if request.actor_role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin can assign doctors")
    assigned_patients[request.doctor_id].add(request.patient_id)
    event = build_audit_event(
        actor_id=request.actor_id,
        actor_role=request.actor_role,
        action="emr.assign_doctor",
        object_type="assignment",
        object_id=f"{request.doctor_id}:{request.patient_id}",
    )
    audit_log.append(event.model_dump(mode="json"))
    return {"status": "assigned"}


@app.post("/emr/entries")
async def save_emr_entry(request: SaveEMRRequest) -> dict:
    if not has_permission(request.actor_role, "emr:write:assigned") and request.actor_role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    if request.actor_role == Role.DOCTOR and request.patient_id not in assigned_patients.get(request.doctor_id, set()):
        raise HTTPException(status_code=403, detail="Doctor is not assigned to patient")

    entry = EMREntry(
        entry_id=str(uuid4()),
        patient_id=request.patient_id,
        doctor_id=request.doctor_id,
        consultation_type=request.consultation_type,
        diagnosis=encrypt_field(request.diagnosis, settings.encryption_key),
        recommendations=encrypt_field(request.recommendations, settings.encryption_key),
        prescriptions=request.prescriptions,
        attachments=request.attachments,
        created_at=datetime.now(UTC),
    )
    emr_by_patient[request.patient_id].append(entry)
    emr_cache.set(request.patient_id, [item.model_dump(mode="json") for item in emr_by_patient[request.patient_id]])

    event = build_audit_event(
        actor_id=request.actor_id,
        actor_role=request.actor_role,
        action="emr.create_entry",
        object_type="emr_entry",
        object_id=entry.entry_id,
        details={"patient_id": request.patient_id},
    )
    audit_log.append(event.model_dump(mode="json"))
    return entry.model_dump(mode="json")


@app.post("/emr/patient/{patient_id}")
async def get_patient_emr(patient_id: str, request: ReadEMRRequest) -> dict:
    allowed = can_access_patient_data(
        request.actor_role,
        actor_id=request.actor_id,
        patient_id=patient_id,
        assigned_patient_ids=assigned_patients.get(request.actor_id, set()),
    )
    _log_access(request.actor_id, request.actor_role, patient_id, "emr.read", allowed)
    if not allowed:
        raise HTTPException(status_code=403, detail="Forbidden")

    started = time.perf_counter()
    cached = emr_cache.get(patient_id)
    if cached is not None:
        records = cached
    else:
        records = [item.model_dump(mode="json") for item in emr_by_patient.get(patient_id, [])]
        emr_cache.set(patient_id, records)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    if request.reveal_sensitive:
        decrypted = []
        for item in records:
            copy = dict(item)
            copy["diagnosis"] = decrypt_field(copy["diagnosis"], settings.encryption_key)
            copy["recommendations"] = decrypt_field(copy["recommendations"], settings.encryption_key)
            decrypted.append(copy)
        records = decrypted

    return {
        "patient_id": patient_id,
        "elapsed_ms": elapsed_ms,
        "target_ms": settings.emr_target_load_ms,
        "target_met": elapsed_ms <= settings.emr_target_load_ms,
        "items": records,
    }


@app.get("/emr/fhir/{patient_id}")
async def fhir_bundle(patient_id: str, actor_id: str, actor_role: Role) -> dict:
    allowed = can_access_patient_data(
        actor_role,
        actor_id=actor_id,
        patient_id=patient_id,
        assigned_patient_ids=assigned_patients.get(actor_id, set()),
    )
    _log_access(actor_id, actor_role, patient_id, "emr.fhir_read", allowed)
    if not allowed:
        raise HTTPException(status_code=403, detail="Forbidden")

    entries = emr_by_patient.get(patient_id, [])
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "ClinicalImpression",
                    "id": entry.entry_id,
                    "subject": {"reference": f"Patient/{entry.patient_id}"},
                    "assessor": {"reference": f"Practitioner/{entry.doctor_id}"},
                    "date": entry.created_at.isoformat(),
                    "summary": decrypt_field(entry.diagnosis, settings.encryption_key),
                    "description": decrypt_field(entry.recommendations, settings.encryption_key),
                }
            }
            for entry in entries
        ],
    }
    return bundle


@app.get("/emr/timeline/{patient_id}")
async def timeline(patient_id: str, actor_id: str, actor_role: Role) -> dict:
    allowed = can_access_patient_data(
        actor_role,
        actor_id=actor_id,
        patient_id=patient_id,
        assigned_patient_ids=assigned_patients.get(actor_id, set()),
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Forbidden")
    items = [
        {
            "date": entry.created_at.isoformat(),
            "consultation_type": str(entry.consultation_type),
            "doctor_id": entry.doctor_id,
            "entry_id": entry.entry_id,
        }
        for entry in emr_by_patient.get(patient_id, [])
    ]
    return {"patient_id": patient_id, "timeline": items}


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict:
    if not has_permission(actor_role, "audit:read"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"items": audit_log[-limit:]}


@app.get("/access-log")
async def get_access_log(limit: int = 200, actor_role: Role = Role.ADMIN) -> dict:
    if not has_permission(actor_role, "audit:read"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"items": access_log[-limit:]}
