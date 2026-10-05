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


def test_bootstrap_has_planning_active_delivery_and_history_projections():
    data = json.loads(BOOTSTRAP.read_text(encoding="utf-8-sig"))

    assert data["project_title"] == PROJECT_TITLE
    assert data["views"] == [PLANNING_VIEW, DELIVERY_VIEW, {
        "name": "Release & Delivery History", "layout": "table", "filter": "is:pr is:merged"
    }]
    assert data["history_projection"]["project_status_is_projection_only"] is True
    assert data["history_projection"]["multi_pr_release_supported"] is True

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
        "ADD_PROJECT_FIELD_OPTIONS",
        "MISSING_PROJECT_FIELD_OPTIONS",
        '"remaining_count": len(problems)',
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


def test_reconciler_materializes_missing_configured_project_options_and_normalizes_to_versioned_contract():
    ns = runpy.run_path(
        str(RECONCILER_CORE),
        run_name="ddda_project_option_reconcile_contract_test",
    )
    calls = []

    def fake_gql(query, variables=None):
        calls.append((query, variables or {}))
        return {
            "data": {
                "updateProjectV2Field": {
                    "projectV2Field": {"id": "FIELD-1", "name": "Work Package"}
                }
            }
        }

    ns["reconcile_configured_project_options"].__globals__["gql"] = fake_gql
    fields = {
        "Work Package": {
            "id": "FIELD-1",
            "name": "Work Package",
            "dataType": "SINGLE_SELECT",
            "options": [
                {"id": "OPT-08", "name": "WP-08", "color": "BLUE", "description": "foundation"},
                {"id": "OPT-LEGACY", "name": "Legacy", "color": "GRAY", "description": "preserve"},
            ],
        }
    }
    cfg = {
        "fields": [
            {
                "name": "Work Package",
                "type": "SINGLE_SELECT",
                "options": [
                    {"name": "WP-08", "color": "BLUE", "description": "foundation"},
                    {"name": "WP-14", "color": "GREEN", "description": "workbench"},
                ],
            }
        ]
    }
    repairs = []

    changed = ns["reconcile_configured_project_options"](cfg, 7, fields, repairs)

    assert changed is True
    assert len(calls) == 1
    mutation, variables = calls[0]
    assert "updateProjectV2Field" in mutation
    assert variables["fieldId"] == "FIELD-1"
    assert [option["name"] for option in variables["options"]] == ["WP-08", "WP-14"]
    assert variables["options"][0]["id"] == "OPT-08"
    assert "id" not in variables["options"][1]
    assert repairs == [
        {
            "project": 7,
            "action": "ADD_PROJECT_FIELD_OPTIONS",
            "field": "Work Package",
            "value": ["WP-14"],
        }
    ]


