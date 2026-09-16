import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCOPE_COLLECTOR = ROOT / "scripts/platform/Test-DDDAReleaseScope.py"
MERGE_COLLECTOR = ROOT / "scripts/platform/Test-DDDAMergeReleaseEligibility.py"


def _scope_namespace():
    spec = importlib.util.spec_from_file_location("ddda_release_scope_collector_test", SCOPE_COLLECTOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_previous_release_tag_selects_latest_older_semver_and_dereferences_annotation():
    ns = _scope_namespace()

    def fake_get(path, _token):
        if path.endswith("matching-refs/tags/"):
            return [
                {"ref": "refs/tags/v0.1.0", "object": {"sha": "a" * 40, "type": "tag"}},
                {"ref": "refs/tags/v0.1.1", "object": {"sha": "b" * 40, "type": "commit"}},
                {"ref": "refs/tags/not-a-release", "object": {"sha": "c" * 40, "type": "commit"}},
            ]
        if path.endswith(f"git/tags/{'a' * 40}"):
            return {"object": {"sha": "d" * 40, "type": "commit"}}
        raise AssertionError(path)

    ns.rest_get = fake_get
    assert ns.previous_release_tag("owner/repo", "0.1.2", "token") == {
        "tag": "v0.1.1",
        "sha": "b" * 40,
    }
    assert ns.previous_release_tag("owner/repo", "0.1.1", "token") == {
        "tag": "v0.1.0",
        "sha": "d" * 40,
    }


def test_physical_scope_inventory_keeps_unmapped_commit_and_exact_primary_relation():
    ns = _scope_namespace()
    ns.previous_release_tag = lambda *_: {"tag": "v0.1.0", "sha": "a" * 40}
    ns.compare_commits = lambda *_: (
        "ahead",
        [{"sha": "b" * 40}, {"sha": "c" * 40}],
    )

    def fake_pages(path, _token):
        if f"commits/{'b' * 40}/pulls" in path:
            return [{"number": 77}]
        if f"commits/{'c' * 40}/pulls" in path:
            return []
        raise AssertionError(path)

    def fake_get(path, _token):
        if path.endswith("pulls/77"):
            return {"merged_at": "2026-08-25T00:00:00Z", "body": "Implements #96\n"}
        if path.endswith("issues/96"):
            return {"milestone": {"title": "DDDA 0.1.1"}}
        raise AssertionError(path)

    ns.rest_pages = fake_pages
    ns.rest_get = fake_get
    ns.recovery_ledger_at_source = lambda *_: None
    actual = ns.physical_scope_snapshot(
        "owner/repo", "0.1.1", "d" * 40, "token", {96: {"Target Release": "0.1.1"}}
    )
    assert actual["unmapped_commit_shas"] == ["c" * 40]
    assert actual["shipping_prs"] == [
        {
            "number": 77,
            "merged": True,
            "merge_commit_sha": None,
            "primary_crs": [96],
            "milestone": "DDDA 0.1.1",
            "target_release": "0.1.1",
        }
    ]


def test_merge_collector_recognizes_one_open_release_train_and_tbd_target():
    spec = importlib.util.spec_from_file_location("ddda_merge_eligibility_collector_test", MERGE_COLLECTOR)
    assert spec and spec.loader
    ns = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ns)
    assert ns.active_release([{"title": "DDDA 0.1.1", "state": "open"}]) == {
        "version": "0.1.1"
    }
    assert ns.primary_changes("Implements #96\nCloses #96\n") == [96]
    assert ns.target_release("Target Release: `TBD`\n") == "TBD"


def test_scope_collector_emits_utf8_evidence_without_windows_charmap(capsysbinary):
    ns = _scope_namespace()
    payload = '{"note":"ř"}\\n'

    ns.emit_utf8(payload)

    captured = capsysbinary.readouterr()
    assert captured.out == payload.encode("utf-8")


def test_physical_scope_preserves_candidate_source_sha_and_derives_metadata_tip():
    ns = _scope_namespace()
    candidate_sha = "d" * 40
    recovered_sha = "b" * 40
    source_merge_sha = "e" * 40
    ns.previous_release_tag = lambda *_: {"tag": "v0.1.0", "sha": "a" * 40}
    ns.compare_commits = lambda *_: ("ahead", [{"sha": recovered_sha}, {"sha": candidate_sha}])
    ns.recovery_ledger_at_source = lambda *_: {
        "schema_version": 1,
        "version": "0.1.1",
        "previous_release_tag": "v0.1.0",
        "entries": [{
            "recovered_commit_sha": recovered_sha,
            "source_pr": 77,
            "source_merge_commit_sha": source_merge_sha,
            "primary_cr": 96,
        }],
    }
    ns.commit_path_hashes = lambda _repo, sha, _token: (
        {ns.RECOVERY_LEDGER_PATH: "ledger"} if sha == candidate_sha else {"file": sha}
    )
    ns.shipping_row = lambda _repo, number, _token, _rows: {
        "number": number,
        "merged": True,
        "merge_commit_sha": source_merge_sha,
        "primary_crs": [96],
        "milestone": "DDDA 0.1.1",
        "target_release": "0.1.1",
    }

    actual = ns.physical_scope_snapshot(
        "owner/repo", "0.1.1", candidate_sha, "token", {96: {"Target Release": "0.1.1"}}
    )

    assert actual["release_source_sha"] == candidate_sha
    assert actual["recovery_ledger"]["metadata_commit_shas"] == [candidate_sha]


