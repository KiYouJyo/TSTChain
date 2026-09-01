#!/usr/bin/env python3
"""TST Chain v0.7 persistent ledger conformance."""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator, FormatChecker

from v0_5_conformance import req
from v0_7_ledger import LedgerStore, b64u

ROOT = Path(__file__).resolve().parents[1]
SD = ROOT / "schemas" / "v0.7"
DEFN = ROOT / "examples" / "v0.5" / "workflow-referencecity.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(name: str, value) -> None:
    schema = load(SD / name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def validator_fixture():
    private_keys = {}
    members = []
    for index in range(1, 4):
        actor = f"tst:actor:validator-{index:02d}"
        key_id = f"tst:key:validator-{index:02d}"
        private = Ed25519PrivateKey.from_private_bytes(bytes([index]) * 32)
        public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        private_keys[actor] = private
        members.append({"actor_id": actor, "key_id": key_id, "algorithm": "ed25519", "public_key": b64u(public)})
    return {"validator_set_id": "tst:validator-set:referencecity-v0.7", "members": members, "quorum": 2, "status": "active", "schema_version": "0.7"}, private_keys


def advance_to_effective(store: LedgerStore, definition: dict, name: str, subject: str) -> None:
    instance = f"tst:wf-instance:{name}"
    steps = [
        req(name + "-create", "create_plan", instance, subject, None, "plan.create"),
        req(name + "-submit", "submit_plan", instance, subject, "1", "plan.submit", docs=["RC:DOC:000001"], sigs=["tst:signature:submit"]),
        req(name + "-review", "review_pass", instance, subject, "1", "plan.review", docs=["RC:DOC:000001"], sigs=["tst:signature:review"]),
        req(name + "-approve", "approve_plan", instance, subject, "1", "plan.approve", docs=["RC:DOC:000001"], sigs=["tst:signature:approve"]),
        req(name + "-activate", "activate_plan", instance, subject, "1", "plan.activate", docs=["RC:DOC:000001"], sigs=["tst:signature:activate"]),
    ]
    for index, request in enumerate(steps, 1):
        result = store.commit_workflow(definition, request, f"2030-04-01T00:00:{index:02d}Z")
        assert result["accepted"] is True
    assert store.instances[instance]["current_state"] == "effective"


def main() -> int:
    definition = load(DEFN)
    validators, private_keys = validator_fixture()
    validate("validator-set.schema.json", validators)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "node"
        store = LedgerStore(root)

        # S001: accepted registration becomes authoritative and survives restart.
        create = req("ledger-s001", "create_plan", "tst:wf-instance:ledger-s001", "RC:PLAN:0003", None, "plan.create")
        result = store.commit_workflow(definition, create, "2030-04-01T00:00:01Z")
        assert result["accepted"] and result["current_version"] == "1"
        validate("ledger-entry.schema.json", store.entries[-1])
        before = len(store.entries)
        replay = store.commit_workflow(definition, create, "2030-04-01T00:00:02Z")
        assert replay["idempotent_replay"] is True and len(store.entries) == before

        # S004: denied action is audit-persistent but cannot mutate state.
        denied = req("ledger-s004", "open_amendment", "tst:wf-instance:ledger-s001", "RC:PLAN:0003", "1", "plan.amend", decision="deny", rules=[{"evaluation_ref": "x", "outcome": "pass"}])
        denied_result = store.commit_workflow(definition, denied, "2030-04-01T00:00:03Z")
        assert denied_result["semantic_code"] == "UNAUTHORIZED"
        assert store.entries[-1]["entry_type"] == "workflow_rejection"
        assert store.instances[create["instance_id"]]["current_version"] == "1"

        # S008: a required-signature failure is persisted without state mutation.
        missing_sig = req("ledger-s008", "submit_plan", create["instance_id"], create["subject_ref"], "1", "plan.submit", docs=["RC:DOC:000001"], sigs=[])
        missing_result = store.commit_workflow(definition, missing_sig, "2030-04-01T00:00:04Z")
        assert missing_result["semantic_code"] == "MISSING_SIGNATURE"
        assert store.instances[create["instance_id"]]["current_state"] == "draft"

        # Build a real effective plan then amend it: history retains v1 while current becomes v2.
        advance_to_effective(store, definition, "ledger-history", "RC:PLAN:0001")
        history_instance = "tst:wf-instance:ledger-history"
        amend = req("ledger-s002", "open_amendment", history_instance, "RC:PLAN:0001", "1", "plan.amend", rules=[{"evaluation_ref": "tst:rule-evaluation:s002", "outcome": "pass"}])
        amend_result = store.commit_workflow(definition, amend, "2030-04-01T00:01:00Z")
        assert amend_result["accepted"] and amend_result["previous_version"] == "1" and amend_result["current_version"] == "2"
        history = store.history("RC:PLAN:0001")
        assert any(item["payload"]["result"].get("current_version") == "1" for item in history)
        assert any(item["payload"]["result"].get("current_version") == "2" for item in history)

        # S010: stale optimistic-concurrency request is rejected and audit-persisted.
        stale = req("ledger-s010", "open_amendment", history_instance, "RC:PLAN:0001", "1", "plan.amend", rules=[{"evaluation_ref": "x", "outcome": "pass"}])
        stale_result = store.commit_workflow(definition, stale, "2030-04-01T00:01:01Z")
        assert stale_result["semantic_code"] == "VERSION_CONFLICT"
        assert store.instances[history_instance]["current_version"] == "2"

        # S006-style rule rejection on another effective plan proves rejected rule gates are durable.
        advance_to_effective(store, definition, "ledger-rule", "RC:PLAN:0004")
        conflict = req("ledger-s006", "open_amendment", "tst:wf-instance:ledger-rule", "RC:PLAN:0004", "1", "plan.amend", rules=[{"evaluation_ref": "tst:rule-evaluation:referencecity-s006", "outcome": "fail"}])
        conflict_result = store.commit_workflow(definition, conflict, "2030-04-01T00:02:00Z")
        assert conflict_result["semantic_code"] == "RULE_CONFLICT"
        assert store.instances["tst:wf-instance:ledger-rule"]["current_version"] == "1"

        # S005: evidence is hash-bound; modifying stored payload bytes without rebuilding the chain is detected.
        store.record_evidence({"evidence_id": "tst:evidence:referencecity-s005", "content_digest": "a" * 64, "status": "approved"}, "2030-04-01T00:03:00Z")
        tampered_root = Path(tmp) / "tampered"
        tampered_root.mkdir()
        rows = [json.loads(line) for line in store.ledger_path.read_text(encoding="utf-8").splitlines()]
        rows[-1]["payload"]["content_digest"] = "b" * 64
        (tampered_root / "ledger.jsonl").write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
        try:
            LedgerStore(tampered_root)
            raise AssertionError("tampered ledger was accepted")
        except ValueError:
            pass

        # Snapshot is disposable cache: delete it, restart, and recover identical authoritative state from ledger.
        state_before = copy.deepcopy(store.instances)
        store.snapshot_path.unlink()
        recovered = LedgerStore(root)
        assert recovered.instances == state_before
        assert recovered.snapshot_path.exists()

        # Quorum-signed Merkle checkpoint establishes finality for all current entries.
        checkpoint = recovered.checkpoint(validators, private_keys, "2030-04-01T00:04:00Z")
        validate("checkpoint.schema.json", checkpoint)
        LedgerStore.verify_checkpoint(checkpoint, validators)
        assert checkpoint["through_sequence"] == len(recovered.entries)
        assert len(checkpoint["approvals"]) >= validators["quorum"]

        # Removing one approval drops below quorum and must invalidate finality.
        nonfinal = copy.deepcopy(checkpoint)
        nonfinal["approvals"] = nonfinal["approvals"][:1]
        from v0_7_ledger import sha256_hex, checkpoint_body
        nonfinal["checkpoint_hash"] = sha256_hex(checkpoint_body(nonfinal))
        try:
            LedgerStore.verify_checkpoint(nonfinal, validators)
            raise AssertionError("non-quorum checkpoint was accepted")
        except ValueError:
            pass

        for entry in recovered.entries:
            validate("ledger-entry.schema.json", entry)

    print("TST Chain v0.7 ledger core conformance: PASS")
    print("  append-only hash chain + audit persistence: PASS")
    print("  snapshot deletion + ledger replay recovery: PASS")
    print("  Merkle checkpoint + Ed25519 validator quorum finality: PASS")
    print("  native token / gas / mining dependency: NONE")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"TST Chain v0.7 conformance: FAIL: {exc}", file=sys.stderr)
        raise
