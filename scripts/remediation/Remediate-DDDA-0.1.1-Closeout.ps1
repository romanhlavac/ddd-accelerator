param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ReleaseSourceSha = '4415c17fcba98298c40b25555a9a0bf5f550f13e'
$ReleaseScope = @(9, 12, 67, 68, 70, 96, 98)
$SelfPath = 'scripts/remediation/Remediate-DDDA-0.1.1-Closeout.ps1'

Set-Location -LiteralPath $RepositoryRoot
$actualHead = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve remediation HEAD.' }
$authorizedHead = [string]$env:AUTHORIZED_HEAD_SHA
if ([string]::IsNullOrWhiteSpace($authorizedHead) -or $actualHead -ne $authorizedHead) {
    throw "Closeout remediation exact-SHA mismatch. Authorized='$authorizedHead', actual='$actualHead'."
}
if ((git status --porcelain)) {
    throw 'Closeout remediation requires a clean working tree.'
}

# The reviewed controlled release source is immutable and intentionally outside
# main ancestry. fetch-depth=0 must make the source object available; otherwise
# fail closed rather than reconstructing release truth heuristically.
git cat-file -e "$ReleaseSourceSha^{commit}"
if ($LASTEXITCODE -ne 0) {
    throw "Frozen DDDA 0.1.1 release-source commit $ReleaseSourceSha is unavailable in this exact-SHA checkout."
}

$python = @'
from __future__ import annotations
import json
from pathlib import Path
import subprocess

