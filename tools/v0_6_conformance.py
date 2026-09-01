#!/usr/bin/env python3
"""TST Chain v0.6 GeoJSON/GIS interoperability conformance."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import rfc8785
from jsonschema import Draft202012Validator, FormatChecker

from referencecity_gis_adapter import evaluate as spatial_evaluate
from v0_3_conformance import evaluate as rule_evaluate
from v0_5_conformance import Engine

ROOT = Path(__file__).resolve().parents[1]
SD = ROOT / "schemas" / "v0.6"
ED3 = ROOT / "examples" / "v0.3"
ED6 = ROOT / "examples" / "v0.6"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(schema_path: Path, value) -> None:
    schema = load(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def request_digest(payload: dict) -> str:
    return hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


def rule_request(subject: str, relation: str, evidence_ref: str, payload_digest: str) -> dict:
    return {
        "request_id": "tst:rule-eval-request:referencecity-s007-runtime",
        "rule_set_id": "tst:ruleset:referencecity-baseline",
        "subject_object_ref": subject,
        "object_type": "parcel",
        "jurisdiction_ref": "RC:CITY:001",
        "occurred_at": "2030-03-07T01:00:00Z",
        "facts": {
            "string_values": {},
            "decimal_values": {},
            "reference_sets": {"spatial_context_refs": ["RC:BOUNDARY:ECO001"]},
            "spatial_relations": [{"constraint_ref": "RC:BOUNDARY:ECO001", "relation": relation, "evidence_ref": evidence_ref}],
        },
        "external_input_digest": {"algorithm": "sha256", "digest": payload_digest, "canonicalization": "RFC8785-JCS"},
        "schema_version": "0.3",
    }


def workflow_request(outcome: str, payload_digest: str, name: str = "referencecity-s007") -> dict:
    return {
        "request_id": f"tst:wf-request:{name}",
        "workflow_id": "tst:workflow:referencecity-project-application",
        "instance_id": f"tst:wf-instance:{name}",
        "subject_ref": "RC:PARCEL:000001",
        "actor_ref": "RC:ACTOR:005",
        "action": "submit_project_application",
        "expected_version": None,
        "occurred_at": "2030-03-07T01:00:00Z",
        "payload_digest": {"algorithm": "sha256", "digest": payload_digest, "canonicalization": "RFC8785-JCS"},
        "authorization": {"decision_ref": f"tst:authz:{name}", "decision": "allow", "granted_permissions": ["project.submit"]},
        "document_refs": [],
        "signature_refs": [],
        "rule_evaluations": [{"evaluation_ref": f"tst:rule-evaluation:{name}", "outcome": outcome}],
        "schema_version": "0.5",
    }


def main() -> int:
    rc_root = Path(os.environ.get("REFERENCECITY_ROOT", ROOT / "referencecity")).resolve()
    if not (rc_root / "data" / "core-v0.1" / "config.json").exists():
        raise FileNotFoundError(f"ReferenceCity checkout not found: {rc_root}")

    project_workflow = load(ED6 / "workflow-project-application.json")
    validate(ROOT / "schemas" / "v0.5" / "workflow-definition.schema.json", project_workflow)

    # S007: calculate from generated geometry. No expected/Ground Truth file is read.
    bundle = spatial_evaluate(rc_root, "RC:PARCEL:000001", "RC:BOUNDARY:ECO001", "intersects")
    for asset in bundle["external_assets"]:
        validate(SD / "external-spatial-asset.schema.json", asset)
    validate(SD / "spatial-adapter-result.schema.json", bundle["adapter_result"])
    validate(ROOT / "schemas" / "v0.3" / "spatial-evaluation.schema.json", bundle["spatial_evaluation"])
    assert bundle["adapter_result"]["relation_value"] is True
    assert bundle["adapter_result"]["relation"] == "intersects"
    assert float(bundle["adapter_result"]["intersection_area_decimal"]) > 0

    # Verify ReferenceCity's public request payload digest independently with RFC 8785.
    rc_request = load(rc_root / "scenarios" / "v0.1" / "S007" / "request.json")
    payload_digest = request_digest(rc_request["payload"])
    assert rc_request["payload_hash"] == "sha256:" + payload_digest

    rule = load(ED3 / "rule-ecological-intersection.json")
    rr = rule_request("RC:PARCEL:000001", bundle["spatial_evaluation"]["relation"], bundle["spatial_evaluation"]["spatial_evaluation_id"], payload_digest)
    validate(ROOT / "schemas" / "v0.3" / "rule-evaluation-request.schema.json", rr)
    verdict = rule_evaluate(rr, [rule])
    assert verdict["outcome"] == "fail"
    assert verdict["violations"] and verdict["violations"][0]["code"] == "TST-RULE-002"

    engine = Engine(project_workflow)
    wf_result = engine.transition(workflow_request(verdict["outcome"], payload_digest), "2030-03-07T01:00:01Z")
    assert wf_result["accepted"] is False
    assert wf_result["state_changed"] is False
    assert wf_result["semantic_code"] == "RULE_CONFLICT"

    # Counterfactual control: a far-eastern parcel must be disjoint from the western ecological band.
    control = spatial_evaluate(rc_root, "RC:PARCEL:000010", "RC:BOUNDARY:ECO001", "intersects")
    assert control["adapter_result"]["relation_value"] is False
    assert control["adapter_result"]["relation"] == "disjoint"
    control_req = rule_request("RC:PARCEL:000010", "disjoint", control["spatial_evaluation"]["spatial_evaluation_id"], payload_digest)
    control_verdict = rule_evaluate(control_req, [rule])
    assert control_verdict["outcome"] == "pass"
    accepted = Engine(project_workflow).transition(workflow_request("pass", payload_digest, "referencecity-control"), "2030-03-07T01:00:01Z")
    assert accepted["accepted"] is True and accepted["current_state"] == "submitted"

    # Ordered external geometry is RFC8785-JCS evidence, never TST-C14N-JSON/0.1 input.
    assert bundle["adapter_result"]["subject_geometry_digest"]["canonicalization"] == "RFC8785-JCS"
    assert bundle["adapter_result"]["constraint_geometry_digest"]["canonicalization"] == "RFC8785-JCS"

    print("TST Chain v0.6 GIS interoperability conformance: PASS")
    print("  ReferenceCity S007: generated geometry -> Shapely -> PlanningRule -> Workflow rejection")
    print("  control parcel: disjoint -> rule pass -> workflow accepted")
    print("  Ground Truth consumed by adapter/conformance: NO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"TST Chain v0.6 conformance: FAIL: {exc}", file=sys.stderr)
        raise
