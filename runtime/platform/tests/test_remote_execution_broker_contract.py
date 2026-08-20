from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REQUEST = ROOT / "scripts/platform/Test-DDDARemoteExecutionRequest.ps1"
WORKFLOW = ROOT / ".github/workflows/assistant-command.yml"


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

    assert '$refspec = \'{0}:{1}\' -f $env:VALIDATED_AFTER_SHA, $targetRef' in workflow
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
    block = workflow[start:]
    assert 'if: always()' in block
    assert 'continue-on-error: true' in block
    assert workflow.index('- name: Upload execution evidence') < start
