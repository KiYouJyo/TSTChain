# v0.1 Compatibility Policy

## Schema identity

The three v0.1 schemas use `schema_version: "0.1"` and immutable `$id` values under `urn:tstchain:schema:v0.1:*`.

Once v0.1 is tagged, changing the meaning of an existing required field, changing canonicalization behavior, or accepting a previously invalid representation that alters hash semantics requires a new protocol schema version.

## Allowed maintenance

Without changing protocol semantics, maintainers may:

- improve documentation;
- add translations;
- add new valid/invalid test cases;
- fix tooling bugs when the expected canonical bytes remain unchanged;
- clarify non-normative examples.

## Requires a new schema/protocol version

- adding a new required property;
- changing an identifier or digest format;
- changing array ordering semantics;
- changing Unicode normalization;
- changing the hash algorithm;
- changing the meaning of `null` versus omission;
- introducing ordered arrays or JSON numeric values into hash-bearing core objects without an explicit canonicalization revision.

## Unknown properties

v0.1 schemas use `additionalProperties: false`. Producers MUST NOT silently insert vendor fields into the core object. Experimental extensions should be maintained outside the v0.1 canonical object until an extension mechanism is standardized.

## Multilingual compatibility

Localization files are not protocol payloads. Adding or correcting `zh-CN`, `ja-JP`, or `en-US` display strings is non-breaking when the machine key remains unchanged.
