from copy import deepcopy

from runtime.platform.release_governance import (
    evaluate_merge_release_eligibility,
    evaluate_release_scope,
    validate_hrdr_shape,
)

REPO = "romanhlavac/ddd-accelerator"
PR = 71
SHA = "a" * 40
PACKAGE = "b" * 64
VERSION = "0.1.1"


def hrdr():
    return {
        "schema_version": 1,
        "repository": REPO,
        "pr": PR,
        "branch": "feature/9-release-scope-gate",
        "source_sha": SHA,
        "candidate_package_sha256": PACKAGE,
        "version": VERSION,
        "reviewer": "romanhlavac",
        "decision_owner": "romanhlavac",
        "decision": "go_with_accepted_risks",
        "decided_at": "2026-08-18T12:00:00Z",
        "scope_issues": [9, 12, 67, 68],
        "findings": [{"id": "F-1", "severity": "amber", "summary": "deferred"}],
        "accepted_risks": [
            {
                "risk_id": "R-66",
                "issue": 66,
                "owner": "romanhlavac",
                "rationale": "product depth deferred",
                "target_horizon": "TBD",
            }
        ],
        "evidence": {},
    }


def snapshot():
    return {
        "current_pr_head": SHA,
        "milestone_title": "DDDA 0.1.1",
        "milestone_issues": [9, 12, 67, 68],
        "issue_states": {"9": "closed", "12": "closed", "67": "closed", "68": "closed"},
        "blockers": {"9": [], "12": [], "67": [], "68": []},
        "project_rows": {
            "9": {"Status": "Done", "Blocked": "No"},
            "12": {"Status": "Done", "Blocked": "No"},
            "67": {"Status": "Done", "Blocked": "No"},
            "68": {"Status": "Done", "Blocked": "No"},
        },
        "risk_issue_states": {"66": "open"},
        "risk_issue_assignees": {"66": ["romanhlavac"]},
        "risk_issue_horizons": {"66": "TBD"},
        "project": {
            "title": "DDDA Platform Backlog & Delivery",
            "planning_view_filter": "is:issue",
            "delivery_view_filter": "is:pr is:open",
        },
        "physical_scope": {
            "previous_release_tag": "v0.1.0",
            "previous_release_sha": "c" * 40,
            "release_source_sha": SHA,
            "compare_status": "ahead",
            "unmapped_commit_shas": [],
            "shipping_prs": [
                {
                    "number": number,
                    "merged": True,
                    "primary_crs": [cr],
                    "milestone": "DDDA 0.1.1",
                    "target_release": "0.1.1",
                }
                for number, cr in [(71, 9), (72, 12), (73, 67), (74, 68)]
            ],
        },
    }


def evaluate(record=None, live=None):
    return evaluate_release_scope(
        record or hrdr(),
        live or snapshot(),
        expected_repository=REPO,
        expected_pr=PR,
        expected_source_sha=SHA,
        expected_package_sha256=PACKAGE,
        expected_version=VERSION,
    )


def test_valid_release_scope_passes():
    result = evaluate()
    assert result.status == "PASS"
    assert result.side_effects_allowed is True


def test_open_current_release_issue_fails_before_side_effects():
    live = snapshot()
    live["issue_states"]["12"] = "open"
    result = evaluate(live=live)
    assert result.status == "FAIL"
    assert "SCOPE_ITEM_NOT_TERMINAL:#12" in result.failures
    assert result.side_effects_allowed is False


def test_unresolved_blocker_fails_before_side_effects():
    live = snapshot()
    live["blockers"]["12"] = [14]
    result = evaluate(live=live)
    assert result.status == "FAIL"
    assert "SCOPE_ITEM_ACTIVE_BLOCKER:#12" in result.failures
    assert result.side_effects_allowed is False


def test_milestone_scope_drift_fails_before_side_effects():
    live = snapshot()
    live["milestone_issues"] = [9, 12, 67]
    result = evaluate(live=live)
    assert result.status == "FAIL"
    assert "MILESTONE_SCOPE_MISMATCH" in result.failures
    assert result.side_effects_allowed is False


def test_project_projection_drift_fails():
    live = snapshot()
    live["project_rows"]["12"]["Status"] = "Blocked"
    result = evaluate(live=live)
    assert result.status == "FAIL"
    assert "SCOPE_ITEM_PROJECT_STATUS:#12" in result.failures


def test_changed_sha_invalidates_human_decision():
    result = evaluate_release_scope(
        hrdr(),
        snapshot(),
        expected_repository=REPO,
        expected_pr=PR,
        expected_source_sha="c" * 40,
        expected_package_sha256=PACKAGE,
        expected_version=VERSION,
    )
    assert result.status == "FAIL"
    assert "IDENTITY_SOURCE_SHA_MISMATCH" in result.failures


