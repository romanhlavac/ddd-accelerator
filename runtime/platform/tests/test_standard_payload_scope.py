from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import zipfile

import pytest
from runtime.platform.governance_kernel import evaluate_physical_scope_binding

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/platform"))
from standard_scope_collection import ScopeCollectionError, package_entries, baseline_snapshot, AssetRedirect, cancellation_evidence

SHA, PACKAGE = "a" * 40, "b" * 64


def evidence():
    old = {"blob": "1" * 40, "mode": "100644"}
    new = {"blob": "2" * 40, "mode": "100644"}
    return {
        "schema_version": 2, "contract": "ddda_standard_payload_scope", "repository": "owner/repo",
        "version": "0.1.2", "release_source_sha": SHA,
        "baseline": {"tag": "v0.1.1", "source_sha": "f" * 40, "tag_object_sha": "e" * 40,
                     "release_id": 1, "asset_id": 2, "package_sha256": "c" * 64, "payload_verified": True,
                     "entries": {"docs/file.md": {**old, "payload_sha256": "1" * 64}}},
        "candidate": {"source_sha": SHA, "package_sha256": PACKAGE, "payload_verified": True,
                      "entries": {"docs/file.md": {**new, "payload_sha256": "2" * 64}}},
        "history": {"anchor_sha": "d" * 40, "anchor_entries": {"docs/file.md": old},
                    "transitions": [{"sha": SHA, "parent": "d" * 40,
                                     "changes": [{"path": "docs/file.md", "before": old, "after": new}],
                                     "pr": {"number": 211, "merge_commit_sha": SHA, "merged": True,
                                            "primary_crs": [171], "milestone": "DDDA 0.1.2"}}]},
        "cancellations": [],
    }


def evaluate(value, scope=(171,)):
    return evaluate_physical_scope_binding(value, expected_source_sha=SHA, expected_version="0.1.2",
                                          declared_scope=scope, expected_repository="owner/repo",
                                          expected_package_sha256=PACKAGE)


def test_complete_cross_lineage_payload_proof_passes_without_authorizing_release():
    result = evaluate(evidence())
    assert result.status == "PASS"
    assert not result.side_effects_allowed and not result.authorization_required


@pytest.mark.parametrize("mutate,code", [
    (lambda x: x["baseline"].update(payload_verified=False), "BASELINE_PAYLOAD_INVALID"),
    (lambda x: x["candidate"].update(package_sha256="0" * 64), "CANDIDATE_IDENTITY_MISMATCH"),
    (lambda x: x["history"]["transitions"][0].update(parent="0" * 40), "HISTORY_CHAIN_INVALID"),
    (lambda x: x["history"]["transitions"][0].update(changes=[]), "HISTORY_PAYLOAD_COVERAGE_MISMATCH"),
    (lambda x: x["history"]["transitions"][0]["pr"].update(primary_crs=[155]), "CONTENT_OUT_OF_SCOPE"),
    (lambda x: x["history"]["transitions"][0]["pr"].update(merge_commit_sha="0" * 40), "HISTORY_PR_IDENTITY_MISMATCH"),
    (lambda x: x["history"]["transitions"][0].update(pr=None), "CONTENT_PROVENANCE_MISSING"),
    (lambda x: x["history"]["transitions"][0]["pr"].update(merged=False), "CONTENT_PROVENANCE_MISSING"),
    (lambda x: x["history"]["transitions"][0]["pr"].update(primary_crs=[171, 16]), "CONTENT_PRIMARY_CR_AMBIGUOUS"),
    (lambda x: x.update(repository="other/repo"), "REPOSITORY_MISMATCH"),
])
def test_payload_scope_fails_closed_on_unproven_or_out_of_scope_content(mutate, code):
    value = evidence()
    mutate(value)
    result = evaluate(value)
    assert result.status == "FAIL"
    assert any(code in failure for failure in result.failure_codes)


