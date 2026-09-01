# TST Chain v0.6 — Interoperability

v0.6 defines the trust boundary between TST Chain and external spatial/data systems. The protocol does **not** move raw GIS/BIM/remote-sensing datasets on-chain and does **not** require a specific geometry engine.

## Objects

- `ExternalSpatialAsset` records the identity, source, CRS and content digest of an externally managed spatial asset.
- `SpatialAdapterResult` records a reproducible spatial predicate evaluation together with the exact source assets and geometry digests used.

## Spatial predicate semantics

`operation` is the requested predicate (`intersects`, `within`, `contains`, or `disjoint`). `relation_value` is the authoritative boolean result for that requested predicate and is therefore required.

`relation` is a coarse observed topological classification independent of the requested predicate. The reference adapter classifies in this order: `disjoint`, `within`, `contains`, then `intersects` as the fallback for other non-disjoint relationships. A failed `within` or `contains` predicate MUST NOT be rewritten as `intersects` unless the observed geometry actually intersects.

`intersection_area_decimal` is optional evidence expressed in the source CRS coordinate-square units. Implementations MUST set it to `null` or omit it when the source CRS does not define meaningful planar area. It must not be interpreted as square metres unless the source CRS/profile explicitly establishes metre coordinates.

## Provenance time and evaluator identity

`evaluated_at` records the actual evaluation time. Reference fixtures may inject an explicit UTC `Z` timestamp for reproducibility; production calls must not reuse a fixture timestamp. The evaluator system and implementation version are recorded so that results can be reproduced or compared across engine upgrades.

Empty or invalid geometries are rejected by the reference adapter rather than silently repaired, because silent repair would change the evidence being evaluated.

## Canonicalization boundary

`TST-C14N-JSON/0.1` is only for TST protocol objects whose array semantics are defined by that profile. It MUST NOT be applied to GeoJSON coordinates or other ordered external JSON arrays.

ReferenceCity JSON/geometry inputs use RFC 8785 JCS. Their SHA-256 digests are imported as evidence into TST objects. A different GIS implementation may replace the reference Shapely adapter as long as it produces the same v0.6 contract and spatial semantics.

## Reference slice

The first v0.6 slice implements GeoJSON/JSON interoperability against the pinned ReferenceCity core snapshot and verifies scenario S007 using an external geometry evaluator. TIM, CSPON, BIM/IFC, remote sensing, document/archive and REST gateway adapters remain later v0.6 slices.
