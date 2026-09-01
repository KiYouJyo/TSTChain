#!/usr/bin/env python3
"""Validator delegation and jurisdiction handoff primitives for TST Chain v0.8."""
from __future__ import annotations

import copy
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from v0_7_ledger import LedgerStore, b64u, b64u_decode, canonical_bytes, sha256_hex
from v0_8_hierarchy import DomainRegistry, verify_domain_checkpoint

DELEGATION_DOMAIN = b"TSTCHAIN-VALIDATOR-DELEGATION-V0.8\x00"


def _unsigned(value: dict) -> dict:
    return {k: v for k, v in value.items() if k not in {"approvals", "delegation_hash"}}


def _body(value: dict) -> dict:
    return {k: v for k, v in value.items() if k != "delegation_hash"}


def parse_z(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("timestamp must use explicit UTC Z")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    return parsed.astimezone(timezone.utc)


def active_at(delegation: dict, at: str) -> bool:
    moment = parse_z(at)
    start = parse_z(delegation["valid_from"])
    end = parse_z(delegation["valid_until"]) if delegation["valid_until"] is not None else None
    return moment >= start and (end is None or moment < end)


def create_validator_delegation(
    issuer_domain: dict,
    subject_domain: dict,
    delegated_validator_set: dict,
    issuer_validator_set: dict,
    issuer_private_keys: dict[str, Ed25519PrivateKey],
    capabilities: list[str],
    epoch: int,
    valid_from: str,
    valid_until: str | None = None,
    supersedes_delegation_hash: str | None = None,
) -> dict:
    if subject_domain["parent_domain_id"] != issuer_domain["domain_id"]:
        raise ValueError("delegation issuer must be the subject's direct parent domain")
    if delegated_validator_set["validator_set_id"] != subject_domain["validator_set_id"]:
        raise ValueError("delegated validator set does not match subject domain descriptor")
    if issuer_validator_set["validator_set_id"] != issuer_domain["validator_set_id"] or issuer_validator_set["status"] != "active":
        raise ValueError("issuer validator set mismatch/inactive")
    if epoch < 1:
        raise ValueError("delegation epoch must be positive")
    if epoch == 1 and supersedes_delegation_hash is not None:
        raise ValueError("epoch 1 cannot supersede another delegation")
    if epoch > 1 and supersedes_delegation_hash is None:
        raise ValueError("rotated delegation must identify the superseded delegation")
    if not capabilities:
        raise ValueError("delegation capabilities cannot be empty")
    if valid_until is not None and parse_z(valid_until) <= parse_z(valid_from):
        raise ValueError("delegation valid_until must be later than valid_from")

    unsigned = {
        "delegation_id": f"tst:validator-delegation:{subject_domain['domain_id'].split(':')[-1]}-e{epoch}",
        "issuer_domain_id": issuer_domain["domain_id"],
        "subject_domain_id": subject_domain["domain_id"],
        "delegated_validator_set_id": delegated_validator_set["validator_set_id"],
        "capabilities": sorted(set(capabilities)),
        "epoch": epoch,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "supersedes_delegation_hash": supersedes_delegation_hash,
        "schema_version": "0.8",
    }
    message = DELEGATION_DOMAIN + canonical_bytes(unsigned)
    approvals = []
    for member in issuer_validator_set["members"]:
        private = issuer_private_keys.get(member["actor_id"])
        if private is None:
            continue
        approvals.append({
            "actor_id": member["actor_id"],
            "key_id": member["key_id"],
            "algorithm": "ed25519",
            "signature": b64u(private.sign(message)),
        })
        if len(approvals) >= issuer_validator_set["quorum"]:
            break
    if len(approvals) < issuer_validator_set["quorum"]:
        raise ValueError("issuer validator quorum unavailable")
    result = {**unsigned, "approvals": approvals}
    result["delegation_hash"] = sha256_hex(result)
    verify_validator_delegation(result, issuer_domain, subject_domain, delegated_validator_set, issuer_validator_set)
    return result


def verify_validator_delegation(
    delegation: dict,
    issuer_domain: dict,
    subject_domain: dict,
    delegated_validator_set: dict,
    issuer_validator_set: dict,
) -> None:
    if subject_domain["parent_domain_id"] != issuer_domain["domain_id"]:
        raise ValueError("delegation issuer is not direct parent")
    if delegation["issuer_domain_id"] != issuer_domain["domain_id"] or delegation["subject_domain_id"] != subject_domain["domain_id"]:
        raise ValueError("delegation endpoint mismatch")
    if delegation["delegated_validator_set_id"] != subject_domain["validator_set_id"]:
        raise ValueError("delegation does not authorize subject domain's validator set")
    if delegated_validator_set["validator_set_id"] != delegation["delegated_validator_set_id"] or delegated_validator_set["status"] != "active":
        raise ValueError("delegated validator set mismatch/inactive")
    if issuer_validator_set["validator_set_id"] != issuer_domain["validator_set_id"] or issuer_validator_set["status"] != "active":
        raise ValueError("issuer validator set mismatch/inactive")
    if delegation["delegation_hash"] != sha256_hex(_body(delegation)):
        raise ValueError("delegation hash mismatch")
    if delegation["valid_until"] is not None and parse_z(delegation["valid_until"]) <= parse_z(delegation["valid_from"]):
        raise ValueError("invalid delegation validity interval")

    message = DELEGATION_DOMAIN + canonical_bytes(_unsigned(delegation))
    members = {item["actor_id"]: item for item in issuer_validator_set["members"]}
    valid = set()
    for approval in delegation["approvals"]:
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
    if len(valid) < issuer_validator_set["quorum"]:
        raise ValueError("delegation issuer quorum not met")


def validate_delegation_history(delegations: list[dict], subject_domain_id: str) -> list[dict]:
    items = sorted((copy.deepcopy(x) for x in delegations if x["subject_domain_id"] == subject_domain_id), key=lambda x: x["epoch"])
    if not items:
        raise ValueError(f"no validator delegation for {subject_domain_id}")
    if items[0]["epoch"] != 1 or items[0]["supersedes_delegation_hash"] is not None:
        raise ValueError("delegation history must begin at epoch 1")
    for previous, current in zip(items, items[1:]):
        if current["epoch"] != previous["epoch"] + 1:
            raise ValueError("delegation epochs must be contiguous")
        if current["supersedes_delegation_hash"] != previous["delegation_hash"]:
            raise ValueError("delegation supersession chain mismatch")
        if parse_z(current["valid_from"]) < parse_z(previous["valid_from"]):
            raise ValueError("delegation epochs cannot move backward in time")
    return items


def current_delegation(delegations: list[dict], subject_domain_id: str, at: str) -> dict:
    history = validate_delegation_history(delegations, subject_domain_id)
    active = [item for item in history if active_at(item, at)]
    if not active:
        raise ValueError(f"no active validator delegation for {subject_domain_id} at {at}")
    return copy.deepcopy(max(active, key=lambda x: x["epoch"]))


def verify_delegation_chain(
    domain_id: str,
    registry: DomainRegistry,
    delegations: list[dict],
    validator_sets: dict[str, dict],
    root_domain_id: str,
    at: str,
    required_capability: str = "checkpoint.sign",
) -> list[dict]:
    root = registry.get(root_domain_id)
    if root["parent_domain_id"] is not None:
        raise ValueError("trust anchor must be a root domain")
    if root["validator_set_id"] not in validator_sets:
        raise ValueError("root trust anchor validator set unavailable")
    lineage = registry.lineage(domain_id)
    if root_domain_id not in lineage or lineage[-1] != root_domain_id:
        raise ValueError("domain does not descend from configured trust anchor")
    if domain_id == root_domain_id:
        return []

    verified = []
    path = list(reversed(lineage))
    for issuer_id, subject_id in zip(path, path[1:]):
        issuer = registry.get(issuer_id)
        subject = registry.get(subject_id)
        delegation = current_delegation(delegations, subject_id, at)
        delegated_set = validator_sets.get(delegation["delegated_validator_set_id"])
        issuer_set = validator_sets.get(issuer["validator_set_id"])
        if delegated_set is None or issuer_set is None:
            raise ValueError("validator set required by delegation chain is unavailable")
        verify_validator_delegation(delegation, issuer, subject, delegated_set, issuer_set)
        if issuer_id != root_domain_id:
            issuer_delegation = current_delegation(delegations, issuer_id, at)
            if "delegation.issue" not in issuer_delegation["capabilities"]:
                raise ValueError("issuer domain was not delegated delegation.issue capability")
        verified.append(delegation)

    leaf = verified[-1]
    if required_capability not in leaf["capabilities"]:
        raise ValueError(f"leaf delegation lacks required capability: {required_capability}")
    return verified


def verify_local_checkpoint_trusted(
    checkpoint: dict,
    domain: dict,
    validator_set: dict,
    registry: DomainRegistry,
    delegations: list[dict],
    validator_sets: dict[str, dict],
    root_domain_id: str,
) -> None:
    verify_delegation_chain(
        domain["domain_id"], registry, delegations, validator_sets, root_domain_id,
        checkpoint["created_at"], "checkpoint.sign"
    )
    if checkpoint["validator_set_id"] != domain["validator_set_id"]:
        raise ValueError("local checkpoint is signed by a non-current domain validator set")
    LedgerStore.verify_checkpoint(checkpoint, validator_set)


def verify_domain_checkpoint_trusted(
    checkpoint: dict,
    domain: dict,
    validator_set: dict,
    registry: DomainRegistry,
    delegations: list[dict],
    validator_sets: dict[str, dict],
    root_domain_id: str,
) -> None:
    capability = "domain_checkpoint.sign" if domain["domain_id"] != root_domain_id else "checkpoint.sign"
    if domain["domain_id"] != root_domain_id:
        verify_delegation_chain(
            domain["domain_id"], registry, delegations, validator_sets, root_domain_id,
            checkpoint["created_at"], capability
        )
    if checkpoint["validator_set_id"] != domain["validator_set_id"]:
        raise ValueError("domain checkpoint is signed by a non-current domain validator set")
    verify_domain_checkpoint(checkpoint, domain, validator_set)
