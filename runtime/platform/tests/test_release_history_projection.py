import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((ROOT / "config/governance/release-history.json").read_text())
SCRIPT = ROOT / "scripts/platform/Reconcile-DDDAReleaseHistory.py"
spec = importlib.util.spec_from_file_location("ddda_release_history_test", SCRIPT)
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)


def test_historical_incomplete_identity_never_claims_physical_package():
    old, new = CONTRACT["releases"]
    assert old["pulls"] == [8]
    assert old["source_sha"] == "64e629dc6dc06c059b0e7569b8401fb726ea9161"
    assert old["status"] == "Historical evidence incomplete"
    assert old["package_sha256"] is None and old["github_release"] == "absent"
    assert new["status"] == "Released" and new["package_sha256"]
    assert new["pulls_from_source_ledger"]


def test_release_status_requires_external_evidence_before_project_write(monkeypatch):
    record = CONTRACT["releases"][1]
    monkeypatch.setattr(history, "tagged_source", lambda r: None)
    monkeypatch.setattr(history, "api", lambda path: {
        "tag_name": record["tag"], "target_commitish": record["source_sha"],
        "draft": False, "prerelease": False,
    })
    monkeypatch.setattr(history, "read_report", lambda r, release: (_ for _ in ()).throw(RuntimeError("digest mismatch")))
    with pytest.raises(RuntimeError, match="digest mismatch"):
        history.release_rows(record)


def test_multiple_ledger_prs_share_release_identity(monkeypatch):
    record = CONTRACT["releases"][1]
    entries = {74: {"source_merge_commit_sha": "a"}, 77: {"source_merge_commit_sha": "b"}}
    monkeypatch.setattr(history, "tagged_source", lambda r: None)
    monkeypatch.setattr(history, "read_report", lambda r, release: None)
    monkeypatch.setattr(history, "decision", lambda r: "https://github.com/romanhlavac/ddd-accelerator/pull/146#decision")
    monkeypatch.setattr(history, "source_ledger", lambda r: entries)
    def fake_api(path):
        if path.startswith("releases/"):
            return {"tag_name": record["tag"], "target_commitish": record["source_sha"],
                    "draft": False, "prerelease": False, "published_at": "2026-09-22T12:00:00Z",
                    "html_url": "https://github.com/romanhlavac/ddd-accelerator/releases/tag/v0.1.1"}
        number = int(path.split("/")[-1])
        return {"number": number, "merged_at": "2026-09-16T00:00:00Z",
                "merge_commit_sha": entries[number]["source_merge_commit_sha"]}
    monkeypatch.setattr(history, "api", fake_api)
    rows = history.release_rows(record)
    assert set(rows) == {74, 77}
    assert {fields["Released Version"] for _, fields in rows.values()} == {"0.1.1"}
    assert {fields["Release Status"] for _, fields in rows.values()} == {"Released"}


def test_merge_alone_does_not_prove_released(monkeypatch):
    monkeypatch.setattr(history.core, "gh", lambda *args, **kwargs: [[]])
    monkeypatch.setattr(history, "merged_prs", lambda: {201: {"number": 201, "merged_at": "today"}})
    monkeypatch.setattr(history, "release_rows", lambda r: {})
    rows = history.expected_rows({"releases": []})
    assert rows[201][1] == {"Release Status": "Merged / awaiting release validation"}


def test_new_publication_requires_explicit_versioned_record(monkeypatch):
    monkeypatch.setattr(history.core, "gh", lambda *args, **kwargs: [[
        {"tag_name": "v0.1.2", "draft": False}
    ]])
    with pytest.raises(RuntimeError, match="lacks versioned history contract"):
        history.expected_rows(CONTRACT)
