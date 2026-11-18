import json
import pytest
from gltest.direct import VMContext
from local_scenario import setup, attest, warp, run, PROVIDER, CUSTOMER, MONITORS, OUTSIDER


@pytest.fixture
def env():
    vm = VMContext()
    with vm.activate():
        contract, policy, sla_id = setup(vm)
        yield vm, contract, policy, sla_id


@pytest.mark.parametrize("scenario,verdict,credit", [("met", "SLA_MET", 0), ("breached", "SLA_BREACHED", 100), ("maintenance", "SLA_MET", 0), ("gap", "INCONCLUSIVE", 0), ("conflict", "INCONCLUSIVE", 0)])
def test_end_to_end(scenario, verdict, credit):
    c = run(scenario)
    assert c["result"]["metrics"]["verdict"] == verdict
    assert c["settled_units"] == credit


def test_missing_monitor_cannot_settle(env):
    vm, c, p, sid = env
    warp(vm, p["end"] + p["evidence_grace"])
    c.open_claim(sid)
    c.adjudicate_claim(sid)
    assert vm.run_validator()
    result = json.loads(c.get_claim(sid))["result"]
    assert result["error"] == "MISSING_MONITOR"
    with vm.expect_revert("Inconclusive"):
        c.settle_claim(sid)


def test_duplicate_settlement_and_open_claim(env):
    vm, c, p, sid = env
    attest(vm, c, p, sid, "breached")
    with vm.expect_revert("One claim"):
        c.open_claim(sid)
    c.adjudicate_claim(sid)
    c.settle_claim(sid)
    assert c.get_credit_balance(PROVIDER, CUSTOMER) == 100
    with vm.expect_revert("already settled"):
        c.settle_claim(sid)
    with vm.expect_revert("already adjudicated"):
        c.adjudicate_claim(sid)
    assert c.get_credit_balance(PROVIDER, CUSTOMER) == 100


def test_evidence_authentication_deadline_and_immutability(env):
    from genlayer import Address
    vm, c, p, sid = env
    warp(vm, p["end"])
    with vm.expect_revert("Approved monitor"):
        c.submit_evidence(sid, "https://monitor.example.com/data", "a" * 64)
    vm.sender = Address(MONITORS[0])
    c.submit_evidence(sid, "https://monitor.example.com/data", "a" * 64)
    with vm.expect_revert("immutable"):
        c.submit_evidence(sid, "https://monitor.example.com/data", "b" * 64)
    vm.sender = Address(MONITORS[1])
    warp(vm, p["end"] + p["evidence_grace"])
    with vm.expect_revert("Evidence window"):
        c.submit_evidence(sid, "https://monitor.example.com/data", "b" * 64)


def test_premature_calls_and_authorization(env):
    from genlayer import Address
    vm, c, p, sid = env
    with vm.expect_revert("not ended"):
        c.open_claim(sid)
    vm.sender = Address(OUTSIDER)
    with vm.expect_revert("SLA party"):
        c.open_claim(sid)
    with vm.expect_revert("Customer only"):
        c.accept_sla(sid)
    vm.sender = Address(CUSTOMER)
    warp(vm, p["end"])
    c.open_claim(sid)
    with vm.expect_revert("deadline"):
        c.adjudicate_claim(sid)


def test_hash_mismatch_and_validator_rejects_forgery(env):
    vm, c, p, sid = env
    attest(vm, c, p, sid, "met")
    c.adjudicate_claim(sid)
    assert vm.run_validator()
    forged = {"metrics": {"verdict": "SLA_BREACHED"}, "classifications": []}
    assert vm.run_validator(leader_result=forged) is False
    assert vm.run_validator(leader_error=ValueError("failed")) is False
    vm.clear_mocks()
    vm.mock_web("https://monitor-1.example.com", {"status": 200, "body": "changed"})
    assert vm.run_validator() is False


@pytest.mark.parametrize("label,verdict", [("COUNTED", "SLA_BREACHED"), ("UNKNOWN", "INCONCLUSIVE"), ("EXCLUDED", "SLA_MET")])
def test_maintenance_decisions(env, label, verdict):
    vm, c, p, sid = env
    attest(vm, c, p, sid, "maintenance")
    vm.mock_llm("You adjudicate", json.dumps({"labels": [label]}))
    c.adjudicate_claim(sid)
    assert vm.run_validator()
    assert json.loads(c.get_claim(sid))["result"]["metrics"]["verdict"] == verdict
    vm.clear_mocks()
    # Missing evidence now must cause disagreement rather than trusting the leader.
    assert vm.run_validator() is False


@pytest.mark.parametrize("answer", [{"labels": []}, {"labels": ["SLA_MET"]}, {"labels": ["EXCLUDED"], "extra": True}, ["EXCLUDED"]])
def test_invalid_llm_fails_closed(env, answer):
    vm, c, p, sid = env
    attest(vm, c, p, sid, "maintenance")
    vm.mock_llm("You adjudicate", json.dumps(answer))
    c.adjudicate_claim(sid)
    assert json.loads(c.get_claim(sid))["result"]["metrics"]["verdict"] == "INCONCLUSIVE"