def test_reconciler_does_not_mutate_project_options_when_contract_is_already_satisfied():
    ns = runpy.run_path(
        str(RECONCILER_CORE),
        run_name="ddda_project_option_reconcile_noop_contract_test",
    )
    calls = []
    ns["reconcile_configured_project_options"].__globals__["gql"] = lambda *args, **kwargs: calls.append((args, kwargs))
    fields = {
        "Work Package": {
            "id": "FIELD-1",
            "options": [
                {"id": "OPT-14", "name": "WP-14", "color": "GREEN", "description": "workbench"}
            ],
        }
    }
    cfg = {
        "fields": [
            {
                "name": "Work Package",
                "type": "SINGLE_SELECT",
                "options": [
                    {"name": "WP-14", "color": "GREEN", "description": "workbench"}
                ],
            }
        ]
    }
    repairs = []

    changed = ns["reconcile_configured_project_options"](cfg, 7, fields, repairs)

    assert changed is False
    assert calls == []
    assert repairs == []


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
        "DDDA 0.1.2": [16, 65, 69, 73, 85, 94, 113, 125, 131, 132, 171, 172, 173, 174],
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
        if title in {"DDDA 0.1.0", "DDDA 0.1.1"}:
            assert specs[title]["state"] == "closed"
        else:
            assert specs[title]["state"] == "open"
        if title != "DDDA 0.1.0":
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
    assert dependencies[172] == [171]
    assert dependencies[173] == [171]
    assert dependencies[174] == [172, 173]
    assert dependencies[69] == [173]
    assert dependencies[73] == [171, 173]
    assert dependencies[85] == [174]
    assert dependencies[94] == [173]
    assert dependencies[113] == [174]
    assert dependencies[131] == [171, 172]
    assert dependencies[132] == [65, 131]
    assert "unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113, 125, 131, 132, 155, 171, 172, 173, 174]" in POLICY.read_text(encoding="utf-8")
    assert meta[75]["Item Type"] == "Enabler"
    assert meta[85]["Work Package"] == "Other"
    assert meta[85]["Target Release"] == "0.1.2"
    assert meta[85]["Status"] == "Backlog"
    assert meta[94]["Item Type"] == "Defect"
    assert meta[94]["Work Package"] == "Other"
    assert meta[94]["Target Release"] == "0.1.2"
    assert meta[113]["Item Type"] == "Change Request"
    assert meta[113]["Work Package"] == "Other"
    assert meta[113]["Priority"] == "P2"
    assert meta[113]["Platform Area"] == "DOC"
    assert meta[113]["Impact"] == "LOW"
    assert meta[113]["Target Release"] == "0.1.2"
    assert meta[113]["Status"] == "Backlog"
    assert meta[113]["Blocked"] == "Yes"
    assert meta[113]["Human Review"] == "Pending"
    assert meta[113]["Outcome summary"] == (
        "Expose the canonical DDDA operating model in entry-point documentation: "
        "Work as development/governance control plane, GitHub as canonical system of record, "
        "GitHub Actions as authoritative technical execution plane, and Cursor as the current "
        "reference project runtime."
    )
    assert meta[125]["Item Type"] == "Change Request"
    assert meta[125]["Work Package"] == "Other"
    assert meta[125]["Priority"] == "P1"
    assert meta[125]["Platform Area"] == "RELEASE"
    assert meta[125]["Impact"] == "HIGH"
    assert meta[125]["Target Release"] == "0.1.2"
    assert meta[125]["Status"] == "Backlog"
    assert meta[125]["Blocked"] == "No"
    assert meta[125]["Human Review"] == "Pending"
    assert meta[125]["Outcome summary"] == (
        "Backfill the historical DDDA 0.1.0 GitHub Release from the original validated "
        "canonical package and portable evidence without changing source, tag or historical "
        "release decision."
    )
    assert meta[131]["Item Type"] == "Change Request"
    assert meta[131]["Work Package"] == "Other"
    assert meta[131]["Priority"] == "P1"
    assert meta[131]["Platform Area"] == "RELEASE"
    assert meta[131]["Impact"] == "HIGH"
    assert meta[131]["Target Release"] == "0.1.2"
    assert meta[131]["Status"] == "Backlog"
    assert meta[131]["Blocked"] == "Yes"
    assert meta[131]["Human Review"] == "Pending"
    assert meta[131]["Outcome summary"] == (
        "Make every DDDA release-candidate PR human-recognizable and machine-verifiable "
        "through consistent title, labels, branch and versioned body marker, with explicit "
        "normal versus controlled-recovery semantics."
    )
    assert meta[132]["Item Type"] == "Change Request"
    assert meta[132]["Work Package"] == "Other"
    assert meta[132]["Priority"] == "P2"
    assert meta[132]["Platform Area"] == "SECURITY-GOVERNANCE"
    assert meta[132]["Impact"] == "MEDIUM"
    assert meta[132]["Target Release"] == "0.1.2"
    assert meta[132]["Status"] == "Backlog"
    assert meta[132]["Blocked"] == "Yes"
    assert meta[132]["Human Review"] == "Pending"
    assert meta[132]["Outcome summary"] == (
        "Define one canonical naming contract for DDDA GitHub Issues, PRs, branches, labels, "
        "markers, milestones, tags, Releases, workflows and evidence artifacts while "
        "preserving #65 and #131 ownership boundaries."
    )
    assert meta[16]["Priority"] == "P0"
    assert meta[65]["Priority"] == "P1" and meta[65]["Blocked"] == "No"
    assert meta[69]["Priority"] == "P2" and meta[69]["Blocked"] == "Yes"
    assert meta[73]["Priority"] == "P1" and meta[73]["Blocked"] == "Yes"
    assert meta[85]["Priority"] == "P2" and meta[85]["Blocked"] == "Yes"
    assert meta[94]["Priority"] == "P1" and meta[94]["Blocked"] == "Yes"
    assert meta[171]["Priority"] == "P0" and meta[171]["Blocked"] == "No"
    assert meta[172]["Priority"] == "P1" and meta[172]["Blocked"] == "Yes"
    assert meta[173]["Priority"] == "P1" and meta[173]["Blocked"] == "Yes"
    assert meta[174]["Priority"] == "P1" and meta[174]["Blocked"] == "Yes"
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


