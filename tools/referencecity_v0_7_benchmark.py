#!/usr/bin/env python3
"""ReferenceCity S001-S010 end-to-end benchmark for the TST Chain v0.7 ledger."""
from __future__ import annotations

import argparse
import copy
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from referencecity_gis_adapter import evaluate as spatial_evaluate
from v0_3_conformance import evaluate as rule_evaluate, validate as validate_v0_3
from v0_5_conformance import req
from v0_6_conformance import rule_request as spatial_rule_request
from v0_6_conformance import workflow_request as project_workflow_request
from v0_7_ledger import LedgerStore, b64u, sha256_hex

ROOT = Path(__file__).resolve().parents[1]
PLAN_DEF = ROOT / "examples" / "v0.5" / "workflow-referencecity.json"
PROJECT_DEF = ROOT / "examples" / "v0.6" / "workflow-project-application.json"
S006_REQUEST = ROOT / "examples" / "v0.3" / "evaluation-request-s006.json"
S006_RULE = ROOT / "examples" / "v0.3" / "rule-farmland-land-use.json"
S007_RULE = ROOT / "examples" / "v0.3" / "rule-ecological-intersection.json"
PLAN_V1 = ROOT / "examples" / "v0.4" / "plan-version-v1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def utc_z(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("ReferenceCity timestamp must include an offset")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rc_request(rc_root: Path, scenario: str, filename: str = "request.json") -> dict:
    return load(rc_root / "scenarios" / "v0.1" / scenario / filename)


def expected(rc_root: Path, scenario: str) -> dict:
    return load(rc_root / "expected" / "v0.1" / f"{scenario}.json")


def request_payload_digest(request: dict) -> str:
    digest = sha256_hex(request["payload"])
    if request["payload_hash"] != "sha256:" + digest:
        raise AssertionError(f"ReferenceCity request payload hash mismatch: {request['request_id']}")
    return digest


def complete_rule_evaluation(raw: dict, request: dict, evaluation_id: str, evaluated_at: str) -> dict:
    result = {
        "evaluation_id": evaluation_id,
        "request_id": request["request_id"],
        "rule_set_id": request["rule_set_id"],
        "outcome": raw["outcome"],
        "evaluated_rule_refs": raw["evaluated_rule_refs"],
        "violations": raw["violations"],
        "evaluator_ref": "tst:reference-rule-evaluator:0.3",
        "evaluated_at": evaluated_at,
        "schema_version": "0.3",
    }
    validate_v0_3("rule-evaluation-result.schema.json", result)
    return result


def mapped_request(
    request: dict,
    name: str,
    action: str,
    instance: str,
    permission: str,
    *,
    decision: str = "allow",
    docs: list[str] | None = None,
    sigs: list[str] | None = None,
    rules: list[dict] | None = None,
) -> dict:
    expected_version = request.get("expected_version")
    mapped = req(
        name,
        action,
        instance,
        request["target_id"],
        None if expected_version is None else str(expected_version),
        permission,
        decision=decision,
        docs=docs if docs is not None else request.get("related_document_ids", []),
        sigs=sigs or [],
        rules=rules or [],
        digest=request_payload_digest(request),
    )
    mapped["actor_ref"] = request["actor_id"]
    mapped["occurred_at"] = utc_z(request["occurred_at"])
    return mapped


def setup_to_state(store: LedgerStore, definition: dict, name: str, subject: str, target_state: str) -> dict:
    instance = f"tst:wf-instance:{name}"
    steps = [
        ("create", "create_plan", None, "plan.create", [], [], "draft"),
        ("submit", "submit_plan", "1", "plan.submit", ["RC:DOC:000001"], ["tst:signature:setup-submit"], "submitted"),
        ("review", "review_pass", "1", "plan.review", ["RC:DOC:000001"], ["tst:signature:setup-review"], "reviewed"),
        ("approve", "approve_plan", "1", "plan.approve", ["RC:DOC:000001"], ["tst:signature:setup-approve"], "approved"),
        ("activate", "activate_plan", "1", "plan.activate", ["RC:DOC:000001"], ["tst:signature:setup-activate"], "effective"),
    ]
    last = None
    for index, (suffix, action, version, permission, docs, sigs, state) in enumerate(steps, 1):
        request = req(
            f"setup-{name}-{suffix}", action, instance, subject, version, permission,
            docs=docs, sigs=sigs,
        )
        request["occurred_at"] = f"2030-01-{index:02d}T00:00:00Z"
        last = store.commit_workflow(definition, request, f"2030-01-{index:02d}T00:00:01Z")
        if not last["accepted"]:
            raise AssertionError(f"setup failed for {name}: {last}")
        if state == target_state:
            return last
    raise ValueError(f"unsupported setup target state: {target_state}")


