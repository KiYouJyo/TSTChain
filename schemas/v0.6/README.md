# TST Chain v0.6 — Interoperability

v0.6 defines the trust boundary between TST Chain and external spatial/data systems. The protocol does **not** move raw GIS/BIM/remote-sensing datasets on-chain and does **not** require a specific geometry engine.

## Objects

- `ExternalSpatialAsset` records the identity, source, CRS and content digest of an externally managed spatial asset.
- `SpatialAdapterResult` records a reproducible spatial predicate evaluation together with the exact source assets and geometry digests used.

## Spatial predicate semantics

`operation` is the requested predicate (`intersects`, `within`, `contains`, or `disjoint`). `relation_value` is the authoritative boolean result for that requested predicate and is required.

`relation` is the protocol relation supplied to downstream PlanningRule evaluation. For backward-compatible positive evidence, when `relation_value=true`, `relation` equals the requested `operation`. When the requested predicate is false, `relation` records an observed coarse topological relation (`disjoint`, `within`, `contains`, or fallback `intersects`) that explains why the predicate failed. This prevents the old error where every failed `within`/`contains` check was reported as `intersects` even when geometries were actually disjoint.

`intersection_area_decimal` is optional evidence expressed in source-CRS coordinate-square units. It MUST NOT be interpreted as square metres unless the source CRS/profile explicitly establishes metre coordinates; implementations should omit it or use `null` when planar area is not meaningful.

## Evidence identity and time

Each reference-adapter result ID binds subject, constraint, requested operation, geometry digests and evaluation time, preventing different evaluations from reusing one identifier.

`evaluated_at` records the actual evaluation time. Deterministic fixtures may inject a UTC `Z` timestamp derived from their source scenario. Production calls must not silently reuse fixture time. Empty or invalid geometries are rejected rather than silently repaired because repair would change the evidence being evaluated.

## Canonicalization boundary

`TST-C14N-JSON/0.1` is only for TST protocol objects whose array semantics are defined by that profile. It MUST NOT be applied to GeoJSON coordinates or other ordered external JSON arrays.

ReferenceCity JSON/geometry inputs use RFC 8785 JCS. Their SHA-256 digests are imported as evidence into TST objects. A different GIS implementation may replace the reference Shapely adapter as long as it produces the same v0.6 contract and spatial semantics.

## Reference slice

The first v0.6 slice implements GeoJSON/JSON interoperability against the pinned ReferenceCity core snapshot and verifies scenario S007 using an external geometry evaluator. TIM, CSPON, BIM/IFC, remote sensing, document/archive and REST gateway adapters remain later v0.6 slices.
