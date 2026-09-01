# TST Chain v0.7 — Distributed Ledger Prototype

v0.7 introduces the first persistent authoritative ledger for TST protocol/workflow outcomes. It is intentionally a planning-governance ledger prototype, not a cryptocurrency network.

## Ledger semantics

- Append-only entries are chained by SHA-256 predecessor hashes.
- Entry payloads use RFC 8785 JCS before SHA-256 so ordered arrays keep their meaning.
- Accepted workflow transitions and rejected attempts are both persisted; rejection never mutates authoritative state.
- `state-snapshot.json` is only a disposable cache. Authoritative workflow state is recovered by replaying the ledger.
- Duplicate request replay is idempotent and does not append another ledger entry.
- Evidence and provenance records are hash-bound and can be verified later against persisted approved/historical digests.
- S005-style document verification produces a durable `HASH_MISMATCH` result from the approved digest and the current document digest rather than treating file tamper detection as an out-of-band test.

## Checkpoint and finality

A checkpoint commits the actual ledger prefix through a deterministic Merkle root. `quorum_signed` finality requires Ed25519 approvals from an active authority-based validator set. Verification checks both validator signatures and the Merkle root reconstructed from the referenced ledger prefix; a validly signed checkpoint cannot be detached from different ledger contents.

## Verifiable state synchronization

`StateSyncBundle` carries exactly one finalized ledger prefix together with its checkpoint and validator set. Import verifies:

1. bundle hash and schema/version boundary;
2. append-only sequence, predecessor hashes and payload digests;
3. checkpoint hash and Ed25519 quorum;
4. checkpoint Merkle root against the supplied ledger prefix;
5. local-prefix compatibility.

A node rejects a diverging local fork and rejects an older finalized prefix that would roll back a longer local ledger. The synchronized snapshot is regenerated from ledger replay and is never trusted as the authoritative source.

This is still a prototype synchronization model: it transfers a finalized prefix as a bundle rather than implementing peer discovery, streaming block propagation or Byzantine network consensus.

## ReferenceCity end-to-end benchmark

`tools/referencecity_v0_7_benchmark.py` runs ReferenceCity S001–S010 against one persistent ledger and compares every scenario with the pinned ReferenceCity expected outputs. The benchmark includes:

- persistent plan creation, version amendment and review/approval/activation;
- durable unauthorized, missing-signature and optimistic-concurrency rejection paths;
- real approved-vs-tampered document RFC8785-JCS hashing;
- real v0.3 planning-rule evaluation for S006;
- real ReferenceCity geometry → Shapely → SpatialEvaluation → PlanningRule → Workflow execution for S007;
- historical v1 provenance persistence and verification after v2 creation for S009;
- restart/replay recovery followed by quorum-signed Merkle finality.

The pinned benchmark is gated on Python 3.11, 3.12 and 3.13 and currently reaches **10 full / 0 partial / 0 unsupported** under the repository's definition of `full`.

## Prototype boundary / next slices

The local JSONL file is rewritten atomically for prototype safety. The next ledger slices should focus on node identity, checkpoint-chain rules, crash/fault recovery, incremental synchronization and multi-node replication before v0.8 introduces hierarchical/domain partitioning.

## Non-goals

There is no native tradable token, mining, Gas requirement, DeFi primitive or financial consensus incentive in the v0.7 core.
