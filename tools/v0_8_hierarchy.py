#!/usr/bin/env python3
"""Hierarchical jurisdiction and cross-domain proof primitives for TST Chain v0.8."""
from __future__ import annotations

import copy
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from v0_7_ledger import (
    LedgerStore,
    b64u,
    b64u_decode,
    canonical_bytes,
    entry_core,
    merkle_root,
    sha256_hex,
)

DOMAIN_CHECKPOINT_DOMAIN = b"TSTCHAIN-DOMAIN-CHECKPOINT-V0.8\x00"
LEVEL_RANK = {"local": 0, "county": 1, "city": 2, "province": 3, "national": 4, "federation": 5}


def _domain_checkpoint_unsigned(checkpoint: dict) -> dict:
    return {k: v for k, v in checkpoint.items() if k not in {"approvals", "domain_checkpoint_hash"}}


def _domain_checkpoint_body(checkpoint: dict) -> dict:
    return {k: v for k, v in checkpoint.items() if k != "domain_checkpoint_hash"}


def canonical_commitments(commitments: list[dict]) -> list[dict]:
    return sorted((copy.deepcopy(x) for x in commitments), key=canonical_bytes)


def commitments_root(commitments: list[dict]) -> str:
    ordered = canonical_commitments(commitments)
    return merkle_root([sha256_hex(item) for item in ordered])


class DomainRegistry:
    def __init__(self, domains: list[dict]):
        self.domains = {d["domain_id"]: copy.deepcopy(d) for d in domains}
        if len(self.domains) != len(domains):
            raise ValueError("duplicate domain_id")
        self.verify()

    def get(self, domain_id: str) -> dict:
        try:
            return copy.deepcopy(self.domains[domain_id])
        except KeyError as exc:
            raise KeyError(f"unknown domain: {domain_id}") from exc

    def verify(self) -> None:
        for domain in self.domains.values():
            parent_id = domain["parent_domain_id"]
            if parent_id is None:
                continue
            if parent_id == domain["domain_id"]:
                raise ValueError("domain cannot parent itself")
            parent = self.domains.get(parent_id)
            if parent is None:
                raise ValueError(f"missing parent domain: {parent_id}")
            if LEVEL_RANK[parent["level"]] <= LEVEL_RANK[domain["level"]]:
                raise ValueError("parent jurisdiction level must be higher")
        for start in self.domains:
            seen = set()
            cur = start
            while cur is not None:
                if cur in seen:
                    raise ValueError("domain hierarchy cycle")
                seen.add(cur)
                cur = self.domains[cur]["parent_domain_id"]

    def lineage(self, domain_id: str) -> list[str]:
        if domain_id not in self.domains:
            raise KeyError(domain_id)
        out = []
        cur = domain_id
        while cur is not None:
            out.append(cur)
            cur = self.domains[cur]["parent_domain_id"]
        return out


