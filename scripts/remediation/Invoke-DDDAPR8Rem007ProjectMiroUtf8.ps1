#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$RepositoryRoot,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$ExpectedSha,
    [Parameter(Mandatory)][string]$Branch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path -LiteralPath $RepositoryRoot).Path
Set-Location $root

$actualBranch = (git branch --show-current).Trim()
$actualSha = (git rev-parse HEAD).Trim()
$remoteSha = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($actualBranch -ne $Branch) { throw "Unexpected branch '$actualBranch'." }
if ($actualSha -ne $ExpectedSha) { throw "Unexpected HEAD '$actualSha'; expected '$ExpectedSha'." }
if ($remoteSha -ne $ExpectedSha) { throw "Remote branch changed to '$remoteSha'." }
if (-not [string]::IsNullOrWhiteSpace((git status --porcelain | Out-String))) { throw 'Repository is not clean.' }

$initializerPath = Join-Path $root 'scripts\Initialize-DDDAProjectMiro.ps1'
$testPath = Join-Path $root 'tests\powershell\Test-DDDAMiroAutomation.ps1'
$utf8Bom = [Text.UTF8Encoding]::new($true)
$initializerText = [IO.File]::ReadAllText($initializerPath, [Text.UTF8Encoding]::new($false))
$testText = [IO.File]::ReadAllText($testPath, [Text.UTF8Encoding]::new($false))

$oldCliInvocation = '$raw = @(& $script:MiroPython -I -m ddda_miro --project $script:ProjectRoot --platform $script:PlatformRoot @CommandArguments 2>&1)'
$newCliInvocation = '$raw = @(& $script:MiroPython -I -X utf8 -m ddda_miro --project $script:ProjectRoot --platform $script:PlatformRoot @CommandArguments 2>&1)'
$invocationCount = ([regex]::Matches($initializerText, [regex]::Escape($oldCliInvocation))).Count
if ($invocationCount -ne 1) { throw "Expected one isolated Python CLI invocation, found $invocationCount." }
$initializerUpdated = $initializerText.Replace($oldCliInvocation, $newCliInvocation)

$testAnchor = @'
$projectInitializerText = Get-Content (Join-Path $PlatformPath "scripts/Initialize-DDDAProjectMiro.ps1") -Raw -Encoding UTF8
Assert-True -Condition ($projectInitializerText -match '"sync",\s*"--direction",\s*"push"') -Message "Project Miro initializer neprovádí počáteční managed artifact push."
Assert-True -Condition ($projectInitializerText -match 'reports/miro-sync/') -Message "Project Miro initializer nepovoluje auditní sync reporty."
'@

$testReplacement = @'
$projectInitializerText = Get-Content (Join-Path $PlatformPath "scripts/Initialize-DDDAProjectMiro.ps1") -Raw -Encoding UTF8
Assert-True -Condition ($projectInitializerText -match '"sync",\s*"--direction",\s*"push"') -Message "Project Miro initializer neprovádí počáteční managed artifact push."
Assert-True -Condition ($projectInitializerText -match 'reports/miro-sync/') -Message "Project Miro initializer nepovoluje auditní sync reporty."

Assert-True -Condition ($projectInitializerText -match '\$script:MiroPython\s+-I\s+-X\s+utf8\s+-m\s+ddda_miro') -Message "Project Miro initializer nevynucuje UTF-8 v izolovaném Python procesu pomocí -X utf8."

$pythonProbeCommand = Resolve-DDDAPythonCommand
$pythonProbeCode = 'import json, sys; print(json.dumps({"encoding": sys.stdout.encoding, "text": "Povinn\u00fd d\u016fkaz: k\u00f3dov\u00e1n\u00ed v\u00fdstup\u016f"}, ensure_ascii=False))'
$pythonProbeRaw = @(& $pythonProbeCommand -I -X utf8 -c $pythonProbeCode 2>&1)
$pythonProbeExitCode = $LASTEXITCODE
$pythonProbeText = ($pythonProbeRaw | ForEach-Object { $_.ToString() } | Out-String).Trim()
Assert-Equal -Expected 0 -Actual $pythonProbeExitCode -Message "Python UTF-8 stdout probe selhal. Výstup: $pythonProbeText"
$pythonProbe = $pythonProbeText | ConvertFrom-Json
Assert-Equal -Expected "Povinný důkaz: kódování výstupů" -Actual ([string]$pythonProbe.text) -Message "Python UTF-8 stdout probe poškodil český výstup."
Assert-True -Condition (([string]$pythonProbe.encoding).Replace("-", "") -match '^utf8') -Message "Python stdout nepoužívá UTF-8: $($pythonProbe.encoding)"
'@

$testAnchorCount = ([regex]::Matches($testText, [regex]::Escape($testAnchor))).Count
if ($testAnchorCount -ne 1) { throw "Expected one project initializer test anchor, found $testAnchorCount." }
$testUpdated = $testText.Replace($testAnchor, $testReplacement)

[IO.File]::WriteAllText($initializerPath, $initializerUpdated, $utf8Bom)
[IO.File]::WriteAllText($testPath, $testUpdated, $utf8Bom)
Remove-Item -LiteralPath $PSCommandPath -Force

git add -- 'scripts/Initialize-DDDAProjectMiro.ps1' 'tests/powershell/Test-DDDAMiroAutomation.ps1' 'scripts/remediation/Invoke-DDDAPR8Rem007ProjectMiroUtf8.ps1'
$staged = @(git diff --cached --name-status)
$expectedNames = @('scripts/Initialize-DDDAProjectMiro.ps1', 'tests/powershell/Test-DDDAMiroAutomation.ps1', 'scripts/remediation/Invoke-DDDAPR8Rem007ProjectMiroUtf8.ps1')
$stagedNames = @($staged | ForEach-Object { ($_ -split "`t")[-1] })
if ($staged.Count -ne 3 -or @($stagedNames | Where-Object { $_ -notin $expectedNames }).Count -ne 0) {
    throw "Unexpected staged changes: $($staged -join ', ')."
}

$initializerCheck = [IO.File]::ReadAllText($initializerPath, [Text.UTF8Encoding]::new($false))
if ($initializerCheck -notmatch '\$script:MiroPython\s+-I\s+-X\s+utf8\s+-m\s+ddda_miro') { throw 'Isolated Python UTF-8 option is missing.' }

git commit -m 'fix(miro): force UTF-8 for project CLI subprocess'
if ($LASTEXITCODE -ne 0) { throw 'Failed to create REM-007 commit.' }
$newSha = (git rev-parse HEAD).Trim()
if ((git rev-parse HEAD^).Trim() -ne $ExpectedSha) { throw 'REM-007 parent SHA mismatch.' }

foreach ($suite in @('component', 'regression', 'lint')) {
    & (Join-Path $root 'ddda.ps1') test -Suite $suite -NonInteractive
    if ($LASTEXITCODE -ne 0) { throw "$suite suite failed: $LASTEXITCODE" }
}
if (-not [string]::IsNullOrWhiteSpace((git status --porcelain | Out-String))) { throw 'Repository changed during REM-007 validation.' }

$remoteBeforePush = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($remoteBeforePush -ne $ExpectedSha) { throw "Remote branch changed before push: '$remoteBeforePush'." }
git push origin "HEAD:refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'REM-007 push failed.' }
$remoteAfterPush = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($remoteAfterPush -ne $newSha) { throw 'Remote SHA does not match REM-007 commit.' }

Write-Host "REM-PR8-HVA-CC-007 pushed: $newSha"
