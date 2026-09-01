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
from pathlib import Path

import rfc8785
import shapely
from shapely.geometry import shape

EVALUATED_AT = "2030-03-07T01:00:00Z"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def jcs_digest(value) -> str:
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


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


def evaluate(referencecity_root: Path, subject_ref: str, constraint_ref: str, operation: str = "intersects") -> dict:
    generated = ensure_snapshot(referencecity_root)
    spatial = load(generated / "spatial-objects.json")
    planning = load(generated / "planning-objects.json")
    snapshot = load(generated / "snapshot.json")
    config = load(referencecity_root / "data" / "core-v0.1" / "config.json")

    subject = find_by_id(spatial, subject_ref)
    constraint = find_by_id(planning, constraint_ref)
    subject_geom = shape(subject["geometry"])
    constraint_geom = shape(constraint["boundary_geometry"])

    operations = {
        "intersects": subject_geom.intersects(constraint_geom),
        "within": subject_geom.within(constraint_geom),
        "contains": subject_geom.contains(constraint_geom),
        "disjoint": subject_geom.disjoint(constraint_geom),
    }
    if operation not in operations:
        raise ValueError(f"unsupported operation: {operation}")
    value = bool(operations[operation])
    relation = operation if value else ("disjoint" if operation == "intersects" else "intersects")
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
    adapter_result = {
        "adapter_result_id": "tst:adapter-result:referencecity-s007",
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
        "evaluated_at": EVALUATED_AT,
        "schema_version": "0.6",
    }
    spatial_evaluation = {
        "spatial_evaluation_id": "tst:spatial-evaluation:referencecity-s007",
        "subject_object_ref": subject_ref,
        "constraint_ref": constraint_ref,
        "relation": relation,
        "evaluator_system": "tst-referencecity-gis-adapter/0.6",
        "evaluated_at": EVALUATED_AT,
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
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.referencecity_root.resolve(), args.subject, args.constraint, args.operation)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
