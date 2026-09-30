from copy import deepcopy

import pytest

from runtime.platform.human_review_evidence import (
    MARKER,
    collect_human_review_evidence,
)


REPOSITORY = "romanhlavac/ddd-accelerator"
PR = 184
SHA = "a" * 40
PACKAGE = "b" * 64


def comment(*, verdict: str = "pass") -> dict:
    return {
        "id": 42,
        "user": {"login": "romanhlavac", "type": "User"},
        "body": f'''{MARKER}
```json
{{
  "schema_version": 1,
  "kind": "implementation_pr_review",
  "repository": "{REPOSITORY}",
  "pr": {PR},
  "reviewed_sha": "{SHA}",
  "candidate_package_sha256": "{PACKAGE}",
  "reviewer": "romanhlavac",
  "reviewed_at": "2026-09-28T07:54:55Z",
  "verdict": "{verdict}"
}}
```
''',
    }


def collect(comments: list[dict]) -> dict:
    return collect_human_review_evidence(
        comments,
        repository=REPOSITORY,
        pr_number=PR,
        source_sha=SHA,
        candidate_package_sha256=PACKAGE,
    )


def test_collects_one_human_review_and_binds_it_through_kernel():
    result = collect([comment()])
    assert result["status"] == "PASS"
    assert result["review"]["verdict"] == "PASS"
    assert result["review"]["provenance_verified"] is True
    assert result["comment_id"] == 42


@pytest.mark.parametrize(
    ("comments", "failure"),
    [
        ([], "HUMAN_REVIEW_CARDINALITY"),
        ([comment(), comment()], "HUMAN_REVIEW_CARDINALITY"),
        ([comment(verdict="changes_required")], "HUMAN_REVIEW_NOT_PASS"),
    ],
)
def test_characterized_human_review_outcomes_remain_fail_closed(comments, failure):
    result = collect(comments)
    assert result["status"] == "FAIL"
    assert failure in result["failures"]


def test_rejects_bot_or_reviewer_author_mismatch():
    candidate = comment()
    candidate["user"] = {"login": "reviewer[bot]", "type": "Bot"}
    result = collect([candidate])
    assert result["status"] == "FAIL"
    assert "HUMAN_REVIEW_PROVENANCE_INVALID" in result["failures"]


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("repository", "wrong/repository", "HUMAN_REVIEW_REPOSITORY_MISMATCH"),
        ("pr", 999, "HUMAN_REVIEW_PR_MISMATCH"),
        ("reviewed_sha", "c" * 40, "HUMAN_REVIEW_SOURCE_SHA_MISMATCH"),
        (
            "candidate_package_sha256",
            "c" * 64,
            "HUMAN_REVIEW_PACKAGE_SHA256_MISMATCH",
        ),
    ],
)
def test_rejects_review_identity_drift(field, value, failure):
    candidate = comment()
    candidate["body"] = candidate["body"].replace(
        f'"{field}": "{REPOSITORY if field == "repository" else SHA if field == "reviewed_sha" else PACKAGE}"'
        if field != "pr"
        else f'"pr": {PR}',
        f'"{field}": "{value}"' if field != "pr" else f'"pr": {value}',
    )
    result = collect([candidate])
    assert result["status"] == "FAIL"
    assert failure in result["failures"]


def test_non_authoritative_marker_text_is_ignored():
    duplicate = deepcopy(comment())
    duplicate["body"] = duplicate["body"].replace(
        MARKER, "<!-- ddda:human-pr-review-duplicate:v1 -->"
    )
    assert collect([comment(), duplicate])["status"] == "PASS"
