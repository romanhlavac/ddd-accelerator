from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPOSITORY_ROOT / "config" / "platform" / "development-policy.yaml"
CHAT_WORK_MARKER = "DDDA-EXECUTION-MODE: CHAT-WORK-ONLY"
CANONICAL_DOCUMENTS = (
    "knowledge/ddda-platform-development-skill.md",
    "docs/developer-guide/chat-work-operating-model.md",
    "docs/developer-guide/platform-development-lifecycle.md",
    "docs/developer-guide/testing-strategy.md",
    "docs/developer-guide/remote-validation-broker.md",
)
REQUIRED_GOVERNANCE_DOCUMENTS = {
    "docs/adr/0005-chat-work-only-development-operating-model.md",
    "docs/developer-guide/chat-work-operating-model.md",
}


def load_policy() -> dict[str, object]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_repository_allows_only_chat_and_work() -> None:
    policy = load_policy()
    interfaces = policy["execution_interfaces"]

    assert interfaces["allowed"] == ["chat", "work"]
    assert set(interfaces["forbidden"]) >= {"codex", "agent"}
    assert interfaces["default_mode"] == "chat"
    assert interfaces["implementation_mode"] == "work"


def test_github_actions_is_authoritative_execution_plane() -> None:
    interfaces = load_policy()["execution_interfaces"]

    assert interfaces["authoritative_execution_plane"] == "github-actions"
    assert interfaces["operator_local_shell_required"] is False
    assert interfaces["require_standard_ci_after_write"] is True


def test_work_has_no_secret_or_main_branch_authority() -> None:
    interfaces = load_policy()["execution_interfaces"]

    assert interfaces["assistant_runtime_secret_access"] is False
    assert interfaces["repository_write_scope"] == "pr-branch-only"
    assert interfaces["main_branch_write_allowed"] is False
    assert interfaces["require_transparent_access_failure"] is True


def test_policy_requires_chat_work_governance_documents() -> None:
    policy = load_policy()
    required_documents = set(policy["required_documents"])

    assert REQUIRED_GOVERNANCE_DOCUMENTS <= required_documents
    for relative in required_documents:
        assert (REPOSITORY_ROOT / relative).is_file(), relative


def test_canonical_documents_publish_same_execution_contract() -> None:
    for relative in CANONICAL_DOCUMENTS:
        text = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")
        folded = text.casefold()

        assert CHAT_WORK_MARKER in text, relative
        assert "codex" in folded, relative
        assert "github actions" in folded, relative
        assert "secret" in folded, relative


def test_legacy_cursor_runtime_bootstrap_is_not_distributed() -> None:
    assert not (REPOSITORY_ROOT / ".cursor").exists()


def test_remote_broker_forbids_unsafe_operations() -> None:
    remote = load_policy()["remote_execution"]

    assert set(remote["forbidden_operations"]) >= {
        "merge",
        "tag",
        "release",
        "promotion",
        "force-push",
    }
    assert remote["exact_sha_required"] is True
    assert remote["same_repository_only"] is True
