param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryRoot,
    [switch]$NoPush
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Read-LfText {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.File]::ReadAllText($Path).Replace("`r`n", "`n")
}

function Write-LfText {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )
    [System.IO.File]::WriteAllText($Path, $Content, [System.Text.UTF8Encoding]::new($false))
}

function Replace-ExactlyOnce {
    param(
        [Parameter(Mandatory = $true)][string]$Content,
        [Parameter(Mandatory = $true)][string]$Old,
        [Parameter(Mandatory = $true)][string]$New,
        [Parameter(Mandatory = $true)][string]$Label
    )

    $oldLf = $Old.Replace("`r`n", "`n")
    $newLf = $New.Replace("`r`n", "`n")
    $first = $Content.IndexOf($oldLf, [System.StringComparison]::Ordinal)
    if ($first -lt 0) {
        throw "Expected planning anchor not found: $Label"
    }
    $second = $Content.IndexOf($oldLf, $first + $oldLf.Length, [System.StringComparison]::Ordinal)
    if ($second -ge 0) {
        throw "Planning anchor is ambiguous: $Label"
    }
    return $Content.Substring(0, $first) + $newLf + $Content.Substring($first + $oldLf.Length)
}

$root = (Resolve-Path -LiteralPath $RepositoryRoot).Path
Set-Location -LiteralPath $root

$expectedBase = '50f30e378a2b916a9fa65da9d5341468282f5a43'
$currentHead = (git rev-parse HEAD).Trim()
if ($currentHead -eq $expectedBase) {
    # expected staging parent is one commit above main; this guard is refined below
}

$branch = (git branch --show-current).Trim()
if ($branch -ne 'fix/16-plan-cr131-cr132-0.1.2') {
    throw "Unexpected branch '$branch'."
}

$statusBefore = git status --porcelain
if ($statusBefore) {
    throw "Working tree is not clean before remediation: $statusBefore"
}

$policyPath = Join-Path $root 'config/governance/backlog-policy.yaml'
$bootstrapPath = Join-Path $root 'config/governance/github-bootstrap.json'
$roadmapPath = Join-Path $root 'docs/roadmap/backlog-index.md'
$testPath = Join-Path $root 'runtime/platform/tests/test_project_backlog_delivery_governance.py'

# backlog-policy.yaml
$policy = Read-LfText $policyPath
$policy = Replace-ExactlyOnce $policy `
    '    unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113, 125]' `
    '    unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113, 125, 131, 132]' `
    'Other unparented_items'
$policy = Replace-ExactlyOnce $policy `
    '      issues: [16, 65, 69, 73, 85, 94, 113, 125]' `
    '      issues: [16, 65, 69, 73, 85, 94, 113, 125, 131, 132]' `
    'DDDA 0.1.2 backlog-policy milestone scope'
Write-LfText $policyPath $policy

