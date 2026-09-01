#!/usr/bin/env python3
"""TST Chain v0.6 spatial interoperability conformance checks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from shapely.geometry import Polygon

from referencecity_gis_adapter import (
    classify_relation,
    jcs_digest,
    predicate_value,
    resolve_evaluated_at,
    result_suffix,
    validate_geometry,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "v0.6"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validator(name: str) -> Draft202012Validator:
    schema = load_json(SCHEMA_DIR / name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def check_schema_contracts() -> None:
    external = validator("external-spatial-asset.schema.json")
    result = validator("spatial-adapter-result.schema.json")

    external.validate(
        {
            "asset_id": "tst:external-asset:test-a",
            "source_system": "fixture",
            "source_ref": "fixture/a.geojson",
            "media_type": "application/geo+json",
            "content_digest": {"algorithm": "sha256", "digest": "0" * 64},
            "canonicalization": "RFC8785-JCS",
            "crs_ref": "TEST-METRIC-1",
            "schema_version": "0.6",
        }
    )

    base = {
        "adapter_result_id": "tst:adapter-result:test-a",
        "operation": "within",
        "subject_ref": "subject-a",
        "constraint_ref": "constraint-a",
        "relation": "disjoint",
        "relation_value": False,
        "intersection_area_decimal": "0",
        "evaluator": {"system": "fixture", "version": "1"},
        "source_assets": ["tst:external-asset:test-a", "tst:external-asset:test-b"],
        "subject_geometry_digest": {
            "algorithm": "sha256",
            "digest": "1" * 64,
            "canonicalization": "RFC8785-JCS",
        },
        "constraint_geometry_digest": {
            "algorithm": "sha256",
            "digest": "2" * 64,
            "canonicalization": "RFC8785-JCS",
        },
        "evaluated_at": "2030-01-01T00:00:00Z",
        "schema_version": "0.6",
    }
    result.validate(base)

    missing_verdict = dict(base)
    missing_verdict.pop("relation_value")
    try:
        result.validate(missing_verdict)
    except ValidationError:
        pass
    else:
        raise AssertionError("SpatialAdapterResult must require relation_value")


def check_topology_semantics() -> None:
    constraint = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    within = Polygon([(1, 1), (2, 1), (2, 2), (1, 2)])
    contains = Polygon([(-1, -1), (11, -1), (11, 11), (-1, 11)])
    disjoint = Polygon([(20, 20), (21, 20), (21, 21), (20, 21)])
    overlap = Polygon([(9, 9), (12, 9), (12, 12), (9, 12)])

    assert classify_relation(within, constraint) == "within"
    assert classify_relation(contains, constraint) == "contains"
    assert classify_relation(disjoint, constraint) == "disjoint"
    assert classify_relation(overlap, constraint) == "intersects"

    assert predicate_value(disjoint, constraint, "within") is False
    assert classify_relation(disjoint, constraint) == "disjoint"
    assert predicate_value(overlap, constraint, "within") is False
    assert classify_relation(overlap, constraint) == "intersects"
    assert predicate_value(overlap, constraint, "intersects") is True
    assert predicate_value(disjoint, constraint, "disjoint") is True


def check_geometry_rejection() -> None:
    invalid = Polygon([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)])
    empty = Polygon()
    for geometry, label in ((invalid, "invalid"), (empty, "empty")):
        try:
            validate_geometry(geometry, label)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{label} geometry must be rejected")


def check_time_and_ids() -> None:
    fixed = "2030-03-07T01:00:00Z"
    assert resolve_evaluated_at(fixed) == fixed
    actual = resolve_evaluated_at(None)
    assert actual.endswith("Z")
    try:
        resolve_evaluated_at("2030-03-07T01:00:00+08:00")
    except ValueError:
        pass
    else:
        raise AssertionError("non-Z evaluated_at must be rejected")

    args = ("subject", "constraint", "intersects", "a" * 64, "b" * 64, fixed)
    assert result_suffix(*args) == result_suffix(*args)
    changed = ("subject", "constraint", "within", "a" * 64, "b" * 64, fixed)
    assert result_suffix(*args) != result_suffix(*changed)


def check_jcs_geometry_order() -> None:
    a = {"type": "LineString", "coordinates": [[0, 0], [1, 1], [2, 2]]}
    b = {"type": "LineString", "coordinates": [[2, 2], [1, 1], [0, 0]]}
    assert jcs_digest(a) != jcs_digest(b), "ordered GeoJSON coordinate arrays must not be sorted"


def main() -> int:
    check_schema_contracts()
    check_topology_semantics()
    check_geometry_rejection()
    check_time_and_ids()
    check_jcs_geometry_order()
    print("TST Chain v0.6 spatial interoperability conformance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
