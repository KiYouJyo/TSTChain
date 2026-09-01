#!/usr/bin/env python3
"""Minimal persistent ledger reference implementation for TST Chain v0.7."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
from pathlib import Path

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from v0_5_conformance import Engine, intent_key

CHECKPOINT_DOMAIN = b"TSTCHAIN-CHECKPOINT-V0.7\x00"


def canonical_bytes(value) -> bytes:
    return rfc8785.dumps(value)


def sha256_hex(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def b64u(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def b64u_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * ((4 - len(value) % 4) % 4))


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def merkle_root(hashes: list[str]) -> str:
    if not hashes:
        raise ValueError("cannot checkpoint an empty ledger")
    level = [bytes.fromhex(item) for item in hashes]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0].hex()


def entry_core(entry: dict) -> dict:
    return {key: value for key, value in entry.items() if key != "entry_hash"}


def checkpoint_unsigned(checkpoint: dict) -> dict:
    return {key: value for key, value in checkpoint.items() if key not in {"approvals", "checkpoint_hash"}}


def checkpoint_body(checkpoint: dict) -> dict:
    return {key: value for key, value in checkpoint.items() if key != "checkpoint_hash"}


class LedgerStore:
    def __init__(self, root: Path, ledger_id: str = "tst:ledger:referencecity"):
        self.root = Path(root)
        self.ledger_id = ledger_id
        self.ledger_path = self.root / "ledger.jsonl"
        self.snapshot_path = self.root / "state-snapshot.json"
        self.entries = self._read_entries()
        self.verify()
        self.instances: dict[str, dict] = {}
        self.request_records: dict[str, tuple[bytes, dict]] = {}
        self._replay()
        self.write_snapshot()

    def _read_entries(self) -> list[dict]:
        if not self.ledger_path.exists():
            return []
        return [json.loads(line) for line in self.ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def verify(self) -> None:
        previous = None
        for index, entry in enumerate(self.entries, 1):
            if entry["ledger_id"] != self.ledger_id:
                raise ValueError("ledger id mismatch")
            if entry["sequence"] != index:
                raise ValueError("sequence mismatch")
            if entry["previous_entry_hash"] != previous:
                raise ValueError("hash-chain predecessor mismatch")
            if entry["payload_digest"] != {"algorithm": "sha256", "digest": sha256_hex(entry["payload"]), "canonicalization": "RFC8785-JCS"}:
                raise ValueError("payload digest mismatch")
            if entry["entry_hash"] != sha256_hex(entry_core(entry)):
                raise ValueError("entry hash mismatch")
            previous = entry["entry_hash"]

    def _replay(self) -> None:
        self.instances = {}
        self.request_records = {}
        for entry in self.entries:
            if entry["entry_type"] == "state_seed":
                instance = copy.deepcopy(entry["payload"]["instance"])
                self.instances[instance["instance_id"]] = instance
                continue
            if entry["entry_type"] not in {"workflow_commit", "workflow_rejection"}:
                continue
            request = entry["payload"]["request"]
            result = entry["payload"]["result"]
            self.request_records[request["request_id"]] = (intent_key(request), copy.deepcopy(result))
            if result["accepted"] and result["state_changed"]:
                self.instances[request["instance_id"]] = {
                    "instance_id": request["instance_id"],
                    "workflow_id": request["workflow_id"],
                    "subject_ref": request["subject_ref"],
                    "current_state": result["current_state"],
                    "current_version": result["current_version"],
                    "updated_at": request["occurred_at"],
                    "schema_version": "0.5",
                }

    def write_snapshot(self) -> None:
        snapshot = {
            "ledger_id": self.ledger_id,
            "through_sequence": len(self.entries),
            "through_entry_hash": self.entries[-1]["entry_hash"] if self.entries else None,
            "instances": sorted(self.instances.values(), key=lambda item: item["instance_id"]),
            "schema_version": "0.7",
        }
        atomic_text(self.snapshot_path, json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    def append(self, entry_type: str, payload: dict, committed_at: str) -> dict:
        previous = self.entries[-1]["entry_hash"] if self.entries else None
        sequence = len(self.entries) + 1
        entry = {
            "ledger_id": self.ledger_id,
            "entry_id": f"tst:ledger-entry:{sequence:012d}",
            "sequence": sequence,
            "entry_type": entry_type,
            "previous_entry_hash": previous,
            "payload": copy.deepcopy(payload),
            "payload_digest": {"algorithm": "sha256", "digest": sha256_hex(payload), "canonicalization": "RFC8785-JCS"},
            "committed_at": committed_at,
            "schema_version": "0.7",
        }
        entry["entry_hash"] = sha256_hex(entry)
        new_entries = self.entries + [entry]
        atomic_text(self.ledger_path, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for item in new_entries))
        self.entries = new_entries
        self.verify()
        self._replay()
        self.write_snapshot()
        return copy.deepcopy(entry)

    def seed_instance(self, instance: dict, committed_at: str, source_ref: str) -> dict:
        existing = self.instances.get(instance["instance_id"])
        if existing is not None:
            if existing != instance:
                raise ValueError("conflicting state seed")
            return copy.deepcopy(existing)
        self.append("state_seed", {"instance": instance, "source_ref": source_ref}, committed_at)
        return copy.deepcopy(self.instances[instance["instance_id"]])

    def commit_workflow(self, definition: dict, request: dict, processed_at: str) -> dict:
        engine = Engine(definition, list(self.instances.values()))
        engine.requests = copy.deepcopy(self.request_records)
        result = engine.transition(copy.deepcopy(request), processed_at)
        if result.get("idempotent_replay"):
            return result
        entry_type = "workflow_commit" if result["accepted"] else "workflow_rejection"
        self.append(entry_type, {"request": request, "result": result}, processed_at)
        return result

    def record_evidence(self, payload: dict, committed_at: str) -> dict:
        return self.append("evidence_record", payload, committed_at)

    def record_provenance(self, payload: dict, committed_at: str) -> dict:
        return self.append("provenance_record", payload, committed_at)

    def history(self, subject_ref: str) -> list[dict]:
        out = []
        for entry in self.entries:
            if entry["entry_type"] == "state_seed" and entry["payload"]["instance"].get("subject_ref") == subject_ref:
                out.append(copy.deepcopy(entry))
                continue
            request = entry.get("payload", {}).get("request")
            if request and request.get("subject_ref") == subject_ref:
                out.append(copy.deepcopy(entry))
        return out

    def checkpoint(self, validator_set: dict, private_keys: dict[str, Ed25519PrivateKey], created_at: str, previous_checkpoint_hash: str | None = None) -> dict:
        if not self.entries:
            raise ValueError("empty ledger")
        unsigned = {
            "checkpoint_id": f"tst:checkpoint:{len(self.entries):012d}",
            "ledger_id": self.ledger_id,
            "through_sequence": len(self.entries),
            "entry_count": len(self.entries),
            "merkle_root": merkle_root([item["entry_hash"] for item in self.entries]),
            "previous_checkpoint_hash": previous_checkpoint_hash,
            "validator_set_id": validator_set["validator_set_id"],
            "finality": "quorum_signed",
            "created_at": created_at,
            "schema_version": "0.7",
        }
        message = CHECKPOINT_DOMAIN + canonical_bytes(unsigned)
        approvals = []
        for member in validator_set["members"]:
            private = private_keys.get(member["actor_id"])
            if private is None:
                continue
            approvals.append({"actor_id": member["actor_id"], "key_id": member["key_id"], "algorithm": "ed25519", "signature": b64u(private.sign(message))})
            if len(approvals) >= validator_set["quorum"]:
                break
        if len(approvals) < validator_set["quorum"]:
            raise ValueError("validator quorum unavailable")
        checkpoint = {**unsigned, "approvals": approvals}
        checkpoint["checkpoint_hash"] = sha256_hex(checkpoint)
        self.verify_checkpoint(checkpoint, validator_set)
        atomic_text(self.root / "checkpoint.json", json.dumps(checkpoint, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        return checkpoint

    @staticmethod
    def verify_checkpoint(checkpoint: dict, validator_set: dict) -> None:
        if validator_set["status"] != "active" or checkpoint["validator_set_id"] != validator_set["validator_set_id"]:
            raise ValueError("inactive/mismatched validator set")
        if validator_set["quorum"] > len(validator_set["members"]):
            raise ValueError("invalid quorum")
        if checkpoint["checkpoint_hash"] != sha256_hex(checkpoint_body(checkpoint)):
            raise ValueError("checkpoint hash mismatch")
        members = {item["actor_id"]: item for item in validator_set["members"]}
        message = CHECKPOINT_DOMAIN + canonical_bytes(checkpoint_unsigned(checkpoint))
        valid = set()
        for approval in checkpoint["approvals"]:
            member = members.get(approval["actor_id"])
            if not member or member["key_id"] != approval["key_id"]:
                continue
            try:
                Ed25519PublicKey.from_public_bytes(b64u_decode(member["public_key"])).verify(b64u_decode(approval["signature"]), message)
                valid.add(approval["actor_id"])
            except (ValueError, InvalidSignature):
                continue
        if len(valid) < validator_set["quorum"]:
            raise ValueError("checkpoint is not final: validator quorum not met")
