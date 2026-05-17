from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from statistics import mean

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.telemed_common import Role, Settings, has_permission

settings = Settings(service_name="analytics-service", service_port=8105)
app = FastAPI(title="TeleMedHub Analytics Service", version="1.0.0")

disease_counter: Counter[str] = Counter()
treatment_scores: list[float] = []
doctor_load: dict[str, int] = defaultdict(int)
consultation_latencies_ms: list[int] = []
service_uptime_samples: list[float] = []

dashboards = {
    "patient": {"widgets": ["next_appointment", "medications", "alerts"]},
    "doctor": {"widgets": ["today_schedule", "critical_patients", "session_quality"]},
    "admin": {"widgets": ["global_kpi", "doctor_load", "billing_summary"]},
    "insurance_representative": {"widgets": ["claims", "covered_cases"]},
}


class AnalyticsIngestRequest(BaseModel):
    diagnosis_code: str
    treatment_effectiveness: float = Field(ge=0, le=1)
    doctor_id: str
    consultation_latency_ms: int = Field(ge=0)
    service_uptime_pct: float = Field(ge=0, le=100)


def _assert_can_read(role: Role) -> None:
    if role not in {Role.DOCTOR, Role.ADMIN, Role.INSURER}:
        raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/analytics/ingest")
async def ingest_metric(request: AnalyticsIngestRequest) -> dict:
    disease_counter[request.diagnosis_code] += 1
    treatment_scores.append(request.treatment_effectiveness)
    doctor_load[request.doctor_id] += 1
    consultation_latencies_ms.append(request.consultation_latency_ms)
    service_uptime_samples.append(request.service_uptime_pct)
    return {"status": "ingested"}


@app.get("/analytics/diseases")
async def disease_stats(limit: int = 20, actor_role: Role = Role.DOCTOR) -> dict:
    _assert_can_read(actor_role)
    return {"top": disease_counter.most_common(limit)}


@app.get("/analytics/treatment")
async def treatment_stats(actor_role: Role = Role.DOCTOR) -> dict:
    _assert_can_read(actor_role)
    avg_score = round(mean(treatment_scores), 3) if treatment_scores else 0.0
    return {"avg_effectiveness": avg_score, "records": len(treatment_scores)}


@app.get("/analytics/doctor-load")
async def doctor_load_stats(actor_role: Role = Role.ADMIN) -> dict:
    if not has_permission(actor_role, "analytics:manage"):
        raise HTTPException(status_code=403, detail="Forbidden")
    sorted_items = sorted(doctor_load.items(), key=lambda item: item[1], reverse=True)
    return {"items": [{"doctor_id": doctor_id, "consultations": count} for doctor_id, count in sorted_items]}


@app.get("/analytics/kpi")
async def kpi(actor_role: Role = Role.ADMIN) -> dict:
    if not has_permission(actor_role, "analytics:manage"):
        raise HTTPException(status_code=403, detail="Forbidden")
    avg_latency = round(mean(consultation_latencies_ms), 1) if consultation_latencies_ms else 0.0
    avg_uptime = round(mean(service_uptime_samples), 3) if service_uptime_samples else 100.0
    return {
        "availability_pct": avg_uptime,
        "availability_target_pct": settings.availability_target,
        "video_latency_ms": avg_latency,
        "video_latency_target_ms": settings.video_target_latency_ms,
        "consultation_capacity_target": settings.concurrent_consultations_target,
        "generated_at": datetime.now(UTC).isoformat(),
    }


@app.get("/dashboards/{role}")
async def role_dashboard(role: str) -> dict:
    return {"role": role, "dashboard": dashboards.get(role, dashboards["doctor"]), "languages": ["ru", "en", "kk"]}
