#!/usr/bin/env python3
"""TST Chain v0.2 Trust & Authority conformance checks."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "v0.2"
EXAMPLE_DIR = ROOT / "examples" / "v0.2"
VECTOR_FILE = ROOT / "test-vectors" / "v0.2" / "trust-authority-vectors.json"
DOMAIN = b"TSTCHAIN-SIGNATURE-V0.2\x00"


def b64u_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * ((4 - len(value) % 4) % 4))


def normalize(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, float):
        raise ValueError("TST-C14N-JSON/0.1 does not accept binary floating-point values")
    if isinstance(value, list):
        normalized = [normalize(item) for item in value]
        return sorted(normalized, key=canonical_bytes)
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise ValueError("NFC-normalized JSON key collision")
            normalized[normalized_key] = normalize(item)
        return normalized
    return value


def canonical_bytes(value) -> bytes:
    return json.dumps(
        normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(schema_name: str, data) -> None:
    schema = load_json(SCHEMA_DIR / schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)


def parse_time(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("v0.2 protocol timestamps must be UTC Z timestamps")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def within(at: str, start: str, end: str | None) -> bool:
    t = parse_time(at)
    return t >= parse_time(start) and (end is None or t <= parse_time(end))


def verify_detached(payload, signature, key_record, expected_signer: str | None = None):
    if signature["algorithm"] != "ed25519" or key_record["algorithm"] != "ed25519":
        return False, "TST-SIG-006"
    if signature["signer_actor_id"] != key_record["actor_id"]:
        return False, "TST-SIG-007"
    if expected_signer is not None and signature["signer_actor_id"] != expected_signer:
        return False, "TST-SIG-007"
    if signature["canonicalization"] != "TST-C14N-JSON/0.1":
        return False, "TST-SIG-006"
    if key_record["status"] != "active":
        return False, "TST-SIG-002"
    if not within(signature["created_at"], key_record["valid_from"], key_record["valid_until"]):
        return False, "TST-SIG-003"

    payload_bytes = canonical_bytes(payload)
    digest = hashlib.sha256(payload_bytes).hexdigest()
    if signature["payload_digest"] != {"algorithm": "sha256", "digest": digest}:
        return False, "TST-SIG-004"

    try:
        public = Ed25519PublicKey.from_public_bytes(b64u_decode(key_record["public_key"]))
        public.verify(b64u_decode(signature["signature"]), DOMAIN + payload_bytes)
    except (ValueError, InvalidSignature):
        return False, "TST-SIG-005"
    return True, "TST-SIG-000"


def authorize(request, actor, authorities, credentials):
    if actor["actor_id"] != request["actor_id"] or actor["status"] != "active":
        return "deny", "TST-AUTH-001", [], []

    candidates = [a for a in authorities if a["subject_actor_id"] == request["actor_id"]]
    if not candidates:
        return "deny", "TST-AUTH-002", [], []

    evaluated_authorities = []
    evaluated_credentials = []
    last_reason = "TST-AUTH-002"

    for authority in candidates:
        evaluated_authorities.append(authority["authority_id"])
        if authority["status"] != "active":
            last_reason = "TST-AUTH-003"
            continue
        if not within(request["occurred_at"], authority["valid_from"], authority["valid_until"]):
            last_reason = "TST-AUTH-004"
            continue
        if request["action"] not in authority["permissions"]:
            last_reason = "TST-AUTH-005"
            continue

        scope = authority["scope"]
        if not scope["global"] and request["jurisdiction_ref"] not in scope["jurisdiction_refs"]:
            last_reason = "TST-AUTH-006"
            continue
        if scope["object_types"] and request["object_type"] not in scope["object_types"]:
            last_reason = "TST-AUTH-007"
            continue

        credentials_ok = True
        for requirement in authority.get("credential_requirements", []):
            credential_type = requirement["credential_type"]
            trusted_issuers = set(requirement["issuer_actor_ids"])
            matching = [
                c
                for c in credentials
                if c["credential_type"] == credential_type
                and c["subject_actor_id"] == request["actor_id"]
                and c["issuer_actor_id"] in trusted_issuers
            ]
            if not matching:
                last_reason = "TST-AUTH-008"
                credentials_ok = False
                break

            valid_matching = []
            for credential in matching:
                evaluated_credentials.append(credential["credential_id"])
                if credential["status"] != "active":
                    last_reason = "TST-AUTH-009"
                    continue
                if not within(
                    request["occurred_at"], credential["valid_from"], credential["valid_until"]
                ):
                    last_reason = "TST-AUTH-010"
                    continue
                valid_matching.append(credential)

            if not valid_matching:
                credentials_ok = False
                break

        if credentials_ok:
            return (
                "allow",
                "TST-AUTH-000",
                sorted(set(evaluated_authorities)),
                sorted(set(evaluated_credentials)),
            )

    return (
        "deny",
        last_reason,
        sorted(set(evaluated_authorities)),
        sorted(set(evaluated_credentials)),
    )


def check_schema_examples() -> None:
    mapping = {
        "actor-organization.json": "actor.schema.json",
        "actor-person.json": "actor.schema.json",
        "public-key-current.json": "public-key.schema.json",
        "public-key-revoked.json": "public-key.schema.json",
        "authority.json": "authority.schema.json",
        "authority.signature.json": "signature.schema.json",
        "credential.json": "credential.schema.json",
        "credential.signature.json": "signature.schema.json",
        "credential.signature-revoked-key.json": "signature.schema.json",
        "authorization-request-allow.json": "authorization-request.schema.json",
        "authorization-request-deny.json": "authorization-request.schema.json",
        "authorization-decision-allow.json": "authorization-decision.schema.json",
        "authorization-decision-deny.json": "authorization-decision.schema.json",
        "audit-allow.json": "audit-record.schema.json",
        "audit-deny.json": "audit-record.schema.json",
    }
    for filename, schema in mapping.items():
        validate(schema, load_json(EXAMPLE_DIR / filename))


def check_signature_vectors() -> None:
    vectors = load_json(VECTOR_FILE)
    payload = load_json(ROOT / vectors["credential"]["payload"])
    expected_digest = vectors["credential"]["expected_sha256"]
    actual_digest = sha256_hex(payload)
    assert actual_digest == expected_digest, (actual_digest, expected_digest)

    for label in ("active_key", "revoked_key"):
        vector = vectors["credential"][label]
        key_record = load_json(ROOT / vector["public_key"])
        signature = load_json(ROOT / vector["signature"])

        # Reproduce the deterministic test signature from its test-only seed.
        private = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(vector["private_seed_hex"]))
        reproduced = base64.urlsafe_b64encode(
            private.sign(DOMAIN + canonical_bytes(payload))
        ).decode().rstrip("=")
        assert reproduced == vector["expected_signature_base64url"]
        assert reproduced == signature["signature"]

        valid, reason = verify_detached(payload, signature, key_record, payload["issuer_actor_id"])
        expected_valid = vector["expected_result"] == "valid"
        assert valid == expected_valid, (label, valid, reason)
        assert reason == vector["expected_reason_code"], (label, reason)


def check_authority_signature_vector() -> None:
    vectors = load_json(VECTOR_FILE)
    vector = vectors["authority"]
    payload = load_json(ROOT / vector["payload"])
    key_record = load_json(ROOT / vector["key"])
    signature = load_json(ROOT / vector["signature"])

    assert sha256_hex(payload) == vector["expected_sha256"]
    private = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(vector["private_seed_hex"]))
    reproduced = base64.urlsafe_b64encode(
        private.sign(DOMAIN + canonical_bytes(payload))
    ).decode().rstrip("=")
    assert reproduced == vector["expected_signature_base64url"]
    assert reproduced == signature["signature"]

    valid, reason = verify_detached(payload, signature, key_record, payload["issuer_actor_id"])
    assert valid is True
    assert reason == vector["expected_reason_code"]


def check_authorization_vectors() -> None:
    vectors = load_json(VECTOR_FILE)
    actor = load_json(EXAMPLE_DIR / "actor-person.json")
    authority = load_json(EXAMPLE_DIR / "authority.json")
    credential = load_json(EXAMPLE_DIR / "credential.json")

    for vector in vectors["authorization"]:
        request = load_json(ROOT / vector["request"])
        decision = load_json(ROOT / vector["decision"])
        result, reason, authority_ids, credential_ids = authorize(
            request, actor, [authority], [credential]
        )
        assert result == vector["expected"]
        assert reason == vector["expected_reason_code"]
        assert decision["decision"] == result
        assert decision["reason_code"] == reason
        assert decision["evaluated_authority_ids"] == authority_ids
        assert decision["evaluated_credential_ids"] == credential_ids


def check_lifecycle_consistency() -> None:
    for filename in (
        "public-key-current.json",
        "public-key-revoked.json",
        "authority.json",
        "credential.json",
    ):
        record = load_json(EXAMPLE_DIR / filename)
        start = parse_time(record["valid_from"])
        end = parse_time(record["valid_until"]) if record.get("valid_until") else None
        if end is not None:
            assert start <= end, filename
        if record.get("revoked_at"):
            assert parse_time(record["revoked_at"]) >= start, filename

    current_key = load_json(EXAMPLE_DIR / "public-key-current.json")
    assert current_key["predecessor_key_id"] != current_key["key_id"]


def check_locale_key_parity() -> None:
    locales = [
        load_json(ROOT / "locales" / "zh-CN.json"),
        load_json(ROOT / "locales" / "ja-JP.json"),
        load_json(ROOT / "locales" / "en-US.json"),
    ]
    reference = set(locales[0])
    for locale in locales[1:]:
        assert set(locale) == reference, "locale keys differ"


def main() -> int:
    check_schema_examples()
    check_signature_vectors()
    check_authority_signature_vector()
    check_authorization_vectors()
    check_lifecycle_consistency()
    check_locale_key_parity()
    print("TST Chain v0.2 Trust & Authority conformance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
