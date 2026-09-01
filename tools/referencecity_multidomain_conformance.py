#!/usr/bin/env python3
"""ReferenceCity multi-domain conformance for TST Chain v0.8.

Partitions the pinned ReferenceCity source objects into one city root domain and
three district domains, commits only external digests to local ledgers, anchors
all child checkpoints at the city domain, and verifies a cross-district proof.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator, FormatChecker

from v0_7_ledger import LedgerStore, b64u, canonical_bytes, sha256_hex
from v0_8_delegation import (
    create_validator_delegation,
    verify_local_checkpoint_trusted,
)
from v0_8_hierarchy import (
    DomainRegistry,
    child_commitment,
    create_cross_domain_proof,
    create_domain_checkpoint,
    verify_cross_domain_proof,
    verify_domain_checkpoint,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "integrations/referencecity/v0.1/multidomain-profile.json"
SCHEMA = ROOT / "schemas/v0.8"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(schema_name: str, value: dict) -> None:
    schema = load(SCHEMA / schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def deterministic_private(label: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(label.encode("utf-8")).digest())


def validator_bundle(label: str):
    members = []
    keys = {}
    for index in range(1, 4):
        actor_id = f"tst:actor:{label}-validator-{index}"
        key_id = f"tst:key:{label}-validator-{index}"
        private = deterministic_private(key_id)
        public = private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        members.append({
            "actor_id": actor_id,
            "key_id": key_id,
            "algorithm": "ed25519",
            "public_key": b64u(public),
        })
        keys[actor_id] = private
    return {
        "validator_set_id": f"tst:validator-set:{label}",
        "members": members,
        "quorum": 2,
        "status": "active",
        "schema_version": "0.7",
    }, keys


def make_domain(domain_id: str, level: str, jurisdiction_ref: str, parent: str | None, validator_set_id: str, allowed_targets: list[str]):
    return {
        "domain_id": domain_id,
        "level": level,
        "jurisdiction_ref": jurisdiction_ref,
        "parent_domain_id": parent,
        "ledger_id": "tst:ledger:" + domain_id.removeprefix("tst:domain:"),
        "validator_set_id": validator_set_id,
        "replication_policy": {
            "mode": "proof_only",
            "allowed_target_domains": allowed_targets,
        },
        "data_residency": {
            "classification": "restricted" if parent is not None else "internal",
            "raw_payload_export": "denied",
            "proof_export": "required",
        },
        "schema_version": "0.8",
    }


def spatial_owner(object_id: str, spatial_by_id: dict[str, dict], district_domains: dict[str, str], city_domain_id: str) -> str:
    current_id = object_id
    seen = set()
    while current_id is not None:
        if current_id in seen:
            raise ValueError(f"ReferenceCity spatial parent cycle: {object_id}")
        seen.add(current_id)
        if current_id in district_domains:
            return district_domains[current_id]
        if current_id == "RC:CITY:001":
            return city_domain_id
        current = spatial_by_id.get(current_id)
        if current is None:
            raise ValueError(f"unresolved ReferenceCity spatial parent: {current_id}")
        current_id = current.get("parent_id")
    return city_domain_id


def planning_owner(item: dict, spatial_by_id: dict[str, dict], district_domains: dict[str, str], city_domain_id: str) -> str:
    owners = set()
    for target_id in item.get("target_ids", []):
        if target_id in spatial_by_id:
            owners.add(spatial_owner(target_id, spatial_by_id, district_domains, city_domain_id))
        elif target_id == "RC:CITY:001":
            owners.add(city_domain_id)
        else:
            owners.add(city_domain_id)
    if len(owners) == 1:
        return next(iter(owners))
    return city_domain_id


def main() -> int:
    profile = load(PROFILE)
    if profile["referencecity_pin"] != "f810758d151a36747dbc7ccf11998f12d40bef4e":
        raise ValueError("unexpected ReferenceCity benchmark pin")

    rc_root = Path(os.environ.get("REFERENCECITY_ROOT", ROOT / "referencecity")).resolve()
    generated = rc_root / "data/core-v0.1/generated"
    if not (generated / "spatial-objects.json").is_file() or not (generated / "planning-objects.json").is_file():
        raise FileNotFoundError("ReferenceCity generated snapshot is required")
    spatial = load(generated / "spatial-objects.json")
    planning = load(generated / "planning-objects.json")
    expected = profile["expected_source_counts"]
    assert len(spatial) == expected["spatial_objects"] == 221
    assert len(planning) == expected["planning_objects"] == 65
    assert len(spatial) + len(planning) == expected["total_objects"] == 286

    spatial_by_id = {item["id"]: item for item in spatial}
    if len(spatial_by_id) != len(spatial):
        raise ValueError("duplicate spatial object IDs")
    planning_by_id = {item["id"]: item for item in planning}
    if len(planning_by_id) != len(planning):
        raise ValueError("duplicate planning object IDs")
    if set(spatial_by_id).intersection(planning_by_id):
        raise ValueError("spatial/planning ID collision")

    city_id = profile["root_domain"]["domain_id"]
    child_specs = profile["child_domains"]
    child_ids = [item["domain_id"] for item in child_specs]
    district_domains = {item["jurisdiction_ref"]: item["domain_id"] for item in child_specs}
    assert set(district_domains) == {"RC:DISTRICT:001", "RC:DISTRICT:002", "RC:DISTRICT:003"}

    city_vs, city_keys = validator_bundle("referencecity-city")
    child_bundles = {
        spec["domain_id"]: validator_bundle(spec["domain_id"].split(":")[-1])
        for spec in child_specs
    }
    city = make_domain(city_id, "city", "RC:CITY:001", None, city_vs["validator_set_id"], [])
    domains = [city]
    for spec in child_specs:
        validator_set, _ = child_bundles[spec["domain_id"]]
        domains.append(make_domain(
            spec["domain_id"],
            spec["level"],
            spec["jurisdiction_ref"],
            city_id,
            validator_set["validator_set_id"],
            [target for target in [*child_ids, city_id] if target != spec["domain_id"]],
        ))
    for value in domains:
        validate("jurisdiction-domain.schema.json", value)
    registry = DomainRegistry(domains)
    domain_by_id = {item["domain_id"]: item for item in domains}

    delegations = []
    validator_sets = {city_vs["validator_set_id"]: city_vs}
    child_keys = {}
    for child_id in child_ids:
        validator_set, private_keys = child_bundles[child_id]
        validator_sets[validator_set["validator_set_id"]] = validator_set
        child_keys[child_id] = private_keys
        delegation = create_validator_delegation(
            city,
            domain_by_id[child_id],
            validator_set,
            city_vs,
            city_keys,
            ["checkpoint.sign", "cross_domain_proof.issue"],
            1,
            "2030-01-01T00:00:00Z",
        )
        validate("validator-delegation.schema.json", delegation)
        delegations.append(delegation)

    assignments: dict[str, list[tuple[str, dict]]] = {domain_id: [] for domain_id in domain_by_id}
    ownership: dict[str, str] = {}
    for item in spatial:
        owner = spatial_owner(item["id"], spatial_by_id, district_domains, city_id)
        assignments[owner].append(("spatial", item))
        if item["id"] in ownership:
            raise ValueError(f"duplicate assignment: {item['id']}")
        ownership[item["id"]] = owner
    for item in planning:
        owner = planning_owner(item, spatial_by_id, district_domains, city_id)
        assignments[owner].append(("planning", item))
        if item["id"] in ownership:
            raise ValueError(f"duplicate assignment: {item['id']}")
        ownership[item["id"]] = owner

    assert len(ownership) == 286
    assert set(ownership) == set(spatial_by_id) | set(planning_by_id)
    assert all(assignments[child_id] for child_id in child_ids)
    assert ownership["RC:PARCEL:000001"] == "tst:domain:referencecity-district-1"
    assert ownership["RC:PARCEL:000005"] == "tst:domain:referencecity-district-2"
    assert ownership["RC:PARCEL:000010"] == "tst:domain:referencecity-district-3"
    assert ownership["RC:ROAD:0001"] == city_id
    assert ownership["RC:CONTROL:0001"] == "tst:domain:referencecity-district-1"
    assert ownership["RC:CONTROL:0010"] == "tst:domain:referencecity-district-3"

    temp = Path(tempfile.mkdtemp(prefix="tst-referencecity-multidomain-"))
    try:
        stores = {}
        entries_by_subject: dict[str, dict[str, dict]] = {}
        local_checkpoints = {}
        for domain_id, assigned in assignments.items():
            descriptor = domain_by_id[domain_id]
            validator_set = city_vs if domain_id == city_id else child_bundles[domain_id][0]
            keys = city_keys if domain_id == city_id else child_keys[domain_id]
            store = LedgerStore(temp / domain_id.split(":")[-1], ledger_id=descriptor["ledger_id"])
            entries_by_subject[domain_id] = {}
            for family, source_object in sorted(assigned, key=lambda pair: pair[1]["id"]):
                payload = {
                    "kind": "referencecity_object_commitment",
                    "subject_ref": source_object["id"],
                    "object_family": family,
                    "external_payload_digest": "sha256:" + sha256_hex(source_object),
                    "source_snapshot_ref": "ReferenceCity:RC:DATASET:COREV01SNAPSHOT:0.1.0",
                }
                entry = store.record_evidence(payload, "2030-07-01T00:00:00Z")
                entries_by_subject[domain_id][source_object["id"]] = entry
            checkpoint = store.checkpoint(validator_set, keys, "2030-07-01T00:10:00Z")
            stores[domain_id] = store
            local_checkpoints[domain_id] = checkpoint

        # Source geometry/planning payloads are external: no coordinates/controls are copied into district ledgers.
        for child_id in child_ids:
            ledger_bytes = canonical_bytes(stores[child_id].entries)
            assert b'"coordinates"' not in ledger_bytes
            assert b'"controls"' not in ledger_bytes
            verify_local_checkpoint_trusted(
                local_checkpoints[child_id],
                domain_by_id[child_id],
                child_bundles[child_id][0],
                registry,
                delegations,
                validator_sets,
                city_id,
            )

        city_dc = create_domain_checkpoint(
            city,
            local_checkpoints[city_id],
            [child_commitment(child_id, local_checkpoints[child_id]["checkpoint_hash"]) for child_id in child_ids],
            city_vs,
            city_keys,
            "2030-07-01T00:20:00Z",
        )
        validate("domain-checkpoint.schema.json", city_dc)
        verify_domain_checkpoint(city_dc, city, city_vs)
        for child_id in child_ids:
            assert any(
                item["domain_id"] == child_id and item["checkpoint_hash"] == local_checkpoints[child_id]["checkpoint_hash"]
                for item in city_dc["commitments"]
            )

        source_id = "tst:domain:referencecity-district-1"
        target_id = "tst:domain:referencecity-district-2"
        parcel_entry = entries_by_subject[source_id]["RC:PARCEL:000001"]
        proof = create_cross_domain_proof(
            domain_by_id[source_id],
            domain_by_id[target_id],
            stores[source_id],
            parcel_entry["sequence"],
            local_checkpoints[source_id],
            city_dc,
            "RC:PARCEL:000001",
            "2030-07-01T00:30:00Z",
            disclose_payload=False,
        )
        validate("cross-domain-proof.schema.json", proof)
        verify_cross_domain_proof(
            proof,
            domain_by_id[source_id],
            domain_by_id[target_id],
            local_checkpoints[source_id],
            child_bundles[source_id][0],
            city,
            city_dc,
            city_vs,
        )
        assert proof["disclosure"]["payload"] is None
        assert proof["subject_ref"] == "RC:PARCEL:000001"
        assert proof["source_entry_record"]["payload"]["external_payload_digest"] == "sha256:" + sha256_hex(spatial_by_id["RC:PARCEL:000001"])
        assert b'"coordinates"' not in canonical_bytes(proof)

        domain_counts = {domain_id: len(items) for domain_id, items in assignments.items()}
        assert sum(domain_counts.values()) == 286
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    print("TST × ReferenceCity v0.8 multi-domain conformance: PASS")
    print("  source objects partitioned exactly once: 221 spatial + 65 planning = 286")
    print("  authoritative domains: 1 city + 3 districts")
    print("  district local ledgers contain commitments, not raw geometry/planning payloads")
    print("  city checkpoint aggregates all 3 district checkpoints")
    print("  RC:PARCEL:000001 district-1 -> district-2 proof: PASS")
    print("  validator delegation + Merkle inclusion + city hierarchy anchor: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"TST × ReferenceCity v0.8 multi-domain conformance: FAIL: {exc}", file=sys.stderr)
        raise
