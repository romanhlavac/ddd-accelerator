import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from runtime.platform.check_evidence import evaluate_check_evidence
from runtime.platform.governance_kernel import evaluate_authoritative_checks


SHA = "a" * 40
ROOT = Path(__file__).resolve().parents[3]


def run(name="validate", run_id=1, status="completed", conclusion="success", sha=SHA, app_id=15368):
    return {"name": name, "id": run_id, "status": status, "conclusion": conclusion,
            "head_sha": sha, "app": {"id": app_id}, "started_at": None}


def evaluate(rows, **kwargs):
    kwargs.setdefault("source_sha", SHA)
    kwargs.setdefault("required_checks", ["validate"])
    return evaluate_check_evidence(rows, **kwargs)


@pytest.mark.parametrize("conclusion", [
    "success", "failure", "skipped", "neutral", "cancelled", "timed_out",
    "action_required", "stale", "startup_failure", "unknown", None,
])
def test_only_explicit_success_is_mandatory_pass(conclusion):
    result = evaluate([run(conclusion=conclusion)])
    assert (result["status"] == "PASS") is (conclusion == "success")
    row = result["summary"]["latest_results"][0]
    assert row["source_sha"] == SHA
    assert row["run_id"] == 1
    assert row["classification"] == "MANDATORY"
    assert row["gate_result"] == ("PASS" if conclusion == "success" else "FAIL")


@pytest.mark.parametrize("status", ["queued", "in_progress", "waiting", "pending", "requested", "unknown", None])
def test_noncompleted_state_never_passes_even_with_success(status):
    result = evaluate([run(status=status)])
    assert result["status"] == "FAIL"
    assert result["summary"]["latest_results"][0]["failure_reason"]


def test_newer_failure_blocks_older_success_independent_of_api_order_or_start_time():
    older = run(run_id=1)
    older["started_at"] = "2099-01-01T00:00:00Z"
    newer = run(run_id=2, conclusion="failure")
    for rows in ([older, newer], [newer, older]):
        result = evaluate(rows)
        assert result["status"] == "FAIL"
        assert result["summary"]["latest_results"][0]["run_id"] == 2


def test_authoritative_successful_rerun_supersedes_old_failure():
    result = evaluate([run(run_id=2), run(run_id=1, conclusion="failure")])
    assert result["status"] == "PASS"
    assert result["summary"]["latest_results"][0]["run_id"] == 2


def test_newer_queued_attempt_with_no_start_timestamp_blocks_older_success():
    result = evaluate([run(), run(run_id=2, status="queued", conclusion=None)])
    assert result["status"] == "FAIL"
    assert result["gate_result"] == "NOT_READY"


@pytest.mark.parametrize("rows", [[], [run(sha="c" * 40)], [run(sha=None)], [run(name="Validate")]])
def test_missing_stale_or_fuzzy_named_check_cannot_satisfy_required_set(rows):
    assert evaluate(rows)["status"] == "FAIL"


@pytest.mark.parametrize("conclusion", ["skipped", "failure", "neutral", None])
def test_optional_workflow_cannot_satisfy_or_block_mandatory_gate(conclusion):
    result = evaluate([run(), run("remote broker", 2, conclusion=conclusion)])
    assert result["status"] == "PASS"
    optional = next(row for row in result["summary"]["latest_results"] if row["name"] == "remote broker")
    assert optional["classification"] == "OPTIONAL"
    assert optional["gate_result"] == "NOT_APPLICABLE"
    assert evaluate([run("remote broker", 2, conclusion=conclusion)])["status"] == "FAIL"


def test_required_check_cannot_be_removed_with_ignore_switch():
    result = evaluate([run()], ignored_checks=["validate"])
    assert result["status"] == "FAIL"
    assert "AUTHORITATIVE_REQUIRED_CHECK_IGNORED:validate" in result["failures"]


@pytest.mark.parametrize("rows", [
    [run(), run(conclusion="failure")],
    [run(), run(run_id=2, app_id=999)],
    [run(run_id=0)],
    [run(run_id=None)],
    [run(run_id=True)],
])
def test_attempt_identity_ambiguity_fails_closed(rows):
    assert evaluate(rows)["status"] == "FAIL"


