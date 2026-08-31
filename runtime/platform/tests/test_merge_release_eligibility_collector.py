import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "platform" / "Test-DDDAMergeReleaseEligibility.py"
SPEC = importlib.util.spec_from_file_location("merge_eligibility_collector", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)


def bootstrap(active_issues):
    return {
        "milestones": [
            {
                "title": "DDDA 0.1.1",
                "state": "open",
                "issues": active_issues,
                "pulls": [],
            }
        ],
        "item_groups": [
            {
                "kind": "issue",
                "numbers": active_issues,
                "metadata": {"Target Release": "0.1.1"},
            }
        ],
    }


def future_plan_pr():
    return {
        "number": 104,
        "base": {"sha": "a" * 40},
        "head": {"sha": "b" * 40},
    }


def test_future_release_metadata_requires_unchanged_live_active_scope(monkeypatch):
    base = bootstrap([9, 12])
    head = bootstrap([9, 12])
    head["milestones"].append({"title": "DDDA 0.1.2", "state": "open", "issues": [16], "pulls": []})
    monkeypatch.setattr(
        COLLECTOR,
        "pr_files",
        lambda *_args: [{"filename": path, "status": "modified"} for path in COLLECTOR.FUTURE_RELEASE_METADATA_PATHS],
    )
    monkeypatch.setattr(
        COLLECTOR,
        "content_text",
        lambda _repo, _path, ref, _token: json.dumps(base if ref == "a" * 40 else head),
    )

    result = COLLECTOR.future_release_metadata_evidence(
        repository="romanhlavac/ddd-accelerator",
        pr=future_plan_pr(),
        active={"version": "0.1.1"},
        active_issue_numbers={9, 12},
        token="not-used",
    )

    assert result["status"] == "PASS"
    assert result["active_scope_unchanged"] is True


def test_future_release_metadata_fails_when_active_scope_would_change(monkeypatch):
    base = bootstrap([9, 12])
    head = bootstrap([9])
    head["milestones"].append({"title": "DDDA 0.1.2", "state": "open", "issues": [16], "pulls": []})
    monkeypatch.setattr(
        COLLECTOR,
        "pr_files",
        lambda *_args: [{"filename": path, "status": "modified"} for path in COLLECTOR.FUTURE_RELEASE_METADATA_PATHS],
    )
    monkeypatch.setattr(
        COLLECTOR,
        "content_text",
        lambda _repo, _path, ref, _token: json.dumps(base if ref == "a" * 40 else head),
    )

    result = COLLECTOR.future_release_metadata_evidence(
        repository="romanhlavac/ddd-accelerator",
        pr=future_plan_pr(),
        active={"version": "0.1.1"},
        active_issue_numbers={9, 12},
        token="not-used",
    )

    assert result["status"] == "FAIL"
    assert "MERGE_ELIGIBILITY_FUTURE_RELEASE_ACTIVE_SCOPE_CHANGED" in result["failures"]


def test_transition_requires_exact_marker_and_file_set(monkeypatch):
    body = """Implements #16

<!-- ddda:merge-eligibility-transition:v1 -->
```json
{"schema_version":1,"kind":"future_release_metadata_merge_eligibility_transition","base_sha":"b61392ace66a95c808f321f3bd4b046cc5f564e5"}
```
"""
    pr = {"number": 105, "body": body, "base": {"sha": COLLECTOR.TRANSITION_BASE_SHA}}
    monkeypatch.setattr(
        COLLECTOR,
        "pr_files",
        lambda *_args: [
            {"filename": path, "status": status}
            for path, status in COLLECTOR.TRANSITION_FILE_STATUSES.items()
        ],
    )

    result = COLLECTOR.transition_evidence(pr, "romanhlavac/ddd-accelerator", [16], "not-used")

    assert result["status"] == "PASS"


