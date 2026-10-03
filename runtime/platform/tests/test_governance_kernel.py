import importlib.util
import json
from pathlib import Path

import pytest

from runtime.platform.governance_kernel import (
    evaluate_candidate_context,
    evaluate_candidate_identity,
    evaluate_candidate_package_binding,
    evaluate_authoritative_checks,
    evaluate_hrdr_binding,
    evaluate_human_review_binding,
    evaluate_physical_scope_binding,
    evaluate_promotion_readiness,
)
from runtime.platform.mismatch_taxonomy import classify_mismatch


SHA = "a" * 40
PACKAGE = "b" * 64
ROOT = Path(__file__).resolve().parents[3]
MATRIX = json.loads(
    (ROOT / "tests/fixtures/governance/scenario-matrix-v1.json").read_text(encoding="utf-8")
)
MATRIX_V2 = json.loads(
    (ROOT / "tests/fixtures/governance/scenario-matrix-v2.json").read_text(encoding="utf-8")
)


def context(operation: str = "merge_dry_run") -> dict:
    return {
        "schema_version": 1,
        "context_kind": "ddda_candidate_context",
        "candidate_kind": "NORMAL",
        "release_mode": "STANDARD",
        "operation": operation,
        "repository": "romanhlavac/ddd-accelerator",
        "pr": 176,
        "base_branch": "main",
        "source_branch": "test/174-governance-characterization",
        "source_sha": SHA,
        "version": "0.1.2",
        "generation": 1,
        "pr_state": "READY",
        "validation_evidence": {
            "status": "PASS",
            "repository": "romanhlavac/ddd-accelerator",
            "pr": 176,
            "source_sha": SHA,
            "package_sha256": PACKAGE,
            "package_present": True,
            "observed_package_sha256": PACKAGE,
            "artifact_name": f"ddda-candidate-{SHA}",
            "workflow_run_id": 36355784058,
        },
        "authoritative_check_summary": {
            "source_sha": SHA,
            "status": "PASS",
            "required_checks": ["Platform validation", "One-command PR validation"],
            "latest_results": [
                {
                    "name": "Platform validation",
                    "source_sha": SHA,
                    "status": "COMPLETED",
                    "conclusion": "SUCCESS",
                    "run_id": 36355784058,
                },
                {
                    "name": "One-command PR validation",
                    "source_sha": SHA,
                    "status": "COMPLETED",
                    "conclusion": "SUCCESS",
                    "run_id": 36355784058,
                },
            ],
        },
        "human_review_reference": {
            "repository": "romanhlavac/ddd-accelerator",
            "pr": 176,
            "verdict": "PASS",
            "reviewed_sha": SHA,
            "candidate_package_sha256": PACKAGE,
            "reviewer": "romanhlavac",
            "reviewed_at": "2026-09-28T07:54:55Z",
            "provenance_verified": True,
        },
        "hrdr_reference": None,
        "physical_scope_reference": None,
        "project_evidence_reference": None,
    }


def set_path(target: dict, dotted_path: str, value) -> None:
    cursor = target
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        cursor = cursor[part]
    cursor[parts[-1]] = value


def test_merge_dry_run_passes_exact_ready_context_without_authorizing_side_effects():
    result = evaluate_candidate_context(context())
    assert result.status == "PASS"
    assert result.authorization_required is False
    assert result.side_effects_allowed is False


def test_merge_readiness_still_requires_separate_authorization():
    result = evaluate_candidate_context(context("merge"))
    assert result.status == "PASS"
    assert result.authorization_required is True
    assert result.side_effects_allowed is False


