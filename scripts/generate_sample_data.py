from __future__ import annotations

import argparse
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

CONSULTATION_TYPES = ["therapy", "pediatrics", "cardiology", "dermatology", "psychology"]
SYMPTOMS = [
    "кашель и температура",
    "головная боль",
    "перепады давления",
    "сыпь на коже",
    "тревожность и бессонница",
]


def generate(output: Path, count: int = 3000) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    base_time = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    rows = []
    for idx in range(1, count + 1):
        rows.append(
            {
                "appointment_id": f"APP-{idx:06d}",
                "patient_id": f"PAT-{idx % 1200:04d}",
                "doctor_id": f"DOC-{idx % 80:03d}",
                "consultation_type": random.choice(CONSULTATION_TYPES),
                "scheduled_at": (base_time + timedelta(minutes=30 * (idx % 400))).isoformat(),
                "symptoms": random.choice(SYMPTOMS),
                "language": random.choice(["ru", "en", "kk"]),
            }
        )
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {output} with {len(rows)} rows")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate TeleMedHub sample appointments")
    parser.add_argument("--output", type=Path, default=Path("data/samples/appointments.json"))
    parser.add_argument("--count", type=int, default=3000)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate(args.output, args.count)