def create_domain_checkpoint(
    domain: dict,
    local_checkpoint: dict,
    child_commitments: list[dict],
    validator_set: dict,
    private_keys: dict[str, Ed25519PrivateKey],
    created_at: str,
    previous_domain_checkpoint_hash: str | None = None,
) -> dict:
    if local_checkpoint["ledger_id"] != domain["ledger_id"]:
        raise ValueError("local checkpoint ledger does not match domain")
    if local_checkpoint["validator_set_id"] != domain["validator_set_id"]:
        raise ValueError("local checkpoint validator set does not match domain")
    if validator_set["validator_set_id"] != domain["validator_set_id"] or validator_set["status"] != "active":
        raise ValueError("validator set mismatch/inactive")

    commitments = canonical_commitments([
        {"kind": "local_checkpoint", "domain_id": domain["domain_id"], "checkpoint_hash": local_checkpoint["checkpoint_hash"]},
        *copy.deepcopy(child_commitments),
    ])
    unsigned = {
        "domain_checkpoint_id": f"tst:domain-checkpoint:{domain['domain_id'].split(':')[-1]}-{local_checkpoint['through_sequence']}",
        "domain_id": domain["domain_id"],
        "local_checkpoint_hash": local_checkpoint["checkpoint_hash"],
        "commitments": commitments,
        "commitment_root": commitments_root(commitments),
        "previous_domain_checkpoint_hash": previous_domain_checkpoint_hash,
        "validator_set_id": validator_set["validator_set_id"],
        "finality": "quorum_signed",
        "created_at": created_at,
        "schema_version": "0.8",
    }
    message = DOMAIN_CHECKPOINT_DOMAIN + canonical_bytes(unsigned)
    approvals = []
    for member in validator_set["members"]:
        private = private_keys.get(member["actor_id"])
        if private is None:
            continue
        approvals.append({
            "actor_id": member["actor_id"],
            "key_id": member["key_id"],
            "algorithm": "ed25519",
            "signature": b64u(private.sign(message)),
        })
        if len(approvals) >= validator_set["quorum"]:
            break
    if len(approvals) < validator_set["quorum"]:
        raise ValueError("domain checkpoint validator quorum unavailable")
    checkpoint = {**unsigned, "approvals": approvals}
    checkpoint["domain_checkpoint_hash"] = sha256_hex(checkpoint)
    verify_domain_checkpoint(checkpoint, domain, validator_set)
    return checkpoint


def verify_domain_checkpoint(checkpoint: dict, domain: dict, validator_set: dict) -> None:
    if checkpoint["domain_id"] != domain["domain_id"]:
        raise ValueError("domain checkpoint domain mismatch")
    if checkpoint["validator_set_id"] != domain["validator_set_id"]:
        raise ValueError("domain checkpoint validator mismatch")
    if validator_set["validator_set_id"] != checkpoint["validator_set_id"] or validator_set["status"] != "active":
        raise ValueError("validator set mismatch/inactive")
    if checkpoint["commitment_root"] != commitments_root(checkpoint["commitments"]):
        raise ValueError("commitment root mismatch")
    if checkpoint["domain_checkpoint_hash"] != sha256_hex(_domain_checkpoint_body(checkpoint)):
        raise ValueError("domain checkpoint hash mismatch")

    message = DOMAIN_CHECKPOINT_DOMAIN + canonical_bytes(_domain_checkpoint_unsigned(checkpoint))
    members = {m["actor_id"]: m for m in validator_set["members"]}
    valid = set()
    for approval in checkpoint["approvals"]:
        member = members.get(approval["actor_id"])
        if not member or member["key_id"] != approval["key_id"]:
            continue
        try:
            Ed25519PublicKey.from_public_bytes(b64u_decode(member["public_key"])).verify(
                b64u_decode(approval["signature"]), message
            )
            valid.add(approval["actor_id"])
        except (ValueError, InvalidSignature):
            continue
    if len(valid) < validator_set["quorum"]:
        raise ValueError("domain checkpoint is not final")


def assert_child_commitment(parent_checkpoint: dict, child_domain_id: str, child_checkpoint_hash: str, kind: str) -> None:
    target = {"kind": kind, "domain_id": child_domain_id, "checkpoint_hash": child_checkpoint_hash}
    if target not in parent_checkpoint["commitments"]:
        raise ValueError("child checkpoint is not committed by parent")


def merkle_inclusion_proof(hashes: list[str], index: int) -> list[dict]:
    if not hashes or index < 0 or index >= len(hashes):
        raise ValueError("invalid merkle proof index")
    level = [bytes.fromhex(h) for h in hashes]
    idx = index
    proof = []
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        sibling = idx - 1 if idx % 2 else idx + 1
        proof.append({"side": "left" if sibling < idx else "right", "hash": level[sibling].hex()})
        idx //= 2
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return proof


