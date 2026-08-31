#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "integrations" / "referencecity" / "v0.1"


def load(name: str):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def main() -> int:
    profile = load("profile.json")
    gap = load("capability-gap.json")

    assert profile["referencecity_protocol_version"] == "0.1"
    assert profile["referencecity_core_dataset_version"] == "0.1.0"
    assert profile["canonicalization_boundary"]["tst_core_profile"] == "TST-C14N-JSON/0.1"
    assert profile["canonicalization_boundary"]["referencecity_external_content_profile"] == "RFC8785-JCS"
    assert profile["ground_truth_policy"]["adapter_input_contains_ground_truth"] is False
    assert profile["ground_truth_policy"]["adapter_must_not_read_expected_directory"] is True

    scenarios = gap["scenarios"]
    assert [item["scenario"] for item in scenarios] == [f"S{i:03d}" for i in range(1, 11)]
    counts = {"full": 0, "partial": 0, "unsupported": 0}
    for item in scenarios:
        assert item["status"] in counts
        counts[item["status"]] += 1
        assert item["missing"]
        assert item["target_versions"]
    assert counts == gap["summary"], (counts, gap["summary"])
    assert gap["end_to_end_ready"] is False
    print("TST × ReferenceCity integration profile: PASS")
    print(f"  current: full={counts['full']} partial={counts['partial']} unsupported={counts['unsupported']}")
    print("  canonicalization boundary: TST core != ReferenceCity external JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
