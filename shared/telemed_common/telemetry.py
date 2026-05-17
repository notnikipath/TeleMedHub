from __future__ import annotations

from uuid import uuid4

from .schemas import CriticalAlert, DeviceType


def detect_critical_readings(
    patient_id: str,
    device_type: DeviceType | str,
    values: dict[str, float],
) -> list[CriticalAlert]:
    normalized = DeviceType(device_type) if isinstance(device_type, str) else device_type
    alerts: list[CriticalAlert] = []

    if normalized == DeviceType.BLOOD_PRESSURE:
        systolic = values.get("systolic", 0)
        diastolic = values.get("diastolic", 0)
        if systolic >= 180 or diastolic >= 120:
            alerts.append(
                CriticalAlert(
                    alert_id=str(uuid4()),
                    patient_id=patient_id,
                    severity="critical",
                    reason="Hypertensive crisis threshold exceeded",
                    reading=values,
                )
            )

    if normalized == DeviceType.GLUCOSE:
        glucose = values.get("glucose_mmol_l", 0)
        if glucose <= 3.0 or glucose >= 13.5:
            alerts.append(
                CriticalAlert(
                    alert_id=str(uuid4()),
                    patient_id=patient_id,
                    severity="high",
                    reason="Glucose out of safe range",
                    reading=values,
                )
            )

    if normalized == DeviceType.PULSE_OXIMETER:
        spo2 = values.get("spo2", 100)
        if spo2 < 90:
            alerts.append(
                CriticalAlert(
                    alert_id=str(uuid4()),
                    patient_id=patient_id,
                    severity="critical",
                    reason="Low oxygen saturation",
                    reading=values,
                )
            )

    if normalized == DeviceType.HOLTER:
        hr = values.get("heart_rate", 70)
        if hr < 40 or hr > 140:
            alerts.append(
                CriticalAlert(
                    alert_id=str(uuid4()),
                    patient_id=patient_id,
                    severity="high",
                    reason="Abnormal heart rate detected from Holter stream",
                    reading=values,
                )
            )

    return alerts
