#!/usr/bin/env python3
"""Create synthetic demo fixtures for the next UTC calendar month."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def generate(output, now=None):
    now = now or datetime.now(timezone.utc)
    year, month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    start = int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp())
    end = int(datetime(next_year, next_month, 1, tzinfo=timezone.utc).timestamp())
    customer = "0x" + "2" * 40
    monitors = ["0x" + c * 40 for c in ("3", "4")]
    policy = {"service": "https://api.example.com/health", "customer": customer, "monitors": monitors, "start": start, "end": end, "target_ppm": 999000, "credit_units": 100, "evidence_grace": 86400, "exclusion_policy": "Only preannounced maintenance corroborated by both monitors is excluded.", "maintenance": [{"start": start + 7200, "end": start + 10800, "notice": "Scheduled database upgrade announced before the period."}]}
    output.mkdir(parents=True, exist_ok=True)
    (output / "policy.json").write_text(json.dumps(policy, indent=2) + "\n")
    for scenario in ("met", "breached", "maintenance", "gap", "conflict"):
        for i, monitor in enumerate(monitors):
            if scenario == "met" or (scenario == "conflict" and i == 1):
                records = [(start, end, "up", "Monitoring healthy")]
            elif scenario == "maintenance":
                records = [(start, start + 7200, "up", "Healthy"), (start + 7200, start + 10800, "down", "Scheduled database upgrade observed; matches announced maintenance."), (start + 10800, end, "up", "Recovered")]
            elif scenario == "gap":
                records = [(start + 60, end, "up", "First minute missing")]
            else:
                records = [(start, start + 3600, "down", "Connection timeout; unscheduled outage"), (start + 3600, end, "up", "Recovered")]
            snapshot = {"schema": "slaclaim/v1", "service": policy["service"], "monitor": monitor, "start": start, "end": end, "records": [dict(zip(("start", "end", "status", "notes"), r)) for r in records]}
            (output / f"{scenario}-monitor-{i + 1}.json").write_text(json.dumps(snapshot, indent=2) + "\n")
    return policy


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("examples"))
    args = parser.parse_args()
    generate(args.output)
    print(f"Synthetic examples written to {args.output}. Replace example wallet addresses for live use.")