def test_pr_title_prefix_is_presentation_and_does_not_block_delivery_projection():
    _, _, _, _, core_module = _delivery_contract()
    authority = core_module.delivery_authority(
        [{"number": 113, "title": "[WP-08] implementation", "body": "Implements #16", "draft": True}],
        {16: "Other"},
    )
    assert authority[113]["wp"] == "Other"
    assert authority[113]["presentation_mismatches"] == ["PRESENTATION_WP_MISMATCH:PR#113"]

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


def test_wp14_governance_contract_is_canonical_and_milestone_neutral():
    cfg=json.loads(BOOTSTRAP.read_text(encoding="utf-8-sig"))
    wp=next(x for x in cfg["fields"] if x["name"]=="Work Package")
    assert [x["name"] for x in wp["options"]].count("WP-14")==1
    h={int(x["parent"]):x["children"] for x in cfg["hierarchy"]}; assert h[148]==[149,150,151,152,153,154]
    deps={int(x["blocked"]):x["blocked_by"] for x in cfg["dependencies"]}; assert deps[150]==[149] and deps[153]==[149,150,151,152] and deps[154]==[150,153]
    meta={int(n):g.get("metadata",{}) for g in cfg["item_groups"] if g.get("kind")=="issue" for n in g.get("numbers",[])}
    assert set(range(148,156)).issubset(meta) and all("Priority" not in meta[n] for n in range(148,156))
    assert all(set(range(148,156)).isdisjoint(set(m.get("issues",[]))) for m in cfg["milestones"])
    m=next(x for x in cfg["milestones"] if x["title"]=="DDDA 0.1.1"); assert m["issues"]==[9,12,67,68,70,96,98]
    assert "WP-14-multi-model-workbench-git-sync.md" in (ROOT/"docs/roadmap/README.md").read_text(encoding="utf-8")



PLANNING_MATRIX = json.loads((ROOT / "tests/fixtures/governance/scenario-matrix-v2.json").read_text(encoding="utf-8"))
PLANNING_SCENARIOS = [row for row in PLANNING_MATRIX["scenarios"] if row["adapter"] == "planning_projection"]


@pytest.mark.parametrize("scenario", PLANNING_SCENARIOS, ids=lambda row: row["id"])
def test_planning_projection_matrix_uses_the_production_owner(scenario):
    ns = runpy.run_path(str(RECONCILER))
    v = scenario["input"]
    authority = {} if v["draft"] is None else {
        92: {"primary_cr": 88, "wp": "Other", "pr": {"number": 92, "state": "open", "draft": v["draft"]}}
    }
    wanted = ns["derive_planning_projection"]({88: v["issue"]}, {88: set(v["blockers"])}, authority, {88: v["current"]})[88]
    mismatches = ns["planning_projection_mismatches"](v["current"], wanted)
    assert wanted["Status"] == scenario["expected"]["planning_status"]
    assert ("FAIL" if mismatches else "PASS") == scenario["expected"]["status"]
    for code in mismatches:
        assert ns["core"].classify_result(code)[0]["primary_category"] == scenario["expected"]["mismatch_category"]
    repairs = ns["planning_projection_repairs"](v["current"], wanted)
    fixed = dict(v["current"])
    for field, _, value in repairs:
        fixed[field] = value
    assert ns["planning_projection_repairs"](fixed, wanted) == []
    assert ns["planning_projection_mismatches"](fixed, wanted) == []
    if authority and v["issue"]["state"] == "open":
        delivery = ns["derive_delivery_projection"](authority, {88: set(v["blockers"])})[92]
        assert delivery["Status"] == ("Blocked" if v["blockers"] else "In progress" if v["draft"] else "In review")


