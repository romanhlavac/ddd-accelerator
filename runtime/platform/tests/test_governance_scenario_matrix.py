"""Executable characterization generated from governance scenario matrix v1.

The adapters below arrange evidence and invoke the existing production
evaluators.  They deliberately do not make governance decisions themselves.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from runtime.platform.release_governance import (
    evaluate_merge_release_eligibility,
    evaluate_release_scope,
)
from runtime.platform.candidate_evidence import restore_candidate_evidence


ROOT = Path(__file__).resolve().parents[3]
MATRIX_PATH = ROOT / "tests" / "fixtures" / "governance" / "scenario-matrix-v1.json"
CONTROLLED_CANDIDATE_PATH = ROOT / "scripts" / "platform" / "Test-DDDAControlledReleaseCandidate.py"
HRDR_READER_PATH = ROOT / "scripts" / "platform" / "Read-DDDAHrdr.py"
REPO = "romanhlavac/ddd-accelerator"
PR = 103
SHA = "a" * 40
PACKAGE_BYTES = b"characterized candidate package"
PACKAGE_SHA = hashlib.sha256(PACKAGE_BYTES).hexdigest()
VERSION = "0.1.1"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTROLLED_CANDIDATE = _load_module("governance_matrix_controlled_candidate", CONTROLLED_CANDIDATE_PATH)
HRDR_READER = _load_module("governance_matrix_hrdr_reader", HRDR_READER_PATH)
MATRIX = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
PYTHON_ADAPTERS = {
    "controlled_candidate",
    "package_evidence",
    "workflow_guard",
    "hrdr_comments",
    "release_scope",
    "release_scope_case",
    "merge_eligibility",
}


def _set_path(target: dict[str, Any], dotted_path: str, value: Any) -> None:
    cursor = target
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        cursor = cursor[part]
    cursor[parts[-1]] = value


def _controlled_candidate_baseline() -> dict[str, Any]:
    return {
        "pr": {
            "number": PR,
            "state": "open",
            "draft": True,
            "head": {
                "sha": SHA,
                "ref": "release/0.1.1-controlled-recovery-source",
                "repo": {"full_name": REPO},
            },
            "base": {"ref": "main"},
            "body": "## Controlled release-source candidate — DDDA 0.1.1",
        },
        "context": {
            "repository": REPO,
            "pr_number": PR,
            "source_sha": SHA,
            "version": VERSION,
            "operation": "technical_validation",
        },
    }


def _release_record() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "repository": REPO,
        "pr": PR,
        "branch": "feature/174-governance-characterization",
        "source_sha": SHA,
        "candidate_package_sha256": PACKAGE_SHA,
        "version": VERSION,
        "reviewer": "romanhlavac",
        "decision_owner": "romanhlavac",
        "decision": "go",
        "decided_at": "2026-09-01T09:00:00Z",
        "scope_issues": [9, 12],
        "findings": [],
        "accepted_risks": [],
        "evidence": {},
    }


def _release_snapshot() -> dict[str, Any]:
    return {
        "current_pr_head": SHA,
        "milestone_title": "DDDA 0.1.1",
        "milestone_issues": [9, 12],
        "issue_states": {"9": "closed", "12": "closed"},
        "blockers": {"9": [], "12": []},
        "project_rows": {
            "9": {"Status": "Done", "Blocked": "No"},
            "12": {"Status": "Done", "Blocked": "No"},
        },
        "risk_issue_states": {},
        "risk_issue_assignees": {},
        "risk_issue_horizons": {},
        "project": {
            "title": "DDDA Platform Backlog & Delivery",
            "planning_view_filter": "is:issue",
            "delivery_view_filter": "is:pr is:open",
        },
        "physical_scope": {
            "previous_release_tag": "v0.1.0",
            "previous_release_sha": "b" * 40,
            "release_source_sha": SHA,
            "compare_status": "ahead",
            "unmapped_commit_shas": [],
            "shipping_prs": [
                {"number": 71, "merged": True, "primary_crs": [9], "milestone": "DDDA 0.1.1", "target_release": VERSION},
                {"number": 72, "merged": True, "primary_crs": [12], "milestone": "DDDA 0.1.1", "target_release": VERSION},
            ],
        },
    }


def _release_scope(record: dict[str, Any], snapshot: dict[str, Any]):
    return evaluate_release_scope(
        record,
        snapshot,
        expected_repository=REPO,
        expected_pr=PR,
        expected_source_sha=SHA,
        expected_package_sha256=PACKAGE_SHA,
        expected_version=VERSION,
    )


def _apply_overrides(baseline: dict[str, Any], values: dict[str, Any], prefixes: tuple[str, ...]) -> None:
    for path, value in values.items():
        if path.startswith(prefixes):
            _set_path(baseline, path, value)


def _execute(scenario: dict[str, Any], tmp_path: Path) -> tuple[str, list[str]]:
    adapter = scenario["adapter"]
    values = scenario["input"]

    if adapter == "controlled_candidate":
        evidence = _controlled_candidate_baseline()
        _apply_overrides(evidence, values, ("pr.", "context."))
        result = CONTROLLED_CANDIDATE.validate_request(evidence["pr"], **evidence["context"])
        return result["status"], result["failures"]

    if adapter == "package_evidence":
        package = tmp_path / "candidate.zip"
        if values.get("package_present", True):
            package.write_bytes(PACKAGE_BYTES)
        evidence = {
            "report": {
                "status": "PASS",
                "source": {"repository": REPO, "pr": PR, "commit": SHA},
                "package": {"sha256": PACKAGE_SHA},
            }
        }
        _apply_overrides(evidence, values, ("report.",))
        result = CONTROLLED_CANDIDATE.validate_validation_evidence(
            evidence["report"], repository=REPO, pr_number=PR, source_sha=SHA, package_path=package
        )
        return result["status"], result["failures"]

    if adapter == "workflow_guard":
        # Exercise the shared production evidence-restoration behavior instead
        # of asserting that a workflow contains a particular sentence.
        artifact_root = tmp_path / "duplicate-package-artifact"
        package_name = f"ddda-candidate-{SHA[:12]}.zip"
        report = {
            "status": "PASS",
            "source": {"repository": REPO, "pr": PR, "commit": SHA},
            "package": {
                "path": package_name,
                "artifact_name": f"ddda-candidate-{SHA}",
                "sha256": PACKAGE_SHA,
            },
        }
        report_path = artifact_root / "metadata" / "result.json"
        report_path.parent.mkdir(parents=True)
        report_path.write_text(json.dumps(report), encoding="utf-8")
        for folder in ("candidate-a", "candidate-b"):
            package_path = artifact_root / folder / package_name
            package_path.parent.mkdir(parents=True)
            package_path.write_bytes(PACKAGE_BYTES)
        result = restore_candidate_evidence(
            artifact_root,
            repository=REPO,
            pr_number=PR,
            source_sha=SHA,
        )
        return result["status"], result["failures"]

    if adapter == "hrdr_comments":
        comments = [
            {
                "body": "<!-- ddda:human-release-decision:v1 -->\n```json\n{}\n```",
                "user": {"login": "romanhlavac"},
            }
            for _ in values["records"]
        ]
        try:
            HRDR_READER.extract_hrdr(comments)
        except ValueError:
            return "FAIL", ["HRDR_CARDINALITY"]
        return "PASS", []

    if adapter in {"release_scope", "release_scope_case"}:
        evidence = {"record": _release_record(), "snapshot": _release_snapshot()}
        if adapter == "release_scope_case":
            case = values["case"]
            if case == "extra_shipping_cr":
                evidence["snapshot"]["physical_scope"]["shipping_prs"].append(
                    {"number": 99, "merged": True, "primary_crs": [999], "milestone": "DDDA 0.1.1", "target_release": VERSION}
                )
            elif case == "missing_shipping_cr":
                evidence["snapshot"]["physical_scope"]["shipping_prs"] = evidence["snapshot"]["physical_scope"]["shipping_prs"][:1]
            else:  # pragma: no cover - fixture schema test reports unknown cases
                raise AssertionError(f"Unknown release-scope case: {case}")
        else:
            _apply_overrides(evidence, values, ("record.", "snapshot."))
        result = _release_scope(evidence["record"], evidence["snapshot"])
        return result.status, list(result.failures)

    if adapter == "merge_eligibility":
        snapshot = {
            "active_release": {"version": VERSION},
            "primary_crs": [174],
            "primary_cr": {"milestone": "DDDA 0.1.1", "target_release": VERSION},
        }
        for path, value in values.items():
            _set_path(snapshot, path, value)
        failures = evaluate_merge_release_eligibility(snapshot)
        return ("FAIL" if failures else "PASS"), failures

    raise AssertionError(f"Unsupported Python scenario adapter: {adapter}")


def test_matrix_contract_is_versioned_unique_and_has_explicit_outcomes() -> None:
    assert MATRIX["schema_version"] == 1
    assert MATRIX["contract"] == "ddda-governance-characterization"
    identifiers = [scenario["id"] for scenario in MATRIX["scenarios"]]
    assert len(identifiers) == len(set(identifiers))
    for scenario in MATRIX["scenarios"]:
        assert scenario["adapter"]
        assert scenario["dimensions"]
        assert scenario["expected"]["status"] in {"PASS", "FAIL"}
        assert isinstance(scenario["expected"]["failure_codes"], list)


def test_matrix_covers_every_required_axis_value() -> None:
    observed: dict[str, set[str]] = {axis: set() for axis in MATRIX["required_coverage"]}
    for scenario in MATRIX["scenarios"]:
        for axis, value in scenario["dimensions"].items():
            observed.setdefault(axis, set()).add(value)
    for axis, required in MATRIX["required_coverage"].items():
        assert set(required) <= observed[axis], f"Missing {axis}: {set(required) - observed[axis]}"


PYTHON_SCENARIOS = [scenario for scenario in MATRIX["scenarios"] if scenario["adapter"] in PYTHON_ADAPTERS]


@pytest.mark.parametrize("scenario", PYTHON_SCENARIOS, ids=lambda row: row["id"])
def test_python_characterization_scenario(scenario: dict[str, Any], tmp_path: Path) -> None:
    status, failures = _execute(deepcopy(scenario), tmp_path)
    assert status == scenario["expected"]["status"]
    assert set(scenario["expected"]["failure_codes"]) <= set(failures)


def test_s3_projection_scenarios_are_reported_outside_release_failures() -> None:
    scenarios = [
        scenario
        for scenario in PYTHON_SCENARIOS
        if scenario["expected"].get("projection_mismatches")
    ]
    assert scenarios
    for scenario in scenarios:
        assert scenario["migration"]["change_request"] == 173
        evidence = {"record": _release_record(), "snapshot": _release_snapshot()}
        _apply_overrides(evidence, scenario["input"], ("record.", "snapshot."))
        result = _release_scope(evidence["record"], evidence["snapshot"])
        assert result.status == "PASS"
        assert result.failures == ()
        assert set(scenario["expected"]["projection_mismatches"]) <= set(result.projection_mismatches)
        assert all(
            item["primary_category"] == "GOVERNANCE_PROJECTION"
            for item in result.as_dict()["projection_mismatch_categories"]
        )


def test_non_python_scenarios_are_owned_by_the_powershell_component_suite() -> None:
    non_python = {scenario["adapter"] for scenario in MATRIX["scenarios"] if scenario["adapter"] not in PYTHON_ADAPTERS}
    assert non_python == {"check_runs", "human_review_contract"}
    powershell = (ROOT / "tests" / "powershell" / "Test-DDDAGovernanceScenarioMatrix.ps1").read_text(encoding="utf-8-sig")
    assert "scenario-matrix-v1.json" in powershell
