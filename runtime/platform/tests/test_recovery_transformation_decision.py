from copy import deepcopy

from runtime.platform.recovery_transformation import (
    apply_recovery_transformation_decision,
    parse_recovery_transformation_decision_comments,
    path_hash_differences,
)
from runtime.platform.release_governance import GovernanceResult

REPO = "romanhlavac/ddd-accelerator"
CANDIDATE_PR = 103
SOURCE_SHA = "426ae4d6f9bd71f3056dc4705dbb568960035217"
PACKAGE_SHA256 = "15d7ea28cae093049171b47b0df5d8e1555361f9e79d1b032c63e5399e3e9d98"
VERSION = "0.1.1"
OWNER = "romanhlavac"

PR97_SOURCE = "cdb9237391cafc9dbc1779debd834154828b644c"
PR97_RECOVERED = "9170ab04cdde7b82c494ee8888a7989fac9ee799"
PR111_SOURCE = "036a686568f35ec0f9588d5a06cb2994b6c2d22b"
PR111_RECOVERED = "825f156366eee52b7b9b3c573c51df36fe9bcc4d"

PR97_SOURCE_MAP = {
    "config/governance/backlog-policy.yaml": "ffbe698a4b691367936d99f901ed0af6e1545daa",
    "config/governance/github-bootstrap.json": "bd3b74b23666801cc033cb95ee6af75a15385c79",
    "runtime/platform/tests/test_project_backlog_delivery_governance.py": "42fac9e0566b70561ea7c877b44b2d2fe5037c0b",
}
PR97_RECOVERED_MAP = {}
PR111_SOURCE_MAP = {
    ".github/workflows/controlled-release-candidate-validation.yml": "c1825eca56d3c63895c07396a6edb20a4f77eebb",
    "ddda.ps1": "65ac936be2ee6d39d906db40bc3bb5343a84672f",
    "docs/adr/0013-controlled-release-candidate-validation.md": "17b39f990de6d9631a4bf74f98efc6999a947faf",
    "runtime/platform/tests/test_controlled_release_candidate.py": "b4fb4e4356b7db6a555f66db737382d5a1f8e69c",
    "scripts/platform/Invoke-DDDAValidatePr.ps1": "6b9032a55b6f5e8456c39b7c979efd856d813940",
    "tests/powershell/Test-DDDAPromotionGuards.ps1": "5c0a8758ed6132cb685e8381dcf05d29f7541768",
}
PR111_RECOVERED_MAP = {
    "ddda.ps1": "e9cf0553eabaac611a200dec6bc02f1b87572190",
    "scripts/platform/Invoke-DDDAValidatePr.ps1": "d216d9ce65518355030d3f6c07501fe0c549ea50",
    "tests/powershell/Test-DDDAPromotionGuards.ps1": "c5815799393b6577414d3f0e54958e3ab9f93e3a",
}


def decision_record():
    return {
        "schema_version": 1,
        "kind": "recovery_transformation_decision",
        "repository": REPO,
        "pr": CANDIDATE_PR,
        "source_sha": SOURCE_SHA,
        "candidate_package_sha256": PACKAGE_SHA256,
        "version": VERSION,
        "reviewer": OWNER,
        "decision": "approve",
        "decided_at": "2026-09-15T10:56:00Z",
        "rationale": "Approve only the exact frozen-candidate recovery transformations.",
        "transformations": [
            {
                "source_pr": 97,
                "primary_cr": 96,
                "source_merge_commit_sha": PR97_SOURCE,
                "recovered_commit_sha": PR97_RECOVERED,
                "path_decisions": path_hash_differences(PR97_SOURCE_MAP, PR97_RECOVERED_MAP),
            },
            {
                "source_pr": 111,
                "primary_cr": 96,
                "source_merge_commit_sha": PR111_SOURCE,
                "recovered_commit_sha": PR111_RECOVERED,
                "path_decisions": path_hash_differences(PR111_SOURCE_MAP, PR111_RECOVERED_MAP),
            },
        ],
    }


