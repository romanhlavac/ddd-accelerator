from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = ROOT / "config" / "platform" / "github-capability-routing.json"
RUNBOOK_PATH = ROOT / "docs" / "developer-guide" / "github-capability-authorization.md"
NATIVE_SETUP_PATH = ROOT / "docs" / "governance" / "native-github-setup-runbook.md"
INDEX_PATH = ROOT / "knowledge" / "00-knowledge-index.md"


def load_contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


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
