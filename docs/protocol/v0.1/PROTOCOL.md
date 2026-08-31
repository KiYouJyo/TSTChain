# TST Chain Protocol v0.1

> Territorial Spatial Trust Chain — Domain Foundation

This document defines the interoperable core of TST Chain v0.1. It is intentionally small: `SpatialObject`, `SpatialEvent`, `Evidence`, deterministic canonicalization, and content hashing.

## 1. Scope

v0.1 defines how a territorial-spatial object, an event affecting it, and external evidence are represented and hashed. It does **not** define validator consensus, administrative authorization, planning-rule execution, or production deployment.

## 2. Core objects

### SpatialObject

A stable protocol identity for a territorial-spatial object. Large geometry, GIS, BIM, imagery, documents, and databases remain off-chain and are referenced through `external_refs`.

### Evidence

A verifiable reference to off-chain material. `content_digest` hashes the referenced content, not the Evidence JSON object itself.

### SpatialEvent

An immutable statement that an actor caused or recorded a state transition concerning a SpatialObject. The v0.1 actor identifier is only an identifier; authority and signature verification are introduced in v0.2.

## 3. Identifier profile

Protocol-native IDs use lowercase TST prefixes:

- `tst:object:<namespace>:<local-id>`
- `tst:event:<namespace>:<local-id>`
- `tst:evidence:<namespace>:<local-id>`
- `tst:actor:<namespace>:<local-id>`
- other references may use `tst:<namespace>:...`

IDs are protocol identifiers, not legal identifiers and not proof of authority.

## 4. TST-C14N-JSON/0.1

TST v0.1 hash-bearing objects are normalized before hashing.

1. Input MUST be valid JSON and MUST NOT contain duplicate object keys.
2. All object keys and string values are normalized to Unicode NFC.
3. v0.1 core protocol instances MUST NOT contain JSON number values.
4. All arrays in the three v0.1 core schemas have set semantics. Their normalized elements are sorted by the UTF-8 bytes of each element's canonical JSON form.
5. Objects are serialized with keys in ascending Unicode order, no insignificant whitespace, UTF-8 encoding, and no BOM.
6. String escaping follows normal JSON shortest escaping. Non-ASCII Unicode is encoded directly as UTF-8.
7. `null` and an omitted property are distinct and therefore produce different hashes.

The result is called the **canonical bytes**.

The profile is deliberately narrower than a general JSON canonicalization standard. Future schemas that require ordered arrays or numeric domain values MUST introduce an explicit canonicalization rule rather than silently changing v0.1 behavior.

## 5. Content hash

The v0.1 content hash is:

`lowercase_hex(SHA-256(canonical_bytes))`

Every `contentDigest` structure in v0.1 uses:

```json
{
  "algorithm": "sha256",
  "digest": "<64 lowercase hexadecimal characters>"
}
```

## 6. Off-chain data rule

TST Chain does not place large planning data directly into the protocol object.

Keep off-chain:

- GIS datasets and geometries
- GeoTIFF and remote-sensing imagery
- BIM / IFC / RVT / CAD models
- PDFs and planning archives
- databases and sensor streams

Place in the trust layer:

- stable IDs
- content hashes
- source references
- versions
- events
- provenance relations
- later, signatures and authority proofs

## 7. Language rule

Protocol field names, identifier prefixes, enum-like machine values, and hash inputs are language-neutral machine keys. `zh-CN`, `ja-JP`, and `en-US` resources are presentation assets only and MUST NOT change protocol semantics.

## 8. Interoperability requirement

A conforming implementation MUST reproduce the hashes in `test-vectors/v0.1/hashes.json`.

In particular, the two SpatialObject example files deliberately differ in property and array ordering but MUST normalize to the same canonical bytes and content hash.

## 9. Security boundary

v0.1 proves deterministic representation and integrity only. It does not prove:

- that an actor is who they claim to be;
- that an actor has statutory authority;
- that an external URI remains available;
- that the source data are true;
- that a planning decision is legally valid.

Those concerns are layered on in later protocol versions.
