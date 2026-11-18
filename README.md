# SLAClaim

**Historical uptime claims, independently checked by GenLayer validators.**

SLAClaim locks a monthly API availability policy, authenticates two monitoring
operators through their transaction senders, retrieves hash-pinned historical
snapshots, and decides `SLA_MET`, `SLA_BREACHED`, or `INCONCLUSIVE`.
When an outage overlaps preannounced maintenance, validators independently use
AI to interpret incident notes against the locked exclusion policy. Exact integer
arithmetic determines availability and compensation.

This MVP settles **service-credit units recorded on chain**. It does not hold GEN,
transfer tokens, or certify legal compliance. A credit is an accounting entitlement
against the named provider, redeemable outside this contract.

## Run locally

Python 3.12 is required. No wallet, RPC, API key, or paid service is needed for the demo.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
genvm-lint check contracts/slaclaim.py
python -m pytest
python scripts/demo.py
```

GenLayer's direct-mode harness downloads the SDK on first use. The demo executes
the actual contract with SDK storage and mocked web/AI responses; it is not a live
network deployment or a demonstration of real LLM consensus.

Expected demo:

```text
met          SLA_MET        credits=0 state=SETTLED
breached     SLA_BREACHED   credits=100 state=SETTLED
maintenance  SLA_MET        credits=0 state=SETTLED
gap          INCONCLUSIVE   credits=0 state=ADJUDICATED
conflict     INCONCLUSIVE   credits=0 state=ADJUDICATED
```

## Deploy in Studio

1. Open [GenLayer Studio](https://studio-next.genlayer.com/).
2. Load the complete `contracts/slaclaim.py` file. Deploy `SLAClaim` with **no constructor arguments**.
3. Follow [the deployment walkthrough](docs/DEPLOYMENT.md) with separate provider,
   customer, and monitor accounts. Every write must reach network finality before
   a dependent action or external credit redemption.

There are no administrator keys, mutable policies, privileged verdict overrides,
or upgrade methods. The contract is a single file suitable for Studio. The
SDK runner is pinned in its first line; the ABI is in `docs/abi.json`.

## Claim lifecycle

| Step | Caller | Behavior |
| --- | --- | --- |
| `register_sla(policy_json)` | Provider | Locks service, one future UTC month, customer, two monitor wallets, threshold, windows, exclusions, deadline and credit |
| `accept_sla(sla_id)` | Named customer | Accepts before the month begins |
| `open_claim(sla_id)` | Either party | Opens exactly one claim after the month ends |
| `submit_evidence(sla_id, url, sha256)` | Each approved monitor | Attests to exact hosted snapshot bytes during the evidence grace period; may precede claim opening |
| `adjudicate_claim(sla_id)` | Anyone | After deadline, fetches both snapshots and reaches validator agreement |
| `settle_claim(sla_id)` | Anyone | Adds the fixed service credit once on breach; records zero on met; refuses inconclusive |
| Views | Anyone | `get_sla`, `get_claim`, `get_evidence`, `get_credit_balance` |

Views return canonical JSON strings except `get_credit_balance`, which returns an
integer. IDs are numeric strings starting at `"1"`. A new month needs a new SLA ID.

## Evidence and calculation

- Exactly two distinct monitor wallets are locked before service starts. Neither
  can equal provider or customer. The customer explicitly accepts this trust set.
- A monitor transaction authenticates authorship; SHA-256 pins the **raw HTTP
  response body bytes**. Validators download and verify each independently.
- Records are run-length encoded, half-open UTC Unix-second intervals `[start,end)`.
  Each monitor reports `up`, `down`, or `unknown`. Gaps, disagreement, inaccessible
  snapshots, malformed evidence, and ambiguous maintenance fail closed.
- The built-in measurement convention is HTTPS GET of the locked health endpoint:
  2xx response within 10 seconds is `up`, a failed probe is `down`, and absent or
  unreliable measurement is `unknown`. Operators must agree on probe cadence and
  derive conservative intervals from their logs. The MVP verifies their **attested
  intervals**, not individual HTTP requests or every instant of physical uptime.
- Only windows locked before the period can be excluded. AI cannot expand a
  window, invent an outage duration, change the target, or award credits. Both
  monitor notes must support the maintenance exclusion.
- All time is counted once using the union of interval boundaries, even if the
  monitors use different interval sizes. Maintenance boundaries split records.
- Eligible seconds = month seconds − excluded maintenance seconds. Downtime uses
  only agreed `down` seconds not excluded. Any unknown seconds make the whole
  claim `INCONCLUSIVE`, even when known downtime already exceeds the target.
- Breach iff `downtime × 1,000,000 > eligible × (1,000,000 − target_ppm)`.
  Equality meets the SLA. Displayed availability is rounded down; the verdict
  uses exact integer arithmetic. An entirely excluded period is inconclusive.

For 99.9%, set `target_ppm` to `999000`. For a 30-day month without exclusions,
the allowance is exactly 2,592 seconds, or 43 minutes 12 seconds.

## Project contents

| Path | Purpose |
| --- | --- |
| `contracts/slaclaim.py` | Deployable Intelligent Contract and calculation logic |
| `tests/` | SDK direct-mode lifecycle, security, arithmetic and validator checks |
| `scripts/demo.py` | Five executable mocked scenarios |
| `scripts/evidence.py` | Hash raw snapshots and print submission arguments |
| `scripts/make_examples.py` | Generate synthetic data for the next UTC month |
| `examples/` | Fixed December 2026 synthetic policy and monitor snapshots |
| `docs/DEPLOYMENT.md` | Studio deployment and complete call sequence |
| `docs/SECURITY.md` | Trust assumptions, resource limits and failure behavior |
| `.github/workflows/ci.yml` | Automated SDK validation, tests and demo |

## Scope and trust

Two wallets do not prove two independent organizations. The parties must select
real monitoring operators and verify their independence outside the contract.
An authenticated snapshot proves who attested to its hash and when; it does not
prove the observations happened at their claimed times. This MVP uses trusted
monitor attestations submitted after the month ends, not continuous timestamp
commitments or cryptographic hardware proofs. The provider's status page alone
cannot qualify as evidence.

Inconclusive results are terminal for that locked policy. They do not settle and
cannot be overwritten with later evidence; resolution is outside this MVP.
Network-level consensus failure leaves the transaction undetermined and state
unchanged, rather than fabricating a verdict. See [security details](docs/SECURITY.md).

Built against the official [storage](https://docs.genlayer.com/developers/intelligent-contracts/features/storage),
[web access](https://docs.genlayer.com/developers/intelligent-contracts/features/web-access),
[Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle),
and [direct testing](https://docs.genlayer.com/api-references/genlayer-test/direct)
interfaces. MIT licensed.