ROOT = Path.cwd()
SOURCE_SHA = "4415c17fcba98298c40b25555a9a0bf5f550f13e"
SCOPE = [9, 12, 67, 68, 70, 96, 98]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def exactly_once(text: str, old: str, new: str, path: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one replacement, found {count}: {old[:140]!r}")
    return text.replace(old, new, 1)


# 1) Project the immutable released changelog section back to main, preserving
# only genuine post-release deltas under Unreleased.
current = read("CHANGELOG.md")
frozen = subprocess.check_output(
    ["git", "show", f"{SOURCE_SHA}:CHANGELOG.md"], text=True, encoding="utf-8"
)
release_heading = "## [0.1.1] - 2026-09-16"
explanatory = "Změny pro další verzi se během vývoje zapisují sem. Před promotion se všechny položky přesunou do jediné verze `X.Y.Z` s ISO datem a tato sekce zůstane bez release položek."
if release_heading not in frozen:
    raise RuntimeError("Frozen release source does not contain the canonical 0.1.1 changelog heading")
if release_heading in current:
    raise RuntimeError("Current main already contains the 0.1.1 release section; refusing a non-idempotent rewrite")

frozen_release_start = frozen.index(release_heading)
frozen_expl = frozen.index(explanatory, frozen_release_start)
frozen_release_block = frozen[frozen_release_start:frozen_expl].rstrip()
frozen_body = frozen_release_block[len(release_heading):].strip()

current_unreleased = current.index("## [Unreleased]")
current_expl = current.index(explanatory, current_unreleased)
current_body = current[current_unreleased + len("## [Unreleased]"):current_expl].strip()


def section(body: str, name: str, next_name: str | None) -> str:
    marker = f"### {name}"
    if marker not in body:
        return ""
    start = body.index(marker) + len(marker)
    end = len(body) if next_name is None else body.index(f"### {next_name}", start)
    return body[start:end].strip()

for category, nxt in (("Added", "Changed"), ("Changed", "Fixed")):
    if section(current_body, category, nxt) != section(frozen_body, category, nxt):
        raise RuntimeError(f"Current main {category} is not the exact frozen 0.1.1 section")
current_fixed = section(current_body, "Fixed", None)
frozen_fixed = section(frozen_body, "Fixed", None)
if not current_fixed.endswith(frozen_fixed):
    raise RuntimeError("Current main Fixed section does not end with the frozen 0.1.1 Fixed section")
post_release_fixed = current_fixed[: len(current_fixed) - len(frozen_fixed)].strip()
if not post_release_fixed:
    raise RuntimeError("Expected the known post-release Fixed delta on main")

unreleased = (
    "## [Unreleased]\n\n"
    "### Changed\n\n"
    "- release-train governance now permits the single marker-designated train to be explicitly closed after publication without implicitly activating any planned future milestone; a later train requires a separate versioned/human planning decision.\n\n"
    "### Fixed\n\n"
    + post_release_fixed
    + "\n\n- post-release closeout now projects the canonical DDDA 0.1.1 release cut back to `main` and closes its versioned release-train state without changing the released tag, GitHub Release, canonical assets or release scope.\n\n"
)
current = current[:current_unreleased] + unreleased + frozen_release_block + "\n\n" + current[current_expl:]
write("CHANGELOG.md", current)

# 2) Make the already-published 0.1.1 train terminal in both versioned sources.
bootstrap_path = "config/governance/github-bootstrap.json"
bootstrap = json.loads(read(bootstrap_path))
matches = [m for m in bootstrap.get("milestones", []) if m.get("title") == "DDDA 0.1.1"]
if len(matches) != 1:
    raise RuntimeError(f"Expected one DDDA 0.1.1 milestone contract, got {len(matches)}")
ms = matches[0]
if ms.get("state") != "open" or ms.get("issues") != SCOPE or ms.get("pulls") != []:
    raise RuntimeError(f"Unexpected DDDA 0.1.1 bootstrap baseline: {ms}")
ms["state"] = "closed"
write(bootstrap_path, json.dumps(bootstrap, ensure_ascii=False, indent=2) + "\n")

policy_path = "config/governance/backlog-policy.yaml"
policy = read(policy_path)
old = """    - name: DDDA 0.1.1
      state: open
      issues: [9, 12, 67, 68, 70, 96, 98]
      pulls: []
      pre_release_prerequisites: [44]"""
policy = exactly_once(policy, old, old.replace("state: open", "state: closed", 1), policy_path)
write(policy_path, policy)

# 3) Closing the marker-designated train must produce an intentional idle state,
# not implicitly activate an already-planned future milestone. Missing or
# multiple markers still fail closed.
collector_path = "scripts/platform/Test-DDDAMergeReleaseEligibility.py"
collector = read(collector_path)
collector = collector.replace(
    "POLICY_ACTIVE_MILESTONE_RE",
    "POLICY_MARKED_MILESTONE_RE",
)
old_state_pattern = '    r"(?:(?!^[ \\t]*-[ \\t]+name:).)*?^[ \\t]+state:[ \\t]*open[ \\t]*\\r?$"'
new_state_pattern = '    r"(?:(?!^[ \\t]*-[ \\t]+name:).)*?^[ \\t]+state:[ \\t]*(?P<state>open|closed)[ \\t]*\\r?$"'
collector = exactly_once(collector, old_state_pattern, new_state_pattern, collector_path)
old_fn = '''def configured_active_release(backlog_policy: str) -> str | None:
    policy = backlog_policy or ""
    marked = POLICY_MARKED_MILESTONE_RE.findall(policy)
    if "release_train:" in policy:
        if len(marked) != 1:
            raise GitHubReadError(
                "Expected exactly one marker-designated active DDDA release train, "
                f"found {sorted(marked)}"
            )
        return marked[0]
'''
new_fn = '''def configured_active_release(backlog_policy: str) -> str | None:
    policy = backlog_policy or ""
    marked = POLICY_MARKED_MILESTONE_RE.findall(policy)
    if "release_train:" in policy:
        if len(marked) != 1:
            raise GitHubReadError(
                "Expected exactly one marker-designated DDDA release train, "
                f"found {sorted(marked)}"
            )
        version, state = marked[0]
        if state == "closed":
            return None
        return version
'''
collector = exactly_once(collector, old_fn, new_fn, collector_path)
write(collector_path, collector)

collector_test_path = "runtime/platform/tests/test_merge_release_eligibility_collector.py"
tests = read(collector_test_path)
anchor = '''def test_active_release_fails_closed_when_release_train_has_no_marker() -> None:
'''
addition = '''def test_active_release_allows_closed_marker_without_activating_future_train() -> None:
    backlog_policy = """
milestones:
  release_train:
    - name: DDDA 0.1.1
      state: closed
      issues: [9]
      pulls: []
      pre_release_prerequisites: [44]
    - name: DDDA 0.1.2
      state: open
      issues: [16]
      pulls: []
"""
    milestones = [
        {"title": "DDDA 0.1.1", "state": "closed"},
        {"title": "DDDA 0.1.2", "state": "open"},
    ]
    assert COLLECTOR.active_release(milestones, backlog_policy) is None


def test_active_release_fails_closed_when_release_train_has_no_marker() -> None:
'''
tests = exactly_once(tests, anchor, addition, collector_test_path)
write(collector_test_path, tests)

backlog_test_path = "runtime/platform/tests/test_project_backlog_delivery_governance.py"
backlog_tests = read(backlog_test_path)
old_state_assert = '''    assert specs["DDDA 0.1.0"]["state"] == "closed"
    assert specs["DDDA 0.1.0"]["issues"] == [10, 11, 13, 14]
    assert specs["DDDA 0.1.0"]["pulls"] == [8]
    for title, issues in expected.items():
        assert specs[title]["issues"] == issues
        if title != "DDDA 0.1.0":
            assert specs[title]["state"] == "open"
            assert specs[title]["pulls"] == []
'''
new_state_assert = '''    assert specs["DDDA 0.1.0"]["state"] == "closed"
    assert specs["DDDA 0.1.0"]["issues"] == [10, 11, 13, 14]
    assert specs["DDDA 0.1.0"]["pulls"] == [8]
    for title, issues in expected.items():
        assert specs[title]["issues"] == issues
        if title in {"DDDA 0.1.0", "DDDA 0.1.1"}:
            assert specs[title]["state"] == "closed"
        else:
            assert specs[title]["state"] == "open"
        if title != "DDDA 0.1.0":
            assert specs[title]["pulls"] == []
'''
backlog_tests = exactly_once(backlog_tests, old_state_assert, new_state_assert, backlog_test_path)
write(backlog_test_path, backlog_tests)

lifecycle_path = "docs/developer-guide/platform-development-lifecycle.md"
lifecycle = read(lifecycle_path)
old_lifecycle = '''Dokud je otevřený právě jeden release train `DDDA X.Y.Z`, `merge-pr` navíc fail-closed odmítne PR, jehož jediný primary CR není v jeho Milestone. To je prevence nové kontaminace `main`; není to Release Scope Gate ani release authorization.'''
new_lifecycle = '''Dokud existuje právě jeden marker-designovaný aktivní release train `DDDA X.Y.Z`, `merge-pr` navíc fail-closed odmítne PR, jehož jediný primary CR není v jeho Milestone. To je prevence nové kontaminace `main`; není to Release Scope Gate ani release authorization. Po publikaci lze marker-designovaný train versioned změnou uzavřít; tím vznikne stav bez aktivního release trainu. Pouhá existence otevřených budoucích Milestones žádný z nich neaktivuje — aktivace dalšího trainu vyžaduje samostatné versioned/human planning rozhodnutí.'''
lifecycle = exactly_once(lifecycle, old_lifecycle, new_lifecycle, lifecycle_path)
write(lifecycle_path, lifecycle)

print(json.dumps({
    "status": "prepared",
    "release_source_sha": SOURCE_SHA,
    "release_scope": SCOPE,
    "changed_paths": [
        "CHANGELOG.md",
        bootstrap_path,
        policy_path,
        collector_path,
        collector_test_path,
        backlog_test_path,
        lifecycle_path,
    ],
}, indent=2))
'@

$tempPy = Join-Path $env:RUNNER_TEMP 'ddda-011-closeout.py'
Set-Content -LiteralPath $tempPy -Value $python -Encoding UTF8
python $tempPy
if ($LASTEXITCODE -ne 0) { throw "DDDA 0.1.1 closeout transformation failed: $LASTEXITCODE" }

python -m pip install --disable-pip-version-check --quiet "pytest>=8,<9"
if ($LASTEXITCODE -ne 0) { throw "Failed to provision pytest for focused closeout validation: $LASTEXITCODE" }

python -m pytest -q `
  runtime/platform/tests/test_merge_release_eligibility_collector.py `
  runtime/platform/tests/test_project_backlog_delivery_governance.py
if ($LASTEXITCODE -ne 0) { throw "DDDA 0.1.1 closeout regression tests failed: $LASTEXITCODE" }

python -m json.tool config/governance/github-bootstrap.json | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'github-bootstrap.json is invalid JSON' }

