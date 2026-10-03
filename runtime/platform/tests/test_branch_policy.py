import json
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.platform.branch_policy import (
    PROVENANCE_PATH, STAGING_PREFIX, evaluate_automation_cleanup,
    evaluate_branch, parse_automation_name,
)


POLICY = json.loads(Path("config/governance/branch-policy.json").read_text(encoding="utf-8"))
SHA = "a" * 40


def test_canonical_persistent_taxonomy_and_automation_exclusion():
    for branch in ("feature/65-branch-governance", "fix/65-branch-governance", "docs/65-branch-policy", "release/0.1.2"):
        decision = evaluate_branch(branch, head_sha=SHA, pr_number=197, policy=POLICY)
        assert decision.classification == "PERSISTENT_IMPLEMENTATION"
        assert decision.allowed_implementation_pr
    for branch in ("automation/project-audit-123", "automation/project-audit-abc", "fix/no-issue", "release/0.1.1-controlled-recovery-source-v4"):
        assert not evaluate_branch(branch, head_sha=SHA, pr_number=197, policy=POLICY).allowed_implementation_pr
    assert parse_automation_name("automation/project-audit-123") == ("project-audit", 123)
    assert parse_automation_name("automation/project-audit-abc") is None


def test_new_legacy_prefixes_fail_and_exact_active_exceptions_expire():
    for prefix in ("feat", "chore", "gov", "governance", "agent"):
        assert not evaluate_branch(f"{prefix}/65-new-work", head_sha=SHA, pr_number=197, policy=POLICY).allowed_implementation_pr
    assert evaluate_branch("feat/88-github-browser-auth-bootstrap", head_sha=POLICY["legacy_exceptions"][0]["head_sha"], pr_number=95, policy=POLICY).allowed_implementation_pr
    assert not evaluate_branch("feat/88-github-browser-auth-bootstrap", head_sha=SHA, pr_number=95, policy=POLICY).allowed_implementation_pr
    assert not evaluate_branch("feat/88-github-browser-auth-bootstrap", head_sha=POLICY["legacy_exceptions"][0]["head_sha"], pr_number=197, policy=POLICY).allowed_implementation_pr
    assert evaluate_branch("release/0.1.1-controlled-recovery-source-v4", head_sha=POLICY["legacy_exceptions"][1]["head_sha"], pr_number=146, policy=POLICY).allowed_implementation_pr


def test_cleanup_only_when_all_proofs_bind_same_run_and_isolated_history():
    provenance = {"schema_version": 1, "kind": "ddda_automation_branch", "branch": "automation/project-audit-123", "purpose": "project-audit", "run_id": 123, "source_sha": "b" * 40, "owner": "romanhlavac"}
    kw = dict(name=provenance["branch"], head_sha=SHA, provenance=provenance, open_pr_numbers=[], changed_paths=[PROVENANCE_PATH, STAGING_PREFIX + "report.json"], source_ancestor=True, run_id=123, run_terminal=True, same_owner_run=False, referenced_by_release_or_audit=False)
    assert evaluate_automation_cleanup(**kw).classification == "SAFE_TO_DELETE"
    for change in ({"open_pr_numbers": [198]}, {"changed_paths": [PROVENANCE_PATH, "src/implementation.py"]}, {"provenance": None}, {"source_ancestor": False}, {"run_id": 124}, {"run_terminal": False}, {"referenced_by_release_or_audit": True}):
        assert evaluate_automation_cleanup(**(kw | change)).classification != "SAFE_TO_DELETE"
    assert evaluate_automation_cleanup(**(kw | {"run_terminal": False, "same_owner_run": True})).classification == "SAFE_TO_DELETE"


def test_historical_names_never_infer_deletion_from_prefix_or_zero_unique_commits():
    kw = dict(head_sha=SHA, provenance=None, open_pr_numbers=[], changed_paths=[], source_ancestor=True, run_id=None, run_terminal=True, same_owner_run=False, referenced_by_release_or_audit=False)
    for branch in ("gov/old-readback", "release/0.1.1-controlled-recovery-source-v4", "automation/pr86-governance-normalization"):
        assert evaluate_automation_cleanup(branch, **kw).classification == "AMBIGUOUS"


def test_managed_automation_branch_cleans_up_success_and_failure_paths():
    path = Path("scripts/platform/Manage-DDDAAutomationBranches.py")
    spec = importlib.util.spec_from_file_location("ddda_manage_automation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Api:
        def request(self, path):
            assert path == "/git/ref/heads/automation/project-audit-123"
            return {"object": {"sha": SHA}}

    api = Api()
    with patch.object(module, "create_branch", return_value=("automation/project-audit-123", SHA)), patch.object(module, "cleanup_branch", return_value={"deleted": True}) as cleanup:
        with module.managed_branch(api, purpose="project-audit", run_id=123, owner="romanhlavac", source_sha="b" * 40):
            pass
        assert cleanup.call_count == 1
        with pytest.raises(RuntimeError, match="staging failed"):
            with module.managed_branch(api, purpose="project-audit", run_id=123, owner="romanhlavac", source_sha="b" * 40):
                raise RuntimeError("staging failed")
        assert cleanup.call_count == 2