def test_transition_rejects_wrong_status_for_an_exact_path(monkeypatch):
    pr = {
        "number": 105,
        "body": "",
        "base": {"sha": COLLECTOR.TRANSITION_BASE_SHA},
    }
    statuses = dict(COLLECTOR.TRANSITION_FILE_STATUSES)
    statuses["docs/adr/0012-future-release-metadata-merge-eligibility.md"] = "modified"
    monkeypatch.setattr(
        COLLECTOR,
        "pr_files",
        lambda *_args: [{"filename": path, "status": status} for path, status in statuses.items()],
    )

    result = COLLECTOR.transition_evidence(pr, "romanhlavac/ddd-accelerator", [16], "not-used")

    assert result["status"] == "FAIL"
    assert "MERGE_ELIGIBILITY_TRANSITION_FILE_STATUS_INVALID" in result["failures"]


def test_governance_repair_requires_unchanged_governance_and_exact_paths(monkeypatch):
    base = bootstrap([9, 12])
    pr = future_plan_pr()
    monkeypatch.setattr(
        COLLECTOR,
        "pr_files",
        lambda *_args: [{"filename": path, "status": "modified"} for path in COLLECTOR.GOVERNANCE_REPAIR_PATHS],
    )
    monkeypatch.setattr(COLLECTOR, "content_text", lambda *_args: json.dumps(base))

    result = COLLECTOR.governance_repair_evidence(
        repository="romanhlavac/ddd-accelerator",
        pr=pr,
        active={"version": "0.1.1"},
        active_issue_numbers={9, 12},
        primary=[16],
        token="not-used",
    )

    assert result["status"] == "PASS"
    assert result["active_scope_unchanged"] is True


def test_governance_repair_rejects_a_governance_change(monkeypatch):
    base = bootstrap([9, 12])
    changed = bootstrap([9])
    pr = future_plan_pr()
    monkeypatch.setattr(
        COLLECTOR,
        "pr_files",
        lambda *_args: [{"filename": path, "status": "modified"} for path in COLLECTOR.GOVERNANCE_REPAIR_PATHS],
    )
    monkeypatch.setattr(
        COLLECTOR,
        "content_text",
        lambda _repo, _path, ref, _token: json.dumps(base if ref == "a" * 40 else changed),
    )

    result = COLLECTOR.governance_repair_evidence(
        repository="romanhlavac/ddd-accelerator",
        pr=pr,
        active={"version": "0.1.1"},
        active_issue_numbers={9, 12},
        primary=[16],
        token="not-used",
    )

    assert result["status"] == "FAIL"
    assert "MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_GOVERNANCE_CHANGED" in result["failures"]



def test_integration_merge_files_uses_only_verified_branch_diff(monkeypatch):
    base_sha = "a" * 40
    branch_sha = "b" * 40
    current_main = "c" * 40
    first_parent = "d" * 40
    rows = [{"filename": path, "status": "modified"} for path in COLLECTOR.GOVERNANCE_REPAIR_PATHS]
    responses = {
        f"repos/romanhlavac/ddd-accelerator/commits/{branch_sha}": {
            "parents": [{"sha": first_parent}, {"sha": current_main}]
        },
        "repos/romanhlavac/ddd-accelerator/commits/main": {"sha": current_main},
        f"repos/romanhlavac/ddd-accelerator/compare/{base_sha}...{first_parent}": {"files": rows},
    }
    monkeypatch.setattr(COLLECTOR, "request_json", lambda path, _token: responses[path])

    result = COLLECTOR.integration_merge_files(
        "romanhlavac/ddd-accelerator",
        {"base": {"sha": base_sha}, "head": {"sha": branch_sha}},
        "not-used",
    )

    assert result == (first_parent, rows)


def test_governance_repair_transition_requires_exact_base_marker_and_paths(monkeypatch):
    body = """Implements #16

<!-- ddda:merge-eligibility-governance-repair:v1 -->
```json
{"schema_version":1,"kind":"merge_eligibility_governance_repair_transition","base_sha":"fdcc2b323eff4bcc9cef71207e280f3ffa950dd8"}
```
"""
    pr = {"number": 107, "body": body, "base": {"sha": COLLECTOR.GOVERNANCE_REPAIR_TRANSITION_BASE_SHA}}
    monkeypatch.setattr(
        COLLECTOR,
        "pr_files",
        lambda *_args: [
            {"filename": path, "status": status}
            for path, status in COLLECTOR.GOVERNANCE_REPAIR_TRANSITION_FILE_STATUSES.items()
        ],
    )

    result = COLLECTOR.governance_repair_transition_evidence(
        pr, "romanhlavac/ddd-accelerator", [16], "not-used"
    )

    assert result["status"] == "PASS"