@pytest.mark.parametrize(
    ("mutate", "failure"),
    [
        (lambda value: value.update(pr_state="DRAFT"), "MERGE_OPERATION_REQUIRES_READY"),
        (
            lambda value: value["validation_evidence"].update(source_sha="c" * 40),
            "VALIDATION_SOURCE_SHA_MISMATCH",
        ),
        (
            lambda value: value["human_review_reference"].update(reviewed_sha="c" * 40),
            "HUMAN_REVIEW_SOURCE_SHA_MISMATCH",
        ),
        (
            lambda value: value["human_review_reference"].update(candidate_package_sha256="c" * 64),
            "HUMAN_REVIEW_PACKAGE_SHA256_MISMATCH",
        ),
        (
            lambda value: value["authoritative_check_summary"].update(status="FAIL"),
            "AUTHORITATIVE_CHECKS_NOT_PASS",
        ),
    ],
)
def test_characterized_merge_failures_remain_fail_closed(mutate, failure):
    candidate = context()
    mutate(candidate)
    result = evaluate_candidate_context(candidate)
    assert result.status == "FAIL"
    assert failure in result.failure_codes
    assert result.side_effects_allowed is False


def test_latest_required_check_must_be_present_and_successful():
    candidate = context()
    candidate["authoritative_check_summary"]["latest_results"].pop()
    result = evaluate_candidate_context(candidate)
    assert "AUTHORITATIVE_CHECK_MISSING:One-command PR validation" in result.failure_codes


def test_authoritative_checks_cannot_expand_explicit_success_policy():
    candidate = context()
    candidate["authoritative_check_summary"]["accepted_conclusions"] = ["SUCCESS", "NEUTRAL", "SKIPPED"]
    candidate["authoritative_check_summary"]["latest_results"][0]["conclusion"] = "NEUTRAL"
    result = evaluate_authoritative_checks(candidate)
    assert result.status == "FAIL"
    assert "AUTHORITATIVE_ACCEPTED_CONCLUSION_POLICY_INVALID" in result.failure_codes
    assert result.authorization_required is False
    assert result.side_effects_allowed is False


def test_recovery_kind_requires_explicit_controlled_recovery_mode():
    candidate = context("validate")
    candidate["candidate_kind"] = "RECOVERY"
    result = evaluate_candidate_context(candidate)
    assert "CANDIDATE_KIND_RELEASE_MODE_MISMATCH" in result.failure_codes


def test_controlled_recovery_context_is_explicit_and_valid_for_validation():
    candidate = context("validate")
    candidate["candidate_kind"] = "RECOVERY"
    candidate["release_mode"] = "CONTROLLED_RECOVERY"
    candidate["source_branch"] = "release/0.1.2-controlled-recovery-source"
    candidate["pr_state"] = "DRAFT"
    assert evaluate_candidate_context(candidate).status == "PASS"


def test_controlled_recovery_validation_preserves_characterized_draft_boundary():
    candidate = context("validate")
    candidate["candidate_kind"] = "RECOVERY"
    candidate["release_mode"] = "CONTROLLED_RECOVERY"
    result = evaluate_candidate_context(candidate)
    assert result.status == "FAIL"
    assert "RECOVERY_PREPARATION_REQUIRES_DRAFT" in result.failure_codes


def test_candidate_identity_can_be_evaluated_before_package_restore():
    candidate = context("publish_hrdr_scaffold")
    candidate["candidate_kind"] = "RECOVERY"
    candidate["release_mode"] = "CONTROLLED_RECOVERY"
    candidate["source_branch"] = "release/0.1.2-controlled-recovery-source-v2"
    candidate["generation"] = 2
    candidate["pr_state"] = "DRAFT"
    candidate["validation_evidence"]["status"] = "MISSING"
    candidate["authoritative_check_summary"]["status"] = "MISSING"
    result = evaluate_candidate_identity(candidate)
    assert result.status == "PASS"
    assert result.side_effects_allowed is False


def test_candidate_package_binding_is_a_pure_kernel_decision():
    candidate = context("validate")
    result = evaluate_candidate_package_binding(candidate)
    assert result.status == "PASS"
    assert result.authorization_required is False
    assert result.side_effects_allowed is False


def test_human_review_binding_is_a_pure_kernel_decision():
    candidate = context("merge_dry_run")
    result = evaluate_human_review_binding(candidate)
    assert result.status == "PASS"
    assert result.authorization_required is False
    assert result.side_effects_allowed is False


