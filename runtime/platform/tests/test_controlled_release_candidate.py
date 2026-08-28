import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "platform" / "Test-DDDAControlledReleaseCandidate.py"
WORKFLOW = ROOT / ".github" / "workflows" / "controlled-release-candidate-validation.yml"
SPEC = importlib.util.spec_from_file_location("controlled_candidate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def candidate(*, sha="a" * 40, draft=True, ref="release/0.1.1-controlled-recovery-source"):
    return {
        "number": 103,
        "state": "open",
        "draft": draft,
        "head": {"sha": sha, "ref": ref, "repo": {"full_name": "romanhlavac/ddd-accelerator"}},
        "base": {"ref": "main"},
        "body": "## Controlled release-source candidate — DDDA 0.1.1",
    }


def validate(pr, **overrides):
    arguments = {
        "repository": "romanhlavac/ddd-accelerator",
        "pr_number": 103,
        "source_sha": "a" * 40,
        "version": "0.1.1",
        "operation": "technical_validation",
    }
    arguments.update(overrides)
    return MODULE.validate_request(pr, **arguments)


def test_accepts_only_exact_controlled_candidate_identity():
    assert validate(candidate())["status"] == "PASS"


def test_rejects_non_draft_or_wrong_branch_even_with_matching_sha():
    result = validate(candidate(draft=False, ref="feature/release-validation"))
    assert result["status"] == "FAIL"
    assert "CONTROLLED_CANDIDATE_MUST_REMAIN_OPEN_DRAFT" in result["failures"]
    assert "CONTROLLED_CANDIDATE_BRANCH_INVALID" in result["failures"]


def test_rejects_sha_drift_and_unknown_operation():
    result = validate(candidate(), source_sha="b" * 40, operation="publish_release")
    assert result["status"] == "FAIL"
    assert "CONTROLLED_CANDIDATE_HEAD_SHA_MISMATCH" in result["failures"]
    assert "CONTROLLED_CANDIDATE_OPERATION_INVALID" in result["failures"]


def test_binds_reusable_package_to_exact_validation_report(tmp_path):
    package = tmp_path / "candidate.zip"
    package.write_bytes(b"exact physical package")
    import hashlib

    report = {
        "status": "PASS",
        "source": {"repository": "romanhlavac/ddd-accelerator", "pr": 103, "commit": "a" * 40},
        "package": {"sha256": hashlib.sha256(package.read_bytes()).hexdigest()},
    }
    assert MODULE.validate_validation_evidence(
        report,
        repository="romanhlavac/ddd-accelerator",
        pr_number=103,
        source_sha="a" * 40,
        package_path=package,
    )["status"] == "PASS"


def test_rejects_package_or_report_identity_drift(tmp_path):
    package = tmp_path / "candidate.zip"
    package.write_bytes(b"changed package")
    report = {"status": "PASS", "source": {"repository": "wrong", "pr": 99, "commit": "b" * 40}, "package": {"sha256": "0" * 64}}
    result = MODULE.validate_validation_evidence(
        report,
        repository="romanhlavac/ddd-accelerator",
        pr_number=103,
        source_sha="a" * 40,
        package_path=package,
    )
    assert result["status"] == "FAIL"
    assert "CONTROLLED_CANDIDATE_VALIDATION_SHA_MISMATCH" in result["failures"]
    assert "CONTROLLED_CANDIDATE_PACKAGE_HASH_MISMATCH" in result["failures"]


def test_technical_validation_binds_checkout_to_identified_selection_output():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert """      - name: Read live candidate identity
        id: selection""" in workflow
    assert "source_sha: ${{ steps.selection.outputs.source_sha }}" in workflow
    assert "ref: ${{ needs.select.outputs.source_sha }}" in workflow
    assert "Candidate checkout SHA '$actual' does not match requested SHA '$env:SOURCE_SHA'." in workflow