def verify_merkle_inclusion(entry_hash: str, proof: list[dict], expected_root: str) -> bool:
    current = bytes.fromhex(entry_hash)
    for step in proof:
        sibling = bytes.fromhex(step["hash"])
        current = hashlib.sha256(sibling + current).digest() if step["side"] == "left" else hashlib.sha256(current + sibling).digest()
    return current.hex() == expected_root


def _target_allowed(source_domain: dict, target_domain_id: str) -> bool:
    policy = source_domain["replication_policy"]
    if policy["mode"] == "local_only":
        return False
    allowed = policy["allowed_target_domains"]
    return not allowed or target_domain_id in allowed


def create_cross_domain_proof(
    source_domain: dict,
    target_domain: dict,
    store: LedgerStore,
    entry_sequence: int,
    source_checkpoint: dict,
    parent_domain_checkpoint: dict,
    subject_ref: str,
    created_at: str,
    disclose_payload: bool = False,
    external_payload: dict | None = None,
) -> dict:
    if not _target_allowed(source_domain, target_domain["domain_id"]):
        raise ValueError("target domain is not permitted by replication policy")
    if source_domain["parent_domain_id"] != parent_domain_checkpoint["domain_id"]:
        raise ValueError("hierarchy anchor is not source parent")
    assert_child_commitment(parent_domain_checkpoint, source_domain["domain_id"], source_checkpoint["checkpoint_hash"], "local_checkpoint")
    if entry_sequence > source_checkpoint["through_sequence"]:
        raise ValueError("entry is newer than checkpoint")

    entry = copy.deepcopy(store.entries[entry_sequence - 1])
    if entry["payload"].get("subject_ref") != subject_ref:
        raise ValueError("source entry subject does not match requested proof subject")
    hashes = [x["entry_hash"] for x in store.entries[:source_checkpoint["through_sequence"]]]
    proof = merkle_inclusion_proof(hashes, entry_sequence - 1)

    residency = source_domain["data_residency"]
    if disclose_payload and residency["raw_payload_export"] != "allowed":
        raise ValueError("raw payload export denied by data residency policy")
    if disclose_payload and source_domain["replication_policy"]["mode"] not in {"selective", "full"}:
        raise ValueError("replication mode does not permit payload disclosure")
    if disclose_payload:
        if external_payload is None:
            raise ValueError("external payload required for full disclosure")
        committed = entry["payload"].get("external_payload_digest")
        if committed is None or committed.removeprefix("sha256:") != sha256_hex(external_payload):
            raise ValueError("external payload does not match ledger commitment")
    else:
        external_payload = None

    return {
        "proof_id": f"tst:cross-domain-proof:{source_domain['domain_id'].split(':')[-1]}-{target_domain['domain_id'].split(':')[-1]}-{entry_sequence}",
        "source_domain_id": source_domain["domain_id"],
        "target_domain_id": target_domain["domain_id"],
        "subject_ref": subject_ref,
        "source_entry": {
            "entry_id": entry["entry_id"],
            "sequence": entry["sequence"],
            "entry_hash": entry["entry_hash"],
            "payload_digest": entry["payload_digest"]["digest"],
        },
        "source_entry_record": entry,
        "source_checkpoint": {
            "checkpoint_hash": source_checkpoint["checkpoint_hash"],
            "merkle_root": source_checkpoint["merkle_root"],
            "through_sequence": source_checkpoint["through_sequence"],
        },
        "hierarchy_anchor": {
            "parent_domain_id": parent_domain_checkpoint["domain_id"],
            "parent_domain_checkpoint_hash": parent_domain_checkpoint["domain_checkpoint_hash"],
            "committed_child_checkpoint_hash": source_checkpoint["checkpoint_hash"],
        },
        "inclusion_proof": proof,
        "disclosure": {
            "mode": "full_payload" if disclose_payload else "digest_only",
            "payload_disclosed": disclose_payload,
            "payload": copy.deepcopy(external_payload),
        },
        "created_at": created_at,
        "schema_version": "0.8",
    }


