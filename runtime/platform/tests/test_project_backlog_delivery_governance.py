import json

import pytest
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP = ROOT / "config/governance/github-bootstrap.json"
POLICY = ROOT / "config/governance/backlog-policy.yaml"
RECONCILER = ROOT / "scripts/platform/Reconcile-DDDAProjectBacklog.py"
RECONCILER_CORE = ROOT / "scripts/platform/Reconcile-DDDAProjectBacklogCore.py"
RELEASE_PLANNING = ROOT / "scripts/platform/Reconcile-DDDAReleasePlanning.py"
WORKFLOW = ROOT / ".github/workflows/reconcile-ddda-project-backlog.yml"
CONSISTENCY = ROOT / "docs/governance/wp-backlog-consistency.md"

PROJECT_TITLE = "DDDA Platform Backlog & Delivery"
PLANNING_VIEW = {"name": "Plánování a Backlog", "layout": "table", "filter": "is:issue"}
DELIVERY_VIEW = {"name": "Implementace a Delivery", "layout": "table", "filter": "is:pr is:open"}


def test_bootstrap_has_two_canonical_projections_and_delivery_contract():
    data = json.loads(BOOTSTRAP.read_text(encoding="utf-8-sig"))

    assert data["project_title"] == PROJECT_TITLE
    assert data["views"] == [PLANNING_VIEW, DELIVERY_VIEW]

    delivery = data["delivery_projection"]
    assert delivery["planning_view"] == PLANNING_VIEW
    assert delivery["delivery_view"] == DELIVERY_VIEW
    assert delivery["open_implementation_pr_membership_required"] is True
    assert delivery["primary_change_request_relation"] == "Implements_or_Closes"
    assert delivery["work_package_source"] == "primary_change_request"
    assert delivery["project_item_type_field"] is None
    assert (
        delivery["blocked_source"]
        == "primary_change_request_unresolved_dependency_projection"
    )
    assert delivery["project_blocked_field_is_projection_only"] is True
    assert delivery["fresh_authority_readback_required"] is True

    pull_groups = [g for g in data["item_groups"] if g.get("kind") == "pull"]
    assert pull_groups, "bootstrap must include current legacy/control-plane pull projections"
    for group in pull_groups:
        assert "Item Type" not in group.get("metadata", {})


def test_policy_keeps_planned_prs_out_of_backlog_but_requires_active_delivery_membership():
    text = POLICY.read_text(encoding="utf-8")

    assert "planned_prs_as_backlog_forbidden: true" in text
    assert "active_implementation_prs_project_membership_required: true" in text
    assert "pr_project_item_is_delivery_projection_not_backlog_authority: true" in text
    assert "filter: is:pr is:open" in text
    assert "primary_change_request" in text
    assert "project_item_type_field: unset" in text
    assert "draft_status: In progress" in text
    assert "ready_status: In review" in text
    assert "blocked_override: Blocked" in text
    assert (
        "blocked_source: primary_change_request_unresolved_dependency_projection"
        in text
    )
    assert "project_blocked_field_is_projection_only: true" in text
    assert "fresh_authority_readback_required: true" in text


def test_reconciler_enforces_delivery_membership_mapping_and_readback():
    text = (
        RECONCILER_CORE.read_text(encoding="utf-8")
        + "\n"
        + RECONCILER.read_text(encoding="utf-8")
    )

    required_fragments = [
        'PROJECT_TITLE = "DDDA Platform Backlog & Delivery"',
        'PLANNING_VIEW = "Plánování a Backlog"',
        'DELIVERY_VIEW = "Implementace a Delivery"',
        'LEGACY_PR_WP = {8: "WP-08"}',
        '"is:pr is:open"',
        "MISSING_DELIVERY_PROJECT_ITEM",
        "DELIVERY_WORK_PACKAGE_MISMATCH",
        "DELIVERY_BLOCKED_FLAG_MISMATCH",
        "DELIVERY_STATUS_MISMATCH",
        "DELIVERY_AUTHORITY_CHANGED_DURING_RECONCILIATION",
        "SET_DELIVERY_BLOCKED",
        "DELIVERY_HAS_PLANNING_ITEM_TYPE",
        "DELIVERY_BLOCKED_FLAG_MISMATCH",
        "DELIVERY_AUTHORITY_CHANGED_DURING_RECONCILIATION",
        "PRESENTATION_WP_MISMATCH",
        '"remaining_count": 0',
        'REPORT_DIR = Path(".reports/cr-delivery-audit-v6")',
        "active_dependency_projection",
        "CLOSED_ITEM_ACTIVE_BLOCKER",
        "CLOSED_ITEM_BLOCKED_FLAG",
        "TERMINAL_STATUS_MISMATCH",
        "PLANNING_STALE_BLOCKED_STATUS",
        "core.reconcile_delivery = reconcile_delivery",
        "core.verify_delivery = verify_delivery",
    ]
    for fragment in required_fragments:
        assert fragment in text, fragment


