# Trust model and limits

## What is authenticated

Provider registration and customer acceptance bind the named parties to an
immutable policy. Only its two approved monitor transaction senders can submit
snapshot URLs and SHA-256 hashes, once each, within the locked evidence window.
All these writes are blockchain transactions. Hash checking is over raw retrieved
bytes; invalid identity, period, service or record shape is rejected by evaluation.

This is monitor-attested evidence, not a trustless oracle. A hash and submission
timestamp cannot prove when a remote observation happened. Monitor collusion,
shared ownership, fabricated observations, compromised monitor keys and faulty
probe aggregation are outside the proof provided here. Select and audit monitor
operators before accepting an SLA. For stronger future provenance, add frequent
on-chain commitments, signed raw probes and independently timestamped archives.

The snapshot URL host need not match the monitor identity: the approved wallet
explicitly attests to its content hash. Provider incident notes alone do not pass
the two-monitor requirement. Source ownership is not inferred from a hostname.

## Consensus

The leader and validators each retrieve the same hash-pinned snapshots and
independently classify candidate maintenance segments with the locked policy.
Validators compare complete normalized metrics and classification enum arrays;
there is no prose similarity acceptance and no structure-only approval.

Independent classifications may disagree. GenLayer may retry or leave a
transaction undetermined; no state transition should be assumed before finality.
The contract does not map consensus failure to SLA_MET. Fetch/schema/model-format
errors, when agreed, create an explicit INCONCLUSIVE result. A valid model enum
can still be semantically wrong: independently evaluating it reduces but does not
eliminate model error. Prompt injection is a residual risk; text is delimited as
untrusted data, enum output is checked, and arithmetic/window boundaries remain
deterministic.

## Availability and immutability

Either party can open a claim, and anyone can adjudicate/settle it. Monitor
submissions do not require a claim to have been opened, preventing party delay
from blocking timely attestations. A missing monitor, any coverage gap or monitor
disagreement prevents settlement. This favors conservative results over liveness.
A monitor can therefore force INCONCLUSIVE by withholding evidence. There is no
admin override or second evidence round. Agreed retrieval failures are terminal;
use durable redundant hosting before submitting the immutable URL.

A snapshot is retrievable until adjudication, not guaranteed archived forever.
Retain the original bytes and their immutable hosting references for audit.
The fingerprint commits to the policy hash plus the ordered monitor attestations
(including URLs and on-chain submission timestamps); it is not a raw-log Merkle root.

## Bounds

- One future UTC calendar month per policy; a new policy for each month.
- Exactly two monitor addresses; no dynamic quorum or monitor replacement.
- Policy JSON: 16 KiB; exclusion prose: 2,000 characters.
- At most 16 sorted, nonoverlapping maintenance windows with bounded notices.
- At most 512 run-length intervals and 256 KiB raw JSON per monitor snapshot.
- At most 64 agreed-down segments requiring maintenance classification.
- Grace: 60 seconds to seven days. Fixed breach credit: 1 to 10^12 units.
- Any partial-window outage is split at window boundaries before classification.
- Excluded seconds are removed from the availability denominator.

Public HTTPS hostnames only, no credentials, IP literals, local suffixes,
nonstandard ports or URL fragments. This is input hygiene, not a complete SSRF
filter: DNS rebinding and redirects require the GenVM web provider's network
isolation. Snapshot body size is checked after retrieval; the provider must bound
network responses and timeouts. Do not expose privileged network access through
a custom GenVM web provider.

## Settlement and replay

Settlement updates state once and adds credits only to the fixed
provider/customer ledger. There are no external calls or token custody in the
settlement path. Multiple separately accepted policies can represent multiple
agreements; selecting a canonical commercial agreement is an off-chain concern.
Inconclusive claims cannot settle. Off-chain systems should consume only finalized
settlements and track SLA IDs to avoid redeeming the same entitlement twice.

## Validation limits

Tests use real SDK storage and direct-mode web/LLM mocks. They exercise independent
validator callbacks, malicious leader results, evidence tampering, policy timing,
and settlement replay. They do not run a distributed network, prove model quality,
or guarantee compatibility with a future SDK release. The pinned runner header
and generated ABI identify the implementation target. This MVP is unaudited.
