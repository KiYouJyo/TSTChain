# TST Chain v0.6 — Interoperability

v0.6 defines the trust boundary between TST Chain and external spatial/data systems. The protocol does **not** move raw GIS/BIM/remote-sensing datasets on-chain and does **not** require a specific geometry engine.

## Objects

- `ExternalSpatialAsset` records the identity, source, CRS and content digest of an externally managed spatial asset.
- `SpatialAdapterResult` records a reproducible spatial relation evaluation together with the exact source assets and geometry digests used.

## Canonicalization boundary

`TST-C14N-JSON/0.1` is only for TST protocol objects whose array semantics are defined by that profile. It MUST NOT be applied to GeoJSON coordinates or other ordered external JSON arrays.

ReferenceCity JSON/geometry inputs use RFC 8785 JCS. Their SHA-256 digests are imported as evidence into TST objects. A different GIS implementation may replace the reference Shapely adapter as long as it produces the same v0.6 contract and spatial semantics.

## Reference slice

The first v0.6 slice implements GeoJSON/JSON interoperability against the pinned ReferenceCity core snapshot and verifies scenario S007 using an external geometry evaluator. TIM, CSPON, BIM/IFC, remote sensing, document/archive and REST gateway adapters remain later v0.6 slices.
