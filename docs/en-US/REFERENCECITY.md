# ReferenceCity Benchmark Integration

ReferenceCity is TST Chain's synthetic territorial-spatial-planning benchmark environment. It provides a deterministic city, planning controls, governance actors, lifecycle cases, failure cases, and machine-readable Ground Truth.

The current integration baseline is ReferenceCity protocol `0.1`, core dataset `0.1.0`, and synthetic CRS `RC-SYNTHETIC-1`.

TST Chain v0.2 already provides identity, Evidence, Authority, Credential, Ed25519 signatures, authorization decisions, and AuditRecord. The ten ReferenceCity scenarios additionally require PlanningRule, plan-version provenance, Workflow, GIS spatial conflict evaluation, and a persistent ledger. The benchmark therefore turns roadmap gaps into executable acceptance criteria rather than being artificially made green.

TST Chain implementations must never hard-code `RC:*` IDs, S001-S010 names, or expected results. See `integrations/referencecity/v0.1/`.
