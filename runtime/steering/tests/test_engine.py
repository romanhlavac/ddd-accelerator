from pathlib import Path
import shutil
import subprocess

import pytest

from ddda_steering.engine import SteeringError, bootstrap, generate_status, review_gate, validate_agent_contract


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
    subprocess.run(["git", "-C", str(project), "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(project), "config", "user.name", "DDDA Steering Test"], check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.email", "ddda-steering-test@example.invalid"], check=True)
    return project, intake


def commit_project(project: Path, message: str = "test: baseline") -> str:
    subprocess.run(["git", "-C", str(project), "add", "."], check=True)
    subprocess.run(["git", "-C", str(project), "commit", "-m", message], check=True, capture_output=True)
    return subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def bootstrap_committed(project: Path, intake: Path, platform: Path) -> dict:
    report = bootstrap(project, intake, platform)
    commit_project(project)
    return report


def human_review(project: Path, platform: Path, outcome: str = "passed", **overrides):
    values = {
        "decision_owner": "business_owner",
        "approver": "Roman Reviewer",
        "scope": "G1 project purpose, scope and decision ownership",
        "provenance": "human",
        "condition_owner": None,
        "condition_due_at": None,
        "test_simulation": False,
    }
    values.update(overrides)
    conditions = values.pop("conditions", [])
    return review_gate(
        project,
        platform,
        "G1",
        outcome,
        values.pop("reviewer", "Roman Reviewer"),
        "reviewed",
        conditions,
        **values,
    )


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
    assert report["gates"][0]["status"] == "ready_for_review"
    assert (project / "project-profile.yaml").exists()
    assert (project / "lifecycle-tailoring.yaml").exists()
    assert (project / "artifacts/status/current-status.yaml").exists()
    assert (project / "decisions/gates/G1.yaml").exists()
    assert validate_agent_contract(project)["status"] == "ok"
    assert_generated_yaml_has_no_trailing_whitespace(project)


def test_gate_requires_structured_human_decision_and_updates_workflow(tmp_path: Path) -> None:
    platform = platform_fixture(tmp_path)
    project, intake = project_fixture(tmp_path)
    bootstrap_committed(project, intake, platform)
    result = human_review(project, platform)
    assert result["next_gate"] == "G2"
    assert result["gates"][0]["status"] == "passed"
    text = (project / "project.yaml").read_text(encoding="utf-8")
    assert "completed_gates:" in text
    assert "G1" in text
    assert "current_stage: discover" in text
    record = (project / "decisions/gates/G1.yaml").read_text(encoding="utf-8")
    assert "provenance: human" in record
    assert "decision_owner: business_owner" in record
    assert "project_commit:" in record
    assert "artifact_hashes:" in record
    assert_generated_yaml_has_no_trailing_whitespace(project)


def test_automation_identity_cannot_spoof_human_approval(tmp_path: Path) -> None:
    platform = platform_fixture(tmp_path)
    project, intake = project_fixture(tmp_path)
    bootstrap_committed(project, intake, platform)
    with pytest.raises(SteeringError, match="automatizační identita"):
        human_review(project, platform, reviewer="Acceptance runner", approver="CI bot")


def test_g1_cannot_pass_without_explicit_project_owner(tmp_path: Path) -> None:
    platform = platform_fixture(tmp_path)
    project, intake = project_fixture(tmp_path)
    bootstrap_committed(project, intake, platform)
    manifest = (project / "project.yaml").read_text(encoding="utf-8")
    manifest = manifest.replace("business_owner: Head of Claims", "business_owner:")
    manifest = manifest.replace("architecture_owner: Chief Architect", "architecture_owner:")
    (project / "project.yaml").write_text(manifest, encoding="utf-8")
    commit_project(project, "test: remove owners")
    with pytest.raises(SteeringError, match="neobsahuje konkrétního decision ownera"):
        human_review(project, platform)


def test_relevant_evidence_change_invalidates_passed_decision(tmp_path: Path) -> None:
    platform = platform_fixture(tmp_path)
    project, intake = project_fixture(tmp_path)
    bootstrap_committed(project, intake, platform)
    human_review(project, platform)
    charter = project / "artifacts/align/project-charter.yaml"
    charter.write_text(charter.read_text(encoding="utf-8") + "# changed after review\n", encoding="utf-8")
    result = generate_status(project, platform)
    assert result["next_gate"] == "G1"
    assert result["gates"][0]["status"] == "ready_for_review"
    assert result["gates"][0]["decision_valid"] is False
    assert any("evidence se od review změnila" in item for item in result["gates"][0]["decision_invalid_reasons"])


def test_conditional_is_human_owned_and_not_completed(tmp_path: Path) -> None:
    platform = platform_fixture(tmp_path)
    project, intake = project_fixture(tmp_path)
    bootstrap_committed(project, intake, platform)
    result = human_review(
        project,
        platform,
        outcome="conditional",
        conditions=["Confirm exportable legacy events"],
        condition_owner="Head of Claims",
        condition_due_at="2026-08-15",
    )
    assert result["next_gate"] == "G1"
    assert result["gates"][0]["status"] == "conditional"
    manifest = (project / "project.yaml").read_text(encoding="utf-8")
    assert "- G1" not in manifest


def test_test_simulation_is_forbidden_for_normal_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    platform = platform_fixture(tmp_path)
    project, intake = project_fixture(tmp_path)
    bootstrap_committed(project, intake, platform)
    monkeypatch.setenv("DDDA_GATE_TEST_SIMULATION", "1")
    with pytest.raises(SteeringError, match="pouze v označeném dočasném test fixture"):
        human_review(
            project,
            platform,
            reviewer="Acceptance runner",
            approver="CI bot",
            test_simulation=True,
        )


def test_test_simulation_requires_temp_marker_and_is_auditable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    platform = platform_fixture(tmp_path)
    project, intake = project_fixture(tmp_path)
    bootstrap_committed(project, intake, platform)
    marker = project / ".ddda/test-fixture"
    marker.write_text("ephemeral automated fixture only\n", encoding="utf-8")
    commit_project(project, "test: mark ephemeral fixture")
    monkeypatch.setenv("DDDA_GATE_TEST_SIMULATION", "1")
    result = human_review(
        project,
        platform,
        reviewer="Acceptance runner",
        approver="CI bot",
        test_simulation=True,
    )
    assert result["gates"][0]["status"] == "passed"
    record = (project / "decisions/gates/G1.yaml").read_text(encoding="utf-8")
    assert "provenance: test_simulation" in record


def test_bootstrap_can_preserve_legacy_project_manifest(tmp_path: Path) -> None:
    platform = platform_fixture(tmp_path)
    project, intake = project_fixture(tmp_path)
    original = (project / "project.yaml").read_bytes()

    report = bootstrap(
        project,
        intake,
        platform,
        preserve_project_manifest=True,
    )

    assert report["next_gate"] == "G1"
    assert (project / "project.yaml").read_bytes() == original
    assert (project / ".ddda/adoption.yaml").exists()
    adoption = (project / ".ddda/adoption.yaml").read_text(encoding="utf-8")
    assert "mode: legacy-resume" in adoption
    assert "preserved_project_manifest: true" in adoption
    assert all(item["status"] != "passed" for item in report["gates"])


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
