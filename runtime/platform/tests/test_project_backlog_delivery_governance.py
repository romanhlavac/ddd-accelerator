import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP = ROOT / "config/governance/github-bootstrap.json"
POLICY = ROOT / "config/governance/backlog-policy.yaml"
RECONCILER = ROOT / "scripts/platform/Reconcile-DDDAProjectBacklog.py"
RECONCILER_CORE = ROOT / "scripts/platform/Reconcile-DDDAProjectBacklogCore.py"
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
        "DELIVERY_STATUS_MISMATCH",
        "DELIVERY_HAS_PLANNING_ITEM_TYPE",
        "PRESENTATION_WP_MISMATCH",
        '"remaining_count": 0',
        'REPORT_DIR = Path(".reports/cr-delivery-audit-v6")',
        "active_dependency_projection",
        "CLOSED_ITEM_ACTIVE_BLOCKER",
        "CLOSED_ITEM_BLOCKED_FLAG",
        "TERMINAL_STATUS_MISMATCH",
        "PLANNING_STALE_BLOCKED_STATUS",
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
    assert 'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"' in text
    assert "Reconcile-DDDAProjectBacklogCore.py" in text
    assert "test_project_backlog_delivery_governance.py" in text
    assert ".reports/cr-delivery-audit-v6/audit.json" in text
    assert "remaining_count" in text
    assert "ddda-project-backlog-delivery-audit-v6-${{ github.sha }}" in text
