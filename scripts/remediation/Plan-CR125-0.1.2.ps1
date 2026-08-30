[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $NoPush) {
    throw 'This remediation must run with -NoPush; the trusted broker owns the push.'
}

$root = (Resolve-Path -LiteralPath $RepositoryRoot).Path
Set-Location -LiteralPath $root

$baseSha = 'ab6abb02cf76338796efbb12c32d16ccaf23e47b'
$stagingParent = '5dd36b68ba165104909f09216eb2fb01feb8f861'
$scriptRel = 'scripts/remediation/Plan-CR125-0.1.2.ps1'
$targetPaths = @(
    'config/governance/backlog-policy.yaml',
    'config/governance/github-bootstrap.json',
    'docs/roadmap/backlog-index.md',
    'runtime/platform/tests/test_project_backlog_delivery_governance.py'
)

$head = (& git rev-parse HEAD).Trim()
$parent = (& git rev-parse HEAD^).Trim()
if ($parent -ne $stagingParent) {
    throw "Corrective transport parent '$parent' does not match expected staging SHA '$stagingParent'."
}
if (-not [string]::IsNullOrWhiteSpace(((& git status --porcelain) -join "`n"))) {
    throw 'Working tree must be clean before remediation.'
}

$stagingDelta = @(& git diff --name-only "$baseSha..$head")
if ($stagingDelta.Count -ne 1 -or $stagingDelta[0] -ne $scriptRel) {
    throw "Expected net transport delta to contain only '$scriptRel'; observed: $($stagingDelta -join ', ')."
}