def snapshot():
    return {
        "physical_scope": {
            "recovery_ledger": {
                "entries": [
                    {
                        "source_pr": 97,
                        "primary_cr": 96,
                        "source_merge_commit_sha": PR97_SOURCE,
                        "recovered_commit_sha": PR97_RECOVERED,
                        "changed_path_hashes_match": False,
                        "source_path_hashes": PR97_SOURCE_MAP,
                        "recovered_path_hashes": PR97_RECOVERED_MAP,
                    },
                    {
                        "source_pr": 111,
                        "primary_cr": 96,
                        "source_merge_commit_sha": PR111_SOURCE,
                        "recovered_commit_sha": PR111_RECOVERED,
                        "changed_path_hashes_match": False,
                        "source_path_hashes": PR111_SOURCE_MAP,
                        "recovered_path_hashes": PR111_RECOVERED_MAP,
                    },
                ]
            },
            "recovery_transformation_decision": {
                "status": "PRESENT",
                "comment_id": 5679114537,
                "comment_author": OWNER,
                "record": decision_record(),
            },
        }
    }


def base_result():
    failures = (
        "RECOVERY_LEDGER_PATH_HASH_MISMATCH:PR#97",
        "RECOVERY_LEDGER_PATH_HASH_MISMATCH:PR#111",
        "SCOPE_ITEM_NOT_TERMINAL:#96",
        "SCOPE_ITEM_PROJECT_STATUS:#96",
    )
    return GovernanceResult(
        status="FAIL",
        failures=failures,
        scope_issues=(96,),
        accepted_risk_issues=(),
        side_effects_allowed=False,
    )


def apply(result=None, live=None):
    return apply_recovery_transformation_decision(
        result or base_result(),
        live or snapshot(),
        expected_repository=REPO,
        expected_pr=CANDIDATE_PR,
        expected_source_sha=SOURCE_SHA,
        expected_package_sha256=PACKAGE_SHA256,
        expected_version=VERSION,
        expected_decision_owner=OWNER,
    )


def test_exact_pr97_pr111_decision_removes_only_authorized_path_hash_failures():
    result = apply()
    assert result.status == "FAIL"
    assert result.failures == (
        "SCOPE_ITEM_NOT_TERMINAL:#96",
        "SCOPE_ITEM_PROJECT_STATUS:#96",
    )
    assert result.side_effects_allowed is False


def test_missing_decision_preserves_default_exact_hash_failures():
    live = snapshot()
    del live["physical_scope"]["recovery_transformation_decision"]
    result = apply(live=live)
    assert "RECOVERY_LEDGER_PATH_HASH_MISMATCH:PR#97" in result.failures
    assert "RECOVERY_LEDGER_PATH_HASH_MISMATCH:PR#111" in result.failures


def test_candidate_package_drift_fails_closed_and_preserves_mismatches():
    live = snapshot()
    live["physical_scope"]["recovery_transformation_decision"]["record"][
        "candidate_package_sha256"
    ] = "f" * 64
    result = apply(live=live)
    assert "RECOVERY_TRANSFORMATION_DECISION_PACKAGE_SHA256_MISMATCH" in result.failures
    assert "RECOVERY_LEDGER_PATH_HASH_MISMATCH:PR#97" in result.failures


def test_path_hash_drift_fails_closed_and_preserves_mismatch():
    live = snapshot()
    live["physical_scope"]["recovery_ledger"]["entries"][1]["recovered_path_hashes"][
        "ddda.ps1"
    ] = "f" * 40
    result = apply(live=live)
    assert "RECOVERY_TRANSFORMATION_DECISION_PATH_HASH_MISMATCH:PR#111" in result.failures
    assert "RECOVERY_LEDGER_PATH_HASH_MISMATCH:PR#111" in result.failures


def test_extra_unused_transformation_fails_closed():
    live = snapshot()
    extra = deepcopy(live["physical_scope"]["recovery_transformation_decision"]["record"]["transformations"][0])
    extra["source_pr"] = 999
    extra["source_merge_commit_sha"] = "1" * 40
    extra["recovered_commit_sha"] = "2" * 40
    live["physical_scope"]["recovery_transformation_decision"]["record"]["transformations"].append(extra)
    result = apply(live=live)
    assert "RECOVERY_TRANSFORMATION_DECISION_UNUSED_OR_MISSING_TRANSFORMATION" in result.failures


def test_duplicate_decision_markers_are_invalid_evidence():
    body = "<!-- ddda:recovery-transformation-decision:v1 -->\n```json\n{}\n```"
    evidence = parse_recovery_transformation_decision_comments(
        [
            {"id": 1, "body": body, "user": {"login": OWNER}},
            {"id": 2, "body": body, "user": {"login": OWNER}},
        ]
    )
    assert evidence == {
        "status": "INVALID",
        "reason": "MULTIPLE_MARKERS",
        "marker_count": 2,
    }