def test_red_finding_blocks_release():
    record = hrdr()
    record["findings"].append({"id": "F-RED", "severity": "red", "summary": "blocker"})
    result = evaluate(record=record)
    assert result.status == "FAIL"
    assert "RED_FINDING_PRESENT" in result.failures


def test_pending_human_decision_blocks_release():
    record = hrdr()
    record["decision"] = "pending"
    record["decided_at"] = None
    result = evaluate(record=record)
    assert result.status == "FAIL"
    assert "HUMAN_RELEASE_DECISION_NOT_POSITIVE" in result.failures


def test_deferred_risk_must_be_outside_milestone():
    live = snapshot()
    live["milestone_issues"].append(66)
    record = hrdr()
    record["scope_issues"].append(66)
    live["issue_states"]["66"] = "closed"
    live["blockers"]["66"] = []
    live["project_rows"]["66"] = {"Status": "Done", "Blocked": "No"}
    result = evaluate(record=record, live=live)
    assert result.status == "FAIL"
    assert "DEFERRED_RISK_STILL_IN_MILESTONE:#66" in result.failures


def test_deferred_risk_owner_must_match_live_assignee():
    live = snapshot()
    live["risk_issue_assignees"]["66"] = []
    result = evaluate(live=live)
    assert result.status == "FAIL"
    assert "DEFERRED_RISK_OWNER_MISMATCH:#66" in result.failures


def test_go_cannot_silently_accept_risks():
    record = hrdr()
    record["decision"] = "go"
    failures = validate_hrdr_shape(record)
    assert "HRDR_GO_HAS_ACCEPTED_RISKS" in failures


def test_identity_contract_rejects_package_drift():
    result = evaluate_release_scope(
        hrdr(),
        snapshot(),
        expected_repository=REPO,
        expected_pr=PR,
        expected_source_sha=SHA,
        expected_package_sha256="d" * 64,
        expected_version=VERSION,
    )
    assert result.status == "FAIL"
    assert "IDENTITY_PACKAGE_SHA256_MISMATCH" in result.failures


def test_physical_scope_rejects_later_release_shipping_pr_and_requires_human_recovery():
    live = snapshot()
    live["physical_scope"]["shipping_prs"].append(
        {
            "number": 92,
            "merged": True,
            "primary_crs": [88],
            "milestone": None,
            "target_release": "TBD",
        }
    )
    result = evaluate(live=live)
    assert result.status == "FAIL"
    assert "PHYSICAL_SCOPE_OUT_OF_SCOPE_PRIMARY_CR:PR#92:#88" in result.failures
    assert "RECOVERY_DECISION_REQUIRED" in result.failures
    assert result.side_effects_allowed is False


def test_physical_scope_rejects_unmapped_commit_and_ambiguous_primary_cr():
    live = snapshot()
    live["physical_scope"]["unmapped_commit_shas"] = ["d" * 40]
    live["physical_scope"]["shipping_prs"][0]["primary_crs"] = [9, 12]
    result = evaluate(live=live)
    assert "PHYSICAL_SCOPE_UNMAPPED_COMMIT:" + "d" * 40 in result.failures
    assert "PHYSICAL_SCOPE_PRIMARY_CR_AMBIGUOUS:PR#71" in result.failures


def test_physical_scope_rejects_non_ancestor_or_wrong_source_evidence():
    live = snapshot()
    live["physical_scope"]["compare_status"] = "diverged"
    live["physical_scope"]["release_source_sha"] = "e" * 40
    result = evaluate(live=live)
    assert "PHYSICAL_SCOPE_ANCESTRY_INVALID" in result.failures
    assert "PHYSICAL_SCOPE_SOURCE_SHA_MISMATCH" in result.failures


def test_physical_scope_rejects_declared_change_missing_from_source():
    live = snapshot()
    live["physical_scope"]["shipping_prs"] = [
        row for row in live["physical_scope"]["shipping_prs"] if row["primary_crs"] != [68]
    ]
    result = evaluate(live=live)
    assert "PHYSICAL_SCOPE_DECLARED_CR_NOT_SHIPPED:#68" in result.failures


def test_merge_eligibility_allows_only_active_train_authority():
    allowed = {
        "active_release": {"version": "0.1.1"},
        "primary_crs": [96],
        "primary_cr": {"milestone": "DDDA 0.1.1", "target_release": "0.1.1"},
    }
    assert evaluate_merge_release_eligibility(allowed) == []

    blocked = deepcopy(allowed)
    blocked["primary_cr"] = {"milestone": None, "target_release": "TBD"}
    assert evaluate_merge_release_eligibility(blocked) == [
        "MERGE_ELIGIBILITY_OUTSIDE_ACTIVE_RELEASE:#96",
        "MERGE_ELIGIBILITY_TARGET_RELEASE_MISMATCH:#96",
    ]