def test_active_dependency_projection_materializes_only_unresolved_edges():
    ns = runpy.run_path(
        str(RECONCILER),
        run_name="ddda_project_backlog_reconciler_contract_test",
    )
    project = ns["active_dependency_projection"]

    expected = {
        9: "WP-08",
        10: "WP-08",
        11: "WP-08",
        12: "WP-08",
        13: "WP-08",
        14: "WP-08",
    }
    dependencies = {
        9: {10},
        10: {11},
        11: {12},
        12: {14},
        14: {13},
    }
    details = {
        9: {"state": "open"},
        10: {"state": "closed", "state_reason": "completed"},
        11: {"state": "closed", "state_reason": "completed"},
        12: {"state": "open"},
        13: {"state": "closed", "state_reason": "completed"},
        14: {"state": "open"},
    }

    assert project(expected, dependencies, details) == {
        9: set(),
        10: set(),
        11: set(),
        12: {14},
        13: set(),
        14: set(),
    }


def test_active_dependency_projection_covers_all_governed_items_and_rejects_unknown_endpoints():
    ns = runpy.run_path(
        str(RECONCILER),
        run_name="ddda_project_backlog_reconciler_contract_test_2",
    )
    project = ns["active_dependency_projection"]

    expected = {1: "WP-08", 2: "WP-08"}
    details = {
        1: {"state": "open"},
        2: {"state": "open"},
    }
    assert project(expected, {}, details) == {1: set(), 2: set()}

    try:
        project(expected, {1: {99}}, details)
    except RuntimeError as exc:
        assert "outside governed Change Request set" in str(exc)
    else:
        raise AssertionError("unknown dependency endpoint must fail closed")


def test_project_view_creation_uses_supported_graphql_contract():
    text = RECONCILER_CORE.read_text(encoding="utf-8")

    unsupported = (
        'createProjectV2View(input:{projectId:$projectId,name:$name,'
        'layout:TABLE_LAYOUT,filter:$filter})'
    )
    supported_create = (
        'mutation($projectId:ID!,$name:String!){createProjectV2View('
        'input:{projectId:$projectId,name:$name,layout:TABLE_LAYOUT})'
    )
    assert unsupported not in text
    assert supported_create in text
    assert 'return update_view(created["id"], name, filter_value)' in text


def test_consistency_contract_is_fail_closed_for_planning_and_delivery():
    text = CONSISTENCY.read_text(encoding="utf-8")

    for fragment in [
        PROJECT_TITLE,
        "Project planning item",
        "Project delivery item",
        "is:issue",
        "is:pr is:open",
        "MISSING_DELIVERY_PROJECT_ITEM",
        "DELIVERY_HAS_PLANNING_ITEM_TYPE",
        "remaining_mismatches = 0",
        "PR: #8",
        "CLOSED_ITEM_ACTIVE_BLOCKER",
        "CLOSED_ITEM_BLOCKED_FLAG",
        "PLANNING_STALE_BLOCKED_STATUS",
        "unresolved dependency projection",
    ]:
        assert fragment in text, fragment


