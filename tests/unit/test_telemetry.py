from shared.telemed_common.schemas import DeviceType
from shared.telemed_common.telemetry import detect_critical_readings


def test_detect_critical_spo2() -> None:
    alerts = detect_critical_readings("PAT-1", DeviceType.PULSE_OXIMETER, {"spo2": 86, "heart_rate": 110})
    assert len(alerts) == 1
    assert alerts[0].severity == "critical"


def test_no_alert_for_normal_values() -> None:
    alerts = detect_critical_readings("PAT-1", DeviceType.BLOOD_PRESSURE, {"systolic": 128, "diastolic": 82})
    assert alerts == []