def test_stale_decision_is_blocking_when_exact_recovery_no_longer_needs_exception():
    clean = GovernanceResult(
        status="PASS",
        failures=(),
        scope_issues=(96,),
        accepted_risk_issues=(),
        side_effects_allowed=True,
    )
    result = apply(result=clean)
    assert result.status == "FAIL"
    assert "RECOVERY_TRANSFORMATION_DECISION_UNUSED" in result.failures


def test_release_scope_evaluator_integration_accepts_only_exact_authorized_mismatch():
    import runtime.platform.tests.test_release_governance as base

    live = base.snapshot()
    recovered_sha = "e" * 40
    metadata_sha = "f" * 40
    source_merge_sha = "d" * 40
    source_map = {"a.txt": "1" * 40, "b.txt": "2" * 40}
    recovered_map = {"a.txt": "1" * 40}
    live["physical_scope"]["commit_shas"] = [recovered_sha, metadata_sha]
    live["physical_scope"]["recovery_ledger"] = {
        "schema_version": 1,
        "version": base.VERSION,
        "previous_release_tag": "v0.1.0",
        "metadata_commit_shas": [metadata_sha],
        "entries": [
            {
                "recovered_commit_sha": recovered_sha,
                "source_pr": 71,
                "primary_cr": 9,
                "source_pr_merged": True,
                "source_primary_crs": [9],
                "source_merge_commit_sha": source_merge_sha,
                "observed_source_merge_commit_sha": source_merge_sha,
                "changed_path_hashes_match": False,
                "source_path_hashes": source_map,
                "recovered_path_hashes": recovered_map,
            }
        ],
    }
    live["physical_scope"]["recovery_transformation_decision"] = {
        "status": "PRESENT",
        "comment_id": 1,
        "comment_author": "romanhlavac",
        "record": {
            "schema_version": 1,
            "kind": "recovery_transformation_decision",
            "repository": base.REPO,
            "pr": base.PR,
            "source_sha": base.SHA,
            "candidate_package_sha256": base.PACKAGE,
            "version": base.VERSION,
            "reviewer": "romanhlavac",
            "decision": "approve",
            "decided_at": "2026-09-15T10:56:00Z",
            "rationale": "exact bounded recovery transformation",
            "transformations": [
                {
                    "source_pr": 71,
                    "primary_cr": 9,
                    "source_merge_commit_sha": source_merge_sha,
                    "recovered_commit_sha": recovered_sha,
                    "path_decisions": [
                        {
                            "path": "b.txt",
                            "source_present": True,
                            "source_blob_sha": "2" * 40,
                            "recovered_present": False,
                            "recovered_blob_sha": None,
                        }
                    ],
                }
            ],
        },
    }

    result = base.evaluate(live=live)

    assert result.status == "PASS"
    assert result.failures == ()
    assert result.side_effects_allowed is True


def test_collector_enrichment_reads_marker_and_exact_mismatch_path_maps():
    from runtime.platform.recovery_transformation import (
        augment_recovery_transformation_evidence,
    )

    source_sha = "a" * 40
    recovered_sha = "b" * 40
    physical = {
        "recovery_ledger": {
            "entries": [
                {
                    "source_pr": 97,
                    "primary_cr": 96,
                    "source_merge_commit_sha": source_sha,
                    "recovered_commit_sha": recovered_sha,
                    "changed_path_hashes_match": False,
                }
            ]
        }
    }
    body = (
        "<!-- ddda:recovery-transformation-decision:v1 -->\n"
        "```json\n{\"schema_version\":1}\n```"
    )

    def fake_comments(path, _token):
        assert path == "repos/owner/repo/issues/103/comments"
        return [{"id": 5, "body": body, "user": {"login": "romanhlavac"}}]

    def fake_hashes(_repo, sha, _token):
        if sha == source_sha:
            return {"a.txt": "c" * 40}
        if sha == recovered_sha:
            return {"a.txt": "d" * 40}
        raise AssertionError(sha)

    actual = augment_recovery_transformation_evidence(
        physical,
        repository="owner/repo",
        pr=103,
        token="token",
        fetch_comments=fake_comments,
        fetch_commit_path_hashes=fake_hashes,
    )

    assert actual["recovery_transformation_decision"] == {
        "status": "PRESENT",
        "comment_id": 5,
        "comment_author": "romanhlavac",
        "record": {"schema_version": 1},
    }
    entry = actual["recovery_ledger"]["entries"][0]
    assert entry["source_path_hashes"] == {"a.txt": "c" * 40}
    assert entry["recovered_path_hashes"] == {"a.txt": "d" * 40}
