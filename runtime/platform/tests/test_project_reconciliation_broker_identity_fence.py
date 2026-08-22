from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/assistant-command.yml"


def test_project_reconciliation_final_identity_fence_closes_late_drift_window():
    workflow = WORKFLOW.read_text(encoding="utf-8-sig")
    remaining_guard = workflow.index("if ($remaining -ne 0)")
    final_pr = workflow.index("$finalPr = Invoke-RestMethod", remaining_guard)
    final_branch = workflow.index("$finalBranch = Invoke-RestMethod", final_pr)
    accepted = workflow.index("$selectedRun = $run", final_branch)

    assert remaining_guard < final_pr < final_branch < accepted
    assert "PR head drifted before evidence acceptance" in workflow
    assert "if ($finalSourceSha -ne $sourceSha)" in workflow
    assert "during final evidence acceptance" in workflow
