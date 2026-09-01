#!/usr/bin/env python3
"""Run isolated ReferenceCity v0.1 scenarios through the TST v0.7 ledger.

The adapter consumes only the benchmark-input bundle produced by ReferenceCity.
It never reads expected/ Ground Truth; scoring remains a separate ReferenceCity step.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import rfc8785
from shapely.geometry import shape

from v0_3_conformance import evaluate as rule_evaluate
from v0_7_ledger import LedgerStore

ROOT = Path(__file__).resolve().parents[1]
PLAN_WORKFLOW = ROOT / "examples/v0.5/workflow-referencecity.json"
PROJECT_WORKFLOW = ROOT / "examples/v0.6/workflow-project-application.json"
ECO_RULE = ROOT / "examples/v0.3/rule-ecological-intersection.json"
FARM_RULE = ROOT / "examples/v0.7/rule-farmland-intersection.json"

OPERATION_MAP = {
    "CREATE_PLAN": ("create_plan", "plan.create", "plan"),
    "OPEN_AMENDMENT": ("open_amendment", "plan.amend", "plan"),
    "SUBMIT_PLAN": ("submit_plan", "plan.submit", "plan"),
    "REVIEW_PASS": ("review_pass", "plan.review", "plan"),
    "APPROVE_PLAN": ("approve_plan", "plan.approve", "plan"),
    "ACTIVATE_PLAN": ("activate_plan", "plan.activate", "plan"),
    "SUBMIT_AMENDMENT": ("submit_amendment", "plan.submit", "plan"),
    "SUBMIT_PROJECT_APPLICATION": ("submit_project_application", "project.submit", "parcel"),
}

ERROR_MAP = {
    "UNAUTHORIZED": "UNAUTHORIZED",
    "INVALID_STATE_TRANSITION": "INVALID_STATE_TRANSITION",
    "MISSING_DOCUMENT": "MISSING_DOCUMENT",
    "MISSING_SIGNATURE": "MISSING_SIGNATURE",
    "VERSION_CONFLICT": "VERSION_CONFLICT",
    "REQUEST_ID_REUSE": "REQUEST_ID_REUSE",
}

CONFLICT_TYPE = {
    "ecological_constraint": "ecological_boundary_conflict",
    "farmland_constraint": "farmland_control_conflict",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def safe(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._~-" else "-" for ch in value)


def utc_z(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"timezone required: {value}")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def jcs_sha(value) -> str:
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def find(items: list[dict], object_id: str) -> dict | None:
    return next((item for item in items if item.get("id") == object_id), None)


def instance_id(target_id: str) -> str:
    return "tst:wf-instance:" + safe(target_id.lower())


def actor_role(entities: list[dict], actor_id: str) -> str | None:
    actor = find(entities, actor_id)
    return actor.get("role_id") if actor else None


def authorized(entities: list[dict], actor_id: str, operation: str, resource_type: str) -> bool:
    role = actor_role(entities, actor_id)
    if role is None:
        return False
    for permission in entities:
        if permission.get("entity_type") != "permission" or permission.get("role_id") != role:
            continue
        if permission.get("operation") != operation:
            continue
        allowed_resource = permission.get("resource_type")
        if allowed_resource not in {"*", resource_type}:
            continue
        if "RC:CITY:001" not in permission.get("scope_ids", []):
            continue
        return True
    return False


def initial_object(benchmark: Path, scenario: dict, target_id: str, planning: list[dict]) -> tuple[dict | None, str | None]:
    for relative in scenario.get("fixtures", []):
        if relative.endswith("initial-state.json"):
            obj = load(benchmark / relative)
            if obj.get("id") == target_id:
                return obj, relative
    obj = find(planning, target_id)
    return (obj, "data/core-v0.1/generated/planning-objects.json") if obj else (None, None)


def seed_plan(store: LedgerStore, obj: dict, workflow_id: str, source_ref: str, committed_at: str) -> None:
    store.seed_instance(
        {
            "instance_id": instance_id(obj["id"]),
            "workflow_id": workflow_id,
            "subject_ref": obj["id"],
            "current_state": obj["status"].lower(),
            "current_version": str(obj["version"]),
            "updated_at": utc_z(obj.get("valid_from") or committed_at),
            "schema_version": "0.5",
        },
        committed_at,
        source_ref,
    )


def signature_bundle_available(benchmark: Path, scenario: dict) -> bool:
    return any(
        relative.endswith("documents-and-approvals.json") and (benchmark / relative).is_file()
        for relative in scenario.get("fixtures", [])
    )


def transition_audit(definition: dict, action: str) -> str:
    transition = next((item for item in definition["transitions"] if item["action"] == action), None)
    return (transition.get("audit_event") if transition else action).upper()


def workflow_request(rc_request: dict, definition: dict, action: str, permission: str, is_authorized: bool, rule_outcome: str | None, signature_available: bool, project_create: bool = False) -> dict:
    docs = list(rc_request.get("related_document_ids", []))
    transition = next((item for item in definition["transitions"] if item["action"] == action), None)
    signatures = []
    if transition and transition.get("signature_required") and signature_available:
        signatures = ["tst:signature:" + safe(rc_request["request_id"].lower())]
    rules = [] if rule_outcome is None else [{
        "evaluation_ref": "tst:rule-evaluation:" + safe(rc_request["request_id"].lower()),
        "outcome": rule_outcome,
    }]
    expected = None if project_create else rc_request.get("expected_version")
    return {
        "request_id": "tst:wf-request:" + safe(rc_request["request_id"].lower()),
        "workflow_id": definition["workflow_id"],
        "instance_id": instance_id(rc_request["target_id"]) if not project_create else "tst:wf-instance:" + safe(rc_request["request_id"].lower()),
        "subject_ref": rc_request["target_id"],
        "actor_ref": rc_request["actor_id"],
        "action": action,
        "expected_version": None if expected is None else str(expected),
        "occurred_at": utc_z(rc_request["occurred_at"]),
        "payload_digest": {"algorithm": "sha256", "digest": rc_request["payload_hash"].removeprefix("sha256:"), "canonicalization": "RFC8785-JCS"},
        "authorization": {
            "decision_ref": "tst:authz:" + safe(rc_request["request_id"].lower()),
            "decision": "allow" if is_authorized else "deny",
            "granted_permissions": [permission] if is_authorized else [],
        },
        "document_refs": docs,
        "signature_refs": signatures,
        "rule_evaluations": rules,
        "schema_version": "0.5",
    }


def geometry_relation(subject: dict, constraint: dict) -> tuple[str, dict]:
    subject_geom = shape(subject["geometry"])
    constraint_geom = shape(constraint["boundary_geometry"])
    if subject_geom.is_empty or constraint_geom.is_empty or not subject_geom.is_valid or not constraint_geom.is_valid:
        raise ValueError("invalid benchmark geometry")
    if subject_geom.disjoint(constraint_geom):
        relation = "disjoint"
    elif subject_geom.within(constraint_geom):
        relation = "within"
    elif subject_geom.crosses(constraint_geom):
        relation = "crosses"
    else:
        relation = "intersects"
    evidence = {
        "subject_ref": subject["id"],
        "constraint_ref": constraint["id"],
        "relation": relation,
        "subject_geometry_digest": {"algorithm": "sha256", "digest": jcs_sha(subject["geometry"]), "canonicalization": "RFC8785-JCS"},
        "constraint_geometry_digest": {"algorithm": "sha256", "digest": jcs_sha(constraint["boundary_geometry"]), "canonicalization": "RFC8785-JCS"},
        "intersection_area_decimal": format(subject_geom.intersection(constraint_geom).area, ".6f").rstrip("0").rstrip(".") or "0",
        "evaluator_system": "tst-referencecity-ledger-adapter/0.7;shapely",
    }
    return relation, evidence


def make_rule_request(rc_request: dict, subject_id: str, constraint_id: str, relation: str) -> dict:
    return {
        "request_id": "tst:rule-eval-request:" + safe(rc_request["request_id"].lower()),
        "rule_set_id": "tst:ruleset:referencecity-baseline",
        "subject_object_ref": subject_id,
        "object_type": "parcel",
        "jurisdiction_ref": "RC:CITY:001",
        "occurred_at": utc_z(rc_request["occurred_at"]),
        "facts": {
            "string_values": {},
            "decimal_values": {},
            "reference_sets": {"spatial_context_refs": [constraint_id]},
            "spatial_relations": [{
                "constraint_ref": constraint_id,
                "relation": relation,
                "evidence_ref": "tst:spatial-evaluation:" + safe(rc_request["request_id"].lower()),
            }],
        },
        "external_input_digest": {"algorithm": "sha256", "digest": rc_request["payload_hash"].removeprefix("sha256:"), "canonicalization": "RFC8785-JCS"},
        "schema_version": "0.3",
    }


def spatial_rule_outcome(rc_request: dict, scenario: dict, spatial: list[dict], planning: list[dict]) -> tuple[str | None, list[dict], dict | None]:
    operation = rc_request["operation"]
    if operation == "SUBMIT_PROJECT_APPLICATION":
        subject = find(spatial, rc_request["target_id"])
        constraint = next(item for item in planning if item.get("constraint_code") == "ecological_constraint")
        relation, evidence = geometry_relation(subject, constraint)
        verdict = rule_evaluate(make_rule_request(rc_request, subject["id"], constraint["id"], relation), [load(ECO_RULE)])
        conflicts = []
        if verdict["outcome"] == "fail":
            conflicts.append({
                "conflict_type": CONFLICT_TYPE[constraint["constraint_code"]],
                "target_id": subject["id"],
                "constraint_id": constraint["id"],
                "severity": "ERROR",
            })
        return verdict["outcome"], conflicts, evidence

    if operation == "OPEN_AMENDMENT" and "proposed_land_use" in rc_request.get("payload", {}):
        params = scenario["actions"][0].get("parameters", {})
        parcel_id = params.get("affected_parcel_id")
        subject = find(spatial, parcel_id) if parcel_id else None
        constraint = next(item for item in planning if item.get("constraint_code") == "farmland_constraint")
        relation, evidence = geometry_relation(subject, constraint) if subject else ("disjoint", None)
        verdict = rule_evaluate(make_rule_request(rc_request, subject["id"], constraint["id"], relation), [load(FARM_RULE)])
        conflicts = []
        if verdict["outcome"] == "fail":
            conflicts.append({
                "conflict_type": CONFLICT_TYPE[constraint["constraint_code"]],
                "target_id": subject["id"],
                "constraint_id": constraint["id"],
                "severity": "ERROR",
            })
        return verdict["outcome"], conflicts, evidence

    if operation == "OPEN_AMENDMENT":
        return "pass", [], None
    return None, [], None


def verify_document(benchmark: Path, rc_request: dict, documents: list[dict]) -> tuple[bool, dict]:
    record = find(documents, rc_request["target_id"])
    if not record:
        return False, {"reason": "document metadata missing"}
    content = load(benchmark / record["metadata"]["content_path"])
    candidate = copy.deepcopy(content)
    if rc_request.get("payload", {}).get("tampered"):
        candidate["_benchmark_tamper_marker"] = True
    actual = "sha256:" + jcs_sha(candidate)
    return actual == record["content_hash"], {
        "document_id": record["id"],
        "stored_hash": record["content_hash"],
        "calculated_hash": actual,
    }


def verify_history(benchmark: Path, rc_request: dict, planning: list[dict]) -> tuple[bool, dict]:
    requested_version = rc_request.get("payload", {}).get("version")
    version_object = next((item for item in planning if item.get("planning_object_type") == "plan_version" and item.get("plan_id") == rc_request["target_id"] and item.get("version") == requested_version), None)
    snapshot = load(benchmark / "data/core-v0.1/generated/snapshot.json")
    asset = next(item for item in snapshot["assets"] if item["path"] == "planning-objects.json")
    actual_asset_hash = "sha256:" + jcs_sha(planning)
    match = version_object is not None and actual_asset_hash == asset["canonical_sha256"]
    return match, {
        "plan_id": rc_request["target_id"],
        "version": requested_version,
        "planning_asset_hash": actual_asset_hash,
        "locked_hash": asset["canonical_sha256"],
    }


def result_version(result: dict | None, fallback: int | None) -> int | None:
    if result and result.get("current_version") is not None:
        return int(result["current_version"])
    return fallback


def audit_result(definition: dict, action: str, result: dict) -> list[str]:
    events = [transition_audit(definition, action)]
    semantic = result.get("semantic_code")
    if not result.get("accepted"):
        events.append("VERIFY")
    if semantic == "UNAUTHORIZED":
        events.append("ATTEMPT_UNAUTHORIZED_CHANGE")
    return list(dict.fromkeys(events))


def run_scenario(benchmark: Path, entry: dict, ledger_root: Path, entities: list[dict], planning: list[dict], spatial: list[dict], documents: list[dict]) -> dict:
    scenario = load(benchmark / entry["scenario_ref"])
    scenario_name = scenario["scenario_id"].split(":")[-1]
    store = LedgerStore(ledger_root / scenario_name, ledger_id="tst:ledger:referencecity-" + scenario_name.lower())
    plan_workflow = load(PLAN_WORKFLOW)
    project_workflow = load(PROJECT_WORKFLOW)

    audit_events: list[str] = []
    spatial_conflicts: list[dict] = []
    hash_match: bool | None = None
    overall_authorized = True
    final_result = None
    final_error = None
    fallback_version = None

    for action in scenario["actions"]:
        rc_request = load(benchmark / action["request_ref"])
        request_hash_ok = "sha256:" + jcs_sha(rc_request["payload"]) == rc_request["payload_hash"]
        if not request_hash_ok:
            raise ValueError(f"input payload hash mismatch before execution: {rc_request['request_id']}")
        hash_match = True
        if fallback_version is None and rc_request.get("expected_version") is not None:
            fallback_version = int(rc_request["expected_version"])

        operation = rc_request["operation"]
        if operation == "VERIFY":
            is_auth = authorized(entities, rc_request["actor_id"], operation, "*")
            overall_authorized = overall_authorized and is_auth
            audit_events.append("VERIFY")
            if rc_request["target_id"].startswith("RC:DOC:"):
                hash_match, proof = verify_document(benchmark, rc_request, documents)
                accepted = is_auth and hash_match
                final_error = None if accepted else ("UNAUTHORIZED" if not is_auth else "HASH_MISMATCH")
                ledger_entry = store.record_evidence({
                    "request": rc_request,
                    "verification": proof,
                    "authorized": is_auth,
                    "accepted": accepted,
                    "hash_match": hash_match,
                }, utc_z(rc_request["occurred_at"]))
            else:
                obj, source_ref = initial_object(benchmark, scenario, rc_request["target_id"], planning)
                if obj:
                    seed_plan(store, obj, plan_workflow["workflow_id"], source_ref, utc_z(rc_request["occurred_at"]))
                    fallback_version = obj["version"]
                hash_match, proof = verify_history(benchmark, rc_request, planning)
                accepted = is_auth and hash_match
                final_error = None if accepted else ("UNAUTHORIZED" if not is_auth else "HASH_MISMATCH")
                ledger_entry = store.record_provenance({
                    "request": rc_request,
                    "verification": proof,
                    "authorized": is_auth,
                    "accepted": accepted,
                    "hash_match": hash_match,
                }, utc_z(rc_request["occurred_at"]))
            final_result = {
                "accepted": accepted,
                "state_changed": False,
                "current_version": str(fallback_version) if fallback_version is not None else None,
                "ledger_entry_id": ledger_entry["entry_id"],
            }
            continue

        if operation not in OPERATION_MAP:
            raise ValueError(f"unsupported ReferenceCity operation: {operation}")
        action_name, tst_permission, resource_type = OPERATION_MAP[operation]
        is_auth = authorized(entities, rc_request["actor_id"], operation, resource_type)
        overall_authorized = overall_authorized and is_auth
        definition = project_workflow if operation == "SUBMIT_PROJECT_APPLICATION" else plan_workflow

        if resource_type == "plan" and operation != "CREATE_PLAN" and instance_id(rc_request["target_id"]) not in store.instances:
            obj, source_ref = initial_object(benchmark, scenario, rc_request["target_id"], planning)
            if obj is None:
                raise ValueError(f"missing initial plan state: {rc_request['target_id']}")
            seed_plan(store, obj, definition["workflow_id"], source_ref, utc_z(rc_request["occurred_at"]))
            fallback_version = obj["version"]

        rule_outcome, conflicts, spatial_evidence = spatial_rule_outcome(rc_request, scenario, spatial, planning)
        spatial_conflicts.extend(conflicts)
        if spatial_evidence is not None:
            store.record_evidence({
                "kind": "spatial_evaluation",
                "request_id": rc_request["request_id"],
                **spatial_evidence,
            }, utc_z(rc_request["occurred_at"]))

        wf_request = workflow_request(
            rc_request,
            definition,
            action_name,
            tst_permission,
            is_auth,
            rule_outcome,
            signature_bundle_available(benchmark, scenario),
            project_create=(operation == "SUBMIT_PROJECT_APPLICATION"),
        )
        before = len(store.entries)
        final_result = store.commit_workflow(definition, wf_request, utc_z(rc_request["occurred_at"]))
        if len(store.entries) <= before and not final_result.get("idempotent_replay"):
            raise AssertionError("workflow result was not audit-persisted")
        audit_events.extend(audit_result(definition, action_name, final_result))

        semantic = final_result.get("semantic_code")
        if semantic == "RULE_CONFLICT":
            final_error = "SPATIAL_CONFLICT" if operation == "SUBMIT_PROJECT_APPLICATION" else "PLANNING_CONSTRAINT_CONFLICT"
        elif semantic and semantic != "OK":
            final_error = ERROR_MAP.get(semantic, semantic)
        else:
            final_error = None
        fallback_version = result_version(final_result, fallback_version)
        if not final_result["accepted"]:
            break

    if final_result is None:
        raise AssertionError("scenario produced no result")

    last_entry = store.entries[-1] if store.entries else None
    observed = {
        "scenario_id": scenario["scenario_id"],
        "protocol_version": "0.1",
        "adapter": {
            "name": "TSTChain ReferenceCity Ledger Adapter",
            "version": "0.7",
            "implementation": "python-reference",
            "commit": None,
        },
        "executed_at": scenario["actions"][-1]["occurred_at"],
        "authorized": overall_authorized,
        "accepted": bool(final_result["accepted"]),
        "state_changed": bool(final_result.get("state_changed", False)),
        "state_version": result_version(final_result, fallback_version),
        "error_code": final_error,
        "audit_events": list(dict.fromkeys(audit_events)),
        "hash_match": hash_match,
        "spatial_conflicts": spatial_conflicts,
        "evidence": {
            "transaction_id": last_entry["entry_id"] if last_entry else None,
            "state_proof": last_entry["entry_hash"] if last_entry else None,
            "log_ref": str(store.ledger_path),
        },
    }
    return observed


def run(benchmark: Path, output: Path, ledger_root: Path) -> dict:
    manifest = load(benchmark / "benchmark-input.json")
    if manifest.get("ground_truth_included") is not False:
        raise ValueError("adapter requires ground_truth_included=false")
    if (benchmark / "expected").exists():
        raise ValueError("Ground Truth directory must not be present in adapter input")

    entities = load(benchmark / "data/governance-v0.1/entities.json")
    planning = load(benchmark / "data/core-v0.1/generated/planning-objects.json")
    spatial = load(benchmark / "data/core-v0.1/generated/spatial-objects.json")
    documents = load(benchmark / "data/governance-v0.1/documents-and-approvals.json")

    if output.exists():
        shutil.rmtree(output)
    if ledger_root.exists():
        shutil.rmtree(ledger_root)
    output.mkdir(parents=True)
    ledger_root.mkdir(parents=True)

    produced = []
    for entry in manifest["scenarios"]:
        observed = run_scenario(benchmark, entry, ledger_root, entities, planning, spatial, documents)
        name = observed["scenario_id"].split(":")[-1]
        (output / f"{name}.json").write_text(
            json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        produced.append(name)
    return {"adapter": "TSTChain/0.7", "scenarios": produced, "ground_truth_read": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ledger-root", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.benchmark.resolve(), args.output.resolve(), args.ledger_root.resolve())
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
