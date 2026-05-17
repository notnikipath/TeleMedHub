from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.telemed_common import PaymentRequest, PaymentResult, Role, Settings, has_permission

settings = Settings(service_name="billing-service", service_port=8107)
app = FastAPI(title="TeleMedHub Billing Service", version="1.0.0")

payments: dict[str, dict] = {}
insurance_claims: list[dict] = []


class InsuranceClaimRequest(BaseModel):
    appointment_id: str
    patient_id: str
    insurance_company: str
    policy_number: str
    amount: float = Field(gt=0)
    actor_role: Role = Role.INSURER


class RefundRequest(BaseModel):
    transaction_id: str
    actor_role: Role = Role.ADMIN
    reason: str = ""


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/payments/charge")
async def charge(request: PaymentRequest) -> dict:
    if request.actor_role == Role.PATIENT and not has_permission(request.actor_role, "billing:pay:own"):
        raise HTTPException(status_code=403, detail="Forbidden")

    transaction_id = str(uuid4())
    result = PaymentResult(
        transaction_id=transaction_id,
        appointment_id=request.appointment_id,
        status="paid",
        amount=request.amount,
        currency=request.currency,
        created_at=datetime.now(UTC),
    )
    payments[transaction_id] = {
        **result.model_dump(mode="json"),
        "patient_id": request.patient_id,
        "provider": request.provider,
    }
    return payments[transaction_id]


@app.get("/payments/{transaction_id}")
async def get_payment(transaction_id: str, actor_role: Role = Role.ADMIN) -> dict:
    if actor_role not in {Role.ADMIN, Role.INSURER, Role.PATIENT}:
        raise HTTPException(status_code=403, detail="Forbidden")
    item = payments.get(transaction_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return item


@app.post("/payments/refund")
async def refund(request: RefundRequest) -> dict:
    if request.actor_role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin can refund")
    payment = payments.get(request.transaction_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    payment["status"] = "refunded"
    payment["refund_reason"] = request.reason
    payment["refunded_at"] = datetime.now(UTC).isoformat()
    return payment


@app.post("/insurance/claim")
async def insurance_claim(request: InsuranceClaimRequest) -> dict:
    if request.actor_role not in {Role.INSURER, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Forbidden")
    claim = {
        "claim_id": str(uuid4()),
        "appointment_id": request.appointment_id,
        "patient_id": request.patient_id,
        "insurance_company": request.insurance_company,
        "policy_number": request.policy_number,
        "amount": request.amount,
        "status": "approved",
        "created_at": datetime.now(UTC).isoformat(),
    }
    insurance_claims.append(claim)
    return claim


@app.get("/insurance/claims")
async def list_claims(actor_role: Role = Role.INSURER) -> dict:
    if actor_role not in {Role.INSURER, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"items": insurance_claims}
