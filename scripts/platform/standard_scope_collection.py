"""Read-only acquisition for standard payload scope v2; no release decisions."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
import zipfile


class ScopeCollectionError(ValueError):
    pass


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return result.stdout


def tree_entries(root, sha):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ScopeCollectionError("Invalid immutable Git source")
    result = {}
    for row in git(root, "ls-tree", "-rz", "--full-tree", sha).split(b"\0"):
        if not row:
            continue
        metadata, name = row.split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        path = name.decode("utf-8")
        if kind != "blob" or mode not in {"100644", "100755", "120000"}:
            raise ScopeCollectionError("Unsupported source entry")
        result[path] = {"blob": blob, "mode": mode}
    return result


def package_entries(data, tree, source_sha, kind, version=None):
    """Bind all physical ZIP bytes to the complete immutable source tree."""
    entries = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [x.filename for x in archive.infolist()]
        if len(names) != len(set(names)):
            raise ScopeCollectionError("Duplicate ZIP entry")
        if sum(x.file_size for x in archive.infolist()) > 100_000_000:
            raise ScopeCollectionError("Package expansion exceeds evidence limit")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in item.filename:
                raise ScopeCollectionError("Unsafe ZIP path")
            if item.is_dir():
                continue
            raw = archive.read(item)
            if item.filename == "ddda-package.json":
                manifest = json.loads(raw.decode("utf-8-sig"))
                if manifest.get("source_commit") != source_sha or manifest.get("kind") != kind:
                    raise ScopeCollectionError("Package manifest identity mismatch")
                if version is not None and manifest.get("version") != version:
                    raise ScopeCollectionError("Package manifest version mismatch")
                continue
            expected = tree.get(item.filename)
            if expected is None:
                raise ScopeCollectionError("ZIP entry outside immutable source tree")
            archive_mode = item.external_attr >> 16
            if expected["mode"] == "120000" and archive_mode & 0o170000 != 0o120000:
                raise ScopeCollectionError("Package does not preserve source symlink")
            if expected["mode"] == "100755" and (archive_mode & 0o170000 != 0o100000 or not archive_mode & 0o111):
                raise ScopeCollectionError("Package does not preserve executable source mode")
            if expected["mode"] == "100644" and archive_mode & (0o111 | 0o070000):
                raise ScopeCollectionError("Package mode differs from regular non-executable source")
            def blob_hash(value):
                return hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest()
            binding = "EXACT"
            if blob_hash(raw) != expected["blob"]:
                # Windows git archive exports tracked text with CRLF. This is
                # a source binding only: raw payload hashes remain authoritative
                # for baseline delta; we never normalize away a payload change.
                if b"\0" in raw or blob_hash(raw.replace(b"\r\n", b"\n")) != expected["blob"]:
                    raise ScopeCollectionError("Package bytes do not bind to Git blob")
                binding = "CRLF_EXPORT"
            entries[item.filename] = {**expected, "payload_sha256": hashlib.sha256(raw).hexdigest(), "binding": binding, "archive_mode": archive_mode}
        if "ddda-package.json" not in names or set(entries) != set(tree):
            raise ScopeCollectionError("Package/tree coverage mismatch")
    return entries


class AssetRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urlsplit(newurl)
        if parts.scheme != "https" or parts.hostname not in {
            "api.github.com", "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"
        }:
            raise ScopeCollectionError("Unexpected release asset redirect")
        target = super().redirect_request(req, fp, code, msg, headers, newurl)
        if target is not None and parts.hostname != urlsplit(req.full_url).hostname:
            target.remove_header("Authorization")
        return target


def download_asset(repository, asset_id, token):
    request = Request(
        f"https://api.github.com/repos/{repository}/releases/assets/{int(asset_id)}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/octet-stream",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "DDDA-Standard-Scope"},
    )
    with build_opener(AssetRedirect()).open(request, timeout=60) as response:
        data = response.read(50_000_001)
    if len(data) > 50_000_000:
        raise ScopeCollectionError("Release asset exceeds evidence limit")
    return data


def baseline_snapshot(root, repository, previous, token, rest_get):
    release = rest_get(f"repos/{repository}/releases/tags/{previous['tag']}", token)
    if release.get("draft") or release.get("prerelease") or release.get("tag_name") != previous["tag"]:
        raise ScopeCollectionError("Previous canonical release identity invalid")
    ref = rest_get(f"repos/{repository}/git/ref/tags/{previous['tag']}", token)
    obj = ref.get("object") or {}
    if obj.get("type") != "tag":
        raise ScopeCollectionError("Canonical baseline must be an annotated tag")
    tag = rest_get(f"repos/{repository}/git/tags/{obj['sha']}", token)
    if (tag.get("object") or {}).get("sha") != previous["sha"] or (tag.get("object") or {}).get("type") != "commit":
        raise ScopeCollectionError("Baseline tag/source mismatch")
    version = previous["tag"].removeprefix("v")
    assets = [x for x in release.get("assets", []) if x.get("name") == f"ddda-{version}.zip"]
    if len(assets) != 1:
        raise ScopeCollectionError("Canonical baseline asset missing or ambiguous")
    asset = assets[0]
    digest = str(asset.get("digest") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ScopeCollectionError("Canonical baseline digest missing")
    data = download_asset(repository, asset["id"], token)
    actual = hashlib.sha256(data).hexdigest()
    if digest != f"sha256:{actual}" or len(data) != asset.get("size"):
        raise ScopeCollectionError("Canonical baseline asset integrity mismatch")
    reports = [x for x in release.get("assets", []) if x.get("name") == f"ddda-{version}-release-report.json"]
    if len(reports) != 1:
        raise ScopeCollectionError("Canonical baseline validation report missing or ambiguous")
    report_asset = reports[0]
    report_data = download_asset(repository, report_asset["id"], token)
    report_digest = hashlib.sha256(report_data).hexdigest()
    if report_asset.get("digest") != f"sha256:{report_digest}" or len(report_data) != report_asset.get("size"):
        raise ScopeCollectionError("Baseline validation report integrity mismatch")
    report = json.loads(report_data.decode("utf-8-sig"))
    origin = report.get("source") or {}
    if report.get("status") != "PASS" or origin.get("repository") != repository or origin.get("kind") != "release" or origin.get("commit") != previous["sha"] or (report.get("package") or {}).get("sha256") != actual:
        raise ScopeCollectionError("Baseline package is not bound to published PASS release evidence")
    tree = tree_entries(root, previous["sha"])
    entries = package_entries(data, tree, previous["sha"], "release", version)
    return {"tag": previous["tag"], "source_sha": previous["sha"], "tag_object_sha": obj["sha"],
            "release_id": release["id"], "asset_id": asset["id"], "package_sha256": actual,
            "report_asset_id": report_asset["id"], "report_sha256": report_digest,
            "entries": entries, "payload_verified": True}


def cancellation_evidence(repository, scope_rows, token, rest_pages):
    result = []
    for issue in scope_rows:
        if issue.get("state") != "closed" or issue.get("state_reason") != "not_planned":
            continue
        # An explicit human marker must be read from the Issue conversation,
        # not inferred from closure, a bot audit or arbitrary body prose.
        marker = "<!-- ddda:cancelled-no-delivery:v1 -->"
        records = []
        for comment in rest_pages(f"repos/{repository}/issues/{issue['number']}/comments", token):
            user = comment.get("user") or {}
            if marker not in (comment.get("body") or "") or user.get("type") != "User" or user.get("login") != repository.split("/", 1)[0]:
                continue
            blocks = re.findall(r"```json\s*([\s\S]*?)```", comment["body"])
            if len(blocks) != 1:
                continue
            record = json.loads(blocks[0])
            if record.get("schema_version") == 1 and record.get("repository") == repository and record.get("issue") == issue["number"] and record.get("decision_owner") == user.get("login") and record.get("decision") == "CANCELLED_NO_DELIVERY":
                records.append({"issue": issue["number"], "decision_owner": user["login"], "comment_id": comment["id"],
                                "state": "closed", "state_reason": "not_planned", "provenance_verified": True})
        if len(records) == 1:
            result.extend(records)
    return result


def collect_content_scope(root, repository, version, source_sha, candidate_path, candidate_digest,
                          previous, token, rest_get, rest_pages, shipping, scope_rows):
    baseline = baseline_snapshot(root, repository, previous, token, rest_get)
    tree = tree_entries(root, source_sha)
    data = Path(candidate_path).read_bytes()
    if hashlib.sha256(data).hexdigest() != candidate_digest:
        raise ScopeCollectionError("Candidate package digest mismatch")
    entries = package_entries(data, tree, source_sha, "candidate")
    anchors = git(root, "merge-base", "--all", previous["sha"], source_sha).decode().split()
    if len(anchors) != 1:
        raise ScopeCollectionError("Baseline/candidate merge base ambiguous")
    anchor = anchors[0]
    chain = git(root, "rev-list", "--first-parent", "--reverse", f"{anchor}..{source_sha}").decode().split()
    current = tree_entries(root, anchor)
    anchor_entries = current
    transitions = []
    by_merge = {x.get("merge_commit_sha"): x for x in shipping if x.get("merged") is True}
    expected_parent = anchor
    for sha in chain:
        parents = git(root, "show", "-s", "--format=%P", sha).decode().split()
        if not parents or parents[0] != expected_parent:
            raise ScopeCollectionError("First-parent source chain is not complete")
        after = tree_entries(root, sha)
        changes = [{"path": path, "before": current.get(path), "after": after.get(path)}
                   for path in sorted(set(current) | set(after)) if current.get(path) != after.get(path)]
        transitions.append({"sha": sha, "parent": expected_parent, "changes": changes, "pr": by_merge.get(sha)})
        expected_parent, current = sha, after
    if expected_parent != source_sha:
        raise ScopeCollectionError("Source chain does not reach exact candidate")
    return {"schema_version": 2, "contract": "ddda_standard_payload_scope", "repository": repository,
            "version": version, "release_source_sha": source_sha, "baseline": baseline,
            "candidate": {"source_sha": source_sha, "package_sha256": candidate_digest, "entries": entries,
                          "payload_verified": True},
            "history": {"anchor_sha": anchor, "anchor_entries": anchor_entries, "transitions": transitions},
            "cancellations": cancellation_evidence(repository, scope_rows, token, rest_pages)}
