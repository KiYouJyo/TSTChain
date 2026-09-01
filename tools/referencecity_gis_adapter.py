#!/usr/bin/env python3
"""Reference v0.6 GIS adapter for a pinned ReferenceCity checkout.

Raw ordered geometry stays external. The adapter evaluates geometry with Shapely,
hashes each geometry with RFC 8785 JCS, and emits TST interoperability evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import rfc8785
import shapely
from shapely.geometry import shape


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def jcs_digest(value) -> str:
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def resolve_evaluated_at(value: str | None) -> str:
    """Return a verified UTC-Z timestamp, defaulting to actual evaluation time."""
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if not value.endswith("Z"):
        raise ValueError("evaluated_at must be an explicit UTC Z timestamp")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("evaluated_at is not a valid ISO-8601 timestamp") from exc
    return value


def ensure_snapshot(referencecity_root: Path) -> Path:
    generated = referencecity_root / "data" / "core-v0.1" / "generated"
    snapshot = generated / "snapshot.json"
    if not snapshot.exists():
        subprocess.run(
            [sys.executable, str(referencecity_root / "tools" / "build_snapshot.py"), "--output", str(generated)],
            cwd=referencecity_root,
            check=True,
        )
    return generated


def find_by_id(items: list[dict], object_id: str) -> dict:
    for item in items:
        if item.get("id") == object_id:
            return item
    raise KeyError(object_id)


def snapshot_asset(snapshot: dict, path: str) -> dict:
    for asset in snapshot["assets"]:
        if asset["path"] == path:
            return asset
    raise KeyError(path)


def external_asset(asset_id: str, source_ref: str, digest: str, crs_ref: str, snapshot_ref: str) -> dict:
    return {
        "asset_id": asset_id,
        "source_system": "ReferenceCity",
        "source_ref": source_ref,
        "media_type": "application/json",
        "content_digest": {"algorithm": "sha256", "digest": digest.removeprefix("sha256:")},
        "canonicalization": "RFC8785-JCS",
        "crs_ref": crs_ref,
        "snapshot_ref": snapshot_ref,
        "schema_version": "0.6",
    }


def validate_geometry(geometry, label: str) -> None:
    if geometry.is_empty:
        raise ValueError(f"{label} geometry is empty")
    if not geometry.is_valid:
        raise ValueError(f"{label} geometry is invalid")


def classify_relation(subject_geom, constraint_geom) -> str:
    """Return a coarse observed relation for explaining a failed predicate."""
    if subject_geom.disjoint(constraint_geom):
        return "disjoint"
    if subject_geom.within(constraint_geom):
        return "within"
    if subject_geom.contains(constraint_geom):
        return "contains"
    return "intersects"


def predicate_value(subject_geom, constraint_geom, operation: str) -> bool:
    operations = {
        "intersects": subject_geom.intersects,
        "within": subject_geom.within,
        "contains": subject_geom.contains,
        "disjoint": subject_geom.disjoint,
    }
    try:
        predicate = operations[operation]
    except KeyError as exc:
        raise ValueError(f"unsupported operation: {operation}") from exc
    return bool(predicate(constraint_geom))


def result_suffix(
    subject_ref: str,
    constraint_ref: str,
    operation: str,
    subject_digest: str,
    constraint_digest: str,
    evaluated_at: str,
) -> str:
    seed = "\0".join(
        [subject_ref, constraint_ref, operation, subject_digest, constraint_digest, evaluated_at]
    ).encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:24]


def evaluate(
    referencecity_root: Path,
    subject_ref: str,
    constraint_ref: str,
    operation: str = "intersects",
    evaluated_at: str | None = None,
) -> dict:
    generated = ensure_snapshot(referencecity_root)
    spatial = load(generated / "spatial-objects.json")
    planning = load(generated / "planning-objects.json")
    snapshot = load(generated / "snapshot.json")
    config = load(referencecity_root / "data" / "core-v0.1" / "config.json")

    subject = find_by_id(spatial, subject_ref)
    constraint = find_by_id(planning, constraint_ref)
    subject_geom = shape(subject["geometry"])
    constraint_geom = shape(constraint["boundary_geometry"])
    validate_geometry(subject_geom, "subject")
    validate_geometry(constraint_geom, "constraint")

    evaluated_at = resolve_evaluated_at(evaluated_at)
    value = predicate_value(subject_geom, constraint_geom, operation)
    relation = operation if value else classify_relation(subject_geom, constraint_geom)
    intersection_area = subject_geom.intersection(constraint_geom).area
    area_text = format(intersection_area, ".6f").rstrip("0").rstrip(".") or "0"

    spatial_asset = snapshot_asset(snapshot, "spatial-objects.json")
    planning_asset = snapshot_asset(snapshot, "planning-objects.json")
    snapshot_ref = f"ReferenceCity:{snapshot['snapshot_id']}:{snapshot['dataset_version']}"
    assets = [
        external_asset(
            "tst:external-asset:referencecity-core-spatial-v0.1",
            "data/core-v0.1/generated/spatial-objects.json",
            spatial_asset["canonical_sha256"],
            config["crs_identifier"],
            snapshot_ref,
        ),
        external_asset(
            "tst:external-asset:referencecity-core-planning-v0.1",
            "data/core-v0.1/generated/planning-objects.json",
            planning_asset["canonical_sha256"],
            config["crs_identifier"],
            snapshot_ref,
        ),
    ]
    subject_digest = jcs_digest(subject["geometry"])
    constraint_digest = jcs_digest(constraint["boundary_geometry"])
    suffix = result_suffix(
        subject_ref,
        constraint_ref,
        operation,
        subject_digest,
        constraint_digest,
        evaluated_at,
    )
    adapter_result = {
        "adapter_result_id": f"tst:adapter-result:referencecity-{suffix}",
        "operation": operation,
        "subject_ref": subject_ref,
        "constraint_ref": constraint_ref,
        "relation": relation,
        "relation_value": value,
        "intersection_area_decimal": area_text,
        "evaluator": {"system": "shapely-reference-adapter", "version": shapely.__version__},
        "source_assets": [a["asset_id"] for a in assets],
        "subject_geometry_digest": {"algorithm": "sha256", "digest": subject_digest, "canonicalization": "RFC8785-JCS"},
        "constraint_geometry_digest": {"algorithm": "sha256", "digest": constraint_digest, "canonicalization": "RFC8785-JCS"},
        "evaluated_at": evaluated_at,
        "schema_version": "0.6",
    }
    spatial_evaluation = {
        "spatial_evaluation_id": f"tst:spatial-evaluation:referencecity-{suffix}",
        "subject_object_ref": subject_ref,
        "constraint_ref": constraint_ref,
        "relation": relation,
        "evaluator_system": f"tst-referencecity-gis-adapter/0.6;shapely/{shapely.__version__}",
        "evaluated_at": evaluated_at,
        "subject_geometry_digest": adapter_result["subject_geometry_digest"],
        "constraint_geometry_digest": adapter_result["constraint_geometry_digest"],
        "schema_version": "0.3",
    }
    return {"external_assets": assets, "adapter_result": adapter_result, "spatial_evaluation": spatial_evaluation}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--referencecity-root", type=Path, required=True)
    parser.add_argument("--subject", default="RC:PARCEL:000001")
    parser.add_argument("--constraint", default="RC:BOUNDARY:ECO001")
    parser.add_argument("--operation", default="intersects", choices=["intersects", "within", "contains", "disjoint"])
    parser.add_argument(
        "--evaluated-at",
        help="Explicit UTC Z timestamp for deterministic fixtures; defaults to actual current UTC time.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(
        args.referencecity_root.resolve(),
        args.subject,
        args.constraint,
        args.operation,
        args.evaluated_at,
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
