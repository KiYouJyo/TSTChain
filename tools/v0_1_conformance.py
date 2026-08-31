#!/usr/bin/env python3
"""TST Chain v0.1 protocol conformance checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unicodedata

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
VECTOR_FILE = ROOT / "test-vectors" / "v0.1" / "hashes.json"
LOCALES = ("zh-CN", "ja-JP", "en-US")

SCHEMAS = {
    "SpatialObject": ROOT / "schemas" / "v0.1" / "spatial-object.schema.json",
    "SpatialEvent": ROOT / "schemas" / "v0.1" / "spatial-event.schema.json",
    "Evidence": ROOT / "schemas" / "v0.1" / "evidence.schema.json",
}


def no_duplicate_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(
            handle,
            object_pairs_hook=no_duplicate_pairs,
            parse_int=lambda value: (_ for _ in ()).throw(
                ValueError(f"JSON numbers are not allowed in v0.1 instances: {value}")
            ),
            parse_float=lambda value: (_ for _ in ()).throw(
                ValueError(f"JSON numbers are not allowed in v0.1 instances: {value}")
            ),
        )


def canonical_dump(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def normalize_v01(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)

    if value is None or isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        raise ValueError("JSON number values are not allowed in TST v0.1 core instances")

    if isinstance(value, dict):
        normalized = {}
        for key, child in value.items():
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise ValueError(
                    f"keys collide after NFC normalization: {normalized_key}"
                )
            normalized[normalized_key] = normalize_v01(child)
        return normalized

    if isinstance(value, list):
        normalized_items = [normalize_v01(item) for item in value]
        normalized_items.sort(key=canonical_dump)
        return normalized_items

    raise TypeError(f"unsupported JSON value: {type(value)!r}")


def canonical_bytes(value) -> bytes:
    return canonical_dump(normalize_v01(value))


def digest(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_instance(kind: str, value) -> None:
    schema = json.loads(SCHEMAS[kind].read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise AssertionError(f"{kind} schema validation failed: {messages}")


def check_vectors() -> None:
    manifest = json.loads(VECTOR_FILE.read_text(encoding="utf-8"))
    if manifest["profile"] != "TST-C14N-JSON/0.1":
        raise AssertionError("unexpected canonicalization profile")
    if manifest["hash_algorithm"] != "sha256":
        raise AssertionError("unexpected hash algorithm")

    for vector in manifest["vectors"]:
        source = ROOT / vector["input"]
        value = load_json(source)
        validate_instance(vector["type"], value)

        actual_canonical = canonical_bytes(value).decode("utf-8")
        actual_digest = digest(value)

        if actual_canonical != vector["canonical_utf8"]:
            raise AssertionError(f"canonical bytes mismatch: {source}")
        if actual_digest != vector["sha256"]:
            raise AssertionError(f"SHA-256 mismatch: {source}")

        equivalent = vector.get("equivalent_input")
        if equivalent:
            other = load_json(ROOT / equivalent)
            validate_instance(vector["type"], other)
            if canonical_bytes(other) != canonical_bytes(value):
                raise AssertionError(f"equivalent input canonical mismatch: {equivalent}")
            if digest(other) != actual_digest:
                raise AssertionError(f"equivalent input digest mismatch: {equivalent}")


def check_locales() -> None:
    locale_maps = {}
    for locale in LOCALES:
        path = ROOT / "locales" / f"{locale}.json"
        locale_maps[locale] = json.loads(path.read_text(encoding="utf-8"))

    baseline = set(locale_maps["en-US"])
    for locale, mapping in locale_maps.items():
        keys = set(mapping)
        missing = sorted(baseline - keys)
        extra = sorted(keys - baseline)
        if missing or extra:
            raise AssertionError(
                f"locale key mismatch for {locale}: missing={missing}, extra={extra}"
            )
        if any(not isinstance(value, str) or not value.strip() for value in mapping.values()):
            raise AssertionError(f"locale {locale} contains empty/non-string values")


def main() -> int:
    check_vectors()
    check_locales()
    print("TST Chain v0.1 conformance: PASS")
    print("  schemas: SpatialObject, SpatialEvent, Evidence")
    print("  canonicalization: TST-C14N-JSON/0.1")
    print("  hash: SHA-256")
    print("  locales: zh-CN, ja-JP, en-US")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"TST Chain v0.1 conformance: FAIL: {exc}", file=sys.stderr)
        raise