def verify_cross_domain_proof(
    proof: dict,
    source_domain: dict,
    target_domain: dict,
    source_checkpoint: dict,
    source_validator_set: dict,
    parent_domain: dict,
    parent_domain_checkpoint: dict,
    parent_validator_set: dict,
) -> None:
    if proof["source_domain_id"] != source_domain["domain_id"] or proof["target_domain_id"] != target_domain["domain_id"]:
        raise ValueError("cross-domain proof endpoint mismatch")
    if not _target_allowed(source_domain, target_domain["domain_id"]):
        raise ValueError("cross-domain target is not allowed")

    record = proof["source_entry_record"]
    if record["entry_hash"] != sha256_hex(entry_core(record)):
        raise ValueError("source entry record hash mismatch")
    summary = proof["source_entry"]
    if summary["entry_id"] != record["entry_id"] or summary["sequence"] != record["sequence"] or summary["entry_hash"] != record["entry_hash"]:
        raise ValueError("source entry summary mismatch")
    if summary["payload_digest"] != record["payload_digest"]["digest"]:
        raise ValueError("source entry payload digest mismatch")
    if record["payload"].get("subject_ref") != proof["subject_ref"]:
        raise ValueError("proof subject is not committed by source entry")

    LedgerStore.verify_checkpoint(source_checkpoint, source_validator_set)
    if proof["source_checkpoint"]["checkpoint_hash"] != source_checkpoint["checkpoint_hash"]:
        raise ValueError("source checkpoint hash mismatch")
    if proof["source_checkpoint"]["merkle_root"] != source_checkpoint["merkle_root"]:
        raise ValueError("source checkpoint root mismatch")
    if proof["source_checkpoint"]["through_sequence"] != source_checkpoint["through_sequence"]:
        raise ValueError("source checkpoint sequence mismatch")
    if summary["sequence"] > source_checkpoint["through_sequence"]:
        raise ValueError("source entry beyond checkpoint")
    if not verify_merkle_inclusion(summary["entry_hash"], proof["inclusion_proof"], source_checkpoint["merkle_root"]):
        raise ValueError("invalid ledger inclusion proof")

    verify_domain_checkpoint(parent_domain_checkpoint, parent_domain, parent_validator_set)
    anchor = proof["hierarchy_anchor"]
    if anchor["parent_domain_id"] != parent_domain["domain_id"]:
        raise ValueError("parent domain anchor mismatch")
    if anchor["parent_domain_checkpoint_hash"] != parent_domain_checkpoint["domain_checkpoint_hash"]:
        raise ValueError("parent domain checkpoint hash mismatch")
    if anchor["committed_child_checkpoint_hash"] != source_checkpoint["checkpoint_hash"]:
        raise ValueError("child checkpoint anchor mismatch")
    assert_child_commitment(parent_domain_checkpoint, source_domain["domain_id"], source_checkpoint["checkpoint_hash"], "local_checkpoint")

    disclosure = proof["disclosure"]
    residency = source_domain["data_residency"]
    if residency["raw_payload_export"] == "denied" and (disclosure["payload_disclosed"] or disclosure["payload"] is not None):
        raise ValueError("proof violates source data residency policy")
    if disclosure["payload_disclosed"]:
        if disclosure["mode"] != "full_payload" or disclosure["payload"] is None:
            raise ValueError("invalid full-payload disclosure")
        committed = record["payload"].get("external_payload_digest")
        if committed is None or committed.removeprefix("sha256:") != sha256_hex(disclosure["payload"]):
            raise ValueError("disclosed external payload digest mismatch")
    elif disclosure["mode"] != "digest_only" or disclosure["payload"] is not None:
        raise ValueError("invalid digest-only disclosure")


def child_commitment(domain_id: str, checkpoint_hash: str, kind: str = "local_checkpoint") -> dict:
    if kind not in {"local_checkpoint", "domain_checkpoint"}:
        raise ValueError(kind)
    return {"kind": kind, "domain_id": domain_id, "checkpoint_hash": checkpoint_hash}
