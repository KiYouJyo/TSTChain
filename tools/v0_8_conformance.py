#!/usr/bin/env python3
"""TST Chain v0.8 hierarchical jurisdiction conformance."""
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

from v0_7_ledger import LedgerStore, b64u, canonical_bytes, sha256_hex
from v0_8_hierarchy import (
    DomainRegistry,
    assert_child_commitment,
    child_commitment,
    create_cross_domain_proof,
    create_domain_checkpoint,
    verify_cross_domain_proof,
    verify_domain_checkpoint,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/v0.8"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(name: str, value: dict) -> None:
    schema = load(SCHEMA / name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def deterministic_private(label: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(label.encode("utf-8")).digest())


def validator_bundle(label: str) -> tuple[dict, dict[str, Ed25519PrivateKey]]:
    members = []
    keys = {}
    for i in range(1, 4):
        actor = f"tst:actor:{label}-validator-{i}"
        key_id = f"tst:key:{label}-validator-{i}"
        private = deterministic_private(key_id)
        public = private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        members.append({"actor_id": actor, "key_id": key_id, "algorithm": "ed25519", "public_key": b64u(public)})
        keys[actor] = private
    return {
        "validator_set_id": f"tst:validator-set:{label}",
        "members": members,
        "quorum": 2,
        "status": "active",
        "schema_version": "0.7",
    }, keys


def domain(domain_id: str, level: str, parent: str | None, ledger_id: str, validator_set_id: str, mode: str, targets: list[str], classification: str, raw_export: str) -> dict:
    return {
        "domain_id": domain_id,
        "level": level,
        "jurisdiction_ref": "RC:" + domain_id.split(":")[-1].upper(),
        "parent_domain_id": parent,
        "ledger_id": ledger_id,
        "validator_set_id": validator_set_id,
        "replication_policy": {"mode": mode, "allowed_target_domains": targets},
        "data_residency": {
            "classification": classification,
            "raw_payload_export": raw_export,
            "proof_export": "required" if raw_export == "denied" else "allowed",
        },
        "schema_version": "0.8",
    }


def checkpoint_store(root: Path, domain_value: dict, validator_set: dict, keys: dict, payload: dict, at: str):
    store = LedgerStore(root, ledger_id=domain_value["ledger_id"])
    entry = store.record_evidence(payload, at)
    cp = store.checkpoint(validator_set, keys, at)
    return store, entry, cp


def expect_failure(fn, message: str) -> None:
    try:
        fn()
    except (ValueError, KeyError):
        return
    raise AssertionError(message)


def main() -> int:
    d1_vs, d1_keys = validator_bundle("rc-d1")
    d2_vs, d2_keys = validator_bundle("rc-d2")
    city_vs, city_keys = validator_bundle("rc-city")
    province_vs, province_keys = validator_bundle("rc-province")

    d1_id = "tst:domain:rc-district-1"
    d2_id = "tst:domain:rc-district-2"
    city_id = "tst:domain:rc-city"
    province_id = "tst:domain:rc-province"

    d1 = domain(d1_id, "county", city_id, "tst:ledger:rc-district-1", d1_vs["validator_set_id"], "proof_only", [d2_id, city_id], "restricted", "denied")
    d2 = domain(d2_id, "county", city_id, "tst:ledger:rc-district-2", d2_vs["validator_set_id"], "full", [d1_id, city_id], "public", "allowed")
    city = domain(city_id, "city", province_id, "tst:ledger:rc-city", city_vs["validator_set_id"], "proof_only", [province_id], "internal", "denied")
    province = domain(province_id, "province", None, "tst:ledger:rc-province", province_vs["validator_set_id"], "local_only", [], "internal", "denied")

    for item in (d1, d2, city, province):
        validate("jurisdiction-domain.schema.json", item)
    registry = DomainRegistry([d1, d2, city, province])
    assert registry.lineage(d1_id) == [d1_id, city_id, province_id]
    assert registry.lineage(d2_id) == [d2_id, city_id, province_id]

    bad_cycle = copy.deepcopy(d1)
    bad_cycle["parent_domain_id"] = d1_id
    expect_failure(lambda: DomainRegistry([bad_cycle]), "self-parent domain must fail")

    restricted_raw = {
        "parcel": "RC:CONTROL:0010",
        "detail": "SYNTHETIC-RESTRICTED-DETAIL-DO-NOT-REPLICATE",
        "geometry_payload": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
    }
    public_raw = {
        "notice_id": "RC:PUBLIC:0001",
        "title": "Synthetic public planning notice",
        "summary": "public planning notice",
    }

    temp = Path(tempfile.mkdtemp(prefix="tst-v08-"))
    try:
        d1_store, d1_entry, d1_cp = checkpoint_store(
            temp / "d1",
            d1,
            d1_vs,
            d1_keys,
            {
                "kind": "external_asset_commitment",
                "subject_ref": "RC:CONTROL:0010",
                "classification": "restricted",
                "external_payload_digest": "sha256:" + sha256_hex(restricted_raw),
            },
            "2030-05-01T00:00:00Z",
        )
        d2_store, d2_entry, d2_cp = checkpoint_store(
            temp / "d2",
            d2,
            d2_vs,
            d2_keys,
            {
                "kind": "external_asset_commitment",
                "subject_ref": "RC:PUBLIC:0001",
                "classification": "public",
                "external_payload_digest": "sha256:" + sha256_hex(public_raw),
            },
            "2030-05-01T00:00:00Z",
        )
        city_store, _, city_local_cp = checkpoint_store(
            temp / "city",
            city,
            city_vs,
            city_keys,
            {"kind": "hierarchy_service", "subject_ref": "RC:CITY:001"},
            "2030-05-01T00:01:00Z",
        )
        province_store, _, province_local_cp = checkpoint_store(
            temp / "province",
            province,
            province_vs,
            province_keys,
            {"kind": "hierarchy_root", "subject_ref": "RC:PROVINCE:001"},
            "2030-05-01T00:02:00Z",
        )

        # Restricted raw data is never written to the ledger; only its commitment is.
        assert b"SYNTHETIC-RESTRICTED-DETAIL-DO-NOT-REPLICATE" not in canonical_bytes(d1_store.entries)

        city_dc = create_domain_checkpoint(
            city,
            city_local_cp,
            [
                child_commitment(d1_id, d1_cp["checkpoint_hash"]),
                child_commitment(d2_id, d2_cp["checkpoint_hash"]),
            ],
            city_vs,
            city_keys,
            "2030-05-01T00:03:00Z",
        )
        validate("domain-checkpoint.schema.json", city_dc)
        verify_domain_checkpoint(city_dc, city, city_vs)
        assert_child_commitment(city_dc, d1_id, d1_cp["checkpoint_hash"], "local_checkpoint")
        assert_child_commitment(city_dc, d2_id, d2_cp["checkpoint_hash"], "local_checkpoint")

        province_dc = create_domain_checkpoint(
            province,
            province_local_cp,
            [child_commitment(city_id, city_dc["domain_checkpoint_hash"], "domain_checkpoint")],
            province_vs,
            province_keys,
            "2030-05-01T00:04:00Z",
        )
        validate("domain-checkpoint.schema.json", province_dc)
        verify_domain_checkpoint(province_dc, province, province_vs)
        assert_child_commitment(province_dc, city_id, city_dc["domain_checkpoint_hash"], "domain_checkpoint")

        restricted_proof = create_cross_domain_proof(
            d1,
            d2,
            d1_store,
            d1_entry["sequence"],
            d1_cp,
            city_dc,
            "RC:CONTROL:0010",
            "2030-05-01T00:05:00Z",
            disclose_payload=False,
        )
        validate("cross-domain-proof.schema.json", restricted_proof)
        validate("../v0.7/ledger-entry.schema.json", restricted_proof["source_entry_record"])
        verify_cross_domain_proof(restricted_proof, d1, d2, d1_cp, d1_vs, city, city_dc, city_vs)
        assert restricted_proof["disclosure"] == {"mode": "digest_only", "payload_disclosed": False, "payload": None}
        assert b"SYNTHETIC-RESTRICTED-DETAIL-DO-NOT-REPLICATE" not in canonical_bytes(restricted_proof)

        expect_failure(
            lambda: create_cross_domain_proof(
                d1, d2, d1_store, 1, d1_cp, city_dc, "RC:CONTROL:0010", "2030-05-01T00:05:01Z",
                disclose_payload=True, external_payload=restricted_raw,
            ),
            "restricted domain must block raw payload export",
        )

        public_proof = create_cross_domain_proof(
            d2,
            d1,
            d2_store,
            d2_entry["sequence"],
            d2_cp,
            city_dc,
            "RC:PUBLIC:0001",
            "2030-05-01T00:06:00Z",
            disclose_payload=True,
            external_payload=public_raw,
        )
        validate("cross-domain-proof.schema.json", public_proof)
        verify_cross_domain_proof(public_proof, d2, d1, d2_cp, d2_vs, city, city_dc, city_vs)
        assert public_proof["disclosure"]["payload"] == public_raw

        tampered = copy.deepcopy(restricted_proof)
        tampered["source_entry"]["entry_hash"] = "0" * 64
        expect_failure(
            lambda: verify_cross_domain_proof(tampered, d1, d2, d1_cp, d1_vs, city, city_dc, city_vs),
            "tampered inclusion proof must fail",
        )

        tampered_subject = copy.deepcopy(restricted_proof)
        tampered_subject["subject_ref"] = "RC:CONTROL:FAKE"
        expect_failure(
            lambda: verify_cross_domain_proof(tampered_subject, d1, d2, d1_cp, d1_vs, city, city_dc, city_vs),
            "unbound subject ref must fail",
        )

        tampered_dc = copy.deepcopy(city_dc)
        tampered_dc["commitments"][0]["checkpoint_hash"] = "f" * 64
        expect_failure(lambda: verify_domain_checkpoint(tampered_dc, city, city_vs), "tampered domain checkpoint must fail")

        # Province has only the signed city commitment; district raw payload remains local/off-chain.
        assert b"SYNTHETIC-RESTRICTED-DETAIL-DO-NOT-REPLICATE" not in canonical_bytes(province_dc)
        assert province_store.entries and city_store.entries

    finally:
        shutil.rmtree(temp, ignore_errors=True)

    print("TST Chain v0.8 hierarchical jurisdiction conformance: PASS")
    print("  county/domain -> city -> province commitment hierarchy: PASS")
    print("  restricted raw data remains off-ledger and in-domain: PASS")
    print("  digest-only cross-domain proof with bound ledger entry: PASS")
    print("  public full-payload replication against ledger commitment: PASS")
    print("  Merkle inclusion + parent checkpoint anchor + tamper rejection: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"TST Chain v0.8 conformance: FAIL: {exc}", file=sys.stderr)
        raise
