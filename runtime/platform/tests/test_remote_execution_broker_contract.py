from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REQUEST = ROOT / "scripts/platform/Test-DDDARemoteExecutionRequest.ps1"
WORKFLOW = ROOT / ".github/workflows/assistant-command.yml"
REMOTE_RUNBOOK = ROOT / "docs/developer-guide/remote-validation-broker.md"

HEAD = "a" * 40
REPOSITORY = "romanhlavac/ddd-accelerator"


def run_request(
    command: str,
    *,
    actor: str = "romanhlavac",
    head_sha: str = HEAD,
    head_repository: str = REPOSITORY,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(REQUEST),
            "-PlatformPath",
            str(ROOT),
            "-Repository",
            REPOSITORY,
            "-Actor",
            actor,
            "-Pr",
            "95",
            "-HeadSha",
            head_sha,
            "-HeadRepository",
            head_repository,
            "-CommandText",
            command,
            "-Json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_remote_broker_tolerates_optional_miro_team_id():
    text = REQUEST.read_text(encoding="utf-8-sig")
    assert '$remote.PSObject.Properties.Name -contains "miro_team_id"' in text
    assert 'miro_team_id = $miroTeamId' in text
    assert 'miro_team_id = [string]$remote.miro_team_id' not in text


def test_remediation_script_existence_is_checked_after_exact_pr_checkout():
    request = REQUEST.read_text(encoding="utf-8-sig")
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")

    assert 'Remediation script does not exist at the exact PR head' not in request
    checkout = workflow.index('name: Checkout exact PR branch without write credentials')
    run = workflow.index('name: Run guarded remediation without push')
    existence = workflow.index('Authorized remediation script does not exist at exact PR head')
    assert checkout < run < existence


def test_remediation_push_refspec_avoids_powershell_env_colon_ambiguity():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")

    assert "$refspec = '{0}:{1}' -f $env:VALIDATED_AFTER_SHA, $targetRef" in workflow
    assert 'git push origin $refspec' in workflow
    assert 'git push origin "$env:VALIDATED_AFTER_SHA:' not in workflow


def test_broker_failure_comment_uses_issues_rest_api():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")
    assert 'gh api --method POST "repos/$env:REPOSITORY/issues/$env:PR_NUMBER/comments"' in workflow
    assert 'gh pr comment $env:PR_NUMBER' not in workflow
    assert 'issues: write' in workflow


def test_broker_result_comment_failure_is_non_destructive():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")

    start = workflow.index('- name: Comment execution result')
    end = workflow.index('  reconcile-project:', start)
    block = workflow[start:end]
    assert 'if: always()' in block
    assert 'continue-on-error: true' in block
    assert workflow.index('- name: Upload execution evidence') < start


def test_valid_actor_exact_sha_and_canonical_reconcile_command_authorize_pass():
    result = run_request(f"/ddda reconcile-project --expected-sha {HEAD}")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["action"] == "reconcile-project"
    assert payload["head_sha"] == HEAD
    assert payload["expected_sha"] == HEAD
    assert payload["canonical_workflow"] == ".github/workflows/reconcile-ddda-project-backlog.yml"
    assert payload["reconciliation_source_ref"] == "main"
    assert payload["merge_allowed"] is False
    assert payload["promotion_allowed"] is False
    assert payload["release_allowed"] is False
    assert payload["tag_allowed"] is False


def test_reconcile_sha_mismatch_fails_before_dispatch_authorization():
    result = run_request(f"/ddda reconcile-project --expected-sha {'b' * 40}")
    assert result.returncode != 0
    assert "expected SHA does not match the current PR head" in (result.stderr + result.stdout)


def test_unauthorized_actor_fails_reconcile_authorization():
    result = run_request(
        f"/ddda reconcile-project --expected-sha {HEAD}", actor="not-authorized"
    )
    assert result.returncode != 0
    assert "is not allowed" in (result.stderr + result.stdout)


def test_wrong_repository_or_fork_fails_reconcile_authorization():
    result = run_request(
        f"/ddda reconcile-project --expected-sha {HEAD}",
        head_repository="example/fork",
    )
    assert result.returncode != 0
    assert "same-repository" in (result.stderr + result.stdout)


def test_unsupported_command_fails_closed():
    result = run_request("/ddda reconcile-project")
    assert result.returncode != 0
    assert "Unsupported remote DDDA command" in (result.stderr + result.stdout)


def test_arbitrary_workflow_name_cannot_be_injected():
    result = run_request(
        f"/ddda reconcile-project --expected-sha {HEAD} --workflow evil.yml"
    )
    assert result.returncode != 0
    assert "Unsupported remote DDDA command" in (result.stderr + result.stdout)


def test_extra_args_and_command_injection_fail_closed():
    for suffix in (
        " --ref feature/other",
        " ; Write-Host pwned",
        " && echo pwned",
        " --expected-sha " + ("b" * 40),
    ):
        result = run_request(f"/ddda reconcile-project --expected-sha {HEAD}{suffix}")
        assert result.returncode != 0, suffix


def test_reconcile_actions_write_is_isolated_to_dedicated_job():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")
    reconcile_start = workflow.index("  reconcile-project:")
    before = workflow[:reconcile_start]
    reconcile = workflow[reconcile_start:]
    assert "actions: write" not in before
    assert reconcile.count("actions: write") == 1
    assert "group: ddda-project-backlog-reconciliation" in reconcile
    assert "cancel-in-progress: false" in reconcile


def test_project_credential_is_not_available_to_broker_workflow_or_evidence():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")
    assert "DDDA_GITHUB_PROJECT_TOKEN" not in workflow
    assert "ddda-backlog-governance" not in workflow
    assert "No Project credential was exposed to Chat/Work or broker evidence" in workflow


def test_broker_dispatch_target_is_fixed_canonical_workflow_only():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")
    assert "$workflowEndpoint = 'reconcile-ddda-project-backlog.yml'" in workflow
    assert "Only the canonical DDDA Project reconciliation workflow may be dispatched" in workflow
    assert "$env:CANONICAL_WORKFLOW -ne '.github/workflows/reconcile-ddda-project-backlog.yml'" in workflow
    assert "actions/workflows/$workflowEndpoint/dispatches" in workflow
    assert "actions/workflows/$env:" not in workflow


def test_reconcile_waits_for_existing_privileged_run_before_dispatch():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")
    wait = workflow.index("Wait-NoActiveReconciliation")
    dispatch = workflow.index("$dispatchUri =", wait)
    assert wait < dispatch
    assert "queued" in workflow
    assert "in_progress" in workflow


def test_workflow_failure_can_never_be_broker_pass():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")
    assert "if ([string]$run.conclusion -ne 'success')" in workflow
    assert "broker cannot issue PASS" in workflow


def test_wrong_reconciliation_source_sha_is_rejected_or_retried():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")
    assert "if ([string]$run.head_sha -ne $sourceSha)" in workflow
    assert "Canonical source moved from $sourceSha" in workflow
    assert "$maxAttempts = 3" in workflow


def test_successful_reconciliation_evidence_contains_run_and_artifact_identity():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")
    for key in (
        "workflow_run_id",
        "workflow_conclusion",
        "audit_artifact_id",
        "audit_artifact_name",
        "reconciliation_source_sha",
    ):
        assert key in workflow
    assert "workflow_run_id=$($selectedRun.id)" in workflow
    assert "audit_artifact_id=$($selectedArtifact.id)" in workflow


def test_reconciliation_acceptance_requires_zero_remaining_mismatches():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")
    assert "$auditRemaining = [int]$audit.remaining_count" in workflow
    assert "$presentationRemaining = [int]$presentation.remaining_count" in workflow
    assert "$releaseRemaining = [int]$release.remaining_count" in workflow
    assert "if ($remaining -ne 0)" in workflow
    assert '"remaining_mismatches=0"' in workflow


def test_reconciliation_pass_cannot_create_hvr_merge_release_or_tag_authorization():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")
    reconcile = workflow[workflow.index("  reconcile-project:") :]
    assert "human_review_status = 'PENDING'" in reconcile
    assert "merge_authorized = $false" in reconcile
    assert "release_authorized = $false" in reconcile
    assert "tag_authorized = $false" in reconcile
    assert "No Human Review, merge, tag, release or promotion was performed" in reconcile


def test_browser_authorization_is_bootstrap_not_recurring_project_reconcile_step():
    runbook = REMOTE_RUNBOOK.read_text(encoding="utf-8")
    assert "HUMAN_BOOTSTRAP_ONLY" in runbook
    assert "nikoli o opakovaný operating step" in runbook
    assert "Browser/device authorization" not in runbook.split("## Canonical GitHub Project reconciliation broker", 1)[1].split("## Runtime isolation", 1)[0]


def test_default_branch_activation_constraint_is_explicit_not_bypassed():
    runbook = REMOTE_RUNBOOK.read_text(encoding="utf-8")
    assert "Default-branch activation boundary" in runbook
    assert "nemůže sama sobě před merge vytvořit produkční `issue_comment` end-to-end důkaz" in runbook
    assert "ruční Project GUI" in runbook
