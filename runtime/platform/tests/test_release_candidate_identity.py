import json
import pytest
from runtime.platform.governance_kernel import evaluate_release_candidate_pr_identity

SHA = "a" * 40
REPO = "romanhlavac/ddd-accelerator"

def context(kind="NORMAL", branch="release/0.1.2", generation=1):
    return {
        "schema_version": 1, "context_kind": "ddda_candidate_context",
        "candidate_kind": kind,
        "release_mode": "STANDARD" if kind == "NORMAL" else "CONTROLLED_RECOVERY",
        "operation": "promotion_dry_run", "repository": REPO, "pr": 202,
        "base_branch": "main", "source_branch": branch, "source_sha": SHA,
        "version": "0.1.2", "generation": generation, "pr_state": "READY",
        "validation_evidence": None, "authoritative_check_summary": None,
        "human_review_reference": None, "hrdr_reference": None,
        "physical_scope_reference": None, "project_evidence_reference": None,
    }

def pr(kind="NORMAL", branch="release/0.1.2"):
    recovery = kind == "RECOVERY"
    return {
        "number": 202, "state": "open", "draft": False,
        "title": ("[RELEASE][0.1.2][RECOVERY] Controlled release candidate"
                  if recovery else "[RELEASE][0.1.2] Release candidate"),
        "labels": [{"name": "release-candidate"}] +
                  ([{"name": "controlled-recovery"}] if recovery else []),
        "head": {"ref": branch, "sha": SHA, "repo": {"full_name": REPO}},
        "base": {"ref": "main"},
        "body": ('<!-- ddda:release-candidate:v1 -->\n```json\n'
                 + json.dumps({"schema_version": 1,
                               "kind": "controlled_recovery" if recovery else "normal",
                               "version": "0.1.2"})
                 + '\n```\n'),
    }

def decision(c, p):
    return evaluate_release_candidate_pr_identity(c, p)

def test_normal_and_recovery_identity_pass():
    assert decision(context(), pr()).status == "PASS"
    branch = "release/0.1.2-controlled-recovery-source-v2"
    assert decision(context("RECOVERY", branch, 2), pr("RECOVERY", branch)).status == "PASS"

@pytest.mark.parametrize("change, expected", [
    (lambda p: p.update(title="fix(release): adjust validator"),
     "RELEASE_CANDIDATE_TITLE_MISMATCH"),
    (lambda p: p.update(labels=[]), "RELEASE_CANDIDATE_LABEL_MISSING"),
    (lambda p: p["head"].update(ref="fix/202-release-code"),
     "RELEASE_CANDIDATE_BRANCH_MISMATCH"),
    (lambda p: p.update(body="release candidate"),
     "RELEASE_CANDIDATE_MARKER_INVALID"),
    (lambda p: p.update(body=p["body"] + p["body"]),
     "RELEASE_CANDIDATE_MARKER_INVALID"),
    (lambda p: p.update(body=p["body"].replace('"normal"', '"controlled_recovery"')),
     "RELEASE_CANDIDATE_MARKER_MISMATCH"),
    (lambda p: p.update(body=p["body"].replace('"kind":', '"kind":"normal","kind":')),
     "RELEASE_CANDIDATE_MARKER_INVALID"),
    (lambda p: p["labels"].append({"name": "controlled-recovery"}),
     "RELEASE_CANDIDATE_RECOVERY_LABEL_MISMATCH"),
])
def test_identity_disagreement_fails_closed(change, expected):
    c, p = context(), pr()
    change(p)
    assert expected in decision(c, p).failure_codes

def test_recovery_requires_all_four_surfaces_and_canonical_generation():
    branch = "release/0.1.2-controlled-recovery-source"
    c, p = context("RECOVERY", branch), pr("RECOVERY", branch)
    p["title"] = "[RELEASE][0.1.2] Release candidate"
    p["labels"] = [{"name": "release-candidate"}]
    p["body"] = pr()["body"]
    codes = decision(c, p).failure_codes
    assert "RELEASE_CANDIDATE_TITLE_MISMATCH" in codes
    assert "RELEASE_CANDIDATE_RECOVERY_LABEL_MISMATCH" in codes
    assert "RELEASE_CANDIDATE_MARKER_MISMATCH" in codes
    c["source_branch"] = branch + "-v1"
    p["head"]["ref"] = branch + "-v1"
    assert "RECOVERY_BRANCH_INVALID" in decision(c, p).failure_codes
