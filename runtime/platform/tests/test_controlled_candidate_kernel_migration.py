from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import hashlib

from runtime.platform.governance_kernel import KernelDecision


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/platform/Test-DDDAControlledReleaseCandidate.py"


def load_module():
    spec = spec_from_file_location("controlled_candidate_kernel_migration", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request(*, branch: str, draft: bool, state: str = "open") -> dict:
    return {
        "number": 103,
        "state": state,
        "draft": draft,
        "head": {
            "sha": "a" * 40,
            "ref": branch,
            "repo": {"full_name": "romanhlavac/ddd-accelerator"},
        },
        "base": {"ref": "main"},
        "body": "Controlled release-source candidate — DDDA 0.1.1",
    }


def evaluate(module, pr: dict, operation: str = "technical_validation") -> dict:
    return module.validate_request(
        pr,
        repository="romanhlavac/ddd-accelerator",
        pr_number=103,
        source_sha="a" * 40,
        version="0.1.1",
        operation=operation,
    )


def test_controlled_candidate_selection_calls_shared_kernel():
    module = load_module()
    observed = {}

    def fake_kernel(context):
        observed.update(context)
        return KernelDecision(
            status="FAIL",
            operation=context["operation"],
            failure_codes=("RECOVERY_BRANCH_INVALID",),
            authorization_required=False,
        )

    module.evaluate_candidate_identity = fake_kernel
    result = evaluate(
        module,
        request(branch="release/0.1.1-controlled-recovery-source", draft=True),
    )
    assert observed["candidate_kind"] == "RECOVERY"
    assert observed["release_mode"] == "CONTROLLED_RECOVERY"
    assert observed["generation"] == 1
    assert result["failures"] == ["CONTROLLED_CANDIDATE_BRANCH_INVALID"]


def test_first_and_superseding_generation_preserve_characterized_pass():
    module = load_module()
    first = evaluate(
        module,
        request(branch="release/0.1.1-controlled-recovery-source", draft=True),
    )
    superseding = evaluate(
        module,
        request(branch="release/0.1.1-controlled-recovery-source-v2", draft=True),
    )
    assert first["status"] == "PASS"
    assert superseding["status"] == "PASS"


def test_invalid_generation_and_ready_validation_preserve_public_failures():
    module = load_module()
    invalid_generation = evaluate(
        module,
        request(branch="release/0.1.1-controlled-recovery-source-v1", draft=True),
    )
    ready_validation = evaluate(
        module,
        request(branch="release/0.1.1-controlled-recovery-source", draft=False),
    )
    assert invalid_generation["failures"] == ["CONTROLLED_CANDIDATE_BRANCH_INVALID"]
    assert ready_validation["failures"] == ["CONTROLLED_CANDIDATE_MUST_REMAIN_OPEN_DRAFT"]


def test_ready_dry_run_and_closed_candidate_preserve_characterized_results():
    module = load_module()
    ready = evaluate(
        module,
        request(branch="release/0.1.1-controlled-recovery-source", draft=False),
        operation="release_scope_dry_run",
    )
    closed = evaluate(
        module,
        request(
            branch="release/0.1.1-controlled-recovery-source",
            draft=True,
            state="closed",
        ),
    )
    assert ready["status"] == "PASS"
    assert closed["failures"] == ["CONTROLLED_CANDIDATE_MUST_REMAIN_OPEN"]


def test_validation_package_binding_calls_shared_kernel(tmp_path):
    module = load_module()
    package = tmp_path / "candidate.zip"
    package.write_bytes(b"one physical candidate")
    package_sha = hashlib.sha256(package.read_bytes()).hexdigest()
    observed = {}

    def fake_kernel(context):
        observed.update(context)
        return KernelDecision(
            status="FAIL",
            operation="validate",
            failure_codes=("CANDIDATE_PACKAGE_SHA256_MISMATCH",),
            authorization_required=False,
        )

    module.evaluate_candidate_package_binding = fake_kernel
    result = module.validate_validation_evidence(
        {
            "status": "PASS",
            "source": {
                "repository": "romanhlavac/ddd-accelerator",
                "pr": 103,
                "commit": "a" * 40,
            },
            "package": {"sha256": package_sha},
        },
        repository="romanhlavac/ddd-accelerator",
        pr_number=103,
        source_sha="a" * 40,
        package_path=package,
    )
    evidence = observed["validation_evidence"]
    assert evidence["package_present"] is True
    assert evidence["observed_package_sha256"] == package_sha
    assert result["failures"] == ["CONTROLLED_CANDIDATE_PACKAGE_HASH_MISMATCH"]