def test_privileged_workflow_is_manual_exact_sha_and_publishes_v6_audit():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "environment: ddda-backlog-governance" in text
    assert "uses: actions/setup-python@v5" in text
    assert 'python-version: "3.12"' in text
    assert 'python -m pip install --disable-pip-version-check "pytest>=8,<9"' in text
    assert 'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"' in text
    assert "Reconcile-DDDAProjectBacklogCore.py" in text
    assert "test_project_backlog_delivery_governance.py" in text
    assert ".reports/cr-delivery-audit-v6/audit.json" in text
    assert "remaining_count" in text
    assert "ddda-project-backlog-delivery-audit-v6-${{ github.sha }}" in text


def test_release_planning_readback_retries_boundedly_until_consistent():
    ns = runpy.run_path(str(RELEASE_PLANNING))
    results = [
        ([{"result": "stale"}], [{"result": "MILESTONE_MEMBERSHIP_MISMATCH"}]),
        ([{"result": "fresh"}], []),
    ]
    sleeps = []

    def fake_verify(_specs):
        return results.pop(0)

    rows, problems, attempts = ns["verify_eventually"](
        [],
        max_attempts=3,
        delay_seconds=2,
        verify_fn=fake_verify,
        sleep_fn=sleeps.append,
    )

    assert rows == [{"result": "fresh"}]
    assert problems == []
    assert attempts == 2
    assert sleeps == [2]

    exhausted_sleeps = []
    rows, problems, attempts = ns["verify_eventually"](
        [],
        max_attempts=2,
        delay_seconds=2,
        verify_fn=lambda _specs: (
            [{"result": "stale"}],
            [{"result": "MILESTONE_MEMBERSHIP_MISMATCH"}],
        ),
        sleep_fn=exhausted_sleeps.append,
    )

    assert rows == [{"result": "stale"}]
    assert problems == [{"result": "MILESTONE_MEMBERSHIP_MISMATCH"}]
    assert attempts == 2
    assert exhausted_sleeps == [2]



def test_release_train_milestone_and_project_target_contract():
    cfg = json.loads((ROOT / "config/governance/github-bootstrap.json").read_text(encoding="utf-8-sig"))
    specs = {x["title"]: x for x in cfg["milestones"]}
    expected = {
        "DDDA 0.1.0": [10, 11, 13, 14],
        "DDDA 0.1.1": [9, 12, 67, 68, 70, 96, 98],
        "DDDA 0.1.2": [16, 65, 69, 73, 85, 94],
        "DDDA 0.2.0": [34, 35, 48, 52, 66],
        "DDDA 0.3.0": [27, 28, 29, 30, 31, 32, 33, 47, 62, 46],
        "DDDA 0.3.1": [53, 54, 55, 56, 57],
        "DDDA 0.4.0": [21, 22, 23, 24, 25, 50, 26, 51],
        "DDDA 0.5.0": [36, 37, 38, 39, 40, 41],
    }
    assert set(specs) == set(expected)
    assert specs["DDDA 0.1.0"]["state"] == "closed"
    assert specs["DDDA 0.1.0"]["issues"] == [10, 11, 13, 14]
    assert specs["DDDA 0.1.0"]["pulls"] == [8]
    for title, issues in expected.items():
        assert specs[title]["issues"] == issues
        if title != "DDDA 0.1.0":
            assert specs[title]["state"] == "open"
            assert specs[title]["pulls"] == []

    meta = {}
    for group in cfg["item_groups"]:
        if group.get("kind") != "issue":
            continue
        for number in group.get("numbers", []):
            meta[int(number)] = group.get("metadata", {})
    assert meta[44]["Item Type"] == "Defect"
    assert meta[44]["Status"] == "Ready"
    assert meta[67]["Item Type"] == "Defect" and meta[67]["Target Release"] == "0.1.1"
    assert meta[68]["Item Type"] == "Defect" and meta[68]["Target Release"] == "0.1.1"
    assert meta[70]["Item Type"] == "Change Request" and meta[70]["Target Release"] == "0.1.1"
    assert meta[96]["Item Type"] == "Defect"
    assert meta[96]["Work Package"] == "Other"
    assert meta[96]["Target Release"] == "0.1.1"
    assert meta[98]["Item Type"] == "Defect"
    assert meta[98]["Work Package"] == "Other"
    for title, issues in expected.items():
        if title == "DDDA 0.1.0":
            continue
        version = title.removeprefix("DDDA ")
        for issue in issues:
            assert meta[issue]["Target Release"] == version
    assert meta[44]["Target Release"] == "TBD"
    assert meta[88]["Target Release"] == "TBD"
    assert meta[98]["Target Release"] == "0.1.1"
    assert meta[98]["Priority"] == "P0"
    assert meta[98]["Platform Area"] == "RELEASE"
    assert meta[98]["Impact"] == "HIGH"
    dependencies = {entry["blocked"]: entry["blocked_by"] for entry in cfg["dependencies"]}
    assert dependencies[75] == [96, 98]
    assert "unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98]" in POLICY.read_text(encoding="utf-8")
    assert meta[75]["Item Type"] == "Enabler"
    assert meta[85]["Work Package"] == "Other"
    assert meta[85]["Target Release"] == "0.1.2"
    assert meta[85]["Status"] == "Backlog"
    assert meta[94]["Item Type"] == "Defect"
    assert meta[94]["Work Package"] == "Other"
    assert meta[94]["Target Release"] == "0.1.2"
    assert meta[88]["Item Type"] == "Enabler"
    assert meta[88]["Work Package"] == "Other"
    assert meta[88]["Target Release"] == "TBD"
    assert meta[88]["Status"] == "Backlog"