def test_human_review_binding_rejects_stale_candidate_identity():
    candidate = context("merge_dry_run")
    candidate["human_review_reference"]["reviewed_sha"] = "c" * 40
    result = evaluate_human_review_binding(candidate)
    assert result.status == "FAIL"
    assert "HUMAN_REVIEW_SOURCE_SHA_MISMATCH" in result.failure_codes


def test_hrdr_binding_is_a_pure_kernel_decision():
    candidate = context("promotion_dry_run")
    candidate["hrdr_reference"] = {
        "repository": "romanhlavac/ddd-accelerator",
        "pr": 176,
        "decision": "GO",
        "source_sha": SHA,
        "candidate_package_sha256": PACKAGE,
        "version": "0.1.2",
        "decision_owner": "romanhlavac",
        "decided_at": "2026-09-28T08:30:00Z",
        "provenance_verified": True,
    }
    result = evaluate_hrdr_binding(candidate)
    assert result.status == "PASS"
    assert result.authorization_required is False
    assert result.side_effects_allowed is False


def test_hrdr_binding_rejects_stale_candidate_identity():
    candidate = context("promotion_dry_run")
    candidate["hrdr_reference"] = {
        "repository": "romanhlavac/ddd-accelerator",
        "pr": 176,
        "decision": "GO",
        "source_sha": "c" * 40,
        "candidate_package_sha256": PACKAGE,
        "version": "0.1.1",
        "decision_owner": "romanhlavac",
        "decided_at": "2026-09-28T08:30:00Z",
        "provenance_verified": True,
    }
    result = evaluate_hrdr_binding(candidate)
    assert result.status == "FAIL"
    assert "HRDR_SOURCE_SHA_MISMATCH" in result.failure_codes
    assert "HRDR_VERSION_MISMATCH" in result.failure_codes


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("repository", "wrong/repository", "HUMAN_REVIEW_REPOSITORY_MISMATCH"),
        ("pr", 999, "HUMAN_REVIEW_PR_MISMATCH"),
    ],
)
def test_human_review_root_identity_is_a_kernel_invariant(field, value, failure):
    candidate = context("merge_dry_run")
    candidate["human_review_reference"][field] = value
    result = evaluate_human_review_binding(candidate)
    assert result.status == "FAIL"
    assert failure in result.failure_codes


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("repository", "wrong/repository", "HRDR_REPOSITORY_MISMATCH"),
        ("pr", 999, "HRDR_PR_MISMATCH"),
    ],
)
def test_hrdr_root_identity_is_a_kernel_invariant(field, value, failure):
    candidate = context("promotion_dry_run")
    candidate["hrdr_reference"] = {
        "repository": "romanhlavac/ddd-accelerator",
        "pr": 176,
        "decision": "GO",
        "source_sha": SHA,
        "candidate_package_sha256": PACKAGE,
        "version": "0.1.2",
        "decision_owner": "romanhlavac",
        "decided_at": "2026-09-28T08:30:00Z",
        "provenance_verified": True,
    }
    candidate["hrdr_reference"][field] = value
    result = evaluate_hrdr_binding(candidate)
    assert result.status == "FAIL"
    assert failure in result.failure_codes


def test_physical_scope_binding_is_a_pure_kernel_decision():
    physical = {
        "previous_release_tag": "v0.1.1",
        "previous_release_sha": "c" * 40,
        "release_source_sha": SHA,
        "compare_status": "ahead",
        "unmapped_commit_shas": [],
        "shipping_prs": [
            {
                "number": 187,
                "merged": True,
                "primary_crs": [171],
                "milestone": "DDDA 0.1.2",
                "target_release": "0.1.2",
            }
        ],
    }
    result = evaluate_physical_scope_binding(
        physical,
        expected_source_sha=SHA,
        expected_version="0.1.2",
        declared_scope=[171],
    )
    assert result.status == "PASS"
    assert result.authorization_required is False
    assert result.side_effects_allowed is False


