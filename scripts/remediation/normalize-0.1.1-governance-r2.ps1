[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $RepositoryRoot

$expectedParent = 'fa04c13da29ce72a769ab0d0815631f871b901b1'
$current = (& git rev-parse HEAD).Trim()
$parent = (& git rev-parse HEAD^).Trim()
if ($parent -ne $expectedParent) {
    throw "Corrective staging commit is not based on expected PR #86 head $expectedParent; parent=$parent current=$current"
}
if ((& git status --porcelain)) {
    throw 'Working tree must be clean before corrective remediation.'
}

function Normalize-Lf {
    param([Parameter(Mandatory = $true)][string]$Value)
    return $Value.Replace("`r`n", "`n").Replace("`r", "`n")
}

function Replace-LiteralOnce {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Old,
        [Parameter(Mandatory = $true)][string]$New,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $sourceLf = Normalize-Lf $Source
    $oldLf = Normalize-Lf $Old
    $newLf = Normalize-Lf $New
    $count = ([regex]::Matches($sourceLf, [regex]::Escape($oldLf))).Count
    if ($count -ne 1) {
        throw "$Label preimage occurrence count must be 1; actual=$count."
    }
    return $sourceLf.Replace($oldLf, $newLf)
}

$originalRel = 'scripts/remediation/normalize-0.1.1-governance.ps1'
$originalPath = Join-Path $RepositoryRoot $originalRel
if (-not (Test-Path -LiteralPath $originalPath -PathType Leaf)) {
    throw "Original normalization remediation script is missing: $originalRel"
}

$text = Get-Content -LiteralPath $originalPath -Raw -Encoding UTF8

$oldExpected = '$expectedBase = ''1f66880c30b7bc1814d21200ef6fcc5b08cadfba'''
$newExpected = '$expectedBase = ''fa04c13da29ce72a769ab0d0815631f871b901b1'''
$text = Replace-LiteralOnce $text $oldExpected $newExpected 'Expected-base'

# Patch only the fragile CHANGELOG insertion line. Matching a single semantic
# line avoids CRLF/LF coupling and keeps the surrounding original script intact.
$oldChangelogLine = "    changelog = replace_once(changelog, changed_anchor, changed_anchor + entry, 'changelog changed section')"
$newChangelogBlock = @'
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
'@
$text = Replace-LiteralOnce $text $oldChangelogLine $newChangelogBlock 'Changelog insertion'

# Include the newly created systemic GitHub control-plane Enabler #88 in the
# versioned planning contract without changing the frozen 0.1.1 release scope.
$oldManaged = 'managed = {9, 12, 14, 15, 17, 44, 65, 66, 67, 68, 69, 70, 73, 75, 85}'
$newManaged = 'managed = {9, 12, 14, 15, 17, 44, 65, 66, 67, 68, 69, 70, 73, 75, 85, 88}'
$text = Replace-LiteralOnce $text $oldManaged $newManaged 'Managed-item #88'

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
$text = Replace-LiteralOnce $text $oldGroupTail $newGroupTail 'Enabler #88 metadata insertion'

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
    $text = Replace-LiteralOnce $text ([string]$patch[0]) ([string]$patch[1]) ([string]$patch[2])
}

$oldTestLine = '    assert meta[85]["Status"] == "Backlog"'
$newTestBlock = @'
    assert meta[85]["Status"] == "Backlog"
    assert meta[88]["Item Type"] == "Enabler"
    assert meta[88]["Work Package"] == "Other"
    assert meta[88]["Target Release"] == "TBD"
    assert meta[88]["Status"] == "Backlog"
'@
$text = Replace-LiteralOnce $text $oldTestLine $newTestBlock 'Regression-test insertion for #88'

# The trusted broker establishes Python but does not install test dependencies.
# Keep this temporary PR86-scoped compatibility shim until #88 hardens dependency
# parity in the broker itself. Pin to the same pytest major range as standard CI.
& python -m pip install --disable-pip-version-check 'pytest>=8,<9'
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to install pytest required by governance regression tests.'
}

$oldCleanup = @'
$scriptPath = Join-Path $RepositoryRoot 'scripts/remediation/normalize-0.1.1-governance.ps1'
Remove-Item -LiteralPath $scriptPath -Force
'@
$newCleanup = @'
$scriptPaths = @(
    (Join-Path $RepositoryRoot 'scripts/remediation/normalize-0.1.1-governance.ps1')
    (Join-Path $RepositoryRoot 'scripts/remediation/normalize-0.1.1-governance-r2.ps1')
    (Join-Path $RepositoryRoot 'noop')
)
foreach ($path in $scriptPaths) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        Remove-Item -LiteralPath $path -Force
    }
}
'@
$text = Replace-LiteralOnce $text $oldCleanup $newCleanup 'Self-removal'

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