def test_governance_projection_is_transactional_and_fail_closed():
    consistency = (ROOT / "docs/governance/wp-backlog-consistency.md").read_text(encoding="utf-8")
    skill = (ROOT / "knowledge/ddda-platform-development-skill.md").read_text(encoding="utf-8-sig")
    assert "Issue/PR + Project projection je jeden celek" in consistency
    assert "BLOCKED / GOVERNANCE_INCOMPLETE" in consistency
    assert "remaining_mismatches = 0" in consistency
    assert "Backlog / Project transactional completion" in skill
    assert "remaining_mismatches = 0" in skill


def test_reconciler_supports_non_cr_planning_items_and_target_correction():
    core = (ROOT / "scripts/platform/Reconcile-DDDAProjectBacklogCore.py").read_text(encoding="utf-8-sig")
    release = (ROOT / "scripts/platform/Reconcile-DDDAReleasePlanning.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/reconcile-ddda-project-backlog.yml").read_text(encoding="utf-8-sig")
    assert '{"Change Request", "Defect", "Risk", "Enabler", "GAP"}' in core
    assert 'current.get("Target Release") != target' in core
    assert 'TARGET_RELEASE_MISMATCH' in core
    assert 'REMOVE_FROM_MILESTONE' in release
    assert 'MILESTONE_MEMBERSHIP_MISMATCH' in release
    assert 'Reconcile-DDDAReleasePlanning.py --mode reconcile' in workflow
    assert 'release_planning[\'remaining_count\'] == 0' in workflow

def _delivery_contract():
    ns = runpy.run_path(
        str(RECONCILER),
        run_name="ddda_delivery_projection_contract_test",
    )
    return (
        ns["derive_delivery_projection"],
        ns["delivery_projection_repairs"],
        ns["delivery_projection_mismatches"],
        ns["delivery_authority_signature"],
        ns["core"],
    )


def test_delivery_reconcile_clears_historical_stale_blocked_for_draft_pr():
    derive, repairs, mismatches, _, _ = _delivery_contract()
    authority = {
        101: {
            "primary_cr": 16,
            "wp": "Other",
            "pr": {"number": 101, "draft": True, "head": {"sha": "a" * 40}},
        }
    }
    wanted = derive(authority, {16: set()})[101]
    stale = {"Blocked": "Yes", "Status": "Blocked"}

    assert wanted == {
        "Blocked": "No",
        "Status": "In progress",
        "authoritative_blockers": [],
    }
    assert repairs(stale, wanted) == [
        ("Blocked", "SET_DELIVERY_BLOCKED", "No"),
        ("Status", "SET_DELIVERY_STATUS", "In progress"),
    ]
    assert mismatches(stale, wanted) == [
        "DELIVERY_BLOCKED_FLAG_MISMATCH",
        "DELIVERY_STATUS_MISMATCH",
    ]


