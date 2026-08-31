# TST Chain v0.2 Trust & Authority Protocol

## 1. Purpose

v0.2 answers two questions that v0.1 intentionally leaves open:

1. **Who produced or approved a trusted event?**
2. **Was that actor authorized for the requested action, scope, and time?**

The protocol separates identity, cryptographic proof, credentials, and authority so that later planning workflows can compose them without embedding legal semantics into the ledger.

## 2. Core model

```text
Actor
  ├─ PublicKey
  │    └─ DetachedSignature
  ├─ Credential
  └─ Authority
        ↓
AuthorizationRequest
        ↓ TST-AUTHZ/0.2
AuthorizationDecision
        ↓
AuditRecord
```

## 3. Actor

`Actor` represents a person, organization, or service. Display names are descriptive; `actor_id` is the protocol identity anchor.

An organization can therefore sign credentials and authorities in exactly the same cryptographic model as a person or service, while deployments remain free to map that identity to local registries.

## 4. Keys and rotation

v0.2 supports Ed25519 only.

A key record includes lifecycle state and an optional `predecessor_key_id`. Rotation is represented by publishing a new key record that points to the former key. Revocation is explicit.

A verifier must reject a signature when the referenced key is revoked, expired, not yet valid, or outside its validity interval even if the underlying Ed25519 signature is mathematically valid.

## 5. Detached signatures

Signatures are detached from payloads to avoid recursive canonicalization.

The exact signing bytes are:

```text
UTF8("TSTCHAIN-SIGNATURE-V0.2") || 0x00 || TST-C14N-JSON/0.1(payload)
```

The `payload_digest` is SHA-256 of the canonical payload bytes only; it does not include the domain separator.

## 6. Credentials

Credentials bind:

- issuer actor;
- subject actor;
- credential type;
- scalar claims;
- validity interval;
- lifecycle status.

Credential payloads should be paired with a detached signature from the issuer's valid key.

v0.2 intentionally limits claim values to strings, integers, booleans, or null. Arbitrary floating-point values are excluded from this profile so that cross-language number serialization does not weaken deterministic hashing.

## 7. Authority

An authority record binds:

- subject actor;
- issuer actor;
- role;
- explicit permission strings;
- jurisdiction scope;
- object-type scope;
- credential requirements with explicit trusted issuer actors;
- validity interval and status;
- external basis references.

`Authority` is a protocol assertion, not a source of administrative power.

## 8. Authorization policy

The reference `TST-AUTHZ/0.2` policy uses exact matching for jurisdiction references and object types. Hierarchical administrative-code interpretation belongs to future interoperability profiles rather than the trust core.

An authorization result is always explicit `allow` or `deny`, includes a stable reason code, and lists the authority/credential records actually evaluated.

## 9. Reason codes

### Authorization

| Code | Meaning |
|---|---|
| `TST-AUTH-000` | allowed |
| `TST-AUTH-001` | actor inactive |
| `TST-AUTH-002` | no authority for actor |
| `TST-AUTH-003` | authority inactive |
| `TST-AUTH-004` | authority outside validity window |
| `TST-AUTH-005` | permission missing |
| `TST-AUTH-006` | jurisdiction outside scope |
| `TST-AUTH-007` | object type outside scope |
| `TST-AUTH-008` | required credential missing |
| `TST-AUTH-009` | credential inactive |
| `TST-AUTH-010` | credential outside validity window |

### Signatures

| Code | Meaning |
|---|---|
| `TST-SIG-000` | valid signature |
| `TST-SIG-001` | key not found |
| `TST-SIG-002` | key inactive/revoked |
| `TST-SIG-003` | key outside validity window |
| `TST-SIG-004` | payload digest mismatch |
| `TST-SIG-005` | invalid Ed25519 signature |
| `TST-SIG-006` | unsupported algorithm/profile |
| `TST-SIG-007` | signer actor does not match key or expected issuer |

## 10. Audit records

Authorization and signature verification should emit append-oriented audit records. Sensitive details should be kept off-chain when necessary; an optional digest can commit to external audit detail without exposing it.

## 11. ReferenceCity

`ReferenceCity` will become the richer integration dataset when its repository is ready. v0.2 conformance intentionally uses small synthetic fixtures so protocol development does not depend on the city dataset's completion.