def test_shared_path_keeps_out_of_scope_intermediate_contribution_blocking():
    value = evidence()
    first = deepcopy(value["history"]["transitions"][0])
    first.update(sha="3" * 40)
    first["pr"].update(merge_commit_sha="3" * 40, primary_crs=[155])
    first["changes"][0]["after"] = {"blob": "4" * 40, "mode": "100644"}
    final = value["history"]["transitions"][0]
    final["parent"] = first["sha"]
    final["changes"][0]["before"] = first["changes"][0]["after"]
    value["history"]["transitions"] = [first, final]
    assert any("CONTENT_OUT_OF_SCOPE" in x for x in evaluate(value).failure_codes)


def test_exact_net_zero_unmapped_pair_does_not_become_new_delivery():
    value = evidence()
    before = deepcopy(value["history"]["transitions"][0])
    before.update(sha="3" * 40, pr=None)
    before["changes"] = [{"path": "noop", "before": None, "after": {"blob": "5" * 40, "mode": "100644"}}]
    undo = {"sha": "4" * 40, "parent": "3" * 40, "pr": None,
            "changes": [{"path": "noop", "before": before["changes"][0]["after"], "after": None}]}
    value["history"]["transitions"][0]["parent"] = "4" * 40
    value["history"]["transitions"] = [before, undo, *value["history"]["transitions"]]
    assert evaluate(value).status == "PASS"
    undo["changes"] = []
    assert evaluate(value).status == "FAIL"


def test_cancelled_no_delivery_preserves_declared_scope_and_requires_authority():
    value = evidence()
    record = {"issue": 125, "comment_id": 123, "decision_owner": "owner", "provenance_verified": True,
              "state": "closed", "state_reason": "not_planned"}
    value["cancellations"] = [record]
    assert evaluate(value, (171, 125)).status == "PASS"
    record["provenance_verified"] = False
    assert evaluate(value, (171, 125)).status == "FAIL"


def test_cancelled_cr_cannot_be_delivered():
    value = evidence()
    value["cancellations"] = [{"issue": 171, "comment_id": 123, "decision_owner": "owner", "provenance_verified": True,
                               "state": "closed", "state_reason": "not_planned"}]
    assert "PHYSICAL_SCOPE_CANCELLED_CR_SHIPPED:#171" in evaluate(value).failure_codes


def test_payload_line_endings_are_not_normalized_out_of_delta():
    value = evidence()
    old = value["baseline"]["entries"]["docs/file.md"]
    value["candidate"]["entries"]["docs/file.md"]["blob"] = old["blob"]
    value["history"]["transitions"][0]["changes"] = []
    assert any("PAYLOAD_FORMAT_DRIFT" in x for x in evaluate(value).failure_codes)


def zip_bytes(content=b"a\n", source=SHA, kind="release", version="0.1.1", duplicate=False):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("file", content)
        archive.writestr("ddda-package.json", json.dumps({"source_commit": source, "kind": kind, "version": version}))
        if duplicate:
            archive.writestr("file", content)
    return stream.getvalue()


def test_package_binding_checks_physical_hash_and_exact_git_blob_with_windows_export():
    raw = b"a\n"
    tree = {"file": {"blob": hashlib.sha1(b"blob 2\0" + raw).hexdigest(), "mode": "100644"}}
    entries = package_entries(zip_bytes(b"a\r\n"), tree, SHA, "release", "0.1.1")
    assert entries["file"]["binding"] == "CRLF_EXPORT"
    assert entries["file"]["payload_sha256"] == hashlib.sha256(b"a\r\n").hexdigest()
    for data in [zip_bytes(b"b\n"), zip_bytes(source="0" * 40), zip_bytes(duplicate=True)]:
        with pytest.raises(ScopeCollectionError):
            package_entries(data, tree, SHA, "release", "0.1.1")
    with pytest.raises(ScopeCollectionError):
        package_entries(zip_bytes(), {}, SHA, "release", "0.1.1")