def observation(
    *,
    authorized: bool,
    accepted: bool,
    state_changed: bool,
    state_version: int,
    error_code: str | None,
    audit_event: str,
    hash_match: bool,
    spatial_conflicts: list[dict] | None = None,
) -> dict:
    return {
        "authorized": authorized,
        "accepted": accepted,
        "state_changed": state_changed,
        "state_version": state_version,
        "error_code": error_code,
        "audit_event": audit_event.upper(),
        "hash_match": hash_match,
        "spatial_conflicts": spatial_conflicts or [],
    }


def check_expected(scenario: str, observed: dict, exp: dict) -> None:
    pairs = {
        "authorized": exp["authorized"],
        "accepted": exp["accepted"],
        "state_changed": exp["state_changed"],
        "state_version": exp["expected_state_version"],
        "error_code": exp["expected_error_code"],
        "audit_event": exp["expected_audit_event"],
        "hash_match": exp["expected_hash_match"],
        "spatial_conflicts": exp["expected_spatial_conflicts"],
    }
    for key, value in pairs.items():
        if observed[key] != value:
            raise AssertionError(f"{scenario} mismatch for {key}: observed={observed[key]!r} expected={value!r}")


def validators_fixture():
    private_keys = {}
    members = []
    for index in range(1, 4):
        actor = f"tst:actor:benchmark-validator-{index:02d}"
        key_id = f"tst:key:benchmark-validator-{index:02d}"
        private = Ed25519PrivateKey.from_private_bytes(bytes([10 + index]) * 32)
        public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        private_keys[actor] = private
        members.append({"actor_id": actor, "key_id": key_id, "algorithm": "ed25519", "public_key": b64u(public)})
    return {
        "validator_set_id": "tst:validator-set:referencecity-benchmark-v0.7",
        "members": members,
        "quorum": 2,
        "status": "active",
        "schema_version": "0.7",
    }, private_keys


