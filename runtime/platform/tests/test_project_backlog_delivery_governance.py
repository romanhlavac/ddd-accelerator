import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP = ROOT / "config/governance/github-bootstrap.json"
POLICY = ROOT / "config/governance/backlog-policy.yaml"
RECONCILER = ROOT / "scripts/platform/Reconcile-DDDAProjectBacklog.py"
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
    text = RECONCILER.read_text(encoding="utf-8")

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
    ]
    for fragment in required_fragments:
        assert fragment in text, fragment


def test_project_view_creation_uses_supported_graphql_contract():
    text = RECONCILER.read_text(encoding="utf-8")

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
    ]:
        assert fragment in text, fragment


def test_privileged_workflow_is_manual_exact_sha_and_publishes_v6_audit():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "environment: ddda-backlog-governance" in text
    assert 'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"' in text
    assert "test_project_backlog_delivery_governance.py" in text
    assert ".reports/cr-delivery-audit-v6/audit.json" in text
    assert "remaining_count" in text
    assert "ddda-project-backlog-delivery-audit-v6-${{ github.sha }}" in text