def test_delivery_projection_uses_in_review_for_ready_unblocked_pr():
    derive, _, _, _, _ = _delivery_contract()
    authority = {
        102: {
            "primary_cr": 16,
            "wp": "Other",
            "pr": {"number": 102, "draft": False},
        }
    }
    assert derive(authority, {16: set()})[102]["Blocked"] == "No"
    assert derive(authority, {16: set()})[102]["Status"] == "In review"


def test_delivery_projection_uses_primary_cr_unresolved_blockers():
    derive, _, _, _, _ = _delivery_contract()
    authority = {
        103: {
            "primary_cr": 16,
            "wp": "Other",
            "pr": {"number": 103, "draft": True},
        }
    }
    wanted = derive(authority, {16: {44}})[103]
    assert wanted["Blocked"] == "Yes"
    assert wanted["Status"] == "Blocked"
    assert wanted["authoritative_blockers"] == [44]


def test_delivery_projection_unblocks_when_last_authoritative_blocker_closes():
    derive, _, _, _, _ = _delivery_contract()
    authority = {
        104: {
            "primary_cr": 16,
            "wp": "Other",
            "pr": {"number": 104, "draft": False},
        }
    }
    assert derive(authority, {16: {44}})[104]["Status"] == "Blocked"
    after_close = derive(authority, {16: set()})[104]
    assert after_close["Blocked"] == "No"
    assert after_close["Status"] == "In review"


def test_stale_project_blocked_pair_cannot_pass_verification():
    derive, _, mismatches, _, _ = _delivery_contract()
    authority = {
        105: {
            "primary_cr": 16,
            "wp": "Other",
            "pr": {"number": 105, "draft": True},
        }
    }
    wanted = derive(authority, {16: set()})[105]
    assert mismatches(
        {"Blocked": "Yes", "Status": "Blocked"}, wanted
    ) == [
        "DELIVERY_BLOCKED_FLAG_MISMATCH",
        "DELIVERY_STATUS_MISMATCH",
    ]


def test_delivery_projection_second_reconcile_is_semantically_idempotent():
    derive, repairs, _, _, _ = _delivery_contract()
    authority = {
        106: {
            "primary_cr": 16,
            "wp": "Other",
            "pr": {"number": 106, "draft": True},
        }
    }
    wanted = derive(authority, {16: set()})[106]
    assert repairs(wanted, wanted) == []


def test_delivery_authority_fails_closed_for_missing_or_ambiguous_primary_cr():
    _, _, _, _, core_module = _delivery_contract()
    expected = {16: "Other"}

    with pytest.raises(RuntimeError, match="exactly one primary"):
        core_module.delivery_authority(
            [{"number": 107, "title": "fix", "body": "", "draft": True}],
            expected,
        )

    with pytest.raises(RuntimeError, match="exactly one primary"):
        core_module.delivery_authority(
            [
                {
                    "number": 108,
                    "title": "fix",
                    "body": "Implements #16\nCloses #88",
                    "draft": True,
                }
            ],
            expected,
        )


def test_delivery_authority_signature_detects_draft_or_head_staleness():
    _, _, _, signature, _ = _delivery_contract()
    initial = {
        109: {
            "primary_cr": 16,
            "wp": "Other",
            "pr": {"number": 109, "draft": True, "head": {"sha": "a" * 40}},
        }
    }
    changed = {
        109: {
            "primary_cr": 16,
            "wp": "Other",
            "pr": {"number": 109, "draft": False, "head": {"sha": "b" * 40}},
        }
    }
    assert signature(initial) != signature(changed)


def test_delivery_runtime_does_not_treat_project_blocked_as_authority():
    wrapper = RECONCILER.read_text(encoding="utf-8-sig")
    core_text = RECONCILER_CORE.read_text(encoding="utf-8-sig")

    assert 'blocked = current.get("Blocked") == "Yes"' not in wrapper
    assert 'blocked = current.get("Blocked") == "Yes"' not in core_text
    assert "derive_delivery_projection" in wrapper
    assert "active_dependency_projection" in wrapper
