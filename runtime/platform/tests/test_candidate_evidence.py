import hashlib
import json
from pathlib import Path

import runtime.platform.candidate_evidence as candidate_evidence
from runtime.platform.candidate_evidence import (
    restore_candidate_evidence,
    restore_candidate_evidence_paths,
    validate_candidate_evidence,
)
from runtime.platform.governance_kernel import KernelDecision


REPOSITORY = "romanhlavac/ddd-accelerator"
PR = 103
SHA = "a" * 40


def report(package: Path) -> dict:
    return {
        "status": "PASS",
        "source": {"repository": REPOSITORY, "pr": PR, "commit": SHA},
        "package": {
            "path": package.name,
            "sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
            "artifact_name": f"ddda-candidate-{SHA}",
            "workflow_run_id": 123,
        },
    }


def test_shared_collector_validates_explicit_report_and_package(tmp_path):
    package = tmp_path / f"ddda-candidate-pr-{PR}-{SHA[:12]}-unit.zip"
    package.write_bytes(b"exact candidate")
    result = validate_candidate_evidence(
        report(package),
        repository=REPOSITORY,
        pr_number=PR,
        source_sha=SHA,
        package_path=package,
    )
    assert result["status"] == "PASS"
    assert result["candidate_package_sha256"] == result["observed_package_sha256"]


def test_shared_collector_submits_normalized_binding_to_kernel(tmp_path, monkeypatch):
    package = tmp_path / f"ddda-candidate-pr-{PR}-{SHA[:12]}-kernel.zip"
    package.write_bytes(b"exact candidate")
    observed = {}

    def fake_kernel(context):
        observed.update(context)
        return KernelDecision(
            status="FAIL",
            operation="validate",
            failure_codes=("CANDIDATE_PACKAGE_SHA256_MISMATCH",),
            authorization_required=False,
        )

    monkeypatch.setattr(candidate_evidence, "evaluate_candidate_package_binding", fake_kernel)
    result = validate_candidate_evidence(
        report(package),
        repository=REPOSITORY,
        pr_number=PR,
        source_sha=SHA,
        package_path=package,
    )
    evidence = observed["validation_evidence"]
    assert evidence["package_present"] is True
    assert evidence["observed_package_sha256"] == evidence["package_sha256"]
    assert result["failures"] == ["CONTROLLED_CANDIDATE_PACKAGE_HASH_MISMATCH"]


def test_restore_finds_exactly_one_report_bound_package(tmp_path):
    package = tmp_path / f"ddda-candidate-pr-{PR}-{SHA[:12]}-restore.zip"
    package.write_bytes(b"exact candidate")
    nested = tmp_path / "validation-reports" / "run"
    nested.mkdir(parents=True)
    (nested / "result.json").write_text(json.dumps(report(package)), encoding="utf-8")
    result = restore_candidate_evidence(
        tmp_path,
        repository=REPOSITORY,
        pr_number=PR,
        source_sha=SHA,
    )
    assert result["status"] == "PASS"
    assert Path(result["candidate_package_path"]).name == package.name


def test_restore_accepts_short_sha_ci_package_with_full_sha_artifact_identity(tmp_path):
    package = tmp_path / f"ddda-candidate-{SHA[:12]}.zip"
    package.write_bytes(b"exact CI candidate")
    (tmp_path / "result.json").write_text(json.dumps(report(package)), encoding="utf-8")

    result = restore_candidate_evidence(
        tmp_path,
        repository=REPOSITORY,
        pr_number=PR,
        source_sha=SHA,
    )

    assert result["status"] == "PASS"
    assert Path(result["candidate_package_path"]).name == package.name


