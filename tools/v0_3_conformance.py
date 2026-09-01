#!/usr/bin/env python3
"""TST Chain v0.3 Planning Rule conformance checks."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "v0.3"
EXAMPLE_DIR = ROOT / "examples" / "v0.3"
VECTOR_FILE = ROOT / "test-vectors" / "v0.3" / "planning-rule-vectors.json"
DECIMAL_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?$")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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


def validate(schema_name: str, data) -> None:
    schema = load_json(SCHEMA_DIR / schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)


def parse_time(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("v0.3 protocol timestamps must be UTC Z timestamps")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def ref_for(rule):
    return {
        "rule_id": rule["rule_id"],
        "version": rule["version"],
        "content_digest": {"algorithm": "sha256", "digest": sha256_hex(rule)},
    }


def same_ref(a, b) -> bool:
    return (
        a["rule_id"] == b["rule_id"]
        and a["version"] == b["version"]
        and a["content_digest"] == b["content_digest"]
    )


def active_at(record, at: str) -> bool:
    if record["status"] != "active":
        return False
    t = parse_time(at)
    start = record.get("effective_from", record.get("valid_from"))
    end = record.get("effective_until", record.get("valid_until"))
    if t < parse_time(start):
        return False
    return end is None or t <= parse_time(end)


def evaluate_rule(rule, request, exceptions):
    rule_ref = ref_for(rule)
    result_base = {
        "rule_ref": rule_ref,
        "observed_value": None,
        "applied_exception_id": None,
        "evidence_refs": [],
    }

    if not active_at(rule, request["requested_at"]):
        return result_base | {"status": "not_applicable", "reason_code": "TST-RULE-003"}

    scope = rule["scope"]
    if not scope["global"] and request["jurisdiction_ref"] not in scope["jurisdiction_refs"]:
        return result_base | {"status": "not_applicable", "reason_code": "TST-RULE-003"}
    if scope["object_types"] and request["object_type"] not in scope["object_types"]:
        return result_base | {"status": "not_applicable", "reason_code": "TST-RULE-003"}
    if scope["object_ids"] and request["subject_object_id"] not in scope["object_ids"]:
        return result_base | {"status": "not_applicable", "reason_code": "TST-RULE-003"}

    applied = None
    for exception in exceptions:
        if exception["status"] != "active":
            continue
        if request["subject_object_id"] not in exception["subject_object_ids"]:
            continue
        if not same_ref(exception["rule_ref"], rule_ref):
            continue
        t = parse_time(request["requested_at"])
        if t < parse_time(exception["valid_from"]):
            continue
        if exception["valid_until"] is not None and t > parse_time(exception["valid_until"]):
            continue
        applied = exception
        break

    if applied and applied["exception_type"] == "exempt":
        return result_base | {
            "status": "not_applicable",
            "reason_code": "TST-RULE-003",
            "applied_exception_id": applied["exception_id"],
        }
    if applied and applied["exception_type"] == "override":
        # v0.3 records the override reference but leaves recursive rule loading
        # to the host implementation. The reference evaluator therefore routes
        # it to review rather than guessing.
        return result_base | {
            "status": "review",
            "reason_code": "TST-RULE-002",
            "applied_exception_id": applied["exception_id"],
        }

    expression = rule["expression"]
    kind = expression["kind"]
    observed = None
    evidence_refs = []

    try:
        if kind in {
            "numeric_constraint",
            "numeric_range",
            "enum_constraint",
            "boolean_constraint",
        }:
            path = expression["property_path"]
            if path not in request["facts"]:
                return result_base | {"status": "error", "reason_code": "TST-RULE-004"}
            fact = request["facts"][path]
            observed = fact

            if kind in {"numeric_constraint", "numeric_range"}:
                if fact["type"] != "decimal":
                    return result_base | {
                        "status": "error",
                        "reason_code": "TST-RULE-005",
                        "observed_value": fact,
                    }
                if "unit" in expression and fact.get("unit") != expression["unit"]:
                    return result_base | {
                        "status": "error",
                        "reason_code": "TST-RULE-005",
                        "observed_value": fact,
                    }
                value = Decimal(fact["value"])
                if kind == "numeric_constraint":
                    threshold = Decimal(expression["value"])
                    op = expression["operator"]
                    passed = {
                        "lt": value < threshold,
                        "lte": value <= threshold,
                        "eq": value == threshold,
                        "gte": value >= threshold,
                        "gt": value > threshold,
                    }[op]
                else:
                    lower = Decimal(expression["lower"])
                    upper = Decimal(expression["upper"])
                    passed = (
                        lower <= value <= upper
                        if expression["operator"] == "between_inclusive"
                        else lower < value < upper
                    )

            elif kind == "enum_constraint":
                if fact["type"] != "string":
                    return result_base | {
                        "status": "error",
                        "reason_code": "TST-RULE-005",
                        "observed_value": fact,
                    }
                passed = fact["value"] in expression["values"]
                if expression["operator"] == "not_in":
                    passed = not passed

            else:
                if fact["type"] != "boolean":
                    return result_base | {
                        "status": "error",
                        "reason_code": "TST-RULE-005",
                        "observed_value": fact,
                    }
                passed = fact["value"] is expression["expected"]

        elif kind == "spatial_constraint":
            observations = [
                item
                for item in request["spatial_observations"]
                if item["predicate"] == expression["predicate"]
                and item["target_object_id"] == expression["target_object_id"]
            ]
            if not observations:
                return result_base | {"status": "error", "reason_code": "TST-RULE-008"}
            observation = observations[0]
            passed = observation["result"]
            observed = {"type": "boolean", "value": passed}
            evidence_refs = [observation["engine_evidence_ref"]]
        else:
            return result_base | {"status": "error", "reason_code": "TST-RULE-006"}
    except Exception:
        return result_base | {
            "status": "error",
            "reason_code": "TST-RULE-007",
            "observed_value": observed,
            "evidence_refs": evidence_refs,
        }

    if applied and applied["exception_type"] == "review_required":
        return result_base | {
            "status": "review",
            "reason_code": "TST-RULE-002",
            "observed_value": observed,
            "applied_exception_id": applied["exception_id"],
            "evidence_refs": evidence_refs,
        }

    return result_base | {
        "status": "pass" if passed else "fail",
        "reason_code": "TST-RULE-000" if passed else "TST-RULE-001",
        "observed_value": observed,
        "evidence_refs": evidence_refs,
    }


def check_schema_examples() -> None:
    mapping = {
        "rule-far.json": "planning-rule.schema.json",
        "rule-height.json": "planning-rule.schema.json",
        "rule-landuse.json": "planning-rule.schema.json",
        "rule-protected.json": "planning-rule.schema.json",
        "rule-ecoredline.json": "planning-rule.schema.json",
        "rule-far-draft-v1.1.json": "planning-rule.schema.json",
        "rule-set.json": "rule-set.schema.json",
        "rule-set-draft-v1.1.json": "rule-set.schema.json",
        "rule-exception-review.json": "rule-exception.schema.json",
        "evaluation-request.json": "rule-evaluation-request.schema.json",
        "evaluation-result.json": "rule-evaluation-result.schema.json",
        "engine-manifest.json": "rule-engine-manifest.schema.json",
    }
    for filename, schema in mapping.items():
        validate(schema, load_json(EXAMPLE_DIR / filename))


def check_decimal_profile() -> None:
    vectors = load_json(VECTOR_FILE)
    schema = load_json(SCHEMA_DIR / "planning-rule.schema.json")
    decimal_schema = schema["$defs"]["canonicalDecimal"]
    validator = Draft202012Validator(decimal_schema)

    for value in vectors["canonical_decimal_valid"]:
        assert DECIMAL_PATTERN.fullmatch(value)
        assert not list(validator.iter_errors(value)), value

    for value in vectors["canonical_decimal_invalid"]:
        assert list(validator.iter_errors(value)), value


def check_hash_vectors() -> None:
    vectors = load_json(VECTOR_FILE)
    for item in vectors["rules"]:
        assert sha256_hex(load_json(ROOT / item["path"])) == item["expected_sha256"]
    for key in (
        "draft_rule",
        "rule_set",
        "draft_rule_set",
        "exception",
        "evaluation_request",
        "evaluation_result",
    ):
        item = vectors[key]
        assert sha256_hex(load_json(ROOT / item["path"])) == item["expected_sha256"]


def check_version_links() -> None:
    vectors = load_json(VECTOR_FILE)
    current_rule = load_json(EXAMPLE_DIR / "rule-far.json")
    draft_rule = load_json(EXAMPLE_DIR / "rule-far-draft-v1.1.json")
    assert draft_rule["rule_id"] == current_rule["rule_id"]
    assert draft_rule["supersedes"] == ref_for(current_rule)
    assert draft_rule["supersedes"]["content_digest"]["digest"] == vectors["draft_rule"]["supersedes_sha256"]

    current_set = load_json(EXAMPLE_DIR / "rule-set.json")
    draft_set = load_json(EXAMPLE_DIR / "rule-set-draft-v1.1.json")
    expected_ref = {
        "rule_set_id": current_set["rule_set_id"],
        "version": current_set["version"],
        "content_digest": {"algorithm": "sha256", "digest": sha256_hex(current_set)},
    }
    assert draft_set["previous_version"] == expected_ref
    assert (
        draft_set["previous_version"]["content_digest"]["digest"]
        == vectors["draft_rule_set"]["previous_sha256"]
    )


def check_evaluation_vector() -> None:
    vectors = load_json(VECTOR_FILE)
    request = load_json(EXAMPLE_DIR / "evaluation-request.json")
    exception = load_json(EXAMPLE_DIR / "rule-exception-review.json")
    result = load_json(EXAMPLE_DIR / "evaluation-result.json")
    rules = [
        load_json(EXAMPLE_DIR / name)
        for name in (
            "rule-far.json",
            "rule-height.json",
            "rule-landuse.json",
            "rule-protected.json",
            "rule-ecoredline.json",
        )
    ]

    actual_results = [evaluate_rule(rule, request, [exception]) for rule in rules]
    expected_by_id = {item["rule_ref"]["rule_id"]: item for item in result["rule_results"]}
    for item in actual_results:
        expected = expected_by_id[item["rule_ref"]["rule_id"]]
        assert item == expected
        assert item["status"] == vectors["expected_statuses"][item["rule_ref"]["rule_id"]]

    assert result["input_digest"] == {
        "algorithm": "sha256",
        "digest": sha256_hex(request),
    }
    assert result["engine"]["interface_profile"] == "TST-RULE-ENGINE/0.3"


def check_rule_set_integrity() -> None:
    rule_set = load_json(EXAMPLE_DIR / "rule-set.json")
    rules = {
        rule["rule_id"]: rule
        for rule in [
            load_json(EXAMPLE_DIR / name)
            for name in (
                "rule-far.json",
                "rule-height.json",
                "rule-landuse.json",
                "rule-protected.json",
                "rule-ecoredline.json",
            )
        ]
    }
    for ref in rule_set["rule_refs"]:
        rule = rules[ref["rule_id"]]
        assert ref == ref_for(rule)


def check_locale_key_parity() -> None:
    locales = [
        load_json(ROOT / "locales" / "zh-CN.json"),
        load_json(ROOT / "locales" / "ja-JP.json"),
        load_json(ROOT / "locales" / "en-US.json"),
    ]
    keys = set(locales[0])
    for locale in locales[1:]:
        assert set(locale) == keys, "locale keys differ"


def main() -> int:
    check_schema_examples()
    check_decimal_profile()
    check_hash_vectors()
    check_version_links()
    check_rule_set_integrity()
    check_evaluation_vector()
    check_locale_key_parity()
    print("TST Chain v0.3 Planning Rule conformance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
