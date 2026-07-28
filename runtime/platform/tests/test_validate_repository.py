from __future__ import annotations

import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import jsonschema


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
