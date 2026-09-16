import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "platform" / "Test-DDDAControlledReleaseCandidate.py"
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
