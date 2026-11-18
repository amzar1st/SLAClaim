#!/usr/bin/env python3
"""Execute all five synthetic scenarios against actual SDK storage in direct mode."""
from local_scenario import run

for scenario in ("met", "breached", "maintenance", "gap", "conflict"):
    claim = run(scenario)
    metrics = claim["result"]["metrics"]
    print(f"{scenario:12s} {metrics['verdict']:14s} credits={claim['settled_units']} state={claim['state']}")
