# TST Chain Architecture Overview

## Position

TST Chain is a trust, evidence, event, and provenance layer for territorial spatial planning. It does not perform GIS rendering, remote-sensing computation, BIM authoring, or administrative approval itself.

## Five core domain models

### SpatialObject
Represents a stable territorial spatial entity.

```text
object_id
object_type
jurisdiction
parent_object_id?
external_refs[]
schema_version
```

### SpatialEvent
Represents a verifiable lifecycle state transition.

```text
event_id
subject_object_id
event_type
previous_state_hash?
new_state_hash
actor_id
authority_id?
basis_refs[]
evidence_refs[]
timestamp
previous_event_hash?
signature
schema_version
```

Spatial Event is the primary business primitive. Planning-facing products should expose domain meanings such as approval, amendment, verification, and monitoring rather than financial-blockchain transaction terminology.

### PlanningRule
Represents a machine-readable, versioned, traceable planning constraint.

```text
rule_id
rule_type
scope
expression
unit?
source_plan_id
basis_refs[]
effective_from
effective_to?
status
schema_version
```

GIS, BIM, or external rule engines perform computation. TST Chain records the rule version, input digest, output digest, evidence, and signatures.

### Authority
Represents organizations, persons, roles, jurisdictions, and credentials grounded in real governance structures. A chain configuration must never be treated as creating legal or administrative authority.

### Provenance
Represents how a plan, rule, indicator, or spatial state originated, changed, and was transmitted.

Recommended relation types include:

- `DERIVED_FROM`
- `SUPERSEDES`
- `AMENDS`
- `TRANSMITS_TO`
- `IMPLEMENTS`
- `VERIFIES`
- `MONITORS`
- `AFFECTS`

## Evidence-first hybrid storage

```text
GIS / TIM / BIM / RS / Document / Database
                  │
                  ├─ source data stays external
                  └─ hash / metadata / reference
                              ↓
                           TST Chain
```

On-chain or ledger-critical data should remain compact: stable IDs, content hashes, timestamps, versions, signatures, authority links, lifecycle state changes, and provenance relations.

## Hierarchical and jurisdictional scaling

```text
Local / County Domain
        ↓ signed checkpoint
City Trust Layer
        ↓ signed checkpoint
Province Trust Layer
        ↓ signed checkpoint
National / Federation Root
```

Upper layers should not need to replicate every lower-level record. They verify signed commitments and selected evidence according to policy.

## Core invariants

1. Identical canonical payloads must produce identical content hashes.
2. Localized text must never enter consensus-critical fields.
3. Every state change must be represented by an identifiable Spatial Event.
4. Every event must be traceable to actor, evidence, and schema version.
5. Planning rule changes must create new versions and provenance edges rather than silently overwriting old rules.
6. Historical evidence must remain verifiable after external files change.
7. Hierarchical checkpoints must not require full replication of lower-level detail.
8. Rule-engine output must not be represented as an administrative decision unless a competent authority actually issues that decision.

## Relationship to planning AI

```text
Spatial Object
      +
Planning Rule
      +
Spatial Event
      +
Authority
      +
Provenance
      ↓
Trusted Spatial Knowledge Graph
      ↓
Planning AI / RAG / Decision Support
```

The chain supplies evidence-bearing context so AI outputs can cite which object, rule version, event, and authority support a planning conclusion.

## Implementation order

1. Canonical serialization
2. Content hash
3. SpatialObject
4. SpatialEvent
5. Evidence
6. Authority
7. PlanningRule
8. Provenance
9. Workflow
10. Distributed ledger
11. Hierarchical checkpoint
12. Interoperability adapters
13. Knowledge graph projection
