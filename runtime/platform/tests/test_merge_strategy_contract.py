from pathlib import Path
import json
import os
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "config/platform/development-policy.yaml"
MERGE_SCRIPT = ROOT / "scripts/platform/Invoke-DDDAGovernedMergePr.ps1"
SUPPORT = ROOT / "scripts/platform/DDDAMergeStrategySupport.ps1"


def test_merge_policy_is_ancestry_preserving_by_default():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    strategy = policy["merge_strategy"]
    assert policy["merge_method"] == "merge"
    assert strategy["default_method"] == "merge"
    assert strategy["unknown_impact_allowed_methods"] == ["merge"]
    assert strategy["impacts"]["HIGH"]["allowed_methods"] == ["merge"]
    assert strategy["impacts"]["BREAKING"]["allowed_methods"] == ["merge"]
    for impact in ("LOW", "MEDIUM"):
        assert strategy["impacts"][impact]["default_method"] == "merge"
        assert strategy["impacts"][impact]["allowed_methods"] == ["merge", "squash"]
        assert strategy["impacts"][impact]["squash_requires_human_exception"] is True


def test_bootstrap_transition_is_exact_and_prospective():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    transition = policy["merge_strategy"]["bootstrap_transition"]
    assert transition["change_issue"] == 70
    assert transition["legacy_base_sha"] == "297f61f6012f180e70805999df2ac1abe9616a05"
    assert transition["legacy_merge_method"] == "squash"
    assert transition["prospective_after_integration"] is True


def test_bootstrap_binds_to_change_request_relation_not_pr_number():
    support = SUPPORT.read_text(encoding="utf-8-sig")
    assert '$Pr -ne [int]$transition.change_issue' not in support
    assert 'Implements|Closes' in support
    assert '$relations.Count -ne 1' in support


def test_governed_merge_fails_strategy_before_irreversible_merge_and_reads_back_ancestry():
    text = MERGE_SCRIPT.read_text(encoding="utf-8-sig")
    strategy_pos = text.index("Resolve-DDDAMergeStrategy")
    merge_pos = text.index("Merge-DDDAGitHubPullRequest")
    ancestry_pos = text.index("Post-merge ancestry read-back")
    assert strategy_pos < merge_pos < ancestry_pos
    assert 'compare/$headSha...$mergeCommit' in text
    assert 'source_to_result_relation = $sourceToResultRelation' in text
    assert 'ancestry_verified = $ancestryVerified' in text
    assert 'release_side_effects = $false' in text
    assert 'tag_side_effects = $false' in text


def test_rebase_is_not_canonical_and_human_exception_cannot_be_automated():
    support = SUPPORT.read_text(encoding="utf-8-sig")
    assert 'if ($method -notin @("merge", "squash"))' in support
    assert "Rebase není povolen" in support
    assert "Squash exception musí mít lidskou GitHub provenance" in support
    assert 'CommentAuthorType -eq "Bot"' in support
    assert "validated_source_head_sha" in support
    assert "candidate_package_sha256" in support


def test_behavioral_merge_strategy_contract():
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        if os.name == "nt":
            pytest.fail("Windows platform test runtime must expose PowerShell for merge-strategy regression")
        pytest.skip("PowerShell is not installed on this non-Windows validation worker")
    script = ROOT / "tests/powershell/Test-DDDAMergeStrategy.ps1"
    completed = subprocess.run(
        [executable, "-NoProfile", "-File", str(script), "-PlatformPath", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert "DDDA merge strategy contract: PASS" in completed.stdout
