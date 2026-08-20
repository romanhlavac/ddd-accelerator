[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $RepositoryRoot

$expectedParent = '956c10ba6ca72521b4fe6132f5f387ea0ffdff0f'
$current = (& git rev-parse HEAD).Trim()
$parent = (& git rev-parse HEAD^).Trim()
if ($parent -ne $expectedParent) {
    throw "Corrective staging commit is not based on expected PR #86 head $expectedParent; parent=$parent current=$current"
}
if ((& git status --porcelain)) {
    throw 'Working tree must be clean before corrective remediation.'
}

$originalRel = 'scripts/remediation/normalize-0.1.1-governance.ps1'
$originalPath = Join-Path $RepositoryRoot $originalRel
if (-not (Test-Path -LiteralPath $originalPath -PathType Leaf)) {
    throw "Original normalization remediation script is missing: $originalRel"
}

$text = Get-Content -LiteralPath $originalPath -Raw -Encoding UTF8

$oldExpected = '$expectedBase = ''1f66880c30b7bc1814d21200ef6fcc5b08cadfba'''
$newExpected = '$expectedBase = ''956c10ba6ca72521b4fe6132f5f387ea0ffdff0f'''
if (($text.Split($oldExpected).Count - 1) -ne 1) {
    throw 'Expected-base preimage is not unique in original remediation script.'
}
$text = $text.Replace($oldExpected, $newExpected)

$oldChangelog = @'
changelog = CHANGELOG.read_text(encoding='utf-8-sig')
changed_anchor = '### Changed\n\n'
entry = '- GitHub-native backlog governance nyní považžuje Issue/PR mutation, Project planning/delivery projection a release Milestone projection za jednu fail-closed transakci; DDDA 0.1.0/0.1.1 scope je versioned a canonical reconciler opravuje Project/Milestone drift před Ready/merge/release doporučením.\n'
if entry not in changelog:
    changelog = replace_once(changelog, changed_anchor, changed_anchor + entry, 'changelog changed section')
CHANGELOG.write_text(changelog, encoding='utf-8')
'@
$oldChangelogFallback = @'
changelog = CHANGELOG.read_text(encoding='utf-8-sig')
changed_anchor = '### Changed\n\n'
entry = '- GitHub-native backlog governance nyní považžuje Issue/PR mutation, Project planning/delivery projection a release Milestone projection za jednu fail-closed transakci; DDDA 0.1.0/0.1.1 scope je versioned a canonical reconciler opravuje Project/Milestone drift před Ready/merge/release doporučením.\n'
if entry not in changelog:
    changelog = replace_once(changelog, changed_anchor, changed_anchor + entry, 'changelog changed section')
CHANGELOG.write_text(changelog, encoding='utf-8')
'@
$newChangelog = @'
changelog = CHANGELOG.read_text(encoding='utf-8-sig')
changed_anchor = '### Changed\n\n'
entry = '- GitHub-native backlog governance nyní považžuje Issue/PR mutation, Project planning/delivery projection a release Milestone projection za jednu fail-closed transakci; DDDA 0.1.0/0.1.1 scope je versioned a canonical reconciler opravuje Project/Milestone drift před Ready/merge/release doporučením.\n'
if entry not in changelog:
    unreleased_marker = '## [Unreleased]\n'
    start = changelog.find(unreleased_marker)
    if start < 0:
        raise RuntimeError('changelog: missing Unreleased section')
    next_release = changelog.find('\n## [', start + len(unreleased_marker))
    if next_release < 0:
        next_release = len(changelog)
    unreleased = changelog[start:next_release]
    if unreleased.count(changed_anchor) != 1:
        raise RuntimeError(f'changelog Unreleased Changed section: expected one preimage, found {unreleased.count(changed_anchor)}')
    unreleased = unreleased.replace(changed_anchor, changed_anchor + entry, 1)
    changelog = changelog[:start] + unreleased + changelog[next_release:]
CHANGELOG.write_text(changelog, encoding='utf-8')
'@
if (($text.Split($oldChangelogFallback).Count - 1) -eq 1) {
    $text = $text.Replace($oldChangelogFallback, $newChangelog)
}
elseif (($text.Split($oldChangelog).Count - 1) -eq 1) {
    $text = $text.Replace($oldChangelog, $newChangelog)
}
else {
    throw 'Changelog-fix preimage is not unique in original remediation script.'
}

# Include the newly created systemic GitHub control-plane Enabler #88 in the
# versioned planning contract without changing the frozen 0.1.1 release scope.
$oldManaged = 'managed = {9, 12, 14, 15, 17, 44, 65, 66, 67, 68, 69, 70, 73, 75, 85}'
$newManaged = 'managed = {9, 12, 14, 15, 17, 44, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88}'
if (($text.Split($oldManaged).Count - 1) -ne 1) {
    throw 'Managed-item preimage for #88 is not unique in original remediation script.'
}
$text = $text.Replace($oldManaged, $newManaged)

$oldGroupTail = @'
    {'kind':'issue','numbers':[75],'metadata':{
        'Status':'In progress','Priority':'P0','Work Package':'Other','Item Type':'Enabler','Target Release':'0.1.1','Blocked':'No','Human Review':'Not required',
        'Outcome summary':'Coordinate approved DDDA 0.1.1 stabilization scope, governance normalization, release prerequisites and release-candidate gates.'
    }},
])
'@
$newGroupTail = @'
    {'kind':'issue','numbers':[75],'metadata':{
        'Status':'In progress','Priority':'P0','Work Package':'Other','Item Type':'Enabler','Target Release':'0.1.1','Blocked':'No','Human Review':'Not required',
        'Outcome summary':'Coordinate approved DDDA 0.1.1 stabilization scope, governance normalization, release prerequisites and release-candidate gates.'
    }},
    {'kind':'issue','numbers':[88],'metadata':{
        'Status':'Backlog','Work Package':'Other','Item Type':'Enabler','Target Release':'TBD','Blocked':'No','Human Review':'Pending'
    }},
])
'@
if (($text.Split($oldGroupTail).Count - 1) -ne 1) {
    throw 'Enabler #88 metadata insertion preimage is not unique.'
}
$text = $text.Replace($oldGroupTail, $newGroupTail)

