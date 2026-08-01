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

$oldEnvironmentBlock = @'
$originalTokenExists = Test-Path Env:\MIRO_ACCESS_TOKEN
$originalToken = $null
if ($originalTokenExists) {
    $originalToken = $env:MIRO_ACCESS_TOKEN
}

$script:PlatformRoot = (Resolve-Path $PlatformPath).Path
'@

$newEnvironmentBlock = @'
$originalTokenExists = Test-Path Env:\MIRO_ACCESS_TOKEN
$originalToken = $null
if ($originalTokenExists) {
    $originalToken = $env:MIRO_ACCESS_TOKEN
}

$originalPythonUtf8Exists = Test-Path Env:\PYTHONUTF8
$originalPythonUtf8 = $null
if ($originalPythonUtf8Exists) {
    $originalPythonUtf8 = $env:PYTHONUTF8
}

$originalPythonIoEncodingExists = Test-Path Env:\PYTHONIOENCODING
$originalPythonIoEncoding = $null
if ($originalPythonIoEncodingExists) {
    $originalPythonIoEncoding = $env:PYTHONIOENCODING
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$script:PlatformRoot = (Resolve-Path $PlatformPath).Path
'@

$environmentCount = ([regex]::Matches($initializerText, [regex]::Escape($oldEnvironmentBlock))).Count
if ($environmentCount -ne 1) { throw "Expected one initializer environment anchor, found $environmentCount." }
$initializerUpdated = $initializerText.Replace($oldEnvironmentBlock, $newEnvironmentBlock)

$oldFinallyBlock = @'
finally {
    if ($originalTokenExists) {
        $env:MIRO_ACCESS_TOKEN = $originalToken
    }
    else {
        Remove-Item Env:\MIRO_ACCESS_TOKEN -ErrorAction SilentlyContinue
    }
}
'@

$newFinallyBlock = @'
finally {
    if ($originalTokenExists) {
        $env:MIRO_ACCESS_TOKEN = $originalToken
    }
    else {
        Remove-Item Env:\MIRO_ACCESS_TOKEN -ErrorAction SilentlyContinue
    }

    if ($originalPythonUtf8Exists) {
        $env:PYTHONUTF8 = $originalPythonUtf8
    }
    else {
        Remove-Item Env:\PYTHONUTF8 -ErrorAction SilentlyContinue
    }

    if ($originalPythonIoEncodingExists) {
        $env:PYTHONIOENCODING = $originalPythonIoEncoding
    }
    else {
        Remove-Item Env:\PYTHONIOENCODING -ErrorAction SilentlyContinue
    }
}
'@

$finallyCount = ([regex]::Matches($initializerUpdated, [regex]::Escape($oldFinallyBlock))).Count
if ($finallyCount -ne 1) { throw "Expected one initializer cleanup anchor, found $finallyCount." }
$initializerUpdated = $initializerUpdated.Replace($oldFinallyBlock, $newFinallyBlock)

$testAnchor = @'
$projectInitializerText = Get-Content (Join-Path $PlatformPath "scripts/Initialize-DDDAProjectMiro.ps1") -Raw -Encoding UTF8
Assert-True -Condition ($projectInitializerText -match '"sync",\s*"--direction",\s*"push"') -Message "Project Miro initializer neprovádí počáteční managed artifact push."
Assert-True -Condition ($projectInitializerText -match 'reports/miro-sync/') -Message "Project Miro initializer nepovoluje auditní sync reporty."
'@

$testReplacement = @'
$projectInitializerText = Get-Content (Join-Path $PlatformPath "scripts/Initialize-DDDAProjectMiro.ps1") -Raw -Encoding UTF8
Assert-True -Condition ($projectInitializerText -match '"sync",\s*"--direction",\s*"push"') -Message "Project Miro initializer neprovádí počáteční managed artifact push."
Assert-True -Condition ($projectInitializerText -match 'reports/miro-sync/') -Message "Project Miro initializer nepovoluje auditní sync reporty."

$pythonAdapterIndex = $projectInitializerText.IndexOf('& $script:MiroPython', [StringComparison]::Ordinal)
$pythonInvocationIndex = $projectInitializerText.IndexOf('$doctor = Invoke-ProjectMiroCli', [StringComparison]::Ordinal)
$pythonUtf8SetIndex = $projectInitializerText.IndexOf('$env:PYTHONUTF8 = "1"', [StringComparison]::Ordinal)
$pythonIoEncodingSetIndex = $projectInitializerText.IndexOf('$env:PYTHONIOENCODING = "utf-8"', [StringComparison]::Ordinal)
$pythonUtf8CleanupIndex = $projectInitializerText.IndexOf('Remove-Item Env:\PYTHONUTF8', [StringComparison]::Ordinal)
$pythonIoEncodingCleanupIndex = $projectInitializerText.IndexOf('Remove-Item Env:\PYTHONIOENCODING', [StringComparison]::Ordinal)
Assert-True -Condition ($pythonAdapterIndex -ge 0) -Message "Project Miro initializer nemá dohledatelný Python CLI adapter."
Assert-True -Condition ($pythonInvocationIndex -ge 0) -Message "Project Miro initializer nemá dohledatelné první CLI volání."
Assert-True -Condition ($pythonUtf8SetIndex -ge 0 -and $pythonUtf8SetIndex -lt $pythonInvocationIndex) -Message "Project Miro initializer nenastavuje PYTHONUTF8=1 před CLI voláním."
Assert-True -Condition ($pythonIoEncodingSetIndex -ge 0 -and $pythonIoEncodingSetIndex -lt $pythonInvocationIndex) -Message "Project Miro initializer nenastavuje PYTHONIOENCODING=utf-8 před CLI voláním."
Assert-True -Condition ($pythonUtf8CleanupIndex -gt $pythonInvocationIndex) -Message "Project Miro initializer neobnovuje nebo neodstraňuje PYTHONUTF8 po CLI volání."
Assert-True -Condition ($pythonIoEncodingCleanupIndex -gt $pythonInvocationIndex) -Message "Project Miro initializer neobnovuje nebo neodstraňuje PYTHONIOENCODING po CLI volání."
Assert-True -Condition ($projectInitializerText -match '(?s)if\s*\(\$originalPythonUtf8Exists\).*?\$env:PYTHONUTF8\s*=\s*\$originalPythonUtf8') -Message "Project Miro initializer neumí obnovit původní PYTHONUTF8."
Assert-True -Condition ($projectInitializerText -match '(?s)if\s*\(\$originalPythonIoEncodingExists\).*?\$env:PYTHONIOENCODING\s*=\s*\$originalPythonIoEncoding') -Message "Project Miro initializer neumí obnovit původní PYTHONIOENCODING."

$pythonProbeCommand = Resolve-DDDAPythonCommand
$originalProbePythonUtf8Exists = Test-Path Env:\PYTHONUTF8
$originalProbePythonUtf8 = if ($originalProbePythonUtf8Exists) { $env:PYTHONUTF8 } else { $null }
$originalProbePythonIoEncodingExists = Test-Path Env:\PYTHONIOENCODING
$originalProbePythonIoEncoding = if ($originalProbePythonIoEncodingExists) { $env:PYTHONIOENCODING } else { $null }
try {
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $pythonProbeCode = 'import json, sys; print(json.dumps({"encoding": sys.stdout.encoding, "text": "Povinn\u00fd d\u016fkaz: k\u00f3dov\u00e1n\u00ed v\u00fdstup\u016f"}, ensure_ascii=False))'
    $pythonProbeRaw = @(& $pythonProbeCommand -I -c $pythonProbeCode 2>&1)
    $pythonProbeExitCode = $LASTEXITCODE
}
finally {
    if ($originalProbePythonUtf8Exists) {
        $env:PYTHONUTF8 = $originalProbePythonUtf8
    }
    else {
        Remove-Item Env:\PYTHONUTF8 -ErrorAction SilentlyContinue
    }
    if ($originalProbePythonIoEncodingExists) {
        $env:PYTHONIOENCODING = $originalProbePythonIoEncoding
    }
    else {
        Remove-Item Env:\PYTHONIOENCODING -ErrorAction SilentlyContinue
    }
}
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
if ($initializerCheck -notmatch '\$env:PYTHONUTF8\s*=\s*"1"') { throw 'PYTHONUTF8 contract is missing.' }
if ($initializerCheck -notmatch '\$env:PYTHONIOENCODING\s*=\s*"utf-8"') { throw 'PYTHONIOENCODING contract is missing.' }
if ($initializerCheck -notmatch 'Remove-Item Env:\\PYTHONUTF8') { throw 'PYTHONUTF8 cleanup is missing.' }
if ($initializerCheck -notmatch 'Remove-Item Env:\\PYTHONIOENCODING') { throw 'PYTHONIOENCODING cleanup is missing.' }

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