def test_physical_scope_binding_requires_explicit_recovery_for_extra_cr():
    physical = {
        "previous_release_tag": "v0.1.1",
        "previous_release_sha": "c" * 40,
        "release_source_sha": SHA,
        "compare_status": "ahead",
        "unmapped_commit_shas": [],
        "shipping_prs": [
            {
                "number": 187,
                "merged": True,
                "primary_crs": [999],
                "milestone": "DDDA 0.1.2",
                "target_release": "0.1.2",
            }
        ],
    }
    result = evaluate_physical_scope_binding(
        physical,
        expected_source_sha=SHA,
        expected_version="0.1.2",
        declared_scope=[171],
    )
    assert result.status == "FAIL"
    assert "PHYSICAL_SCOPE_OUT_OF_SCOPE_PRIMARY_CR:PR#187:#999" in result.failure_codes
    assert "PHYSICAL_SCOPE_DECLARED_CR_NOT_SHIPPED:#171" in result.failure_codes
    assert "RECOVERY_DECISION_REQUIRED" in result.failure_codes


def test_promotion_readiness_composes_failures_without_authorizing_effects():
    result = evaluate_promotion_readiness(
        ["PROJECT_EVIDENCE_NOT_PASS", "HRDR_NOT_POSITIVE"],
        operation="promotion_dry_run",
    )
    assert result.status == "FAIL"
    assert result.failure_codes == ("HRDR_NOT_POSITIVE", "PROJECT_EVIDENCE_NOT_PASS")
    assert result.authorization_required is False
    assert result.side_effects_allowed is False


def test_release_readiness_pass_still_requires_separate_authorization():
    result = evaluate_promotion_readiness([], operation="release")
    assert result.status == "PASS"
    assert result.authorization_required is True
    assert result.side_effects_allowed is False


def test_promotion_readiness_rejects_malformed_failure_evidence():
    result = evaluate_promotion_readiness(["", None])
    assert result.status == "FAIL"
    assert result.failure_codes == ("PROMOTION_READINESS_EVIDENCE_INVALID",)


@pytest.mark.parametrize(
    ("mutate", "failure"),
    [
        (lambda value: value.update(repository="wrong/repository"), "VALIDATION_REPOSITORY_MISMATCH"),
        (lambda value: value.update(pr=999), "VALIDATION_PR_MISMATCH"),
        (lambda value: value.update(package_present=False), "CANDIDATE_PACKAGE_MISSING"),
        (
            lambda value: value.update(observed_package_sha256="c" * 64),
            "CANDIDATE_PACKAGE_SHA256_MISMATCH",
        ),
    ],
)
def test_candidate_package_binding_fails_closed_on_identity_drift(mutate, failure):
    candidate = context("validate")
    mutate(candidate["validation_evidence"])
    result = evaluate_candidate_package_binding(candidate)
    assert result.status == "FAIL"
    assert failure in result.failure_codes


def test_recovery_branch_and_generation_are_one_kernel_invariant():
    candidate = context("validate")
    candidate["candidate_kind"] = "RECOVERY"
    candidate["release_mode"] = "CONTROLLED_RECOVERY"
    candidate["source_branch"] = "release/0.1.2-controlled-recovery-source-v2"
    candidate["generation"] = 1
    candidate["pr_state"] = "DRAFT"
    result = evaluate_candidate_identity(candidate)
    assert result.status == "FAIL"
    assert "RECOVERY_BRANCH_INVALID" in result.failure_codes


def test_kernel_parity_suite_is_bound_to_characterization_v1_scenarios():
    scenarios = {scenario["id"]: scenario for scenario in MATRIX["scenarios"]}
    expected = {
        "recovery-validate-draft-first-exact": "PASS",
        "recovery-validate-ready-blocked": "FAIL",
        "recovery-validate-closed-blocked": "FAIL",
        "recovery-stale-sha-blocked": "FAIL",
        "human-review-missing": "FAIL",
        "human-review-pass": "PASS",
        "human-review-changes-required": "FAIL",
        "actions-queued": "FAIL",
        "actions-in-progress": "FAIL",
        "actions-missing": "FAIL",
    }
    assert {name: scenarios[name]["expected"]["status"] for name in expected} == expected


