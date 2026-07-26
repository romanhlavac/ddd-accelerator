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
        "suites": [],
        "diagnostics": ["clone failed"],
    }

    jsonschema.validate(report, schema)
