from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPOSITORY_ROOT / "config" / "platform" / "development-policy.yaml"
OPERATING_MODEL_PATH = (
    REPOSITORY_ROOT / "docs" / "developer-guide" / "chat-work-operating-model.md"
)
ADR_PATH = (
    REPOSITORY_ROOT
    / "docs"
    / "adr"
    / "0005-chat-work-only-development-operating-model.md"
)
REQUIRED_GOVERNANCE_DOCUMENTS = {
    "docs/adr/0005-chat-work-only-development-operating-model.md",
    "docs/developer-guide/chat-work-operating-model.md",
}


GOVERNANCE_TEXT_PATHS = {
    "CHANGELOG.md",
    "config/platform/development-policy.yaml",
    "docs/adr/0006-chat-atomic-platform-implementation.md",
    "docs/developer-guide/chat-work-operating-model.md",
    "docs/developer-guide/remote-validation-broker.md",
    "knowledge/ddda-platform-development-skill.md",
    "runtime/platform/tests/test_chat_work_policy.py",
}
MOJIBAKE_FRAGMENTS = (
    "\ufeff",
    "\ufffd",
    "b" + chr(0x0118) + "hem",
    "Rozd" + chr(0x0119) + "lení",
    chr(0x00C3),
    chr(0x00C2),
    chr(0x00E2) + chr(0x20AC),
)

EXPECTED_CURSOR_ASSETS = {
    ".cursor/rules/010-ddda-project-steering.mdc",
    ".cursor/rules/ddda-chat-first.mdc",
    ".cursor/rules/ddda-repository-scope.mdc",
    ".cursor/skills.md",
}


def load_policy() -> dict[str, object]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def read_canonical_git_blob(relative: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "cat-file", "blob", f"HEAD:{relative}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        pytest.skip(
            "Canonical Git blob validation requires a source repository with HEAD."
        )
    return result.stdout


def test_platform_development_allows_only_chat_and_work() -> None:
    platform = load_policy()["execution_interfaces"]["platform_development"]

    assert platform["allowed"] == ["chat", "work"]
    assert set(platform["forbidden"]) >= {"codex", "cursor", "agent"}
    assert platform["default_mode"] == "chat"
    assert platform["preferred_implementation_mode"] == "work"
    assert platform["allowed_implementation_modes"] == ["work", "chat-atomic"]


def test_github_actions_is_platform_execution_plane() -> None:
    platform = load_policy()["execution_interfaces"]["platform_development"]

    assert platform["authoritative_execution_plane"] == "github-actions"
    assert platform["operator_local_shell_required"] is False
    assert platform["require_standard_ci_after_write"] is True
    assert platform["repository_write_scope"] == "platform-pr-branch-only"


def test_work_has_no_secret_or_main_branch_authority() -> None:
    platform = load_policy()["execution_interfaces"]["platform_development"]

    assert platform["assistant_runtime_secret_access"] is False
    assert platform["main_branch_write_allowed"] is False
    assert platform["require_transparent_access_failure"] is True


def test_cursor_is_required_ddda_project_runtime() -> None:
    runtime = load_policy()["execution_interfaces"]["ddda_project_runtime"]

    assert runtime["required_system"] == "cursor"
    assert runtime["primary_interaction"] == "cursor-chat"
    assert runtime["agentic_execution_enabled"] is True
    assert runtime["project_artifact_management_enabled"] is True
    assert runtime["project_repository_write_allowed"] is True
    assert runtime["platform_repository_write_allowed"] is False
    assert runtime["cross_repository_commit_allowed"] is False
    assert runtime["human_gate_decision_required"] is True
    assert set(runtime["cursor_runtime_assets_required"]) == EXPECTED_CURSOR_ASSETS