def test_restore_rejects_report_and_package_cardinality(tmp_path):
    no_report = restore_candidate_evidence(
        tmp_path,
        repository=REPOSITORY,
        pr_number=PR,
        source_sha=SHA,
    )
    assert no_report["failures"] == ["CANDIDATE_EVIDENCE_REPORT_CARDINALITY"]

    package = tmp_path / f"ddda-candidate-pr-{PR}-{SHA[:12]}-duplicate.zip"
    package.write_bytes(b"exact candidate")
    (tmp_path / "result.json").write_text(json.dumps(report(package)), encoding="utf-8")
    duplicate = tmp_path / "duplicate"
    duplicate.mkdir()
    (duplicate / package.name).write_bytes(package.read_bytes())
    result = restore_candidate_evidence(
        tmp_path,
        repository=REPOSITORY,
        pr_number=PR,
        source_sha=SHA,
    )
    assert result["failures"] == ["CANDIDATE_EVIDENCE_PACKAGE_CARDINALITY"]


def test_restore_rejects_report_bound_hash_drift(tmp_path):
    package = tmp_path / f"ddda-candidate-pr-{PR}-{SHA[:12]}-drift.zip"
    package.write_bytes(b"changed candidate")
    evidence = report(package)
    evidence["package"]["sha256"] = "0" * 64
    (tmp_path / "result.json").write_text(json.dumps(evidence), encoding="utf-8")
    result = restore_candidate_evidence(
        tmp_path,
        repository=REPOSITORY,
        pr_number=PR,
        source_sha=SHA,
    )
    assert result["status"] == "FAIL"
    assert result["failures"] == ["CONTROLLED_CANDIDATE_PACKAGE_HASH_MISMATCH"]


def test_explicit_restore_uses_report_bound_package(tmp_path):
    package = tmp_path / f"ddda-candidate-pr-{PR}-{SHA[:12]}-explicit.zip"
    package.write_bytes(b"exact candidate")
    report_path = tmp_path / "result.json"
    report_path.write_text(json.dumps(report(package)), encoding="utf-8")
    result = restore_candidate_evidence_paths(
        report_path,
        repository=REPOSITORY,
        pr_number=PR,
        source_sha=SHA,
        candidate_package_path=package,
    )
    assert result["status"] == "PASS"
    assert Path(result["candidate_package_path"]).name == package.name


def test_explicit_restore_rejects_different_package_name(tmp_path):
    package = tmp_path / f"ddda-candidate-pr-{PR}-{SHA[:12]}-explicit.zip"
    package.write_bytes(b"exact candidate")
    report_path = tmp_path / "result.json"
    report_path.write_text(json.dumps(report(package)), encoding="utf-8")
    other = tmp_path / f"ddda-candidate-pr-{PR}-{SHA[:12]}-other.zip"
    other.write_bytes(package.read_bytes())
    result = restore_candidate_evidence_paths(
        report_path,
        repository=REPOSITORY,
        pr_number=PR,
        source_sha=SHA,
        candidate_package_path=other,
    )
    assert result["failures"] == ["CANDIDATE_EVIDENCE_PACKAGE_IDENTITY_INVALID"]


def test_restore_rejects_ci_candidate_name_for_different_sha(tmp_path):
    other_sha = "b" * 40
    package = tmp_path / f"ddda-candidate-{other_sha}.zip"
    package.write_bytes(b"different source candidate")
    evidence = report(package)
    (tmp_path / "result.json").write_text(json.dumps(evidence), encoding="utf-8")

    result = restore_candidate_evidence(
        tmp_path,
        repository=REPOSITORY,
        pr_number=PR,
        source_sha=SHA,
    )

    assert result["failures"] == ["CANDIDATE_EVIDENCE_PACKAGE_IDENTITY_INVALID"]


def test_restore_rejects_short_sha_package_with_wrong_artifact_identity(tmp_path):
    package = tmp_path / f"ddda-candidate-{SHA[:12]}.zip"
    package.write_bytes(b"candidate with mismatched artifact identity")
    evidence = report(package)
    evidence["package"]["artifact_name"] = f"ddda-candidate-{'b' * 40}"
    (tmp_path / "result.json").write_text(json.dumps(evidence), encoding="utf-8")

    result = restore_candidate_evidence(
        tmp_path,
        repository=REPOSITORY,
        pr_number=PR,
        source_sha=SHA,
    )

    assert result["failures"] == ["CANDIDATE_EVIDENCE_PACKAGE_IDENTITY_INVALID"]