$planningPatches = @(
    @(
        'unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85]',
        'unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88]',
        'Other planning mapping for #88'
    ),
    @(
        'excluded_future_items: [9, 12, 45, 53, 54, 55, 56, 57, 65, 66, 67, 68, 69, 70, 73, 75, 85]',
        'excluded_future_items: [9, 12, 45, 53, 54, 55, 56, 57, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88]',
        '0.1.0 excluded-future contract for #88'
    ),
    @(
        'explicitly_deferred_items: [65, 66, 69, 73, 85]',
        'explicitly_deferred_items: [65, 66, 69, 73, 85, 88]',
        '0.1.1 deferred-items contract for #88'
    ),
    @(
        'Deferred/outside 0.1.1: #65, #66, #69, #73, #85 and PR #43',
        'Deferred/outside 0.1.1: #65, #66, #69, #73, #85, #88 and PR #43',
        'WP-08 roadmap deferral for #88'
    )
)
foreach ($patch in $planningPatches) {
    $old = [string]$patch[0]
    $new = [string]$patch[1]
    $label = [string]$patch[2]
    if (($text.Split($old).Count - 1) -ne 1) {
        throw "$label preimage is not unique."
    }
    $text = $text.Replace($old, $new)
}

$oldTest = @'
    assert meta[85]["Status"] == "Backlog"
'@
$newTest = @'
    assert meta[85]["Status"] == "Backlog"
    assert meta[88]["Item Type"] == "Enabler"
    assert meta[88]["Work Package"] == "Other"
    assert meta[88]["Target Release"] == "TBD"
    assert meta[88]["Status"] == "Backlog"
'@
if (($text.Split($oldTest).Count - 1) -ne 1) {
    throw 'Regression-test insertion preimage for #88 is not unique.'
}
$text = $text.Replace($oldTest, $newTest)

$oldCleanup = @'
$scriptPath = Join-Path $RepositoryRoot 'scripts/remediation/normalize-0.1.1-governance.ps1'
Remove-Item -LiteralPath $scriptPath -Force
'@
$newCleanup = @'
$scriptPaths = @(
    (Join-Path $RepositoryRoot 'scripts/remediation/normalize-0.1.1-governance.ps1')
    (Join-Path $RepositoryRoot 'scripts/remediation/normalize-0.1.1-governance-r2.ps1')
)
foreach ($path in $scriptPaths) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        Remove-Item -LiteralPath $path -Force
    }
}
'@
if (($text.Split($oldCleanup).Count - 1) -ne 1) {
    throw 'Self-removal preimage is not unique in original remediation script.'
}
$text = $text.Replace($oldCleanup, $newCleanup)

$tempPath = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-pr86-normalize-" + [guid]::NewGuid().ToString('N') + ".ps1")
try {
    # Execute the patched implementation from outside the repository so the
    # original remediation clean-tree guard remains meaningful.
    [System.IO.File]::WriteAllText($tempPath, $text, [System.Text.UTF8Encoding]::new($true))
    & $tempPath -RepositoryRoot $RepositoryRoot -NoPush
    if ($LASTEXITCODE -ne 0) {
        throw "Corrected normalization remediation failed with exit code $LASTEXITCODE."
    }
}
finally {
    if (Test-Path -LiteralPath $tempPath -PathType Leaf) {
        Remove-Item -LiteralPath $tempPath -Force
    }
}