def test_cursor_runtime_assets_are_active_and_project_scoped() -> None:
    observed = {
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in (REPOSITORY_ROOT / ".cursor").rglob("*")
        if path.is_file()
    }

    assert observed == EXPECTED_CURSOR_ASSETS

    for relative in sorted(observed):
        text = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")
        folded = text.casefold()
        assert "retired-non-runtime-compatibility-stub" not in folded, relative
        assert "platform repository" in folded, relative
        assert "cursor" in folded, relative
        if relative.endswith(".mdc"):
            assert "alwaysApply: true" in text, relative
            assert "alwaysApply: false" not in text, relative


def test_operating_model_describes_both_execution_planes() -> None:
    text = OPERATING_MODEL_PATH.read_text(encoding="utf-8")

    assert "DDDA-PLATFORM-DEVELOPMENT-MODE: CHAT-WORK-ONLY" in text
    assert "DDDA-PROJECT-RUNTIME: CURSOR" in text
    assert "Cursor je základní a povinný agentic systém" in text
    assert "Cursor write zakázán" in text


def test_adr_records_correction_of_the_scope_misunderstanding() -> None:
    text = ADR_PATH.read_text(encoding="utf-8")

    assert "Předchozí formulace" in text
    assert "Cursor je povinný základní agentic systém" in text
    assert "Cursor nesmí měnit DDDA platform repository" in text


def test_policy_requires_governance_documents() -> None:
    policy = load_policy()
    required_documents = set(policy["required_documents"])

    assert REQUIRED_GOVERNANCE_DOCUMENTS <= required_documents
    for relative in required_documents:
        assert (REPOSITORY_ROOT / relative).is_file(), relative


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

def test_chat_atomic_implementation_is_guarded() -> None:
    platform = load_policy()["execution_interfaces"]["platform_development"]
    atomic = platform["chat_atomic_implementation"]

    assert atomic["enabled"] is True
    assert atomic["transport"] == "github-git-data-api"
    assert atomic["exact_base_sha_required"] is True
    assert atomic["atomic_tree_commit_required"] is True
    assert atomic["direct_contents_api_multi_file_write_allowed"] is False
    assert atomic["target_scope"] == "platform-pr-branch-only"
    assert atomic["maximum_commits_per_change"] == 1
    assert atomic["force_update_allowed"] is False
    assert atomic["prewrite_source_snapshot_required"] is True
    assert atomic["standard_ci_after_write_required"] is True
    assert atomic["evidence_required"] is True

    bootstrap = atomic["bootstrap_exception"]
    assert bootstrap["change_id"] == "REM-PR8-HVA-CC-012.1A"
    assert bootstrap["explicit_authorization_required"] is True
    assert bootstrap["maximum_staging_commits"] == 1
    assert bootstrap["maximum_final_commits"] == 1
    assert bootstrap["self_removing_script_required"] is True


def test_governance_documents_describe_work_preferred_chat_atomic_fallback() -> None:
    operating = OPERATING_MODEL_PATH.read_text(encoding="utf-8")
    skill = (REPOSITORY_ROOT / "knowledge/ddda-platform-development-skill.md").read_text(encoding="utf-8")
    adr = (REPOSITORY_ROOT / "docs/adr/0006-chat-atomic-platform-implementation.md").read_text(encoding="utf-8")

    assert "Work zůstává preferovaným implementačním režimem" in operating
    assert "jeden atomický Git tree commit" in operating
    assert "Chat direct multi-file Contents API writes are prohibited" in skill
    assert "chat-atomic" in adr
    assert "non-force fast-forward" in adr

def test_rem012_governance_files_are_utf8_lf_without_mojibake() -> None:
    for relative in sorted(GOVERNANCE_TEXT_PATHS):
        raw = read_canonical_git_blob(relative)

        assert not raw.startswith(b"\xef\xbb\xbf"), relative
        assert b"\r" not in raw, relative

        text = raw.decode("utf-8")
        for fragment in MOJIBAKE_FRAGMENTS:
            assert fragment not in text, f"{relative}: {fragment!r}"
