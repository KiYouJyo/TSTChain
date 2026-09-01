#!/usr/bin/env python3
"""TST Chain v0.7 persistent ledger and state-sync conformance."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator, FormatChecker

from v0_5_conformance import req
from v0_7_ledger import (
    LedgerStore,
    b64u,
    checkpoint_body,
    entry_core,
    sha256_hex,
    sync_bundle_body,
)

ROOT = Path(__file__).resolve().parents[1]
SD = ROOT / "schemas" / "v0.7"
DEFN = ROOT / "examples" / "v0.5" / "workflow-referencecity.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(name: str, value) -> None:
    schema = load(SD / name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def validator_fixture(seed_offset: int = 0, label: str = "validator"):
    private_keys = {}
    members = []
    for index in range(1, 4):
        actor = f"tst:actor:{label}-{index:02d}"
        key_id = f"tst:key:{label}-{index:02d}"
        private = Ed25519PrivateKey.from_private_bytes(bytes([seed_offset + index]) * 32)
        public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        private_keys[actor] = private
        members.append({"actor_id": actor, "key_id": key_id, "algorithm": "ed25519", "public_key": b64u(public)})
    return {
        "validator_set_id": f"tst:validator-set:{label}-v0.7",
        "members": members,
        "quorum": 2,
        "status": "active",
        "schema_version": "0.7",
    }, private_keys


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


def rebuild_hash_chain(entries: list[dict]) -> None:
    previous = None
    for index, entry in enumerate(entries, 1):
        entry["sequence"] = index
        entry["previous_entry_hash"] = previous
        entry["payload_digest"] = {
            "algorithm": "sha256",
            "digest": sha256_hex(entry["payload"]),
            "canonicalization": "RFC8785-JCS",
        }
        entry["entry_hash"] = sha256_hex(entry_core(entry))
        previous = entry["entry_hash"]


def main() -> int:
    definition = load(DEFN)
    validators, private_keys = validator_fixture()
    validate("validator-set.schema.json", validators)
    Draft202012Validator.check_schema(load(SD / "state-sync-bundle.schema.json"))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "node"
        store = LedgerStore(root)

        # state_seed remains auditable, idempotent and replayable.
        seeded = {
            "instance_id": "tst:wf-instance:seeded",
            "workflow_id": definition["workflow_id"],
            "subject_ref": "RC:PLAN:SEED001",
            "current_state": "effective",
            "current_version": "1",
            "updated_at": "2030-03-01T00:00:00Z",
            "schema_version": "0.5",
        }
        store.seed_instance(seeded, "2030-03-01T00:00:01Z", "referencecity:fixture")
        before_seed_replay = len(store.entries)
        assert store.seed_instance(seeded, "2030-03-01T00:00:02Z", "referencecity:fixture") == seeded
        assert len(store.entries) == before_seed_replay
        conflicting_seed = copy.deepcopy(seeded)
        conflicting_seed["current_version"] = "2"
        try:
            store.seed_instance(conflicting_seed, "2030-03-01T00:00:03Z", "referencecity:fixture")
            raise AssertionError("conflicting state seed was accepted")
        except ValueError:
            pass

        # S001: accepted registration becomes authoritative and survives restart.
        create = req("ledger-s001", "create_plan", "tst:wf-instance:ledger-s001", "RC:PLAN:0003", None, "plan.create")
        result = store.commit_workflow(definition, create, "2030-04-01T00:00:01Z")
        assert result["accepted"] and result["current_version"] == "1"
        validate("ledger-entry.schema.json", store.entries[-1])
        before = len(store.entries)
        replay = store.commit_workflow(definition, create, "2030-04-01T00:00:02Z")
        assert replay["idempotent_replay"] is True and len(store.entries) == before

        # S004: denied action is audit-persistent but cannot mutate state.
        denied = req("ledger-s004", "open_amendment", create["instance_id"], create["subject_ref"], "1", "plan.amend", decision="deny", rules=[{"evaluation_ref": "x", "outcome": "pass"}])
        denied_result = store.commit_workflow(definition, denied, "2030-04-01T00:00:03Z")
        assert denied_result["semantic_code"] == "UNAUTHORIZED"
        assert store.entries[-1]["entry_type"] == "workflow_rejection"
        assert store.instances[create["instance_id"]]["current_version"] == "1"

        # S008: required-signature failure is persisted without state mutation.
        missing_sig = req("ledger-s008", "submit_plan", create["instance_id"], create["subject_ref"], "1", "plan.submit", docs=["RC:DOC:000001"], sigs=[])
        missing_result = store.commit_workflow(definition, missing_sig, "2030-04-01T00:00:04Z")
        assert missing_result["semantic_code"] == "MISSING_SIGNATURE"
        assert store.instances[create["instance_id"]]["current_state"] == "draft"

        # S002 + S010: version history and stale-write rejection are durable.
        advance_to_effective(store, definition, "ledger-history", "RC:PLAN:0001")
        history_instance = "tst:wf-instance:ledger-history"
        amend = req("ledger-s002", "open_amendment", history_instance, "RC:PLAN:0001", "1", "plan.amend", rules=[{"evaluation_ref": "tst:rule-evaluation:s002", "outcome": "pass"}])
        amend_result = store.commit_workflow(definition, amend, "2030-04-01T00:01:00Z")
        assert amend_result["accepted"] and amend_result["previous_version"] == "1" and amend_result["current_version"] == "2"
        history = store.history("RC:PLAN:0001")
        assert any(item.get("payload", {}).get("result", {}).get("current_version") == "1" for item in history)
        assert any(item.get("payload", {}).get("result", {}).get("current_version") == "2" for item in history)

        stale = req("ledger-s010", "open_amendment", history_instance, "RC:PLAN:0001", "1", "plan.amend", rules=[{"evaluation_ref": "x", "outcome": "pass"}])
        stale_result = store.commit_workflow(definition, stale, "2030-04-01T00:01:01Z")
        assert stale_result["semantic_code"] == "VERSION_CONFLICT"
        assert store.instances[history_instance]["current_version"] == "2"

        # S006-style rule rejection is durable.
        advance_to_effective(store, definition, "ledger-rule", "RC:PLAN:0004")
        conflict = req("ledger-s006", "open_amendment", "tst:wf-instance:ledger-rule", "RC:PLAN:0004", "1", "plan.amend", rules=[{"evaluation_ref": "tst:rule-evaluation:referencecity-s006", "outcome": "fail"}])
        conflict_result = store.commit_workflow(definition, conflict, "2030-04-01T00:02:00Z")
        assert conflict_result["semantic_code"] == "RULE_CONFLICT"
        assert store.instances["tst:wf-instance:ledger-rule"]["current_version"] == "1"

        # Persistent evidence verification produces an explicit HASH_MISMATCH verdict.
        store.record_evidence({"evidence_id": "tst:evidence:referencecity-s005", "content_digest": "a" * 64, "status": "approved"}, "2030-04-01T00:03:00Z")
        evidence_result = store.verify_evidence_digest(
            "tst:evidence:referencecity-s005", "b" * 64, "2030-04-01T00:03:01Z"
        )
        assert evidence_result["accepted"] is False
        assert evidence_result["hash_match"] is False
        assert evidence_result["semantic_code"] == "HASH_MISMATCH"

        # Persistent provenance remains verifiable after later ledger activity.
        store.record_provenance({"provenance_id": "tst:plan-version:history-v1", "content_digest": "c" * 64, "version": "1"}, "2030-04-01T00:03:02Z")
        provenance_result = store.verify_provenance_digest(
            "tst:plan-version:history-v1", "c" * 64, "2030-04-01T00:03:03Z"
        )
        assert provenance_result["accepted"] is True and provenance_result["hash_match"] is True

        # Raw ledger tampering remains detectable.
        tampered_root = Path(tmp) / "tampered"
        tampered_root.mkdir()
        rows = copy.deepcopy(store.entries)
        rows[-1]["payload"]["verification"]["expected_content_digest"] = "d" * 64
        (tampered_root / "ledger.jsonl").write_text(
            "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8"
        )
        try:
            LedgerStore(tampered_root)
            raise AssertionError("tampered ledger was accepted")
        except ValueError:
            pass

        # Snapshot is disposable cache; state_seed and workflows both recover from replay.
        state_before = copy.deepcopy(store.instances)
        store.snapshot_path.unlink()
        recovered = LedgerStore(root)
        assert recovered.instances == state_before
        assert recovered.instances[seeded["instance_id"]] == seeded
        assert recovered.snapshot_path.exists()

        # Finality is bound to both validator quorum and the actual ledger prefix Merkle root.
        checkpoint = recovered.checkpoint(validators, private_keys, "2030-04-01T00:04:00Z")
        validate("checkpoint.schema.json", checkpoint)
        LedgerStore.verify_checkpoint(checkpoint, validators, recovered.entries)
        assert checkpoint["through_sequence"] == len(recovered.entries)
        assert len(checkpoint["approvals"]) >= validators["quorum"]

        nonfinal = copy.deepcopy(checkpoint)
        nonfinal["approvals"] = nonfinal["approvals"][:1]
        nonfinal["checkpoint_hash"] = sha256_hex(checkpoint_body(nonfinal))
        try:
            LedgerStore.verify_checkpoint(nonfinal, validators, recovered.entries)
            raise AssertionError("non-quorum checkpoint was accepted")
        except ValueError:
            pass

        # State sync: a fresh node accepts an exact finalized prefix under a locally trusted validator set.
        bundle = recovered.export_sync_bundle(checkpoint, validators)
        assert bundle["bundle_hash"] == sha256_hex(sync_bundle_body(bundle))
        replica = LedgerStore.import_sync_bundle(Path(tmp) / "replica", bundle, validators)
        assert [entry["entry_hash"] for entry in replica.entries] == [entry["entry_hash"] for entry in recovered.entries]
        assert replica.instances == recovered.instances

        # Self-authorized remote validator sets are rejected even if they can produce a cryptographically valid checkpoint.
        attacker_validators, attacker_keys = validator_fixture(20, "attacker")
        attacker_checkpoint = recovered.checkpoint(attacker_validators, attacker_keys, "2030-04-01T00:04:01Z")
        attacker_bundle = recovered.export_sync_bundle(attacker_checkpoint, attacker_validators)
        try:
            LedgerStore.import_sync_bundle(Path(tmp) / "self-authorized", attacker_bundle, validators)
            raise AssertionError("self-authorized remote validator set was trusted")
        except ValueError:
            pass

        # Rebuilding every forged entry hash and the outer bundle hash still cannot preserve the trusted signed checkpoint.
        forged = copy.deepcopy(bundle)
        forged["entries"][0]["payload"]["instance"]["subject_ref"] = "RC:PLAN:FORGED"
        rebuild_hash_chain(forged["entries"])
        forged["bundle_hash"] = sha256_hex(sync_bundle_body(forged))
        try:
            LedgerStore.import_sync_bundle(Path(tmp) / "forged", forged, validators)
            raise AssertionError("forged finalized prefix was accepted")
        except ValueError:
            pass

        # A diverging local fork is never overwritten.
        fork = LedgerStore(Path(tmp) / "fork")
        fork.record_evidence({"evidence_id": "tst:evidence:fork", "content_digest": "f" * 64}, "2030-04-01T00:00:00Z")
        try:
            LedgerStore.import_sync_bundle(fork.root, bundle, validators)
            raise AssertionError("state sync overwrote a local fork")
        except ValueError:
            pass

        # A finalized prefix cannot roll back a node after it has appended newer local entries.
        replica.record_evidence({"evidence_id": "tst:evidence:newer", "content_digest": "e" * 64}, "2030-04-01T00:05:00Z")
        try:
            LedgerStore.import_sync_bundle(replica.root, bundle, validators)
            raise AssertionError("state sync rolled back a longer local ledger")
        except ValueError:
            pass

        for entry in recovered.entries:
            validate("ledger-entry.schema.json", entry)

    print("TST Chain v0.7 ledger core conformance: PASS")
    print("  append-only hash chain + audit persistence + state_seed replay: PASS")
    print("  evidence/provenance digest verification: PASS")
    print("  Merkle checkpoint + Ed25519 validator quorum finality: PASS")
    print("  trust-anchored state sync + self-authorization/fork/rollback rejection: PASS")
    print("  native token / gas / mining dependency: NONE")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"TST Chain v0.7 conformance: FAIL: {exc}", file=sys.stderr)
        raise
