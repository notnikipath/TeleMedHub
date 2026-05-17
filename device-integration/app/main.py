from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from statistics import mean
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.telemed_common import DeviceReading, DeviceType, Role, Settings, detect_critical_readings, has_permission

settings = Settings(service_name="device-integration", service_port=8104)
app = FastAPI(title="TeleMedHub Device Integration Service", version="1.0.0")

registered_devices: dict[str, list[dict]] = defaultdict(list)
readings_by_patient: dict[str, list[dict]] = defaultdict(list)
critical_alerts: list[dict] = []


class RegisterDeviceRequest(BaseModel):
    patient_id: str
    device_type: DeviceType
    serial_number: str
    actor_id: str
    actor_role: Role


class ReadingRequest(BaseModel):
    patient_id: str
    device_type: DeviceType
    values: dict[str, float]
    actor_id: str
    actor_role: Role


class BulkReadingRequest(BaseModel):
    items: list[ReadingRequest]
    concurrency: int = Field(default=32, ge=1, le=128)


def _ensure_device_access(request: ReadingRequest) -> None:
    if request.actor_role == Role.PATIENT and request.actor_id != request.patient_id:
        raise HTTPException(status_code=403, detail="Patient can send only own readings")
    if request.actor_role == Role.DOCTOR and not has_permission(request.actor_role, "consultation:write:assigned"):
        raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/devices/register")
async def register_device(request: RegisterDeviceRequest) -> dict:
    if request.actor_role not in {Role.PATIENT, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Only patient/admin can register device")
    device = {
        "device_id": str(uuid4()),
        "patient_id": request.patient_id,
        "device_type": request.device_type.value,
        "serial_number": request.serial_number,
        "registered_at": datetime.now(UTC).isoformat(),
    }
    registered_devices[request.patient_id].append(device)
    return device


@app.post("/devices/readings")
async def ingest_reading(request: ReadingRequest) -> dict:
    _ensure_device_access(request)
    reading = DeviceReading(
        reading_id=str(uuid4()),
        patient_id=request.patient_id,
        device_type=request.device_type,
        values=request.values,
        captured_at=datetime.now(UTC),
    ).model_dump(mode="json")
    readings_by_patient[request.patient_id].append(reading)

    alerts = detect_critical_readings(request.patient_id, request.device_type, request.values)
    for alert in alerts:
        critical_alerts.append(alert.model_dump(mode="json"))

    return {"reading": reading, "critical_alerts": [alert.model_dump(mode="json") for alert in alerts]}


@app.post("/devices/readings/bulk")
async def ingest_bulk(request: BulkReadingRequest) -> dict:
    sem = asyncio.Semaphore(request.concurrency)

    async def _worker(item: ReadingRequest) -> dict:
        async with sem:
            return await ingest_reading(item)

    results = await asyncio.gather(*[_worker(item) for item in request.items], return_exceptions=True)
    success = sum(1 for item in results if isinstance(item, dict))
    failed = len(results) - success
    return {"total": len(request.items), "success": success, "failed": failed}


@app.get("/devices/{patient_id}")
async def list_patient_devices(patient_id: str, actor_id: str, actor_role: Role) -> dict:
    if actor_role == Role.PATIENT and actor_id != patient_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"items": registered_devices.get(patient_id, [])}


@app.get("/devices/trends/{patient_id}")
async def trends(patient_id: str, actor_id: str, actor_role: Role, metric: str = "systolic") -> dict:
    if actor_role == Role.PATIENT and actor_id != patient_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    readings = readings_by_patient.get(patient_id, [])
    values = [item["values"].get(metric) for item in readings if metric in item["values"]]
    values = [value for value in values if value is not None]
    if not values:
        return {"patient_id": patient_id, "metric": metric, "trend": "no_data", "avg": None}
    trend = "up" if values[-1] > values[0] else "down" if values[-1] < values[0] else "flat"
    return {
        "patient_id": patient_id,
        "metric": metric,
        "count": len(values),
        "avg": round(mean(values), 2),
        "min": min(values),
        "max": max(values),
        "trend": trend,
    }


@app.get("/alerts/critical")
async def list_alerts(patient_id: str | None = None, actor_role: Role = Role.DOCTOR) -> dict:
    if actor_role not in {Role.DOCTOR, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Forbidden")
    if patient_id:
        return {"items": [item for item in critical_alerts if item["patient_id"] == patient_id]}
    return {"items": critical_alerts}
