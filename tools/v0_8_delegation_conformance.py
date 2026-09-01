#!/usr/bin/env python3
"""TST Chain v0.8 validator delegation / jurisdiction handoff conformance."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator, FormatChecker

from v0_7_ledger import LedgerStore, b64u
from v0_8_delegation import (
    create_validator_delegation,
    current_delegation,
    verify_delegation_chain,
    verify_local_checkpoint_trusted,
    verify_validator_delegation,
)
from v0_8_hierarchy import DomainRegistry

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/v0.8"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(name: str, value: dict) -> None:
    schema = load(SCHEMA / name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def private_for(label: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(label.encode()).digest())


def validator_bundle(label: str):
    members = []
    keys = {}
    for i in range(1, 4):
        actor = f"tst:actor:{label}-validator-{i}"
        key_id = f"tst:key:{label}-validator-{i}"
        private = private_for(key_id)
        public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        members.append({"actor_id": actor, "key_id": key_id, "algorithm": "ed25519", "public_key": b64u(public)})
        keys[actor] = private
    return {
        "validator_set_id": f"tst:validator-set:{label}",
        "members": members,
        "quorum": 2,
        "status": "active",
        "schema_version": "0.7",
    }, keys


def domain(domain_id: str, level: str, parent: str | None, ledger_id: str, validator_set_id: str):
    return {
        "domain_id": domain_id,
        "level": level,
        "jurisdiction_ref": "RC:" + domain_id.split(":")[-1].upper(),
        "parent_domain_id": parent,
        "ledger_id": ledger_id,
        "validator_set_id": validator_set_id,
        "replication_policy": {"mode": "proof_only", "allowed_target_domains": []},
        "data_residency": {"classification": "internal", "raw_payload_export": "denied", "proof_export": "required"},
        "schema_version": "0.8",
    }


def expect_failure(fn, message: str):
    try:
        fn()
    except (ValueError, KeyError):
        return
    raise AssertionError(message)


def main() -> int:
    province_vs, province_keys = validator_bundle("delegation-province")
    city_vs, city_keys = validator_bundle("delegation-city")
    district_v1_vs, district_v1_keys = validator_bundle("delegation-district-e1")
    district_v2_vs, district_v2_keys = validator_bundle("delegation-district-e2")

    province_id = "tst:domain:delegation-province"
    city_id = "tst:domain:delegation-city"
    district_id = "tst:domain:delegation-district"

    province = domain(province_id, "province", None, "tst:ledger:delegation-province", province_vs["validator_set_id"])
    city = domain(city_id, "city", province_id, "tst:ledger:delegation-city", city_vs["validator_set_id"])
    district_v1 = domain(district_id, "county", city_id, "tst:ledger:delegation-district", district_v1_vs["validator_set_id"])
    district_v2 = copy.deepcopy(district_v1)
    district_v2["validator_set_id"] = district_v2_vs["validator_set_id"]

    for value in (province, city, district_v1, district_v2):
        validate("jurisdiction-domain.schema.json", value)

    city_delegation = create_validator_delegation(
        province,
        city,
        city_vs,
        province_vs,
        province_keys,
        ["checkpoint.sign", "domain_checkpoint.sign", "delegation.issue", "cross_domain_proof.issue"],
        1,
        "2030-01-01T00:00:00Z",
    )
    district_e1 = create_validator_delegation(
        city,
        district_v1,
        district_v1_vs,
        city_vs,
        city_keys,
        ["checkpoint.sign", "cross_domain_proof.issue"],
        1,
        "2030-01-01T00:00:00Z",
        "2030-06-01T00:00:00Z",
    )
    district_e2 = create_validator_delegation(
        city,
        district_v2,
        district_v2_vs,
        city_vs,
        city_keys,
        ["checkpoint.sign", "cross_domain_proof.issue"],
        2,
        "2030-06-01T00:00:00Z",
        None,
        district_e1["delegation_hash"],
    )
    for value in (city_delegation, district_e1, district_e2):
        validate("validator-delegation.schema.json", value)

    delegations = [city_delegation, district_e1, district_e2]
    validator_sets = {
        value["validator_set_id"]: value
        for value in (province_vs, city_vs, district_v1_vs, district_v2_vs)
    }

    old_registry = DomainRegistry([province, city, district_v1])
    old_chain = verify_delegation_chain(
        district_id, old_registry, [city_delegation, district_e1], validator_sets,
        province_id, "2030-05-01T00:00:00Z", "checkpoint.sign"
    )
    assert [item["subject_domain_id"] for item in old_chain] == [city_id, district_id]
    assert current_delegation([district_e1, district_e2], district_id, "2030-05-01T00:00:00Z")["epoch"] == 1

    new_registry = DomainRegistry([province, city, district_v2])
    new_chain = verify_delegation_chain(
        district_id, new_registry, delegations, validator_sets,
        province_id, "2030-06-02T00:00:00Z", "checkpoint.sign"
    )
    assert new_chain[-1]["epoch"] == 2
    assert new_chain[-1]["delegated_validator_set_id"] == district_v2_vs["validator_set_id"]

    temp = Path(tempfile.mkdtemp(prefix="tst-v08-delegation-"))
    try:
        store = LedgerStore(temp / "district", ledger_id=district_v1["ledger_id"])
        store.record_evidence(
            {"subject_ref": "RC:PLAN:DELEGATION", "kind": "delegation-handoff-test"},
            "2030-05-01T00:00:00Z",
        )
        old_checkpoint = store.checkpoint(district_v1_vs, district_v1_keys, "2030-05-01T00:01:00Z")
        verify_local_checkpoint_trusted(
            old_checkpoint, district_v1, district_v1_vs, old_registry,
            [city_delegation, district_e1], validator_sets, province_id
        )

        store.record_evidence(
            {"subject_ref": "RC:PLAN:DELEGATION", "kind": "post-handoff-state"},
            "2030-06-02T00:00:00Z",
        )
        new_checkpoint = store.checkpoint(district_v2_vs, district_v2_keys, "2030-06-02T00:01:00Z")
        verify_local_checkpoint_trusted(
            new_checkpoint, district_v2, district_v2_vs, new_registry,
            delegations, validator_sets, province_id
        )

        stale_checkpoint = store.checkpoint(district_v1_vs, district_v1_keys, "2030-06-02T00:02:00Z")
        expect_failure(
            lambda: verify_local_checkpoint_trusted(
                stale_checkpoint, district_v2, district_v1_vs, new_registry,
                delegations, validator_sets, province_id
            ),
            "old validator set must not sign new checkpoints after handoff",
        )
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    # A child cannot self-appoint its own validator set.
    expect_failure(
        lambda: create_validator_delegation(
            city, city, city_vs, city_vs, city_keys,
            ["checkpoint.sign"], 1, "2030-01-01T00:00:00Z"
        ),
        "self-issued delegation must fail",
    )

    # Cryptographic signing by the city is insufficient when the city itself was
    # never delegated the authority to issue further delegations.
    city_no_issue = create_validator_delegation(
        province,
        city,
        city_vs,
        province_vs,
        province_keys,
        ["checkpoint.sign", "domain_checkpoint.sign"],
        1,
        "2030-01-01T00:00:00Z",
    )
    district_by_unempowered_city = create_validator_delegation(
        city,
        district_v1,
        district_v1_vs,
        city_vs,
        city_keys,
        ["checkpoint.sign"],
        1,
        "2030-01-01T00:00:00Z",
    )
    expect_failure(
        lambda: verify_delegation_chain(
            district_id, old_registry, [city_no_issue, district_by_unempowered_city], validator_sets,
            province_id, "2030-05-01T00:00:00Z", "checkpoint.sign"
        ),
        "delegation chain must reject an issuer without delegation.issue",
    )

    tampered = copy.deepcopy(city_delegation)
    tampered["capabilities"].append("checkpoint.sign")  # duplicate changes canonical body and violates unique semantics
    expect_failure(
        lambda: verify_validator_delegation(tampered, province, city, city_vs, province_vs),
        "tampered delegation must fail",
    )

    broken_rotation = copy.deepcopy(district_e2)
    broken_rotation["supersedes_delegation_hash"] = "0" * 64
    expect_failure(
        lambda: current_delegation([district_e1, broken_rotation], district_id, "2030-06-02T00:00:00Z"),
        "broken delegation supersession chain must fail",
    )

    print("TST Chain v0.8 validator delegation conformance: PASS")
    print("  province trust anchor -> city -> district delegation chain: PASS")
    print("  delegation.issue capability enforcement: PASS")
    print("  validator epoch handoff + stale signer rejection: PASS")
    print("  self-appointment / tamper / broken supersession rejection: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"TST Chain v0.8 delegation conformance: FAIL: {exc}", file=sys.stderr)
        raise
