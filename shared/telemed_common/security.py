from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from .schemas import Role

PERMISSIONS: dict[Role, set[str]] = {
    Role.PATIENT: {
        "appointment:create",
        "appointment:read:own",
        "consultation:join:own",
        "emr:read:own",
        "billing:pay:own",
        "device:write:own",
    },
    Role.DOCTOR: {
        "appointment:read:assigned",
        "consultation:start:assigned",
        "consultation:write:assigned",
        "emr:write:assigned",
        "emr:read:assigned",
        "analytics:read",
    },
    Role.ADMIN: {
        "appointment:manage",
        "consultation:manage",
        "emr:manage",
        "device:manage",
        "analytics:manage",
        "audit:read",
        "notification:manage",
    },
    Role.INSURER: {
        "billing:read:covered",
        "billing:approve:covered",
        "appointment:read:covered",
    },
}


def has_permission(role: Role | str, action: str) -> bool:
    normalized = Role(role) if isinstance(role, str) else role
    return action in PERMISSIONS.get(normalized, set())


def _derive_signing_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def sign_token(payload: dict[str, Any], secret: str, exp_minutes: int = 120) -> str:
    data = dict(payload)
    data["exp"] = int((datetime.now(UTC) + timedelta(minutes=exp_minutes)).timestamp())
    encoded_payload = base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode("utf-8")).decode("ascii")
    signature = hmac.new(_derive_signing_key(secret), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    encoded_sig = base64.urlsafe_b64encode(signature).decode("ascii")
    return f"{encoded_payload}.{encoded_sig}"


def verify_token(token: str, secret: str) -> dict[str, Any] | None:
    try:
        payload_part, signature_part = token.split(".", maxsplit=1)
        expected_sig = hmac.new(_derive_signing_key(secret), payload_part.encode("ascii"), hashlib.sha256).digest()
        decoded_sig = base64.urlsafe_b64decode(signature_part.encode("ascii"))
        if not hmac.compare_digest(expected_sig, decoded_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_part.encode("ascii")).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(datetime.now(UTC).timestamp()):
            return None
        return payload
    except Exception:
        return None


def encrypt_field(value: str, key: str) -> str:
    if not value:
        return value
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    raw = value.encode("utf-8")
    encrypted = bytes([raw[idx] ^ digest[idx % len(digest)] for idx in range(len(raw))])
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_field(value: str, key: str) -> str:
    if not value:
        return value
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    encrypted = base64.urlsafe_b64decode(value.encode("ascii"))
    raw = bytes([encrypted[idx] ^ digest[idx % len(digest)] for idx in range(len(encrypted))])
    return raw.decode("utf-8")


def can_access_patient_data(
    role: Role | str,
    actor_id: str,
    patient_id: str,
    assigned_patient_ids: set[str] | None = None,
) -> bool:
    normalized = Role(role) if isinstance(role, str) else role
    if normalized == Role.ADMIN:
        return True
    if normalized == Role.PATIENT:
        return actor_id == patient_id
    if normalized == Role.DOCTOR:
        return patient_id in (assigned_patient_ids or set())
    if normalized == Role.INSURER:
        return False
    return False
