# TST Chain v0.7 — Distributed Ledger Prototype

v0.7 introduces the first persistent authoritative ledger for TST protocol/workflow outcomes. It is intentionally a planning-governance ledger prototype, not a cryptocurrency network.

## Ledger semantics

- Append-only entries are chained by SHA-256 predecessor hashes.
- Entry payloads use RFC 8785 JCS before SHA-256 so ordered arrays keep their meaning.
- Accepted workflow transitions and rejected attempts are both persisted; rejection never mutates authoritative state.
- `state-snapshot.json` is only a disposable cache. Authoritative workflow state is recovered by replaying the ledger.
- Duplicate request replay is idempotent and does not append another ledger entry.
- Evidence records are payload-hash bound, enabling tamper detection.

## Checkpoint and finality

A checkpoint commits all entry hashes through a deterministic Merkle root. `quorum_signed` finality requires Ed25519 approvals from an active authority-based validator set. A checkpoint below quorum is not final.

The reference implementation rewrites the local JSONL file atomically for prototype safety. This is not the final storage engine or multi-node replication design; v0.7 follow-up slices will add state synchronization, node identity, fault/recovery protocols and the full ReferenceCity benchmark runner.

## Non-goals

There is no native tradable token, mining, Gas requirement, DeFi primitive or financial consensus incentive in the v0.7 core.
