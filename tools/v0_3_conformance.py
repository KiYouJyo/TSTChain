#!/usr/bin/env python3
"""TST Chain v0.3 Planning Rule conformance checks."""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from v0_2_conformance import canonical_bytes, sha256_hex

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "v0.3"
EXAMPLE_DIR = ROOT / "examples" / "v0.3"

SCHEMA_EXAMPLES = {
    "rule-set-referencecity.json": "rule-set.schema.json",
    "rule-farmland-land-use.json": "planning-rule.schema.json",
    "rule-ecological-intersection.json": "planning-rule.schema.json",
    "spatial-evaluation-s007.json": "spatial-evaluation.schema.json",
    "evaluation-request-s006.json": "rule-evaluation-request.schema.json",
    "evaluation-request-s007.json": "rule-evaluation-request.schema.json",
    "evaluation-result-s006.json": "rule-evaluation-result.schema.json",
    "evaluation-result-s007.json": "rule-evaluation-result.schema.json",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(schema_name: str, value) -> None:
    schema = load(SCHEMA_DIR / schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def active(rule: dict, request: dict) -> bool:
    if rule["status"] != "active":
        return False
    if rule["scope"]["jurisdiction_refs"] and request["jurisdiction_ref"] not in rule["scope"]["jurisdiction_refs"]:
        return False
    if rule["scope"]["object_types"] and request["object_type"] not in rule["scope"]["object_types"]:
        return False
    if rule["scope"]["target_object_refs"] and request["subject_object_ref"] not in rule["scope"]["target_object_refs"]:
        return False
    constraints = set(rule["scope"]["spatial_constraint_refs"])
    if constraints:
        context = set(request["facts"]["reference_sets"].get("spatial_context_refs", []))
        if not constraints.intersection(context):
            return False
    return True


def violation_for(condition: dict, facts: dict):
    kind = condition["kind"]
    key = condition["fact_key"]
    if kind in {"enum_forbid", "enum_allow"}:
        value = facts["string_values"].get(key)
        if value is None:
            return None
        values = set(condition["values"])
        violates = value in values if kind == "enum_forbid" else value not in values
        return violates, []
    if kind in {"decimal_max", "decimal_min"}:
        value = facts["decimal_values"].get(key)
        if value is None:
            return None
        actual = Decimal(value)
        threshold = Decimal(condition["threshold_decimal"])
        violates = actual > threshold if kind == "decimal_max" else actual < threshold
        return violates, []
    if kind in {"spatial_relation_forbid", "spatial_relation_require"}:
        matches = [
            relation for relation in facts["spatial_relations"]
            if relation["constraint_ref"] == condition["constraint_ref"]
            and relation["relation"] in set(condition["relations"])
        ]
        violates = bool(matches) if kind == "spatial_relation_forbid" else not bool(matches)
        return violates, [item["evidence_ref"] for item in matches]
    raise AssertionError(kind)


def evaluate(request: dict, rules: list[dict]) -> dict:
    evaluated = []
    violations = []
    for rule in rules:
        if not active(rule, request):
            continue
        evaluated.append(rule["rule_id"])
        for condition in rule["conditions"]:
            checked = violation_for(condition, request["facts"])
            if checked is None:
                continue
            violates, evidence_refs = checked
            if violates:
                violations.append({
                    "rule_id": rule["rule_id"],
                    "condition_id": condition["condition_id"],
                    "code": condition["violation_code"],
                    "severity": "error",
                    "evidence_refs": sorted(set(evidence_refs)),
                })
    return {
        "outcome": "fail" if violations else "pass",
        "evaluated_rule_refs": sorted(evaluated),
        "violations": sorted(violations, key=canonical_bytes),
    }


def check_schema_examples() -> None:
    for filename, schema in SCHEMA_EXAMPLES.items():
        validate(schema, load(EXAMPLE_DIR / filename))


def check_referencecity_vectors() -> None:
    rules = [
        load(EXAMPLE_DIR / "rule-farmland-land-use.json"),
        load(EXAMPLE_DIR / "rule-ecological-intersection.json"),
    ]
    for suffix in ("s006", "s007"):
        request = load(EXAMPLE_DIR / f"evaluation-request-{suffix}.json")
        expected = load(EXAMPLE_DIR / f"evaluation-result-{suffix}.json")
        actual = evaluate(request, rules)
        assert actual["outcome"] == expected["outcome"]
        assert actual["evaluated_rule_refs"] == expected["evaluated_rule_refs"]
        assert actual["violations"] == expected["violations"]

    s006 = load(EXAMPLE_DIR / "evaluation-request-s006.json")
    assert s006["external_input_digest"]["canonicalization"] == "RFC8785-JCS"
    s007_spatial = load(EXAMPLE_DIR / "spatial-evaluation-s007.json")
    assert s007_spatial["subject_geometry_digest"]["canonicalization"] == "RFC8785-JCS"
    assert s007_spatial["constraint_geometry_digest"]["canonicalization"] == "RFC8785-JCS"


def check_canonicalization() -> None:
    for filename in ("rule-farmland-land-use.json", "rule-ecological-intersection.json", "rule-set-referencecity.json"):
        value = load(EXAMPLE_DIR / filename)
        first = canonical_bytes(value)
        second = canonical_bytes(json.loads(json.dumps(value, ensure_ascii=False)))
        assert first == second
        assert len(sha256_hex(value)) == 64


def main() -> int:
    check_schema_examples()
    check_referencecity_vectors()
    check_canonicalization()
    print("TST Chain v0.3 Planning Rule conformance: PASS")
    print("  ReferenceCity S006: planning rule conflict mapped")
    print("  ReferenceCity S007: external spatial relation evidence mapped")
    print("  geometry engine: external by contract")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"TST Chain v0.3 conformance: FAIL: {exc}", file=sys.stderr)
        raise