@pytest.mark.parametrize("mutate", [
    lambda s: s.update(service="https://wrong.example.com"),
    lambda s: s.update(monitor=OUTSIDER),
    lambda s: s["records"][0].update(end=s["start"]),
    lambda s: s["records"][0].update(status="healthy"),
    lambda s: s.update(start=True),
])
def test_malformed_snapshots_are_inconclusive(env, mutate):
    vm, c, p, sid = env
    def transform(i, body):
        s = json.loads(body)
        if i == 0:
            mutate(s)
        return json.dumps(s).encode()
    attest(vm, c, p, sid, "met", transform)
    c.adjudicate_claim(sid)
    assert vm.run_validator()
    assert json.loads(c.get_claim(sid))["result"]["metrics"]["verdict"] == "INCONCLUSIVE"


def test_exact_threshold_and_rounding(env):
    import sys
    vm, c, p, sid = env
    mod = sys.modules[type(c).__module__]
    # Synthetic arithmetic period isolates exact equality and one-second overflow.
    policy = dict(p, start=0, end=1000000, maintenance=[])
    for downtime, verdict in [(999, "SLA_MET"), (1000, "SLA_MET"), (1001, "SLA_BREACHED")]:
        timeline = [{"start": 0, "end": downtime, "status": "down", "window": None}, {"start": downtime, "end": 1000000, "status": "up", "window": None}]
        result = mod.calculate(policy, timeline, [])
        assert result["verdict"] == verdict
        assert result["downtime_seconds"] == downtime


def test_interval_union_and_partial_maintenance(env):
    import sys
    vm, c, p, sid = env
    mod = sys.modules[type(c).__module__]
    policy = dict(p, start=0, end=100, maintenance=[{"start": 20, "end": 30, "notice": "Upgrade"}])
    a = {"records": [{"start": 0, "end": 40, "status": "down", "notes": "Upgrade"}, {"start": 40, "end": 100, "status": "up", "notes": ""}]}
    b = {"records": [{"start": 0, "end": 10, "status": "down", "notes": "Upgrade"}, {"start": 10, "end": 40, "status": "down", "notes": "Upgrade"}, {"start": 40, "end": 100, "status": "up", "notes": ""}]}
    timeline = mod.segments(policy, [a, b])
    result = mod.calculate(policy, timeline, ["EXCLUDED"])
    assert sum(s["end"] - s["start"] for s in timeline) == 100
    assert result["excluded_seconds"] == 10
    assert result["downtime_seconds"] == 30
    assert result["eligible_seconds"] == 90


def test_fully_excluded_period_is_inconclusive(env):
    import sys
    vm, c, p, sid = env
    mod = sys.modules[type(c).__module__]
    result = mod.calculate(dict(p, start=0, end=100), [{"start": 0, "end": 100, "status": "down", "window": {}}], ["EXCLUDED"])
    assert result["verdict"] == "INCONCLUSIVE"
    assert result["availability_ppm"] is None


def test_no_retroactive_policy_or_late_acceptance(env):
    from genlayer import Address
    vm, c, p, sid = env
    vm.sender = Address(PROVIDER)
    sid2 = c.register_sla(json.dumps(p))
    warp(vm, p["start"])
    with vm.expect_revert("Register before"):
        c.register_sla(json.dumps(p))
    vm.sender = Address(CUSTOMER)
    with vm.expect_revert("Acceptance closed"):
        c.accept_sla(sid2)
    warp(vm, p["end"])
    with vm.expect_revert("not accepted"):
        c.open_claim(sid2)


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(target_ppm=True),
    lambda p: p.update(target_ppm=1000001),
    lambda p: p.update(monitors=[MONITORS[0]] * 2),
    lambda p: p.update(customer=PROVIDER),
    lambda p: p.update(start=p["start"] + 1),
    lambda p: p.update(evidence_grace=0),
    lambda p: p.update(service="http://api.example.com"),
    lambda p: p.update(service="https://127.0.0.1/private"),
    lambda p: p.update(service="https://user:password@api.example.com"),
])
def test_invalid_policies_rejected(env, mutate):
    from genlayer import Address
    vm, c, p, sid = env
    vm.sender = Address(PROVIDER)
    mutate(p)
    with vm.expect_revert():
        c.register_sla(json.dumps(p))


def test_hash_mismatch_creates_explicit_inconclusive(env):
    vm, c, p, sid = env
    attest(vm, c, p, sid, "met")
    vm.clear_mocks()
    vm.mock_web("https://monitor-1.example.com", {"status": 200, "body": "changed bytes"})
    c.adjudicate_claim(sid)
    assert vm.run_validator()
    result = json.loads(c.get_claim(sid))["result"]
    assert result["error"] == "EVIDENCE_HASH_MISMATCH"
    assert result["metrics"]["verdict"] == "INCONCLUSIVE"


def test_validator_rejects_different_maintenance_answer(env):
    vm, c, p, sid = env
    attest(vm, c, p, sid, "maintenance")
    vm.mock_llm("You adjudicate", json.dumps({"labels": ["EXCLUDED"]}))
    c.adjudicate_claim(sid)
    vm._llm_mocks.clear()
    vm.mock_llm("You adjudicate", json.dumps({"labels": ["COUNTED"]}))
    assert vm.run_validator() is False