$changed = @(git diff --name-only)
$expected = @(
    'CHANGELOG.md',
    'config/governance/backlog-policy.yaml',
    'config/governance/github-bootstrap.json',
    'docs/developer-guide/platform-development-lifecycle.md',
    'runtime/platform/tests/test_merge_release_eligibility_collector.py',
    'runtime/platform/tests/test_project_backlog_delivery_governance.py',
    'scripts/platform/Test-DDDAMergeReleaseEligibility.py'
) | Sort-Object
$actual = @($changed | Sort-Object)
if (($actual -join "`n") -ne ($expected -join "`n")) {
    throw "Unexpected closeout diff paths. Expected:`n$($expected -join "`n")`nActual:`n$($actual -join "`n")"
}

# Self-remove the staging transport in the one broker-created implementation commit.
git rm -- $SelfPath
if ($LASTEXITCODE -ne 0) { throw 'Failed to self-remove closeout remediation script' }
git add -- @expected
if ($LASTEXITCODE -ne 0) { throw 'Failed to stage closeout paths' }

git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'git diff --cached --check failed' }

git commit -m 'chore(release): close DDDA 0.1.1 train'
if ($LASTEXITCODE -ne 0) { throw 'Failed to commit DDDA 0.1.1 closeout' }

if ((git status --porcelain)) {
    throw 'Closeout remediation did not leave a clean working tree.'
}

if (-not $NoPush) {
    throw 'This remediation must be invoked by the DDDA remote broker with -NoPush; the broker owns the validated push.'
}
