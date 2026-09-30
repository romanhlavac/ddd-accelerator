import pytest

from runtime.platform.check_evidence import evaluate_check_evidence


def run(name, run_id, started_at, status="completed", conclusion="success"):
    return {
        "name": name,
        "id": run_id,
        "started_at": started_at,
        "status": status,
        "conclusion": conclusion,
    }


def test_latest_success_supersedes_historical_failure():
    result = evaluate_check_evidence(
        [
            run("validate", 1, "2026-09-28T08:00:00Z", conclusion="failure"),
            run("validate", 2, "2026-09-28T08:05:00Z"),
        ]
    )
    assert result["status"] == "PASS"
    assert result["summary"]["latest_results"][0]["run_id"] == 2


@pytest.mark.parametrize(
    ("status", "conclusion"),
    [
        ("queued", None),
        ("in_progress", None),
        ("completed", "failure"),
        ("completed", "cancelled"),
    ],
)
def test_latest_non_pass_blocks(status, conclusion):
    result = evaluate_check_evidence(
        [run("validate", 1, "2026-09-28T08:00:00Z", status, conclusion)]
    )
    assert result["status"] == "FAIL"
    assert "AUTHORITATIVE_CHECK_NOT_SUCCESS:validate" in result["failures"]


def test_missing_explicit_required_check_blocks():
    result = evaluate_check_evidence(
        [run("other", 1, "2026-09-28T08:00:00Z")],
        required_checks=["required"],
        accepted_conclusions=["SUCCESS"],
    )
    assert result["status"] == "FAIL"
    assert "AUTHORITATIVE_CHECK_MISSING:required" in result["failures"]


def test_neutral_and_skipped_preserve_governed_merge_compatibility():
    result = evaluate_check_evidence(
        [
            run("neutral", 1, "2026-09-28T08:00:00Z", conclusion="neutral"),
            run("skipped", 2, "2026-09-28T08:01:00Z", conclusion="skipped"),
        ]
    )
    assert result["status"] == "PASS"


def test_explicit_success_only_mode_rejects_neutral():
    result = evaluate_check_evidence(
        [run("required", 1, "2026-09-28T08:00:00Z", conclusion="neutral")],
        required_checks=["required"],
        accepted_conclusions=["SUCCESS"],
    )
    assert result["status"] == "FAIL"


def test_ignored_current_check_is_not_self_blocking():
    result = evaluate_check_evidence(
        [
            run("current", 1, "2026-09-28T08:00:00Z", "in_progress", None),
            run("validate", 2, "2026-09-28T08:01:00Z"),
        ],
        ignored_checks=["current"],
    )
    assert result["status"] == "PASS"
    assert result["summary"]["required_checks"] == ["validate"]


def test_commit_status_context_is_normalized_into_same_required_set():
    result = evaluate_check_evidence(
        [run("validate", 1, "2026-09-28T08:00:00Z")],
        commit_statuses=[
            {
                "context": "legacy-ci",
                "id": 3,
                "updated_at": "2026-09-28T08:02:00Z",
                "state": "failure",
            }
        ],
    )
    assert result["status"] == "FAIL"
    assert "AUTHORITATIVE_CHECK_NOT_SUCCESS:commit-status:legacy-ci" in result["failures"]


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("name", "", "CHECK_NAME_MISSING"),
        ("id", 0, "CHECK_RUN_ID_INVALID:validate"),
        ("started_at", "", "CHECK_TIMESTAMP_MISSING:validate"),
        ("started_at", "not-a-time", "CHECK_TIMESTAMP_INVALID:validate"),
    ],
)
def test_malformed_latest_selection_fails_closed(field, value, failure):
    candidate = run("validate", 1, "2026-09-28T08:00:00Z")
    candidate[field] = value
    result = evaluate_check_evidence([candidate])
    assert result["status"] == "FAIL"
    assert result["failures"] == [failure]
