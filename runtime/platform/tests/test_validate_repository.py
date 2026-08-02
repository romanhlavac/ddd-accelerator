from __future__ import annotations

import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jsonschema
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_repository.py"
SPEC = spec_from_file_location("ddda_validate_repository", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def not_run_miro_evidence() -> dict[str, object]:
    return {
        "status": "NOT_RUN",
        "board_id": None,
        "board_url": None,
        "workspace": None,
        "managed_artifacts": [],
        "mapping": {"status": "NOT_RUN", "path": None, "verified_count": 0},
        "sync_state": {"status": "NOT_RUN", "path": None, "verified_count": 0},
        "idempotence": {
            "status": "NOT_RUN",
            "verification": None,
            "board_id_stable": None,
            "item_count_before": None,
            "item_count_after": None,
            "second_run_create_board_operations": None,
            "second_run_mutating_operations": None,
        },
        "cleanup": {
            "state": "not_created",
            "attempted_at": None,
            "completed_at": None,
            "error": None,
            "reason": "miro_not_requested",
        },
        "diagnostics": [],
    }


def deleted_miro_evidence() -> dict[str, object]:
    return {
        "status": "PASS",
        "board_id": "uXjVAuditBoard=",
        "board_url": "https://miro.com/app/board/uXjVAuditBoard=/",
        "workspace": "C:/DDDA/acceptance/run-1",
        "managed_artifacts": [
            "ddda.current-status",
            "ddda.next-actions",
            "sample.project-charter",
        ],
        "mapping": {
            "status": "PASS",
            "path": "C:/DDDA/acceptance/run-1/projects/sample/miro/miro-map.yaml",
            "verified_count": 3,
        },
        "sync_state": {
            "status": "PASS",
            "path": "C:/DDDA/acceptance/run-1/projects/sample/miro/sync-state.yaml",
            "verified_count": 3,
        },
        "idempotence": {
            "status": "PASS",
            "verification": "initializer invariant plus stable mapping snapshot",
            "board_id_stable": True,
            "item_count_before": 42,
            "item_count_after": 42,
            "second_run_create_board_operations": 0,
            "second_run_mutating_operations": 0,
        },
        "cleanup": {
            "state": "deleted",
            "attempted_at": "2026-07-28T08:00:00Z",
            "completed_at": "2026-07-28T08:00:01Z",
            "error": None,
            "reason": "successful_run_cleanup",
        },
        "diagnostics": ["C:/DDDA/acceptance-reports/run-1/result.json"],
    }


def test_security_detects_user_specific_path(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "bad.ps1").write_text(
        "Get-Content 'C:\\Users\\someone\\secret.txt'\n",
        encoding="utf-8",
    )

    failures = MODULE.validate_security(tmp_path)

    assert any("user-specific Windows path" in failure for failure in failures)


def test_lint_detects_trailing_whitespace(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "README.md").write_text("# Index\n", encoding="utf-8")
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    for index in range(13):
        (knowledge / f"{index:02d}-test.md").write_text("ok\n", encoding="utf-8")
    (tmp_path / "bad.md").write_text("bad  \n", encoding="utf-8")

    failures = MODULE.validate_lint(tmp_path)

    assert any("trailing whitespace" in failure for failure in failures)


def test_lint_accepts_minimal_clean_structure(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "README.md").write_text("# Index\n", encoding="utf-8")
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    for index in range(13):
        (knowledge / f"{index:02d}-test.md").write_text("ok\n", encoding="utf-8")

    failures = MODULE.validate_lint(tmp_path)

    assert failures == []


def test_failure_report_can_exist_before_package_creation() -> None:
    schema = json.loads(
        (REPOSITORY_ROOT / "schemas" / "validation-report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    report = {
        "schema_version": 1,
        "validation_id": "pr-8-bootstrap-failure",
        "status": "FAIL",
        "started_at": "2026-07-26T10:00:00Z",
        "completed_at": "2026-07-26T10:00:01Z",
        "source": {
            "kind": "pr",
            "repository": "romanhlavac/ddd-accelerator",
            "pr": 8,
            "branch": "feat/project-steering-and-documentation",
            "commit": "0" * 40,
        },
        "package": None,
        "workspace": None,
        "miro_board_id": None,
        "miro": not_run_miro_evidence(),
        "suites": [],
        "diagnostics": ["clone failed"],
    }

    jsonschema.validate(report, schema)

def test_validation_report_preserves_deleted_miro_board_evidence() -> None:
    schema = json.loads(
        (REPOSITORY_ROOT / "schemas" / "validation-report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    evidence = deleted_miro_evidence()
    report = {
        "schema_version": 1,
        "validation_id": "pr-8-miro-deleted",
        "status": "PASS",
        "started_at": "2026-07-28T08:00:00Z",
        "completed_at": "2026-07-28T08:00:02Z",
        "source": {
            "kind": "pr",
            "repository": "romanhlavac/ddd-accelerator",
            "pr": 8,
            "branch": "feat/project-steering-and-documentation",
            "commit": "1" * 40,
        },
        "package": {
            "path": "C:/DDDA/packages/candidate.zip",
            "sha256": "a" * 64,
        },
        "workspace": "C:/DDDA/validation/run-1",
        "miro_board_id": evidence["board_id"],
        "miro": evidence,
        "suites": [
            {
                "name": "miro",
                "status": "PASS",
                "duration_ms": 100,
                "details": "technical acceptance passed",
            }
        ],
        "diagnostics": [],
    }

    jsonschema.validate(report, schema)
    assert report["miro"]["cleanup"]["state"] == "deleted"
    assert report["miro"]["board_id"] == "uXjVAuditBoard="


def test_acceptance_and_validation_use_identical_miro_contract() -> None:
    validation_schema = json.loads(
        (REPOSITORY_ROOT / "schemas" / "validation-report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    acceptance_schema = json.loads(
        (
            REPOSITORY_ROOT
            / "schemas"
            / "miro-acceptance-report.schema.json"
        ).read_text(encoding="utf-8")
    )

    assert validation_schema["properties"]["miro"] == acceptance_schema["properties"]["miro"]


def test_miro_acceptance_schema_accepts_preserved_review_board() -> None:
    schema = json.loads(
        (
            REPOSITORY_ROOT
            / "schemas"
            / "miro-acceptance-report.schema.json"
        ).read_text(encoding="utf-8")
    )
    evidence = deleted_miro_evidence()
    evidence["cleanup"] = {
        "state": "preserved",
        "attempted_at": None,
        "completed_at": None,
        "error": None,
        "reason": "keep_review_board",
    }
    report = {
        "suite": "project-steering",
        "run_id": "20260728-review",
        "status": "PASS",
        "technical_sync_status": "PASS",
        "layout_contract_status": "PASS",
        "remote_layout_status": "PASS",
        "render_contract_status": "PASS",
        "render_contract_version": "REM-PR8-HVA-CC-011",
        "platform_source_commit": "a" * 40,
        "scaffold_sha256": "b" * 64,
        "remote_item_count": 281,
        "overview_child_count": 61,
        "starter_reference_caption_count": 11,
        "remote_content_digest": "c" * 64,
        "review_team_selection_status": "EXPLICIT_TEAM",
        "utf8_status": "PASS",
        "human_visual_acceptance_status": "PENDING",
        "overall_status": "PENDING_HUMAN_REVIEW",
        "miro_board_id": evidence["board_id"],
        "miro_board_url": evidence["board_url"],
        "miro": evidence,
        "gate_assertion": {
            "gate": "G1",
            "expected": "ready_for_review",
            "actual": "ready_for_review",
            "human_decision_created": False,
        },
        "report_created_at": "2026-07-28T08:00:02Z",
    }

    jsonschema.validate(report, schema)

    legacy_mapping_only_report = dict(report)
    legacy_mapping_only_report.pop("remote_content_digest")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(legacy_mapping_only_report, schema)

    baseline_like_report = dict(report)
    baseline_like_report["remote_item_count"] = 211
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(baseline_like_report, schema)


def write_release_contract_fixture(root: Path) -> None:
    (root / "docs/user-guide").mkdir(parents=True, exist_ok=True)
    (root / "docs/developer-guide").mkdir(parents=True, exist_ok=True)
    (root / "docs/reference").mkdir(parents=True, exist_ok=True)
    (root / "scripts/platform").mkdir(parents=True, exist_ok=True)

    canonical = "GH_TOKEN -> GITHUB_TOKEN -> gh auth token -> Git credential helper\n"
    (root / "README.md").write_text("GitHub CLI není povinný.\n", encoding="utf-8")
    (root / "USAGE.md").write_text("Token není CLI argument.\n", encoding="utf-8")
    for relative in (
        "docs/user-guide/validate-and-promote-pr.md",
        "docs/developer-guide/platform-development-lifecycle.md",
        "docs/reference/cli.md",
    ):
        (root / relative).write_text(canonical, encoding="utf-8")

    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "Auth: GH_TOKEN -> GITHUB_TOKEN -> gh auth token -> Git credential helper\n\n"
        "## [Unreleased]\n\n"
        "Development notes belong here without release bullets.\n\n"
        "## [1.2.3] - 2026-07-28\n\n"
        "### Added\n\n"
        "- deterministic release contract.\n",
        encoding="utf-8",
    )
    (root / "scripts/platform/DDDAGitHubSupport.ps1").write_text(
        'Name = "GH_TOKEN"\n'
        'Name = "GITHUB_TOKEN"\n'
        'Source = "gh auth token"\n'
        'Source = "git credential helper"\n',
        encoding="utf-8",
    )
    (root / "scripts/platform/DDDAPlatformSupport.ps1").write_text(
        "function Assert-DDDAPlatformChangelogRelease {}\n",
        encoding="utf-8",
    )
    (root / "scripts/platform/Invoke-DDDAPromotePr.ps1").write_text(
        "Assert-DDDAPlatformChangelogRelease -Path CHANGELOG.md -Version $Version\n",
        encoding="utf-8",
    )


def test_release_contracts_accept_canonical_auth_and_changelog(tmp_path: Path) -> None:
    write_release_contract_fixture(tmp_path)

    failures = MODULE.validate_release_contracts(tmp_path)

    assert failures == []


def test_release_contracts_detect_stale_required_github_cli_claim(tmp_path: Path) -> None:
    write_release_contract_fixture(tmp_path)
    (tmp_path / "docs/adr").mkdir(parents=True)
    (tmp_path / "docs/adr/0001.md").write_text(
        "promotion vyžaduje GitHub CLI a autentizaci.\n",
        encoding="utf-8",
    )

    failures = MODULE.validate_release_contracts(tmp_path)

    assert any("GitHub CLI is required" in failure for failure in failures)


def test_release_contracts_detect_auth_provider_order_drift(tmp_path: Path) -> None:
    write_release_contract_fixture(tmp_path)
    (tmp_path / "docs/reference/cli.md").write_text(
        "Git credential helper -> GH_TOKEN -> GITHUB_TOKEN -> gh auth token\n",
        encoding="utf-8",
    )

    failures = MODULE.validate_release_contracts(tmp_path)

    assert any("inconsistent GitHub auth provider order" in failure for failure in failures)


def test_release_contracts_detect_unreleased_release_items(tmp_path: Path) -> None:
    write_release_contract_fixture(tmp_path)
    changelog = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    changelog = changelog.replace(
        "Development notes belong here without release bullets.\n",
        "- not assigned to a release.\n",
    )
    (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")

    failures = MODULE.validate_release_contracts(tmp_path)

    assert any("[Unreleased] contains release items" in failure for failure in failures)


def test_release_contracts_detect_invalid_release_date(tmp_path: Path) -> None:
    write_release_contract_fixture(tmp_path)
    changelog = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    changelog = changelog.replace("2026-07-28", "2026-02-30")
    (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")

    failures = MODULE.validate_release_contracts(tmp_path)

    assert any("invalid ISO date" in failure for failure in failures)