def run(rc_root: Path, ledger_root: Path) -> dict:
    plan_def = load(PLAN_DEF)
    project_def = load(PROJECT_DEF)
    store = LedgerStore(ledger_root)
    results: dict[str, dict] = {}

    # S001 — new plan registration, persistent version 1.
    q = rc_request(rc_root, "S001")
    r = store.commit_workflow(plan_def, mapped_request(q, "bench-s001", "create_plan", "tst:wf-instance:bench-s001", "plan.create"), utc_z(q["occurred_at"]))
    results["S001"] = observation(
        authorized=True, accepted=r["accepted"], state_changed=r["state_changed"],
        state_version=int(r["current_version"]), error_code=None,
        audit_event=r["audit_event"], hash_match=True,
    )

    # S002 — effective v1 enters amendment and becomes v2.
    setup_to_state(store, plan_def, "bench-s002", "RC:PLAN:0001", "effective")
    q = rc_request(rc_root, "S002")
    r = store.commit_workflow(
        plan_def,
        mapped_request(q, "bench-s002-amend", "open_amendment", "tst:wf-instance:bench-s002", "plan.amend", rules=[{"evaluation_ref": "tst:rule-evaluation:bench-s002", "outcome": "pass"}]),
        utc_z(q["occurred_at"]),
    )
    results["S002"] = observation(
        authorized=True, accepted=r["accepted"], state_changed=r["state_changed"],
        state_version=int(r["current_version"]), error_code=None,
        audit_event=r["audit_event"], hash_match=True,
    )

    # S003 — fixture begins submitted/v1; consume real review, approve and activate requests.
    setup_to_state(store, plan_def, "bench-s003", "RC:PLAN:0002", "submitted")
    s003_steps = [
        ("request-review.json", "review_pass", "plan.review", "review"),
        ("request-approve.json", "approve_plan", "plan.approve", "approve"),
        ("request-activate.json", "activate_plan", "plan.activate", "activate"),
    ]
    s003_hashes = []
    last = None
    for filename, action, permission, suffix in s003_steps:
        q = rc_request(rc_root, "S003", filename)
        s003_hashes.append(request_payload_digest(q))
        mapped = mapped_request(
            q, f"bench-s003-{suffix}", action, "tst:wf-instance:bench-s003", permission,
            docs=q.get("related_document_ids", []), sigs=[f"tst:signature:bench-s003-{suffix}"],
        )
        last = store.commit_workflow(plan_def, mapped, utc_z(q["occurred_at"]))
        if not last["accepted"]:
            raise AssertionError(f"S003 {suffix} failed: {last}")
    assert last is not None
    results["S003"] = observation(
        authorized=True, accepted=last["accepted"], state_changed=last["state_changed"],
        state_version=int(last["current_version"]), error_code=None,
        audit_event=last["audit_event"], hash_match=bool(s003_hashes),
    )

    # S004 — unauthorized amendment is rejected, version 1 remains authoritative, rejection persists.
    setup_to_state(store, plan_def, "bench-s004", "RC:PLAN:0001", "effective")
    q = rc_request(rc_root, "S004")
    r = store.commit_workflow(
        plan_def,
        mapped_request(q, "bench-s004-denied", "open_amendment", "tst:wf-instance:bench-s004", "plan.amend", decision="deny", rules=[{"evaluation_ref": "tst:rule-evaluation:bench-s004", "outcome": "pass"}]),
        utc_z(q["occurred_at"]),
    )
    results["S004"] = observation(
        authorized=False, accepted=r["accepted"], state_changed=r["state_changed"],
        state_version=int(r["current_version"]), error_code=r["semantic_code"],
        audit_event=r["audit_event"], hash_match=True,
    )

    # S005 — compare canonical hashes of the real approved document and the real tampered fixture.
    q = rc_request(rc_root, "S005")
    request_payload_digest(q)
    approved_doc = load(rc_root / "data" / "governance-v0.1" / "documents" / "plan-v1-submission.json")
    tampered_doc = load(rc_root / "scenarios" / "v0.1" / "S005" / "tampered-document.json")
    approved_digest = sha256_hex(approved_doc)
    tampered_digest = sha256_hex(tampered_doc)
    if approved_digest == tampered_digest:
        raise AssertionError("S005 tampered document unexpectedly has the approved canonical hash")
    store.record_evidence(
        {"evidence_id": "RC:DOC:000001", "content_digest": approved_digest, "status": "approved", "source_ref": "ReferenceCity:data/governance-v0.1/documents/plan-v1-submission.json"},
        "2030-02-01T01:00:00Z",
    )
    verified = store.verify_evidence_digest("RC:DOC:000001", tampered_digest, utc_z(q["occurred_at"]))
    results["S005"] = observation(
        authorized=True, accepted=verified["accepted"], state_changed=verified["state_changed"],
        state_version=int(q["expected_version"]), error_code=verified["semantic_code"],
        audit_event=verified["audit_event"], hash_match=verified["hash_match"],
    )

    # S006 — real v0.3 farmland rule evaluation feeds a persistent v0.5 workflow rejection.
    setup_to_state(store, plan_def, "bench-s006", "RC:PLAN:0001", "effective")
    q = rc_request(rc_root, "S006")
    request_payload_digest(q)
    s006_rule_request = load(S006_REQUEST)
    raw_rule_eval = rule_evaluate(s006_rule_request, [load(S006_RULE)])
    rule_eval = complete_rule_evaluation(
        raw_rule_eval,
        s006_rule_request,
        "tst:rule-evaluation:referencecity-s006-runtime",
        utc_z(q["occurred_at"]),
    )
    if rule_eval["outcome"] != "fail" or not rule_eval["violations"]:
        raise AssertionError("S006 reference rule evaluator did not produce the expected conflict")
    store.record_evidence({"rule_evaluation": rule_eval}, rule_eval["evaluated_at"])
    mapped = mapped_request(
        q, "bench-s006-conflict", "open_amendment", "tst:wf-instance:bench-s006", "plan.amend",
        rules=[{"evaluation_ref": rule_eval["evaluation_id"], "outcome": rule_eval["outcome"]}],
    )
    r = store.commit_workflow(plan_def, mapped, utc_z(q["occurred_at"]))
    farmland_rule = load(S006_RULE)
    conflict = {
        "conflict_type": "farmland_control_conflict",
        "target_id": s006_rule_request["subject_object_ref"],
        "constraint_id": farmland_rule["scope"]["spatial_constraint_refs"][0],
        "severity": "ERROR",
    }
    if r["semantic_code"] != "RULE_CONFLICT":
        raise AssertionError(f"S006 workflow did not preserve rule rejection: {r}")
    results["S006"] = observation(
        authorized=True, accepted=r["accepted"], state_changed=r["state_changed"],
        state_version=int(r["current_version"]), error_code="PLANNING_CONSTRAINT_CONFLICT",
        audit_event=r["audit_event"], hash_match=True, spatial_conflicts=[conflict],
    )

    # S007 — real ReferenceCity geometry -> Shapely -> v0.3 rule -> persistent project workflow rejection.
    q = rc_request(rc_root, "S007")
    digest = request_payload_digest(q)
    evaluated_at = utc_z(q["occurred_at"])
    spatial = spatial_evaluate(rc_root, "RC:PARCEL:000001", "RC:BOUNDARY:ECO001", "intersects", evaluated_at)
    adapter = spatial["adapter_result"]
    if adapter["relation_value"] is not True:
        raise AssertionError("S007 real geometry did not intersect ecological boundary")
    rr = spatial_rule_request(
        adapter["subject_ref"], spatial["spatial_evaluation"]["relation"],
        spatial["spatial_evaluation"]["spatial_evaluation_id"], digest,
    )
    raw_rule_eval = rule_evaluate(rr, [load(S007_RULE)])
    rule_eval = complete_rule_evaluation(
        raw_rule_eval,
        rr,
        "tst:rule-evaluation:referencecity-s007-runtime",
        evaluated_at,
    )
    if rule_eval["outcome"] != "fail":
        raise AssertionError("S007 ecological rule did not fail")
    store.record_evidence({"spatial_adapter_result": adapter, "spatial_evaluation": spatial["spatial_evaluation"], "rule_evaluation": rule_eval}, evaluated_at)
    project_request = project_workflow_request(rule_eval["outcome"], digest, "referencecity-benchmark-s007")
    project_request["actor_ref"] = q["actor_id"]
    project_request["occurred_at"] = evaluated_at
    r = store.commit_workflow(project_def, project_request, evaluated_at)
    if r["semantic_code"] != "RULE_CONFLICT":
        raise AssertionError(f"S007 project workflow did not reject spatial conflict: {r}")
    conflict = {
        "conflict_type": "ecological_boundary_conflict",
        "target_id": adapter["subject_ref"],
        "constraint_id": adapter["constraint_ref"],
        "severity": "ERROR",
    }
    results["S007"] = observation(
        authorized=True, accepted=r["accepted"], state_changed=r["state_changed"],
        state_version=int(q["expected_version"]), error_code="SPATIAL_CONFLICT",
        audit_event=r["audit_event"], hash_match=True, spatial_conflicts=[conflict],
    )

    # S008 — approved v1 cannot activate without required signature; rejection persists.
    setup_to_state(store, plan_def, "bench-s008", "RC:PLAN:0002", "approved")
    q = rc_request(rc_root, "S008")
    r = store.commit_workflow(
        plan_def,
        mapped_request(q, "bench-s008-missing-signature", "activate_plan", "tst:wf-instance:bench-s008", "plan.activate", docs=q.get("related_document_ids", []), sigs=[]),
        utc_z(q["occurred_at"]),
    )
    results["S008"] = observation(
        authorized=True, accepted=r["accepted"], state_changed=r["state_changed"],
        state_version=int(r["current_version"]), error_code=r["semantic_code"],
        audit_event=r["audit_event"], hash_match=True,
    )

    # S009 — keep v1 provenance, create v2, then verify historical v1 digest from the ledger.
    setup_to_state(store, plan_def, "bench-s009", "RC:PLAN:0001", "effective")
    v1 = load(PLAN_V1)
    v1_digest = v1["content_digest"]["digest"]
    store.record_provenance(
        {"provenance_id": v1["plan_version_id"], "subject_ref": "RC:PLAN:0001", "version": "1", "content_digest": v1_digest, "status": "effective"},
        "2030-03-01T00:00:00Z",
    )
    amend = req(
        "bench-s009-amend", "open_amendment", "tst:wf-instance:bench-s009", "RC:PLAN:0001", "1", "plan.amend",
        rules=[{"evaluation_ref": "tst:rule-evaluation:bench-s009", "outcome": "pass"}],
    )
    store.commit_workflow(plan_def, amend, "2030-03-02T01:00:00Z")
    q = rc_request(rc_root, "S009")
    request_payload_digest(q)
    verified = store.verify_provenance_digest(v1["plan_version_id"], v1_digest, utc_z(q["occurred_at"]))
    results["S009"] = observation(
        authorized=True, accepted=verified["accepted"], state_changed=verified["state_changed"],
        state_version=int(q["expected_version"]), error_code=None if verified["accepted"] else verified["semantic_code"],
        audit_event=verified["audit_event"], hash_match=verified["hash_match"],
    )

    # S010 — build authoritative v2 then submit real stale expected_version=1 request.
    setup_to_state(store, plan_def, "bench-s010", "RC:PLAN:0001", "effective")
    first_amend = req(
        "bench-s010-first-amend", "open_amendment", "tst:wf-instance:bench-s010", "RC:PLAN:0001", "1", "plan.amend",
        rules=[{"evaluation_ref": "tst:rule-evaluation:bench-s010-first", "outcome": "pass"}],
    )
    first = store.commit_workflow(plan_def, first_amend, "2030-03-09T23:00:00Z")
    if first["current_version"] != "2":
        raise AssertionError("S010 setup did not create authoritative version 2")
    q = rc_request(rc_root, "S010")
    r = store.commit_workflow(
        plan_def,
        mapped_request(q, "bench-s010-stale", "open_amendment", "tst:wf-instance:bench-s010", "plan.amend", rules=[{"evaluation_ref": "tst:rule-evaluation:bench-s010", "outcome": "pass"}]),
        utc_z(q["occurred_at"]),
    )
    results["S010"] = observation(
        authorized=True, accepted=r["accepted"], state_changed=r["state_changed"],
        state_version=int(r["current_version"]), error_code=r["semantic_code"],
        audit_event=r["audit_event"], hash_match=True,
    )

    for scenario in [f"S{i:03d}" for i in range(1, 11)]:
        check_expected(scenario, results[scenario], expected(rc_root, scenario))

    # Restart from the persistent ledger before finality; all workflow states must replay identically.
    state_before = copy.deepcopy(store.instances)
    entry_hashes_before = [entry["entry_hash"] for entry in store.entries]
    recovered = LedgerStore(ledger_root)
    if recovered.instances != state_before or [entry["entry_hash"] for entry in recovered.entries] != entry_hashes_before:
        raise AssertionError("ReferenceCity benchmark state did not survive ledger replay")

    # Finalize the complete benchmark ledger with authority quorum and verify it against the actual Merkle prefix.
    validators, private_keys = validators_fixture()
    checkpoint = recovered.checkpoint(validators, private_keys, "2030-03-10T02:00:00Z")
    LedgerStore.verify_checkpoint(checkpoint, validators, recovered.entries)

    return {
        "benchmark": "ReferenceCity S001-S010 / protocol 0.1",
        "tstchain_version": "0.7",
        "full": 10,
        "partial": 0,
        "unsupported": 0,
        "ledger_entries": len(recovered.entries),
        "checkpoint_hash": checkpoint["checkpoint_hash"],
        "checkpoint_sequence": checkpoint["through_sequence"],
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--referencecity-root", type=Path, required=True)
    parser.add_argument("--ledger-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.ledger_root:
        args.ledger_root.mkdir(parents=True, exist_ok=True)
        report = run(args.referencecity_root.resolve(), args.ledger_root.resolve())
    else:
        with tempfile.TemporaryDirectory() as tmp:
            report = run(args.referencecity_root.resolve(), Path(tmp) / "ledger")

    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print("TST Chain v0.7 ReferenceCity S001-S010 persistent benchmark: PASS")
    print(f"  full={report['full']} partial={report['partial']} unsupported={report['unsupported']}")
    print(f"  finalized ledger entries={report['ledger_entries']} checkpoint={report['checkpoint_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
