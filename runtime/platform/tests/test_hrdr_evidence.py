import json

import pytest

from runtime.platform.hrdr_evidence import MARKER, collect_hrdr_evidence


REPOSITORY = "romanhlavac/ddd-accelerator"
PR = 185
SHA = "a" * 40
PACKAGE = "b" * 64
VERSION = "0.1.2"


def record(*, decision="go", reviewer="romanhlavac", owner="romanhlavac"):
    return {
        "schema_version": 1,
        "repository": REPOSITORY,
        "pr": PR,
        "source_sha": SHA,
        "candidate_package_sha256": PACKAGE,
        "version": VERSION,
        "reviewer": reviewer,
        "decision_owner": owner,
        "decision": decision,
        "decided_at": "2026-09-28T08:30:00Z" if decision != "pending" else None,
        "findings": [{"id": "finding-1", "status": "resolved"}],
    }


def comment(payload=None, *, login="romanhlavac", user_type="User", comment_id=42):
    payload = record() if payload is None else payload
    return {
        "id": comment_id,
        "user": {"login": login, "type": user_type},
        "body": f"{MARKER}\n```json\n{json.dumps(payload)}\n```",
    }


def evaluate(comments):
    return collect_hrdr_evidence(
        comments,
        expected_repository=REPOSITORY,
        expected_pr=PR,
        expected_source_sha=SHA,
        expected_package_sha256=PACKAGE,
        expected_version=VERSION,
    )


def test_accepts_pending_bot_scaffold_without_treating_it_as_release_decision():
    pending = record(
        decision="pending",
        reviewer="<human fills>",
        owner="<human fills>",
    )
    result = collect_hrdr_evidence(
        [comment(pending, login="github-actions[bot]", user_type="Bot")]
    )
    assert result["status"] == "PASS"
    assert result["record"]["decision"] == "pending"


def test_accepts_one_human_positive_decision_bound_to_exact_candidate():
    result = evaluate([comment()])
    assert result["status"] == "PASS"
    assert result["comment_id"] == 42


@pytest.mark.parametrize(
    ("comments", "allow_missing", "failure"),
    [
        ([], False, "HRDR_CARDINALITY"),
        ([comment(), comment(comment_id=43)], False, "HRDR_CARDINALITY"),
        ([{"body": f"{MARKER}\nnot-json", "user": {"login": "x", "type": "User"}}], False, "HRDR_JSON_INVALID"),
    ],
)
def test_rejects_missing_duplicate_or_malformed_authority(comments, allow_missing, failure):
    result = collect_hrdr_evidence(comments, allow_missing=allow_missing)
    assert result["status"] == "FAIL"
    assert failure in result["failures"]


def test_allow_missing_supports_idempotent_scaffold_creation():
    assert collect_hrdr_evidence([], allow_missing=True)["status"] == "MISSING"


@pytest.mark.parametrize(
    "candidate",
    [
        comment(login="github-actions[bot]", user_type="Bot"),
        comment(login="github-actions[bot]", user_type="User"),
        comment(login="mallory", user_type="User"),
        comment(record(owner="mallory")),
        comment(user_type=""),
    ],
)
def test_rejects_bot_or_spoofed_positive_provenance(candidate):
    result = collect_hrdr_evidence([candidate])
    assert result["status"] == "FAIL"
    assert "HRDR_PROVENANCE_INVALID" in result["failures"]


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("repository", "wrong/repository", "HRDR_REPOSITORY_MISMATCH"),
        ("pr", 999, "HRDR_PR_MISMATCH"),
        ("source_sha", "c" * 40, "HRDR_SOURCE_SHA_MISMATCH"),
        ("candidate_package_sha256", "c" * 64, "HRDR_PACKAGE_SHA256_MISMATCH"),
        ("version", "0.1.1", "HRDR_VERSION_MISMATCH"),
        ("decision", "no_go", "HRDR_NOT_POSITIVE"),
    ],
)
def test_rejects_stale_identity_or_non_positive_decision(field, value, failure):
    payload = record()
    payload[field] = value
    result = evaluate([comment(payload)])
    assert result["status"] == "FAIL"
    assert failure in result["failures"]


def test_rejects_partial_expected_identity_contract():
    result = collect_hrdr_evidence([comment()], expected_repository=REPOSITORY)
    assert result["status"] == "FAIL"
    assert result["failures"] == ["HRDR_EXPECTED_IDENTITY_INCOMPLETE"]