def test_unversioned_context_extension_fails_closed_in_kernel():
    candidate = context()
    candidate["implicit_authorization"] = True
    result = evaluate_candidate_context(candidate)
    assert result.status == "FAIL"
    assert "CONTEXT_FIELD_UNKNOWN:implicit_authorization" in result.failure_codes


def test_release_requires_exact_positive_hrdr_and_referenced_evidence():
    candidate = context("release")
    candidate["human_review_reference"] = None
    candidate["hrdr_reference"] = {
        "repository": "romanhlavac/ddd-accelerator",
        "pr": 176,
        "decision": "GO",
        "source_sha": SHA,
        "candidate_package_sha256": PACKAGE,
        "version": "0.1.2",
        "decision_owner": "romanhlavac",
        "decided_at": "2026-09-28T08:30:00Z",
        "provenance_verified": True,
    }
    candidate["physical_scope_reference"] = {"status": "PASS", "evidence_id": "scope-1"}
    candidate["project_evidence_reference"] = {"status": "FAIL", "evidence_id": "projection-drift"}
    result = evaluate_candidate_context(candidate)
    assert result.status == "PASS"
    assert result.authorization_required is True
    assert result.side_effects_allowed is False


def test_release_ignores_project_projection_health_but_rejects_stale_hrdr():
    candidate = context("promotion_dry_run")
    candidate["hrdr_reference"] = {
        "repository": "romanhlavac/ddd-accelerator",
        "pr": 176,
        "decision": "GO",
        "source_sha": "c" * 40,
        "candidate_package_sha256": PACKAGE,
        "version": "0.1.1",
        "decision_owner": "romanhlavac",
        "decided_at": "2026-09-28T08:30:00Z",
        "provenance_verified": True,
    }
    candidate["physical_scope_reference"] = {"status": "PASS", "evidence_id": "scope-1"}
    result = evaluate_candidate_context(candidate)
    assert result.status == "FAIL"
    assert "HRDR_SOURCE_SHA_MISMATCH" in result.failure_codes
    assert "HRDR_VERSION_MISMATCH" in result.failure_codes
    assert "PROJECT_EVIDENCE_NOT_PASS" not in result.failure_codes


def test_release_readiness_does_not_require_project_evidence():
    candidate = context("release")
    candidate["human_review_reference"] = None
    candidate["hrdr_reference"] = {
        "repository": "romanhlavac/ddd-accelerator",
        "pr": 176,
        "decision": "GO",
        "source_sha": SHA,
        "candidate_package_sha256": PACKAGE,
        "version": "0.1.2",
        "decision_owner": "romanhlavac",
        "decided_at": "2026-09-28T08:30:00Z",
        "provenance_verified": True,
    }
    candidate["physical_scope_reference"] = {"status": "PASS", "evidence_id": "scope-1"}
    candidate["project_evidence_reference"] = None
    result = evaluate_candidate_context(candidate)
    assert result.status == "PASS"
    assert result.authorization_required is True
    assert result.side_effects_allowed is False


