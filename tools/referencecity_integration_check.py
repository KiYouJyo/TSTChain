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
        status = item["status"]
        assert status in counts
        counts[status] += 1
        assert isinstance(item.get("missing"), list)
        if status == "full":
            assert item["missing"] == []
            assert item.get("execution_path")
        else:
            assert item["missing"]

    assert counts == gap["summary"]
    complete = counts == {"full": len(scenarios), "partial": 0, "unsupported": 0}
    assert gap["end_to_end_ready"] is complete

    if complete:
        verification = gap["verification"]
        assert verification["runner"] == "tools/referencecity_v0_7_benchmark.py"
        assert verification["referencecity_ref"]
        assert set(verification["python_versions"]) == {"3.11", "3.12", "3.13"}
        assert verification["persistent_replay"] is True
        assert verification["quorum_finality"] is True
        assert verification["checkpoint_bound_state_sync"] is True

    print("TST × ReferenceCity integration profile: PASS")
    print(
        f"  as-of={gap['as_of_tstchain_version']} "
        f"full={counts['full']} partial={counts['partial']} unsupported={counts['unsupported']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