$beforeHashes = [ordered]@{}
foreach ($path in $targetPaths) {
    $baseObject = ('{0}:{1}' -f $baseSha, $path)
    $expectedBlob = (& git rev-parse $baseObject).Trim()
    $actualBlob = (& git hash-object -- $path).Trim()
    if ($actualBlob -ne $expectedBlob) {
        throw "Baseline integrity mismatch for '$path': expected Git blob $expectedBlob, got $actualBlob."
    }
    $beforeHashes[$path] = (Get-FileHash -LiteralPath (Join-Path $root $path) -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Replace-Unique {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Old,
        [Parameter(Mandatory = $true)][string]$New
    )
    $full = Join-Path $root $Path
    $text = [System.IO.File]::ReadAllText($full)
    $count = ([regex]::Matches($text, [regex]::Escape($Old))).Count
    if ($count -ne 1) {
        throw "Expected exactly one match in '$Path', found $count."
    }
    [System.IO.File]::WriteAllText(
        $full,
        $text.Replace($Old, $New),
        [System.Text.UTF8Encoding]::new($false)
    )
}

Replace-Unique -Path $targetPaths[0] `
    -Old '    unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113]' `
    -New '    unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113, 125]'
Replace-Unique -Path $targetPaths[0] `
    -Old '      issues: [16, 65, 69, 73, 85, 94, 113]' `
    -New '      issues: [16, 65, 69, 73, 85, 94, 113, 125]'

Replace-Unique -Path $targetPaths[1] `
    -Old '      "issues": [16, 65, 69, 73, 85, 94, 113],' `
    -New '      "issues": [16, 65, 69, 73, 85, 94, 113, 125],'

$bootstrapPath = Join-Path $root $targetPaths[1]
$bootstrapText = [System.IO.File]::ReadAllText($bootstrapPath)
$nl = if ($bootstrapText.Contains("`r`n")) { "`r`n" } else { "`n" }
$anchor = @(
    '        "Outcome summary": "Expose the canonical DDDA operating model in entry-point documentation: Work as development/governance control plane, GitHub as canonical system of record, GitHub Actions as authoritative technical execution plane, and Cursor as the current reference project runtime."',
    '      }',
    '    },',
    '    {',
    '      "kind": "issue",',
    '      "numbers": [',
    '        67,',
    '        68'
) -join $nl
$replacement = @(
    '        "Outcome summary": "Expose the canonical DDDA operating model in entry-point documentation: Work as development/governance control plane, GitHub as canonical system of record, GitHub Actions as authoritative technical execution plane, and Cursor as the current reference project runtime."',
    '      }',
    '    },',
    '    {',
    '      "kind": "issue",',
    '      "numbers": [125],',
    '      "metadata": {',
    '        "Status": "Backlog",',
    '        "Priority": "P1",',
    '        "Work Package": "Other",',
    '        "Item Type": "Change Request",',
    '        "Platform Area": "RELEASE",',
    '        "Impact": "HIGH",',
    '        "Target Release": "0.1.2",',
    '        "Blocked": "No",',
    '        "Human Review": "Pending",',
    '        "Outcome summary": "Backfill the historical DDDA 0.1.0 GitHub Release from the original validated canonical package and portable evidence without changing source, tag or historical release decision."',
    '      }',
    '    },',
    '    {',
    '      "kind": "issue",',
    '      "numbers": [',
    '        67,',
    '        68'
) -join $nl
Replace-Unique -Path $targetPaths[1] -Old $anchor -New $replacement

Replace-Unique -Path $targetPaths[2] `
    -Old '| DDDA 0.1.2 | Governance consolidation: #16, #65, #69, #73, #85, #94, #113. |' `
    -New '| DDDA 0.1.2 | Governance consolidation: #16, #65, #69, #73, #85, #94, #113, #125. |'
$roadmapPath = Join-Path $root $targetPaths[2]
$roadmapText = [System.IO.File]::ReadAllText($roadmapPath)
$roadmapNl = if ($roadmapText.Contains("`r`n")) { "`r`n" } else { "`n" }
$roadmapAnchor = '- #113 — entry-point operating-model documentation (`Other`, primary `DOC`, secondary `METHODOLOGY`), planned for DDDA 0.1.2.'
$roadmapReplacement = $roadmapAnchor + $roadmapNl + '- #125 — historical DDDA 0.1.0 GitHub Release publication backfill (`Other`, primary `RELEASE`), P1 and planned for DDDA 0.1.2.'
Replace-Unique -Path $targetPaths[2] -Old $roadmapAnchor -New $roadmapReplacement

Replace-Unique -Path $targetPaths[3] `
    -Old '        "DDDA 0.1.2": [16, 65, 69, 73, 85, 94, 113],' `
    -New '        "DDDA 0.1.2": [16, 65, 69, 73, 85, 94, 113, 125],'
Replace-Unique -Path $targetPaths[3] `
    -Old '    assert "unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113]" in POLICY.read_text(encoding="utf-8")' `
    -New '    assert "unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88, 94, 96, 98, 113, 125]" in POLICY.read_text(encoding="utf-8")'

$testPath = Join-Path $root $targetPaths[3]
$testText = [System.IO.File]::ReadAllText($testPath)
$testNl = if ($testText.Contains("`r`n")) { "`r`n" } else { "`n" }
$testAnchor = @(
    '        "reference project runtime."',
    '    )',
    '    assert meta[88]["Item Type"] == "Enabler"'
) -join $testNl
$testReplacement = @(
    '        "reference project runtime."',
    '    )',
    '    assert meta[125]["Item Type"] == "Change Request"',
    '    assert meta[125]["Work Package"] == "Other"',
    '    assert meta[125]["Priority"] == "P1"',
    '    assert meta[125]["Platform Area"] == "RELEASE"',
    '    assert meta[125]["Impact"] == "HIGH"',
    '    assert meta[125]["Target Release"] == "0.1.2"',
    '    assert meta[125]["Status"] == "Backlog"',
    '    assert meta[125]["Blocked"] == "No"',
    '    assert meta[125]["Human Review"] == "Pending"',
    '    assert meta[125]["Outcome summary"] == (',
    '        "Backfill the historical DDDA 0.1.0 GitHub Release from the original validated "',
    '        "canonical package and portable evidence without changing source, tag or historical "',
    '        "release decision."',
    '    )',
    '    assert meta[88]["Item Type"] == "Enabler"'
) -join $testNl
Replace-Unique -Path $targetPaths[3] -Old $testAnchor -New $testReplacement

$policyText = [System.IO.File]::ReadAllText((Join-Path $root $targetPaths[0]))
if (-not $policyText.Contains('      issues: [9, 12, 67, 68, 70, 96, 98]')) {
    throw 'DDDA 0.1.1 versioned scope changed unexpectedly.'
}

& git rm -- $scriptRel | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Failed to remove remediation transport.' }

$expectedChanges = @($targetPaths + $scriptRel) | Sort-Object
$actualChanges = @(& git diff --name-only HEAD --) | Sort-Object
if (($actualChanges -join "`n") -ne ($expectedChanges -join "`n")) {
    throw "Unexpected changed paths. Expected: $($expectedChanges -join ', '); observed: $($actualChanges -join ', ')."
}

& git diff --check
if ($LASTEXITCODE -ne 0) { throw 'git diff --check failed.' }
& python -m json.tool config/governance/github-bootstrap.json *> $null
if ($LASTEXITCODE -ne 0) { throw 'github-bootstrap.json is not valid JSON.' }
& python -m pip install --disable-pip-version-check 'pytest>=8,<9'
if ($LASTEXITCODE -ne 0) { throw 'Failed to install governance test dependency pytest.' }
& python -m pytest -q runtime/platform/tests/test_project_backlog_delivery_governance.py
if ($LASTEXITCODE -ne 0) { throw 'Planning-governance regression test failed.' }

$afterHashes = [ordered]@{}
foreach ($path in $targetPaths) {
    $afterHashes[$path] = (Get-FileHash -LiteralPath (Join-Path $root $path) -Algorithm SHA256).Hash.ToLowerInvariant()
}

& git add -- $targetPaths
& git add -u -- $scriptRel
$staged = @(& git diff --cached --name-only) | Sort-Object
if (($staged -join "`n") -ne ($expectedChanges -join "`n")) {
    throw "Unexpected staged paths before commit: $($staged -join ', ')."
}

& git commit -m 'gov(roadmap): plan CR125 historical release backfill'
if ($LASTEXITCODE -ne 0) { throw 'Failed to create remediation commit.' }
$newHead = (& git rev-parse HEAD).Trim()
if ([int](& git rev-list --count "$head..$newHead") -ne 1) {
    throw 'Remediation must create exactly one commit.'
}
if (-not [string]::IsNullOrWhiteSpace(((& git status --porcelain) -join "`n"))) {
    throw 'Remediation did not finish with a clean working tree.'
}

$reportRoot = Join-Path $env:LOCALAPPDATA 'DDDA/remediation-checks/cr125-planning'
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
[ordered]@{
    schema_version = 1
    change = 'CR125 planning projection'
    repository = 'romanhlavac/ddd-accelerator'
    base_sha = $baseSha
    corrective_transport_sha = $head
    validated_sha = $newHead
    target_release = '0.1.2'
    milestone = 'DDDA 0.1.2'
    issue = 125
    allowed_paths = $targetPaths
    baseline_sha256 = $beforeHashes
    resulting_sha256 = $afterHashes
    technical_status = 'PASS'
    merge = 'NOT_AUTHORIZED'
    release = 'NOT_AUTHORIZED'
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $reportRoot 'result.json') -Encoding utf8

Write-Host "CR125 planning remediation validated at $newHead"
