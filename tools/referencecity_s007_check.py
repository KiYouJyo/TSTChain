#!/usr/bin/env python3
"""Execute ReferenceCity S007 through the v0.6 GIS adapter contract."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from referencecity_gis_adapter import evaluate

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def utc_z(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("ReferenceCity scenario time must include an offset")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate(schema_path: Path, value: dict) -> None:
    schema = load(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--referencecity-root", type=Path, required=True)
    args = parser.parse_args()
    rc = args.referencecity_root.resolve()

    request = load(rc / "scenarios" / "v0.1" / "S007" / "request.json")
    expected = load(rc / "expected" / "v0.1" / "S007.json")
    conflict = expected["expected_spatial_conflicts"][0]
    evaluated_at = utc_z(request["occurred_at"])

    result = evaluate(
        rc,
        request["target_id"],
        conflict["constraint_id"],
        "intersects",
        evaluated_at,
    )

    for asset in result["external_assets"]:
        validate(ROOT / "schemas" / "v0.6" / "external-spatial-asset.schema.json", asset)
    validate(
        ROOT / "schemas" / "v0.6" / "spatial-adapter-result.schema.json",
        result["adapter_result"],
    )
    validate(
        ROOT / "schemas" / "v0.3" / "spatial-evaluation.schema.json",
        result["spatial_evaluation"],
    )

    adapter_result = result["adapter_result"]
    spatial_evaluation = result["spatial_evaluation"]
    assert expected["accepted"] is False
    assert expected["expected_error_code"] == "SPATIAL_CONFLICT"
    assert conflict["target_id"] == request["target_id"]
    assert adapter_result["subject_ref"] == request["target_id"]
    assert adapter_result["constraint_ref"] == conflict["constraint_id"]
    assert adapter_result["operation"] == "intersects"
    assert adapter_result["relation_value"] is True, "S007 must intersect the ecological constraint"
    assert adapter_result["relation"] != "disjoint"
    assert adapter_result["evaluated_at"] == evaluated_at
    assert spatial_evaluation["relation"] == adapter_result["relation"]
    assert spatial_evaluation["evaluated_at"] == evaluated_at
    assert spatial_evaluation["subject_geometry_digest"] == adapter_result["subject_geometry_digest"]
    assert spatial_evaluation["constraint_geometry_digest"] == adapter_result["constraint_geometry_digest"]

    print("ReferenceCity S007 -> TST Chain v0.6 spatial adapter: PASS")
    print(f"  relation={adapter_result['relation']} predicate={adapter_result['relation_value']}")
    print(f"  evaluated_at={evaluated_at}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
