from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_repository.py"
SPEC = spec_from_file_location("ddda_validate_repository", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


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
