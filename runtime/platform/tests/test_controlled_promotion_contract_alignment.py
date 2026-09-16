from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXECUTOR = ROOT / "scripts" / "platform" / "Invoke-DDDAPromotePr.ps1"
WORKFLOW = ROOT / ".github" / "workflows" / "controlled-release-candidate-validation.yml"


def test_controlled_promotion_executor_uses_the_shared_versioned_branch_contract():
    text = EXECUTOR.read_text(encoding="utf-8-sig")

    assert 'DDDAReleaseGovernanceSupport.ps1' in text
    assert 'Test-DDDAControlledReleaseSourceBranch -Branch $headRefName -Version $Version' in text
    assert '$headRefName -ne $expectedControlledRef' not in text


def test_promotion_dry_run_uses_hrdr_bound_evidence_before_staging():
    text = WORKFLOW.read_text(encoding="utf-8")
    dry_run = text.split("  release-scope-dry-run:\n", 1)[1]

    restore = dry_run.index("      - name: Restore exact technical evidence")
    verify = dry_run.index("      - name: Verify restored exact evidence")
    hrdr = dry_run.index("      - name: Read exact Human Release Decision Record")
    promotion = dry_run.index("      - name: Run governed promotion dry-run only")
    staging = dry_run.index("      - name: Stage promotion dry-run evidence")

    assert hrdr < restore < verify < promotion < staging
    verify_block = dry_run[verify:promotion]
    assert "--output restored-evidence.json" in verify_block
    assert "Restored exact candidate evidence did not pass." in verify_block
