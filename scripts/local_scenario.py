"""Shared direct-mode demo setup. All network and AI responses are mocked."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from gltest.direct import VMContext, deploy_contract

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = "0x" + "1" * 40
CUSTOMER = "0x" + "2" * 40
MONITORS = ["0x" + c * 40 for c in ("3", "4")]
OUTSIDER = "0x" + "5" * 40


def warp(vm, timestamp):
    vm.warp(datetime.fromtimestamp(timestamp, timezone.utc).isoformat())


def setup(vm):
    vm.warp("2026-11-18T00:00:00+00:00")
    contract = deploy_contract(ROOT / "contracts/slaclaim.py", vm, sdk_version="v0.2.16")
    from genlayer import Address
    vm.sender = Address(PROVIDER)
    policy = json.loads((ROOT / "examples/policy.json").read_text())
    # Fixed examples are Dec 2026. Tests don't depend on the host clock.
    sla_id = contract.register_sla(json.dumps(policy))
    vm.sender = Address(CUSTOMER)
    contract.accept_sla(sla_id)
    return contract, policy, sla_id


def attest(vm, contract, policy, sla_id, scenario, transform=None):
    from genlayer import Address
    warp(vm, policy["end"])
    for i, monitor in enumerate(MONITORS):
        body = (ROOT / f"examples/{scenario}-monitor-{i + 1}.json").read_bytes()
        if transform:
            body = transform(i, body)
        url = f"https://monitor-{i + 1}.example.com/evidence/{scenario}.json"
        vm.sender = Address(monitor)
        contract.submit_evidence(sla_id, url, hashlib.sha256(body).hexdigest())
        vm.mock_web(url, {"status": 200, "body": body.decode()})
    vm.sender = Address(CUSTOMER)
    contract.open_claim(sla_id)
    warp(vm, policy["end"] + policy["evidence_grace"])


def run(scenario):
    vm = VMContext()
    with vm.activate():
        contract, policy, sla_id = setup(vm)
        attest(vm, contract, policy, sla_id, scenario)
        vm.mock_llm("You adjudicate", json.dumps({"labels": ["EXCLUDED"]}))
        contract.adjudicate_claim(sla_id)
        assert vm.run_validator() is True
        claim = json.loads(contract.get_claim(sla_id))
        if claim["result"]["metrics"]["verdict"] != "INCONCLUSIVE":
            contract.settle_claim(sla_id)
        return json.loads(contract.get_claim(sla_id))
