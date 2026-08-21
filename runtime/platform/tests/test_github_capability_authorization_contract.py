from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = ROOT / "config" / "platform" / "github-capability-routing.json"
RUNBOOK_PATH = ROOT / "docs" / "developer-guide" / "github-capability-authorization.md"
REMOTE_RUNBOOK_PATH = ROOT / "docs" / "developer-guide" / "remote-validation-broker.md"
NATIVE_SETUP_PATH = ROOT / "docs" / "governance" / "native-github-setup-runbook.md"
INDEX_PATH = ROOT / "knowledge" / "00-knowledge-index.md"
DEVELOPMENT_POLICY_PATH = ROOT / "config" / "platform" / "development-policy.yaml"


def load_contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def load_development_policy() -> dict[str, object]:
    return json.loads(DEVELOPMENT_POLICY_PATH.read_text(encoding="utf-8"))


def test_provider_order_is_connector_broker_human_bootstrap_unavailable() -> None:
    contract = load_contract()

    assert contract["provider_order"] == [
        "CONNECTOR",
        "CANONICAL_BROKER_OR_DEDICATED_CREDENTIAL",
        "HUMAN_BOOTSTRAP_ONLY",
        "UNAVAILABLE",
    ]
    assert contract["selection_rules"]["connector_supported"] == "CONNECTOR"
    assert (
        contract["selection_rules"]["connector_missing_broker_supported"]
        == "CANONICAL_BROKER_OR_DEDICATED_CREDENTIAL"
    )


def test_connector_or_broker_support_never_requires_browser_bootstrap() -> None:
    providers = load_contract()["providers"]

    assert providers["CONNECTOR"]["browser_authorization_required"] is False
    assert (
        providers["CANONICAL_BROKER_OR_DEDICATED_CREDENTIAL"][
            "browser_authorization_required"
        ]
        is False
    )


def test_missing_user_oauth_consent_is_human_bootstrap_only_not_generic_blocker() -> None:
    contract = load_contract()
    provider = contract["providers"]["HUMAN_BOOTSTRAP_ONLY"]

    assert (
        contract["selection_rules"]["only_user_oauth_consent_missing"]
        == "HUMAN_BOOTSTRAP_ONLY"
    )
    assert provider["browser_authorization_required"] is True
    assert provider["is_hard_blocker"] is False
    assert provider["human_action"] == "AUTHORIZE_IN_LOCAL_BROWSER_ONLY"


def test_browser_authorization_requests_consent_not_mechanical_github_gui_work() -> None:
    contract = load_contract()
    auth = contract["browser_device_authorization"]

    assert auth["allowed_human_actions"] == [
        "open-verification-url",
        "enter-device-code-if-requested-by-github",
        "approve-github-oauth-consent",
        "confirm-authorization-complete",
    ]
    forbidden = set(auth["forbidden_human_actions"])
    assert "edit-project-fields-through-github-gui" in forbidden
    assert "run-workflow-through-github-gui" in forbidden
    assert (
        "perform-other-programmatically-available-mechanical-github-mutation"
        in forbidden
    )


def test_post_authorization_requires_actor_and_capability_verification() -> None:
    contract = load_contract()
    auth = contract["browser_device_authorization"]
    completion = contract["completion"]

    assert auth["post_authorization_verification"] == [
        "authenticated-actor",
        "required-capability-or-scope",
    ]
    assert completion["actor_verification_required_after_authorization"] is True
    assert completion["capability_verification_required_after_authorization"] is True


def test_project_v2_mutation_has_programmatic_fallback_and_live_read_back() -> None:
    capability = load_contract()["capabilities"]["project_v2_mutation"]

    assert capability["connector_surface_may_be_missing"] is True
    assert "CANONICAL_BROKER_OR_DEDICATED_CREDENTIAL" in capability[
        "approved_programmatic_alternates"
    ]
    assert "gh project" in capability["approved_programmatic_alternates"]
    assert "gh api graphql" in capability["approved_programmatic_alternates"]
    assert capability["manual_github_gui_allowed"] is False
    assert capability["fresh_live_read_back_required"] is True


def test_project_reconciliation_is_fixed_broker_capability_with_exact_identity_contract() -> None:
    capability = load_contract()["capabilities"]["project_v2_reconciliation"]

    assert capability["provider"] == "CANONICAL_BROKER_OR_DEDICATED_CREDENTIAL"
    assert capability["command"] == "/ddda reconcile-project --expected-sha <40-char-pr-head-sha>"
    assert capability["exact_sha_binding_required"] is True
    assert capability["canonical_workflow"] == ".github/workflows/reconcile-ddda-project-backlog.yml"
    assert capability["canonical_source_ref"] == "main"
    assert capability["workflow_identity_user_controlled"] is False
    assert capability["arbitrary_workflow_dispatch_allowed"] is False
    assert capability["active_reconciliation_serialization_required"] is True
    assert capability["workflow_success_required"] is True
    assert capability["source_sha_match_required"] is True
    assert capability["zero_remaining_mismatches_required"] is True
    assert capability["fresh_live_read_back_required"] is True
    assert set(capability["evidence_identity_required"]) >= {
        "repository",
        "pr",
        "requested_actor",
        "authorized_pr_head_sha",
        "expected_sha",
        "canonical_workflow",
        "reconciliation_source_sha",
        "workflow_run_id",
        "workflow_conclusion",
        "audit_artifact_id",
        "audit_artifact_name",
        "remaining_mismatches",
    }


