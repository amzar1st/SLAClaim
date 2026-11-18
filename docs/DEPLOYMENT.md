# Deployment and operation

## Accounts and preparation

Use four distinct funded test accounts: provider, customer, monitor A and monitor
B. A deployment account can also be the provider. Never put private keys in the
repository or snapshot files. The monitors should be operated independently.

Deploy `contracts/slaclaim.py` in https://studio-next.genlayer.com/ with no
constructor arguments. Record the returned contract address and network.
This project does not include a fabricated deployment address.

`examples/policy.json` is a synthetic December 2026 policy. Replace customer and
monitor addresses with your actual accounts and the service with your public
health endpoint. The reporting period must be a future complete UTC calendar
month. You can regenerate examples with `python scripts/make_examples.py`; the
checked-in tests use the fixed December fixtures, so keep regenerated files
separate with `--output /tmp/slaclaim-examples` when running those tests.

The policy cannot be edited after registration. Maintenance windows and notices
must already be known. If a policy is wrong, register a new one and do not accept
the incorrect one. Duplicated policies are independent agreements and may create
separate credit entitlements; agree on the canonical SLA ID outside the contract.

## Studio call sequence

1. **Provider:** call `register_sla` with the entire policy file contents as the
   string `policy_json`. The first returned SLA ID is `"1"`.
2. **Customer:** call `accept_sla("1")` before `start`. Inspect `get_sla("1")` and
   verify the policy hash, provider, service, monitor wallets, target and credit.
3. **Monitors:** independently collect measurements throughout the month using
   the measurement convention in the README. Export each operator's own records
   as `slaclaim/v1`. Preserve missing observations as gaps or `unknown`; never fill
   them with `up`. A snapshot must identify the exact service URL, period and
   monitor wallet.
4. **After end, before end + evidence_grace:** host each snapshot at an immutable
   public HTTPS URL, preferably a GitHub raw URL pinned to a full commit SHA or
   immutable object version. The response must be UTF-8 JSON with no login wall.
   Generate arguments:

   ```bash
   python scripts/evidence.py examples/breached-monitor-1.json \
     --sla-id 1 \
     --url https://monitor.example.com/immutable/month.json
   ```

   Each monitor sends `submit_evidence` from its own wallet using the printed
   arguments. The URL above is a placeholder. Upload real bytes before submitting.
   Whitespace and trailing newline changes alter the hash. A monitor cannot
   replace its attestation, including a mistaken one.
5. **Either party, after end:** call `open_claim("1")`. This may happen before or
   after monitor submissions. Anyone can inspect `get_evidence("1")`.
6. **After end + evidence_grace:** call `adjudicate_claim("1")`. Anyone may do so.
   Wait for FINALIZED. Inspect `get_claim("1")` for metrics, classification labels,
   policy hash, evidence fingerprint and errors. Labels correspond in chronological
   order to agreed-down timeline segments inside locked maintenance windows.
7. **For SLA_MET or SLA_BREACHED:** call `settle_claim("1")`, wait for FINALIZED,
   then inspect `get_credit_balance(provider, customer)`. Breach adds exactly
   `credit_units`; met adds zero. Repeated settlement reverts.

Credits are service entitlements in an on-chain ledger, not GEN or ERC-20 tokens.
There is no deposit, withdrawal, transfer, expiry or credit redemption method.
An off-chain provider billing process can redeem finalized credits once under its
own controls. No such external billing action is performed by this project.

## Demo timing

The normal contract enforces actual future registration, month-end and evidence
deadlines. Do not weaken these checks to accelerate a public demo. `python
scripts/demo.py` uses the official SDK direct-mode time-warp mechanism to execute
all five synthetic scenarios immediately without modifying production checks.
It mocks the monitoring evidence and LLM classifications. For real validation,
run the full sequence on the target network with actual monitors, publicly hosted
evidence and configured validator LLM providers.

## Verification before external use

Run `genvm-lint check`, the tests and demo first. Deploy and exercise the intended
network separately; local direct mode cannot prove network finality, validator
availability, endpoint reachability or real LLM agreement. No deployed network
contract is claimed by this repository.