def test_active_release_uses_versioned_policy_for_one_open_active_train() -> None:
    backlog_policy = """
milestones:
  initial:
    - name: DDDA 0.1.1
      state: open
      issues: [9, 12]
"""
    milestones = [
        {"title": "DDDA 0.1.1", "state": "open"},
        {"title": "DDDA 0.1.2", "state": "open"},
        {"title": "DDDA 0.2.0", "state": "open"},
    ]

    assert COLLECTOR.active_release(milestones, backlog_policy) == {"version": "0.1.1"}


def test_active_release_fails_closed_when_versioned_active_train_is_not_live() -> None:
    backlog_policy = """
milestones:
  initial:
    - name: DDDA 0.1.1
      state: open
"""
    try:
        COLLECTOR.active_release([{"title": "DDDA 0.1.2", "state": "open"}], backlog_policy)
    except COLLECTOR.GitHubReadError as exc:
        assert "exactly one live active" in str(exc)
    else:
        raise AssertionError("expected missing live active train to fail closed")


def test_active_release_ignores_open_future_trains_without_prerelease_marker() -> None:
    backlog_policy = """
milestones:
  release_train:
    - name: DDDA 0.1.1
      state: open
      issues: [9]
      pulls: []
      pre_release_prerequisites: [44]
    - name: DDDA 0.1.2
      state: open
      issues: [16]
      pulls: []
"""
    milestones = [{"title": "DDDA 0.1.1", "state": "open"}, {"title": "DDDA 0.1.2", "state": "open"}]
    assert COLLECTOR.active_release(milestones, backlog_policy) == {"version": "0.1.1"}


def test_active_release_fails_closed_when_release_train_has_no_marker() -> None:
    backlog_policy = """
milestones:
  release_train:
    - name: DDDA 0.1.1
      state: open
      issues: [9]
      pulls: []
"""
    try:
        COLLECTOR.active_release([{"title": "DDDA 0.1.1", "state": "open"}], backlog_policy)
    except COLLECTOR.GitHubReadError as exc:
        assert "marker-designated" in str(exc)
    else:
        raise AssertionError("expected unmarked release_train to fail closed")


def test_governance_repair_allows_exact_ci_check_run_aggregation_set(monkeypatch):
    base = bootstrap([9, 12])
    pr = future_plan_pr()
    monkeypatch.setattr(
        COLLECTOR,
        "pr_files",
        lambda *_args: [
            {"filename": path, "status": status}
            for path, status in COLLECTOR.CI_CHECK_RUN_REPAIR_FILE_STATUSES.items()
        ],
    )
    monkeypatch.setattr(COLLECTOR, "content_text", lambda *_args: json.dumps(base))
    result = COLLECTOR.governance_repair_evidence(
        repository="romanhlavac/ddd-accelerator",
        pr=pr,
        active={"version": "0.1.1"},
        active_issue_numbers={9, 12},
        primary=[16],
        token="not-used",
    )
    assert result["status"] == "PASS"


def test_governance_repair_rejects_ci_check_run_status_change(monkeypatch):
    base = bootstrap([9, 12])
    pr = future_plan_pr()
    statuses = dict(COLLECTOR.CI_CHECK_RUN_REPAIR_FILE_STATUSES)
    statuses["tests/powershell/Test-DDDAGitHubCheckRuns.ps1"] = "modified"
    monkeypatch.setattr(
        COLLECTOR,
        "pr_files",
        lambda *_args: [{"filename": path, "status": status} for path, status in statuses.items()],
    )
    monkeypatch.setattr(COLLECTOR, "content_text", lambda *_args: json.dumps(base))
    result = COLLECTOR.governance_repair_evidence(
        repository="romanhlavac/ddd-accelerator",
        pr=pr,
        active={"version": "0.1.1"},
        active_issue_numbers={9, 12},
        primary=[16],
        token="not-used",
    )
    assert result["status"] == "FAIL"
    assert "MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_FILE_STATUS_INVALID" in result["failures"]