def test_scenario_matrix_v2_contract_and_quality_metrics_are_consistent():
    scenarios = MATRIX_V2["scenarios"]
    identifiers = [scenario["id"] for scenario in scenarios]
    assert MATRIX_V2["schema_version"] == 2
    assert MATRIX_V2["contract"] == "ddda-governance-scenario-matrix"
    assert len(identifiers) == len(set(identifiers))
    assert len(scenarios) == MATRIX_V2["quality_metrics"]["scenario_count"]
    assert len(MATRIX_V2["decision_owners"]) == MATRIX_V2["quality_metrics"]["declared_decision_domains"]
    assert MATRIX_V2["quality_metrics"]["duplicate_decision_owners_per_domain"] == 0
    assert all(isinstance(owner, str) and owner for owner in MATRIX_V2["decision_owners"].values())

    observed: dict[str, set[str]] = {axis: set() for axis in MATRIX_V2["required_coverage"]}
    for scenario in scenarios:
        observed["flow"].add(scenario["flow"])
        observed["candidate_kind"].add(scenario["candidate_kind"])
        observed["operation"].add(scenario["operation"])
        observed["outcome"].add(scenario["expected"]["status"])
        if "mismatch_category" in scenario["expected"]:
            observed["mismatch_category"].add(scenario["expected"]["mismatch_category"])
        elif scenario["adapter"] == "project_release_projection":
            observed["mismatch_category"].add(scenario["expected"]["projection_category"])
    for axis, required in MATRIX_V2["required_coverage"].items():
        assert set(required) <= observed[axis], f"Missing {axis}: {set(required) - observed[axis]}"
    readback = next(row for row in scenarios if row["adapter"] == "existing_behavior_test")
    assert "test_mismatch_taxonomy.py::test_project_mutation_audit_keeps_zero_mismatch_transaction_gate" in readback["input"]["test"]


KERNEL_SCENARIOS_V2 = [row for row in MATRIX_V2["scenarios"] if row["adapter"] == "candidate_context"]


@pytest.mark.parametrize("scenario", KERNEL_SCENARIOS_V2, ids=lambda row: row["id"])
def test_scenario_matrix_v2_candidate_context_invariants(scenario: dict):
    candidate = context(scenario["operation"])
    for mutation in scenario["input"]:
        set_path(candidate, mutation["path"], mutation["value"])
    result = evaluate_candidate_context(candidate)
    expected = scenario["expected"]
    assert result.status == expected["status"]
    assert set(expected["failure_codes"]) == set(result.failure_codes)
    assert result.authorization_required is expected["authorization_required"]
    assert result.side_effects_allowed is expected["side_effects_allowed"]


PROMOTION_SCENARIOS_V2 = [row for row in MATRIX_V2["scenarios"] if row["adapter"] == "promotion_readiness"]


@pytest.mark.parametrize("scenario", PROMOTION_SCENARIOS_V2, ids=lambda row: row["id"])
def test_scenario_matrix_v2_promotion_invariants(scenario: dict):
    result = evaluate_promotion_readiness(
        scenario["input"]["failure_codes"],
        operation=scenario["operation"],
    )
    expected = scenario["expected"]
    assert result.status == expected["status"]
    assert set(expected["failure_codes"]) == set(result.failure_codes)
    assert result.authorization_required is expected["authorization_required"]
    assert result.side_effects_allowed is expected["side_effects_allowed"]


MISMATCH_SCENARIOS_V2 = [row for row in MATRIX_V2["scenarios"] if row["adapter"] == "mismatch_taxonomy"]


@pytest.mark.parametrize("scenario", MISMATCH_SCENARIOS_V2, ids=lambda row: row["id"])
def test_scenario_matrix_v2_mismatch_classification(scenario: dict):
    result = classify_mismatch(scenario["input"]["code"])
    assert result["primary_category"] == scenario["expected"]["mismatch_category"]


def test_scenario_matrix_v2_project_projection_behavior():
    scenario = next(row for row in MATRIX_V2["scenarios"] if row["adapter"] == "project_release_projection")
    module_path = ROOT / "runtime/platform/tests/test_release_governance.py"
    spec = importlib.util.spec_from_file_location("governance_matrix_release_scope", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    live = module.snapshot()
    live["project_rows"]["12"] = {"Status": "In progress", "Blocked": "Yes"}
    result = module.evaluate(live=live)
    categories = result.as_dict()["projection_mismatch_categories"]
    assert result.status == scenario["expected"]["status"]
    assert categories
    assert all(item["primary_category"] == scenario["expected"]["projection_category"] for item in categories)