def test_identical_duplicate_api_row_is_idempotent():
    assert evaluate([run(), run()])["status"] == "PASS"


def test_missing_required_contract_and_expanded_conclusion_policy_fail_closed():
    assert evaluate_check_evidence([run()], source_sha=SHA)["status"] == "FAIL"
    assert evaluate([run()], accepted_conclusions=["SUCCESS", "SKIPPED"])["status"] == "FAIL"
    assert evaluate([run()], required_checks=["validate", "validate"])["status"] == "FAIL"
    assert evaluate([run()], source_sha="wrong")["status"] == "FAIL"


def test_commit_status_uses_observed_response_sha_and_same_kernel():
    status = {"context": "legacy-ci", "id": 3, "sha": SHA, "state": "success"}
    result = evaluate([], commit_statuses=[status], required_checks=["commit-status:legacy-ci"])
    assert result["status"] == "PASS"
    status["sha"] = "c" * 40
    assert evaluate([], commit_statuses=[status], required_checks=["commit-status:legacy-ci"])["status"] == "FAIL"


@pytest.mark.parametrize("operation", ["validate", "merge_dry_run", "merge", "promotion_dry_run", "release"])
def test_all_lifecycle_operations_consume_same_kernel_result(operation):
    summary = evaluate([run(conclusion="skipped")])["summary"]
    decision = evaluate_authoritative_checks({
        "operation": operation, "source_sha": SHA, "authoritative_check_summary": summary,
    })
    assert decision.status == "FAIL"
    assert decision.side_effects_allowed is False


def test_live_collector_pages_all_attempts_and_binds_status_response_sha(monkeypatch):
    path = ROOT / "scripts/platform/Evaluate-DDDACheckRuns.py"
    spec = importlib.util.spec_from_file_location("check_collector73", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    urls = []
    def get(url, token):
        urls.append(url)
        if "/check-runs?" in url:
            assert "filter=all" in url
            return {"check_runs": [run(run_id=i + 1) for i in range(100)] if "page=1" in url else [run(run_id=101, conclusion="failure")]}
        return {"sha": "c" * 40, "statuses": [{"context": "legacy-ci", "id": 3, "state": "success"}]}
    monkeypatch.setattr(module, "_get_json", get)
    rows, statuses = module._collect("owner/repo", SHA, "test-only")
    assert len(rows) == 101
    assert evaluate(rows)["status"] == "FAIL"
    assert statuses[0]["sha"] == "c" * 40


@pytest.mark.parametrize("conclusion,exit_code", [("success", 0), ("skipped", 1), ("neutral", 1)])
def test_process_adapter_preserves_evidence_and_fail_closed_exit(tmp_path, conclusion, exit_code):
    input_path = tmp_path / "checks.json"
    output_path = tmp_path / "evidence.json"
    input_path.write_text(json.dumps({"check_runs": [run(conclusion=conclusion)]}), encoding="utf-8")
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts/platform/Evaluate-DDDACheckRuns.py"),
        "--input", str(input_path), "--commit", SHA, "--required-check", "validate",
        "--output", str(output_path),
    ], capture_output=True, text=True)
    assert result.returncode == exit_code
    evidence = json.loads(output_path.read_text(encoding="utf-8"))
    assert evidence["source_sha"] == SHA
    assert evidence["required_check_set"] == ["validate"]
    assert evidence["summary"]["latest_results"][0]["conclusion"] == conclusion.upper()


MATRIX = json.loads((ROOT / "tests/fixtures/governance/scenario-matrix-v2.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("scenario", [
    row for row in MATRIX["scenarios"] if row["adapter"] == "mandatory_checks"
], ids=lambda row: row["id"])
def test_active_scenario_matrix_calls_production_owner(scenario):
    result = evaluate(**scenario["input"])
    assert result["status"] == scenario["expected"]["status"]
    assert result["gate_result"] == scenario["expected"]["gate_result"]
