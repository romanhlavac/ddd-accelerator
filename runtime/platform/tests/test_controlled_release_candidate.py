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


def test_pre_promotion_candidate_validation_keeps_release_notes_for_promotion_only() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    cli = (ROOT / "ddda.ps1").read_text(encoding="utf-8")
    test_runner = (ROOT / "scripts/platform/Invoke-DDDAPlatformTest.ps1").read_text(encoding="utf-8")
    validator = (ROOT / "scripts/platform/Invoke-DDDAValidatePr.ps1").read_text(encoding="utf-8")
    guards = (ROOT / "tests/powershell/Test-DDDAPromotionGuards.ps1").read_text(encoding="utf-8")

    assert r".\candidate\ddda.ps1 test -Suite component -PrePromotionCandidate -NonInteractive" in workflow
    assert "-PrePromotionCandidate" in workflow
    assert "[switch]$PrePromotionCandidate" in cli
    assert "[switch]$PrePromotionCandidate" in test_runner
    assert "[switch]$PrePromotionCandidate" in validator
    assert "[switch]$PrePromotionCandidate" in guards
    assert "if (-not $PrePromotionCandidate)" in guards
    assert "Public release promotion must stay strictly gated" in guards
    assert "Assert-DDDAPlatformChangelogRelease" in guards


def test_technical_validation_stages_report_bound_exact_evidence_before_upload() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "Stage exact validation evidence" in workflow
    assert "$env:LOCALAPPDATA" in workflow
    assert "$env:RUNNER_TEMP" in workflow
    assert "Expected exactly one exact validation report" in workflow
    assert "Get-Content -LiteralPath $reports[0].FullName -Raw -Encoding utf8 | ConvertFrom-Json" in workflow
    assert "[string]$report.source.commit -ne $env:SOURCE_SHA" in workflow
    assert "[System.IO.Path]::GetFileName([string]$report.package.path)" in workflow
    assert "Get-FileHash -LiteralPath $packagePath -Algorithm SHA256" in workflow
    assert "Exact package hash does not match the canonical validation report." in workflow
    assert "ddda-candidate-pr-$env:CANDIDATE_PR-$env:SOURCE_SHA-*.zip" not in workflow
    assert "${{ runner.temp }}/controlled-candidate-evidence/**" in workflow
    assert "${{ env.LOCALAPPDATA }}" not in workflow
    assert "if-no-files-found: error" in workflow

def test_restored_candidate_evidence_aggregates_paginated_artifact_pages_fail_closed() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert workflow.count('gh api --paginate --slurp "repos/$env:REPOSITORY/actions/artifacts?per_page=100"') == 2
    assert workflow.count('$pages = @(gh api --paginate --slurp') == 2
    assert workflow.count('$artifacts = @($pages | ForEach-Object { @($_.artifacts) })') == 2
    assert '$all.artifacts' not in workflow
    assert workflow.count("Expected exactly one unexpired exact validation artifact") == 2

def test_hrdr_scaffold_forwards_report_bound_package_through_public_review_entrypoint() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    cli = (ROOT / "ddda.ps1").read_text(encoding="utf-8")
    review_command = (ROOT / "scripts/platform/Invoke-DDDAReviewPr.ps1").read_text(encoding="utf-8")

    assert "-CandidatePackagePath $env:candidate_package" in workflow
    assert "[string]$CandidatePackagePath" in cli
    assert 'if (-not [string]::IsNullOrWhiteSpace($CandidatePackagePath)) { $arguments += @("-CandidatePackagePath", $CandidatePackagePath) }' in cli
    assert "[string]$CandidatePackagePath" in review_command
    assert "-PackagePath $CandidatePackagePath" in review_command


def test_hrdr_milestone_discovery_materializes_paginated_api_arrays_without_nesting() -> None:
    support = (ROOT / "scripts/platform/DDDAReleaseGovernanceSupport.ps1").read_text(encoding="utf-8-sig")
    start = support.index("function Get-DDDAReleaseMilestoneScope")
    end = support.index("function Get-DDDAHrdrComments")
    scope_reader = support[start:end]

    assert '$response = Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/milestones?state=all&per_page=100&page=$page" -Token $Token' in scope_reader
    assert '$response = Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/issues?state=all&milestone=$([int]$milestone.number)&per_page=100&page=$page" -Token $Token' in scope_reader
    assert scope_reader.count("$batch = @($response)") == 2
    assert "@(Invoke-DDDAGitHubApi -Method GET -Path \"repos/$RepositorySlug/milestones" not in scope_reader
    assert "@(Invoke-DDDAGitHubApi -Method GET -Path \"repos/$RepositorySlug/issues" not in scope_reader


def test_hrdr_scaffold_has_only_the_pr_comment_write_capability_it_needs() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "issues: write" in workflow
    assert "pull-requests: write" in workflow
    assert "pull-requests: read" not in workflow
    assert "pull-requests: write\n  contents: write" not in workflow
    assert "contents: write" not in workflow
