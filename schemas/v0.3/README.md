# TST Chain v0.3 — Planning Rule

v0.3 defines machine-readable planning rules without turning the ledger into a GIS/BIM computation engine.

## Protocol objects

- `PlanningRule`
- `RuleSet`
- `RuleException`
- `RuleEvaluationRequest`
- `RuleEvaluationResult`
- `RuleEngineManifest`

## Determinism

Protocol decimals are canonical base-10 strings, never JSON binary floating-point numbers. Equivalent values such as `2.5` and `2.50` MUST NOT both be accepted; `2.50` is invalid in v0.3.

## Administrative boundary

A rule-engine result is evidence about compliance under a named rule version and input set. `fail` is not an administrative rejection. `review` explicitly routes cases that require human or statutory discretion.

## Spatial computation

Spatial expressions declare predicates such as `disjoint`, `within`, or `distance_lte`. Geometry stays off-chain. A GIS/TIM/BIM adapter supplies observations and evidence references through `TST-RULE-ENGINE/0.3`.

Synthetic fixtures are used until ReferenceCity is mature enough for integration.