def test_project_reconciliation_keeps_project_credential_outside_chat_work_and_broker() -> None:
    capability = load_contract()["capabilities"]["project_v2_reconciliation"]
    policy = load_development_policy()["remote_execution"]["project_reconciliation"]

    assert capability["persistent_project_credential_available_to_chat_work"] is False
    assert capability["persistent_project_credential_available_to_broker"] is False
    assert capability["secret_bearing_execution_plane"] == "github-actions-environment:ddda-backlog-governance"
    assert capability["broker_permission"] == "actions:write-on-reconcile-job-only"
    assert policy["credential_location"] == "ddda-backlog-governance-environment-only"
    assert policy["broker_credential_access"] is False
    assert policy["chat_work_credential_access"] is False
    assert policy["allow_arbitrary_workflow"] is False


def test_project_reconciliation_policy_requires_canonical_workflow_success_source_and_zero_mismatch() -> None:
    policy = load_development_policy()["remote_execution"]["project_reconciliation"]

    assert policy["enabled"] is True
    assert policy["canonical_workflow"] == ".github/workflows/reconcile-ddda-project-backlog.yml"
    assert policy["source_ref"] == "main"
    assert policy["audit_artifact_prefix"] == "ddda-project-backlog-delivery-audit-v6-"
    assert policy["require_workflow_success"] is True
    assert policy["require_source_sha_match"] is True
    assert policy["require_zero_mismatches"] is True
    assert policy["maximum_source_drift_attempts"] == 3
    assert policy["active_run_serialization_required"] is True


def test_token_and_pat_never_enter_chat_or_evidence_channels() -> None:
    security = load_contract()["security"]

    assert security["pat_or_token_in_chat_allowed"] is False
    assert security["oauth_token_output_allowed"] is False
    assert security["gh_auth_token_as_evidence_allowed"] is False
    assert security["generic_remote_shell_allowed"] is False
    assert set(security["forbidden_credential_evidence_channels"]) >= {
        "chat",
        "prompt",
        "git-history",
        "log",
        "artifact",
        "result-json",
        "pull-request-comment",
    }


def test_authorization_success_does_not_approve_human_or_release_boundaries() -> None:
    boundaries = load_contract()["decision_boundaries"]

    assert boundaries == {
        "authorization_success_implies_human_review_pass": False,
        "authorization_success_implies_merge_authorization": False,
        "authorization_success_implies_release_authorization": False,
        "authorization_success_implies_tag_authorization": False,
    }


def test_route_exhaustion_is_fail_closed_with_concrete_capability_diagnosis() -> None:
    contract = load_contract()
    provider = contract["providers"]["UNAVAILABLE"]

    assert (
        contract["selection_rules"]["no_approved_programmatic_route"]
        == "UNAVAILABLE"
    )
    assert provider["is_hard_blocker"] is True
    assert provider["requires_capability_diagnosis"] is True


def test_local_browser_bootstrap_is_one_command_and_never_assumed_to_bridge_cloud_session() -> None:
    auth = load_contract()["browser_device_authorization"]
    boundary = auth["runtime_session_boundary"]

    assert auth["purpose"] == "one-time-bootstrap-only"
    assert auth["repeat_for_each_reconciliation"] is False
    assert boundary["direct_flow_preferred_when_supported"] is True
    assert boundary["local_bootstrap_command_limit"] == 1
    assert boundary["local_credential_must_not_be_assumed_available_to_cloud_runner"] is True
    assert boundary["session_bridge_gap_requires_explicit_diagnosis"] is True
    assert auth["existing_login_command"] == "gh auth refresh -s <required-scope>"
    assert auth["fresh_login_command"].startswith("gh auth login --hostname github.com")


def test_project_v2_connector_gap_regression_never_sends_human_to_manual_project_edit() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "NO_MANUAL_GITHUB_GUI_FOR_MECHANICAL_OPERATIONS" in runbook
    assert "connector capability missing" in runbook
    assert "gh api graphql" in runbook
    assert "fresh Project V2 read-back" in runbook
    assert "ask human to edit Status/field manually" in runbook
    assert "Forbidden behavior" in runbook


def test_permanent_reconcile_route_uses_connector_broker_existing_environment_and_zero_mismatch() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    remote = REMOTE_RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "/ddda reconcile-project --expected-sha" in runbook
    assert ".github/workflows/reconcile-ddda-project-backlog.yml" in runbook
    assert "ddda-backlog-governance" in runbook
    assert "Project credential remains only" in runbook
    assert "zero remaining mismatches" in runbook
    assert "Canonical GitHub Project reconciliation broker" in remote
    assert "Default-branch activation boundary" in remote


def test_native_setup_runbook_uses_capability_routing_before_cli_auth() -> None:
    runbook = NATIVE_SETUP_PATH.read_text(encoding="utf-8")

    assert "CONNECTOR" in runbook
    assert "CANONICAL_BROKER_OR_DEDICATED_CREDENTIAL" in runbook
    assert "HUMAN_BOOTSTRAP_ONLY" in runbook
    assert "NO_MANUAL_GITHUB_GUI_FOR_MECHANICAL_OPERATIONS" in runbook
    assert "gh auth refresh -s project" in runbook
    assert "gh auth login --hostname github.com --git-protocol https --web --scopes project" in runbook


def test_knowledge_router_registers_capability_authorization_runbook() -> None:
    index = INDEX_PATH.read_text(encoding="utf-8")

    assert "github-capability-authorization.md" in index
    assert "github-capability-routing.json" in index
