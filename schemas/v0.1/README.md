# TST Chain Schemas v0.1

Normative JSON Schemas for the Domain Foundation release.

## Core schemas

- `spatial-object.schema.json` — stable territorial-spatial object identity and off-chain references
- `spatial-event.schema.json` — immutable state-transition event
- `evidence.schema.json` — integrity reference to off-chain evidence

## Normative companion documents

- `docs/protocol/v0.1/PROTOCOL.md`
- `docs/protocol/v0.1/COMPATIBILITY.md`
- `docs/protocol/v0.1/TERMS.md`
- `test-vectors/v0.1/hashes.json`

## v0.1 invariants

- `schema_version` is exactly `0.1`.
- protocol-native IDs use the `tst:` namespace.
- all content digests use SHA-256 and lowercase hexadecimal encoding.
- protocol timestamps are UTC (`Z`).
- unknown properties are rejected.
- canonical bytes and hashes follow `TST-C14N-JSON/0.1`.
- language resources never alter protocol fields.

Run:

```bash
python -m pip install -r requirements-dev.txt
python tools/v0_1_conformance.py
```

A conforming implementation must reproduce every bundled test vector.