def test_physical_scope_does_not_classify_non_metadata_candidate_tip():
    ns = _scope_namespace()
    candidate_sha = "d" * 40
    ns.previous_release_tag = lambda *_: {"tag": "v0.1.0", "sha": "a" * 40}
    ns.compare_commits = lambda *_: ("ahead", [{"sha": candidate_sha}])
    ns.recovery_ledger_at_source = lambda *_: {
        "schema_version": 1,
        "version": "0.1.1",
        "previous_release_tag": "v0.1.0",
        "entries": [],
    }
    ns.commit_path_hashes = lambda *_: {ns.RECOVERY_LEDGER_PATH: "ledger", "other": "x"}
    ns.rest_pages = lambda *_: []

    actual = ns.physical_scope_snapshot(
        "owner/repo", "0.1.1", candidate_sha, "token", {}
    )

    assert actual["recovery_ledger"]["metadata_commit_shas"] == []
    assert actual["unmapped_commit_shas"] == [candidate_sha]


def test_release_cut_readback_requires_one_parent_one_changelog_path_and_exact_blobs():
    ns = _scope_namespace()
    commit_sha = "c" * 40
    parent_sha = "a" * 40
    declared = {
        "commit_sha": commit_sha,
        "path": "CHANGELOG.md",
        "version": "0.1.1",
        "source_blob_sha": "1" * 40,
        "release_blob_sha": "2" * 40,
    }
    ns.rest_get = lambda path, _token: (
        {"parents": [{"sha": parent_sha}]} if path.endswith(f"commits/{commit_sha}") else
        {"type": "file", "sha": "1" * 40}
    )
    ns.commit_path_hashes = lambda *_: {"CHANGELOG.md": "2" * 40}

    actual = ns.release_cut_readback("owner/repo", declared, "token")

    assert actual["changed_paths_match"] is True
    assert actual["source_blob_matches"] is True
    assert actual["release_blob_matches"] is True


def test_physical_scope_v2_classifies_only_release_cut_and_ledger_tip_as_metadata():
    ns = _scope_namespace()
    recovered = "b" * 40
    release_cut = "c" * 40
    ledger_tip = "d" * 40
    source_merge = "e" * 40
    ns.previous_release_tag = lambda *_: {"tag": "v0.1.0", "sha": "a" * 40}
    ns.compare_commits = lambda *_: (
        "ahead",
        [{"sha": recovered}, {"sha": release_cut}, {"sha": ledger_tip}],
    )
    ns.recovery_ledger_at_source = lambda *_: {
        "schema_version": 2,
        "version": "0.1.1",
        "previous_release_tag": "v0.1.0",
        "release_cut": {
            "commit_sha": release_cut,
            "path": "CHANGELOG.md",
            "version": "0.1.1",
            "source_blob_sha": "1" * 40,
            "release_blob_sha": "2" * 40,
        },
        "entries": [{
            "recovered_commit_sha": recovered,
            "source_pr": 97,
            "source_merge_commit_sha": source_merge,
            "primary_cr": 96,
        }],
    }
    ns.release_cut_readback = lambda *_: {
        "commit_sha": release_cut,
        "path": "CHANGELOG.md",
        "version": "0.1.1",
        "source_blob_sha": "1" * 40,
        "release_blob_sha": "2" * 40,
        "changed_paths_match": True,
        "source_blob_matches": True,
        "release_blob_matches": True,
    }
    ns.commit_path_hashes = lambda _repo, sha, _token: (
        {"CHANGELOG.md": "2" * 40} if sha == release_cut else
        {ns.RECOVERY_LEDGER_PATH: "3" * 40} if sha == ledger_tip else
        {"runtime/file.py": "4" * 40}
    )
    ns.shipping_row = lambda _repo, number, _token, _rows: {
        "number": number,
        "merged": True,
        "merge_commit_sha": source_merge,
        "primary_crs": [96],
        "milestone": "DDDA 0.1.1",
        "target_release": "0.1.1",
    }

    actual = ns.physical_scope_snapshot(
        "owner/repo", "0.1.1", ledger_tip, "token", {96: {"Target Release": "0.1.1"}}
    )

    assert actual["recovery_ledger"]["metadata_commit_shas"] == [release_cut, ledger_tip]
    assert actual["unmapped_commit_shas"] == []
