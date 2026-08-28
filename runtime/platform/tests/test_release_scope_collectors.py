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
