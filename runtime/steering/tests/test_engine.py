from pathlib import Path
import shutil

from ddda_steering.engine import bootstrap, generate_status, review_gate, validate_agent_contract


def platform_fixture(tmp_path: Path) -> Path:
    source = Path(__file__).resolve().parents[3]
    root = tmp_path / "platform"
    (root / "config").mkdir(parents=True)
    shutil.copytree(source / "config" / "steering", root / "config" / "steering")
    return root


def project_fixture(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    project.mkdir()
    (project / "project.yaml").write_text(
        """project:\n  id: claims-modernization\n  name: Claims modernization\n  type: legacy-modernization\n  schema_version: 1\nddda:\n  repository: romanhlavac/ddd-accelerator\n  required_ref: main\n  lock_file: ddda.lock.yaml\nartifacts:\n  canonical_source: yaml\n  root: artifacts\n""",
        encoding="utf-8",
    )
    intake = tmp_path / "intake.yaml"
    intake.write_text(
        """intake:\n  project_id: claims-modernization\n  name: Claims modernization\n  type: legacy-modernization\n  business_problem: Vendor lock-in blokuje změny likvidace škod.\n  decision_to_enable: Rozhodnout target boundaries a migrační řez.\n  goal: Převzít doménové know-how a umožnit inkrementální modernizaci.\n  scope:\n    in: [claim intake, adjudication]\n    out: [pricing]\n  actors: [claim handler, customer]\n  quality_attributes: [auditability, availability]\n  owners:\n    business_owner: Head of Claims\n    architecture_owner: Chief Architect\n""",
        encoding="utf-8",
    )
    return project, intake


def assert_generated_yaml_has_no_trailing_whitespace(project: Path) -> None:
    failures: list[str] = []
    for path in sorted(project.rglob("*.yaml")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
            if line.endswith((" ", "\t")):
                failures.append(f"{path.relative_to(project).as_posix()}:{line_number}")
    assert failures == [], f"Generated YAML contains trailing whitespace: {', '.join(failures)}"


def test_bootstrap_generates_status_and_contract(tmp_path: Path) -> None:
    platform = platform_fixture(tmp_path)
    project, intake = project_fixture(tmp_path)
    report = bootstrap(project, intake, platform)
    assert report["next_gate"] == "G1"
    assert (project / "project-profile.yaml").exists()
    assert (project / "lifecycle-tailoring.yaml").exists()
    assert (project / "artifacts/status/current-status.yaml").exists()
    assert (project / "decisions/gates/G1.yaml").exists()
    assert validate_agent_contract(project)["status"] == "ok"
    assert_generated_yaml_has_no_trailing_whitespace(project)


def test_gate_requires_evidence_and_updates_workflow(tmp_path: Path) -> None:
    platform = platform_fixture(tmp_path)
    project, intake = project_fixture(tmp_path)
    bootstrap(project, intake, platform)
    result = review_gate(project, platform, "G1", "passed", "owner", "reviewed", [])
    assert result["next_gate"] == "G2"
    text = (project / "project.yaml").read_text(encoding="utf-8")
    assert "completed_gates:" in text
    assert "G1" in text
    assert "current_stage: discover" in text
    assert_generated_yaml_has_no_trailing_whitespace(project)


def test_status_is_idempotent_in_shape(tmp_path: Path) -> None:
    platform = platform_fixture(tmp_path)
    project, intake = project_fixture(tmp_path)
    bootstrap(project, intake, platform)
    first = generate_status(project, platform)
    second = generate_status(project, platform)
    assert first["current_stage"] == second["current_stage"]
    assert first["next_gate"] == second["next_gate"]
    assert [item["status"] for item in first["gates"]] == [item["status"] for item in second["gates"]]
    assert_generated_yaml_has_no_trailing_whitespace(project)
