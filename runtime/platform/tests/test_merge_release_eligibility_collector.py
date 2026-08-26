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
        lambda *_args: [{"filename": path, "status": "modified"} for path in COLLECTOR.TRANSITION_PATHS],
    )

    result = COLLECTOR.transition_evidence(pr, "romanhlavac/ddd-accelerator", [16], "not-used")

    assert result["status"] == "PASS"
