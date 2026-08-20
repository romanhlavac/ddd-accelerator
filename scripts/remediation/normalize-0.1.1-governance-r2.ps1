[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $RepositoryRoot

$expectedParent = '237a23047775c0157a8365990f3f73e231ebac2c'
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
$newExpected = '$expectedBase = ''237a23047775c0157a8365990f3f73e231ebac2c'''
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
entry = '- GitHub-native backlog governance nyní považuje Issue/PR mutation, Project planning/delivery projection a release Milestone projection za jednu fail-closed transakci; DDDA 0.1.0/0.1.1 scope je versioned a canonical reconciler opravuje Project/Milestone drift před Ready/merge/release doporučením.\n'
if entry not in changelog:
    changelog = replace_once(changelog, changed_anchor, changed_anchor + entry, 'changelog changed section')
CHANGELOG.write_text(changelog, encoding='utf-8')
'@
$newChangelog = @'
changelog = CHANGELOG.read_text(encoding='utf-8-sig')
changed_anchor = '### Changed\n\n'
entry = '- GitHub-native backlog governance nyní považuje Issue/PR mutation, Project planning/delivery projection a release Milestone projection za jednu fail-closed transakci; DDDA 0.1.0/0.1.1 scope je versioned a canonical reconciler opravuje Project/Milestone drift před Ready/merge/release doporučením.\n'
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

Set-Content -LiteralPath $originalPath -Value $text -Encoding UTF8 -NoNewline

& $originalPath -RepositoryRoot $RepositoryRoot -NoPush
if ($LASTEXITCODE -ne 0) {
    throw "Corrected normalization remediation failed with exit code $LASTEXITCODE."
}