def _planning_fixture(monkeypatch):
    ns = runpy.run_path(str(RECONCILER))
    gl = ns["verify_planning"].__globals__
    module = ns["core"]
    expected = {88: "Other"}
    details = {88: {"state": "open"}}
    authority = {92: {"primary_cr": 88, "wp": "Other", "pr": {"number": 92, "state": "open", "draft": True, "head": {"sha": "a" * 40}}}}
    item = {"id": "ITEM-88", "values": {"Status": "Backlog", "Blocked": "No"}}
    monkeypatch.setattr(module, "load_contract", lambda: ({}, {}, {}, expected, {}))
    monkeypatch.setattr(module, "content_item_map", lambda *a: {88: item})
    monkeypatch.setattr(module, "values", lambda value: dict(value["values"]))
    monkeypatch.setattr(module, "current_blockers", lambda n: {})
    monkeypatch.setitem(gl, "_live_details", lambda exp: {n: dict(v) for n,v in details.items()})
    monkeypatch.setitem(gl, "_fresh_delivery_authority", lambda exp: authority)
    monkeypatch.setitem(gl, "_base_reconcile_planning", lambda *a: None)
    monkeypatch.setitem(gl, "_base_verify_planning", lambda *a: ([{"issue":88,"fields":dict(item["values"]),"result":"PASS"}], []))
    mutations = []
    def select(project, fields, item_id, field, value):
        mutations.append((field, value))
        item["values"][field] = value
    monkeypatch.setattr(module, "set_select", select)
    return ns, expected, details, authority, item, mutations


def test_historical_88_92_verify_reconcile_readback_and_second_reconcile(monkeypatch):
    ns, expected, details, authority, item, mutations = _planning_fixture(monkeypatch)
    rows, problems = ns["verify_planning"]({}, expected, {}, 7)
    assert mutations == []
    assert "PLANNING_LIFECYCLE_STATUS_MISMATCH" in rows[0]["result"]
    assert problems and rows[0]["active_implementation_prs"] == [92]
    repairs = []
    ns["reconcile_planning"]({}, {}, expected, details, 7, "PROJECT", {}, repairs)
    assert item["values"] == {"Status":"In progress","Blocked":"No"}
    assert repairs == [{"issue":88,"action":"SET_PLANNING_STATUS","value":"In progress"}]
    rows, problems = ns["verify_planning"]({}, expected, {}, 7)
    assert problems == [] and rows[0]["result"] == "PASS"
    second = []
    ns["reconcile_planning"]({}, {}, expected, details, 7, "PROJECT", {}, second)
    assert second == [] and len(mutations) == 1


def test_planning_verify_rejects_authority_change_during_readback(monkeypatch):
    ns, expected, details, authority, item, mutations = _planning_fixture(monkeypatch)
    item["values"]["Status"] = "In progress"
    calls = []
    def fresh(exp):
        calls.append(1)
        if len(calls) > 1:
            return {88: {"state":"closed", "state_reason":"completed"}}
        return details
    monkeypatch.setitem(ns["verify_planning"].__globals__, "_live_details", fresh)
    rows, problems = ns["verify_planning"]({}, expected, {}, 7)
    assert problems[-1]["result"] == "PLANNING_AUTHORITY_CHANGED_DURING_RECONCILIATION"
    assert mutations == []


def test_planning_verify_binds_initial_primary_head_and_draft(monkeypatch):
    ns, expected, details, authority, item, mutations = _planning_fixture(monkeypatch)
    from copy import deepcopy
    stale = deepcopy(authority)
    stale[92]["pr"]["head"]["sha"] = "b" * 40
    rows, problems = ns["verify_planning"]({}, expected, {}, 7, authority=stale)
    assert not rows and problems[0]["result"] == "PLANNING_AUTHORITY_CHANGED_DURING_RECONCILIATION"
    assert mutations == []