# github-bootstrap.json
$bootstrap = Read-LfText $bootstrapPath
$bootstrapAnchorOld = @'
        "Outcome summary": "Backfill the historical DDDA 0.1.0 GitHub Release from the original validated canonical package and portable evidence without changing source, tag or historical release decision."
      }
    },
    {
      "kind": "issue",
      "numbers": [
        67,
'@
$bootstrapAnchorNew = @'
        "Outcome summary": "Backfill the historical DDDA 0.1.0 GitHub Release from the original validated canonical package and portable evidence without changing source, tag or historical release decision."
      }
    },
    {
      "kind": "issue",
      "numbers": [131],
      "metadata": {
        "Status": "Backlog",
        "Priority": "P1",
        "Work Package": "Other",
        "Item Type": "Change Request",
        "Platform Area": "RELEASE",
        "Impact": "HIGH",
        "Target Release": "0.1.2",
        "Blocked": "No",
        "Human Review": "Pending",
        "Outcome summary": "Make every DDDA release-candidate PR human-recognizable and machine-verifiable through consistent title, labels, branch and versioned body marker, with explicit normal versus controlled-recovery semantics."
      }
    },
    {
      "kind": "issue",
      "numbers": [132],
      "metadata": {
        "Status": "Backlog",
        "Priority": "P2",
        "Work Package": "Other",
        "Item Type": "Change Request",
        "Platform Area": "SECURITY-GOVERNANCE",
        "Impact": "MEDIUM",
        "Target Release": "0.1.2",
        "Blocked": "No",
        "Human Review": "Pending",
        "Outcome summary": "Define one canonical naming contract for DDDA GitHub Issues, PRs, branches, labels, markers, milestones, tags, Releases, workflows and evidence artifacts while preserving #65 and #131 ownership boundaries."
      }
    },
    {
      "kind": "issue",
      "numbers": [
        67,
'@
$bootstrap = Replace-ExactlyOnce $bootstrap $bootstrapAnchorOld $bootstrapAnchorNew 'bootstrap item groups after #125'
$bootstrap = Replace-ExactlyOnce $bootstrap `
    '      "issues": [16, 65, 69, 73, 85, 94, 113, 125],' `
    '      "issues": [16, 65, 69, 73, 85, 94, 113, 125, 131, 132],' `
    'DDDA 0.1.2 bootstrap milestone scope'
Write-LfText $bootstrapPath $bootstrap

# docs/roadmap/backlog-index.md
$roadmap = Read-LfText $roadmapPath
$roadmap = Replace-ExactlyOnce $roadmap `
    '| DDDA 0.1.2 | Governance consolidation: #16, #65, #69, #73, #85, #94, #113, #125. |' `
    '| DDDA 0.1.2 | Governance consolidation: #16, #65, #69, #73, #85, #94, #113, #125, #131, #132. |' `
    'roadmap 0.1.2 scope row'
$roadmap = Replace-ExactlyOnce $roadmap `
    '- #125 — historical DDDA 0.1.0 GitHub Release publication backfill (`Other`, primary `RELEASE`), P1 and planned for DDDA 0.1.2.' `
    @'
- #125 — historical DDDA 0.1.0 GitHub Release publication backfill (`Other`, primary `RELEASE`), P1 and planned for DDDA 0.1.2.
- #131 — canonical release-candidate PR identity (`Other`, primary `RELEASE`), P1 and planned for DDDA 0.1.2; visible through title, labels, branch and versioned body marker.
- #132 — canonical GitHub artifact naming convention (`Other`, primary `SECURITY-GOVERNANCE`), P2 and planned for DDDA 0.1.2; consumes #65 branch ownership and #131 release-candidate specialization.
'@ `
    'roadmap cross-cutting #125 anchor'
Write-LfText $roadmapPath $roadmap

# runtime/platform/tests/test_project_backlog_delivery_governance.py
$tests = Read-LfText $testPath
$tests = Replace-ExactlyOnce $tests `
    '        "DDDA 0.1.2": [16, 65, 69, 73, 85, 94, 113, 125],' `
    '        "DDDA 0.1.2": [16, 65, 69, 73, 85, 94, 113, 125, 131, 132],' `
    'test expected DDDA 0.1.2 scope'
$tests = Replace-ExactlyOnce $tests `
    '    assert "unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113, 125]" in POLICY.read_text(encoding="utf-8")' `
    '    assert "unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113, 125, 131, 132]" in POLICY.read_text(encoding="utf-8")' `
    'test Other unparented_items contract'
$testsAnchorOld = @'
    assert meta[125]["Outcome summary"] == (
        "Backfill the historical DDDA 0.1.0 GitHub Release from the original validated "
        "canonical package and portable evidence without changing source, tag or historical "
        "release decision."
    )
    assert meta[88]["Item Type"] == "Enabler"
'@
$testsAnchorNew = @'
    assert meta[125]["Outcome summary"] == (
        "Backfill the historical DDDA 0.1.0 GitHub Release from the original validated "
        "canonical package and portable evidence without changing source, tag or historical "
        "release decision."
    )
    assert meta[131]["Item Type"] == "Change Request"
    assert meta[131]["Work Package"] == "Other"
    assert meta[131]["Priority"] == "P1"
    assert meta[131]["Platform Area"] == "RELEASE"
    assert meta[131]["Impact"] == "HIGH"
    assert meta[131]["Target Release"] == "0.1.2"
    assert meta[131]["Status"] == "Backlog"
    assert meta[131]["Blocked"] == "No"
    assert meta[131]["Human Review"] == "Pending"
    assert meta[131]["Outcome summary"] == (
        "Make every DDDA release-candidate PR human-recognizable and machine-verifiable "
        "through consistent title, labels, branch and versioned body marker, with explicit "
        "normal versus controlled-recovery semantics."
    )
    assert meta[132]["Item Type"] == "Change Request"
    assert meta[132]["Work Package"] == "Other"
    assert meta[132]["Priority"] == "P2"
    assert meta[132]["Platform Area"] == "SECURITY-GOVERNANCE"
    assert meta[132]["Impact"] == "MEDIUM"
    assert meta[132]["Target Release"] == "0.1.2"
    assert meta[132]["Status"] == "Backlog"
    assert meta[132]["Blocked"] == "No"
    assert meta[132]["Human Review"] == "Pending"
    assert meta[132]["Outcome summary"] == (
        "Define one canonical naming contract for DDDA GitHub Issues, PRs, branches, labels, "
        "markers, milestones, tags, Releases, workflows and evidence artifacts while "
        "preserving #65 and #131 ownership boundaries."
    )
    assert meta[88]["Item Type"] == "Enabler"
'@
$tests = Replace-ExactlyOnce $tests $testsAnchorOld $testsAnchorNew 'test metadata assertions after #125'
Write-LfText $testPath $tests

# Remove the temporary transport so the final net diff contains only canonical planning files.
Remove-Item -LiteralPath $PSCommandPath -Force

# Mechanical precommit checks available without optional Python packages.
python -m json.tool $bootstrapPath *> $null
if ($LASTEXITCODE -ne 0) { throw 'github-bootstrap.json is invalid JSON.' }

git diff --check
if ($LASTEXITCODE -ne 0) { throw 'git diff --check failed.' }

$changed = @(git status --porcelain | ForEach-Object { $_.Substring(3) })
$expected = @(
    'config/governance/backlog-policy.yaml',
    'config/governance/github-bootstrap.json',
    'docs/roadmap/backlog-index.md',
    'runtime/platform/tests/test_project_backlog_delivery_governance.py',
    'scripts/remediation/Plan-CR131-CR132-0.1.2.ps1'
)
foreach ($path in $changed) {
    if ($expected -notcontains $path) {
        throw "Unexpected changed path: $path"
    }
}
foreach ($path in $expected) {
    if ($changed -notcontains $path) {
        throw "Expected changed path missing: $path"
    }
}

# Sanity assertions for the intended versioned contract.
$policyFinal = Read-LfText $policyPath
$bootstrapFinal = Read-LfText $bootstrapPath
$roadmapFinal = Read-LfText $roadmapPath
$testsFinal = Read-LfText $testPath
foreach ($needle in @('131', '132')) {
    if (-not $policyFinal.Contains($needle)) { throw "backlog-policy missing #$needle" }
    if (-not $bootstrapFinal.Contains($needle)) { throw "github-bootstrap missing #$needle" }
    if (-not $roadmapFinal.Contains("#$needle")) { throw "roadmap missing #$needle" }
    if (-not $testsFinal.Contains("meta[$needle]")) { throw "regression test missing #$needle" }
}

# One remediation commit; broker performs the remote push.
git config user.name 'DDDA Remote Remediation'
git config user.email 'ddda-remote-remediation@example.invalid'
git add --all -- config/governance/backlog-policy.yaml config/governance/github-bootstrap.json docs/roadmap/backlog-index.md runtime/platform/tests/test_project_backlog_delivery_governance.py scripts/remediation/Plan-CR131-CR132-0.1.2.ps1
git commit -m 'fix(governance): plan CR131 and CR132 for 0.1.2'
if ($LASTEXITCODE -ne 0) { throw 'git commit failed.' }

$statusAfter = git status --porcelain
if ($statusAfter) {
    throw "Working tree is not clean after remediation: $statusAfter"
}

if (-not $NoPush) {
    throw 'This remediation must run with -NoPush; broker owns the validated push.'
}