def test_asset_redirect_drops_authentication_outside_github_api():
    from urllib.request import Request
    request = Request("https://api.github.com/repos/owner/repo/releases/assets/1", headers={"Authorization": "Bearer test-only"})
    target = AssetRedirect().redirect_request(request, None, 302, "redirect", {}, "https://release-assets.githubusercontent.com/file")
    assert target.get_header("Authorization") is None
    with pytest.raises(ScopeCollectionError):
        AssetRedirect().redirect_request(request, None, 302, "redirect", {}, "https://untrusted.invalid/file")


MATRIX = json.loads((ROOT / "tests/fixtures/governance/scenario-matrix-v2.json").read_text())


@pytest.mark.parametrize("row", [x for x in MATRIX["scenarios"] if x["adapter"] == "standard_payload_scope"], ids=lambda x: x["id"])
def test_active_payload_scenarios_use_production_kernel(row):
    value = evidence()
    scope = [171]
    case = row["input"]["case"]
    if case == "out-of-scope-docs":
        value["history"]["transitions"][0]["pr"]["primary_crs"] = [155]
    elif case == "forged-chain":
        value["history"]["transitions"][0]["changes"] = []
    elif case == "cancelled-no-delivery":
        scope.append(125)
        value["cancellations"] = [{"issue": 125, "comment_id": 123, "decision_owner": "owner", "provenance_verified": True,
                                   "state": "closed", "state_reason": "not_planned"}]
    assert evaluate(value, scope).status == row["expected"]["status"]


def test_baseline_requires_original_asset_digest_and_complete_tag_identity(monkeypatch):
    import standard_scope_collection as ns
    data = zip_bytes()
    tree = {"file": {"blob": hashlib.sha1(b"blob 2\0a\n").hexdigest(), "mode": "100644"}}
    asset = {"id": 1, "name": "ddda-0.1.1.zip", "size": len(data), "digest": "sha256:" + hashlib.sha256(data).hexdigest()}
    def read(path, token):
        if "/releases/tags/" in path:
            return {"id": 2, "tag_name": "v0.1.1", "draft": False, "prerelease": False, "assets": [asset]}
        if "/git/ref/" in path:
            return {"object": {"type": "tag", "sha": "c" * 40}}
        return {"object": {"type": "commit", "sha": SHA}}
    monkeypatch.setattr(ns, "download_asset", lambda *_: data)
    monkeypatch.setattr(ns, "tree_entries", lambda *_: tree)
    assert baseline_snapshot(ROOT, "owner/repo", {"tag": "v0.1.1", "sha": SHA}, "test", read)["payload_verified"] is True
    asset["digest"] = "sha256:" + "0" * 64
    with pytest.raises(ScopeCollectionError):
        baseline_snapshot(ROOT, "owner/repo", {"tag": "v0.1.1", "sha": SHA}, "test", read)


def test_cancellation_collector_requires_explicit_human_owner_and_unique_record():
    rows = [{"number": 125, "state": "closed", "state_reason": "not_planned"}]
    record = {"schema_version": 1, "repository": "owner/repo", "issue": 125,
              "decision": "CANCELLED_NO_DELIVERY", "decision_owner": "owner"}
    comment = {"id": 10, "user": {"login": "owner", "type": "User"},
               "body": "<!-- ddda:cancelled-no-delivery:v1 -->\n```json\n" + json.dumps(record) + "\n```"}
    assert cancellation_evidence("owner/repo", rows, "test", lambda *_: [comment])[0]["comment_id"] == 10
    assert cancellation_evidence("owner/repo", rows, "test", lambda *_: []) == []
    assert cancellation_evidence("owner/repo", rows, "test", lambda *_: [comment, comment]) == []
    comment["user"]["type"] = "Bot"
    assert cancellation_evidence("owner/repo", rows, "test", lambda *_: [comment]) == []
