# TST Chain v0.2 — Trust & Authority Schemas

v0.2 adds verifiable identity, key, credential, authority, authorization, signature, and audit objects on top of the v0.1 domain foundation.

## Schemas

- `actor.schema.json` — person, organization, or service identity.
- `public-key.schema.json` — Ed25519 public key lifecycle and rotation links.
- `authority.schema.json` — scoped authority assertion issued to an actor.
- `credential.schema.json` — issuer/subject credential payload.
- `signature.schema.json` — detached Ed25519 proof over a canonical payload.
- `authorization-request.schema.json` — normalized authorization context.
- `authorization-decision.schema.json` — deterministic policy result.
- `audit-record.schema.json` — append-oriented security/audit record.

## Cryptographic profile

v0.2 fixes the reference signing profile to:

- canonicalization: `TST-C14N-JSON/0.1`
- payload digest: SHA-256
- signature algorithm: Ed25519
- key/signature encoding: unpadded base64url
- signature preimage: `UTF8("TSTCHAIN-SIGNATURE-V0.2") || 0x00 || canonical_payload_bytes`

The domain separator is mandatory.

## Authority boundary

An `Authority` object is a digitally verifiable assertion used by TST Chain. It does **not** create statutory or administrative power by itself. Production deployments must map authority records to legally valid organizational, administrative, or contractual sources.

## Reference authorization policy

`TST-AUTHZ/0.2` evaluates:

1. actor status;
2. authority subject;
3. authority lifecycle;
4. requested permission;
5. jurisdiction scope;
6. object-type scope;
7. required credential types, trusted credential issuers, and credential lifecycle.

A deployment may use a stricter policy, but must not silently reinterpret an `allow` decision generated under another policy version.

## Test data

All examples in `examples/v0.2` are synthetic. The deterministic private seeds in `test-vectors/v0.2` exist only to make cross-implementation signature vectors reproducible and must never be used in production.