def test_planning_unknown_primary_cannot_manufacture_implementation_entry():
    ns = runpy.run_path(str(RECONCILER))
    with pytest.raises(RuntimeError, match="outside governed backlog"):
        ns["derive_planning_projection"]({88:{"state":"open"}}, {88:set()}, {92:{"primary_cr":99,"pr":{}}})
    with pytest.raises(RuntimeError, match="no authoritative primary"):
        ns["derive_planning_projection"]({88:{"state":"open"}}, {88:set()}, {92:{"primary_cr":None,"pr":{}}})


def test_core_verify_mode_has_no_mutations_and_publishes_fail_audit(monkeypatch, tmp_path):
    ns = runpy.run_path(str(RECONCILER))
    module = ns["core"]
    monkeypatch.setattr(module, "load_contract", lambda: ({},{},{},{88:"Other"},{}))
    monkeypatch.setattr(module, "discover_cr_numbers", lambda: {88})
    monkeypatch.setattr(module, "discover_open_prs", lambda: [])
    monkeypatch.setattr(module, "delivery_authority", lambda *a: {})
    monkeypatch.setattr(module, "issue", lambda n: {"state":"open"})
    def prohibited(*a, **kw):
        raise AssertionError("verify-only attempted a mutation")
    for name in ["reconcile_hierarchy", "reconcile_dependencies", "reconcile_views", "reconcile_planning", "reconcile_delivery", "set_select", "add_project_item"]:
        monkeypatch.setattr(module, name, prohibited)
    def resolve(repairs, read_only=False):
        assert read_only and repairs == []
        return 7, "PROJECT", {n:{} for n in ["Status","Work Package","Item Type","Target Release","Blocked"]}, []
    monkeypatch.setattr(module, "resolve_project", resolve)
    monkeypatch.setattr(module, "verify_delivery", lambda *a: ([],[]))
    row={"issue":88,"wp":"Other","parent":None,"result":"PLANNING_LIFECYCLE_STATUS_MISMATCH"}
    monkeypatch.setattr(module, "verify_planning", lambda *a, **kw: ([row], [row]))
    monkeypatch.setattr(module, "verify_project_contract", lambda n: ({"views":{"nodes":[]}},[]))
    monkeypatch.setattr(module, "REPORT_DIR", tmp_path)
    monkeypatch.setattr(module, "cmd", lambda *a: "a"*40)
    with pytest.raises(SystemExit) as stop:
        module.main(["--mode","verify"])
    assert stop.value.code == 1
    audit=json.loads((tmp_path/"audit.json").read_text())
    assert audit["mode"] == "verify" and audit["status"] == "FAIL"
    assert audit["repair_count"] == 0 and audit["remaining_mismatches"] == 1
    assert audit["problems"][0]["mismatch_categories"][0]["primary_category"] == "GOVERNANCE_PROJECTION"


def test_read_only_project_resolution_does_not_repair_title_or_options(monkeypatch):
    ns = runpy.run_path(str(RECONCILER_CORE))
    gl=ns["resolve_project"].__globals__
    monkeypatch.setitem(gl,"gh",lambda *a, **kw:{"projects":[{"number":7,"title":PROJECT_TITLE}]})
    monkeypatch.setitem(gl,"gql",lambda *a, **kw:{"data":{"user":{"projectV2":{"id":"P","title":"DDDA Platform Backlog","fields":{"nodes":[]},"views":{"nodes":[]}}}}})
    def forbidden(*a, **kw): raise AssertionError("read-only resolution mutated Project")
    monkeypatch.setitem(gl,"update_project_title",forbidden)
    monkeypatch.setitem(gl,"reconcile_configured_project_options",forbidden)
    repairs=[]
    assert ns["resolve_project"](repairs,read_only=True) == (7,"P",{},[])
    assert repairs == []


def test_planning_contract_agrees_with_versioned_projection_rules():
    cfg=json.loads(BOOTSTRAP.read_text(encoding="utf-8-sig"))["planning_projection"]
    assert cfg["draft_implementation_status"] == cfg["ready_implementation_status"] == "In progress"
    assert cfg["closed_completed_status"] == "Done"
    assert cfg["closed_not_planned_or_duplicate_status"] == "Cancelled"
    assert cfg["blocked_override"] == "Blocked"
    assert cfg["backlog_with_active_implementation_forbidden"]
    assert cfg["verify_only_mutations_forbidden"]
    assert "planning_projection:" in POLICY.read_text(encoding="utf-8")
