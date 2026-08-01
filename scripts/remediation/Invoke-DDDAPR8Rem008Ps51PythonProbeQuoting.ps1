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

$testPath = Join-Path $root 'tests\powershell\Test-DDDAMiroAutomation.ps1'
$utf8Bom = [Text.UTF8Encoding]::new($true)
$testText = [IO.File]::ReadAllText($testPath, [Text.UTF8Encoding]::new($false))

$oldProbeCode = '$pythonProbeCode = ''import json, sys; print(json.dumps({"encoding": sys.stdout.encoding, "text": "Povinn\u00fd d\u016fkaz: k\u00f3dov\u00e1n\u00ed v\u00fdstup\u016f"}, ensure_ascii=False))'''
$newProbeCode = '$pythonProbeCode = "import json, sys; print(json.dumps(dict(encoding=sys.stdout.encoding, text=''Povinn\u00fd d\u016fkaz: k\u00f3dov\u00e1n\u00ed v\u00fdstup\u016f''), ensure_ascii=False))"'
$probeCount = ([regex]::Matches($testText, [regex]::Escape($oldProbeCode))).Count
if ($probeCount -ne 1) { throw "Expected one PowerShell-5.1-unsafe Python probe, found $probeCount." }
$testUpdated = $testText.Replace($oldProbeCode, $newProbeCode)

[IO.File]::WriteAllText($testPath, $testUpdated, $utf8Bom)
Remove-Item -LiteralPath $PSCommandPath -Force

git add -- 'tests/powershell/Test-DDDAMiroAutomation.ps1' 'scripts/remediation/Invoke-DDDAPR8Rem008Ps51PythonProbeQuoting.ps1'
$staged = @(git diff --cached --name-status)
$expectedNames = @('tests/powershell/Test-DDDAMiroAutomation.ps1', 'scripts/remediation/Invoke-DDDAPR8Rem008Ps51PythonProbeQuoting.ps1')
$stagedNames = @($staged | ForEach-Object { ($_ -split "`t")[-1] })
if ($staged.Count -ne 2 -or @($stagedNames | Where-Object { $_ -notin $expectedNames }).Count -ne 0) {
    throw "Unexpected staged changes: $($staged -join ', ')."
}

$testCheck = [IO.File]::ReadAllText($testPath, [Text.UTF8Encoding]::new($false))
if ($testCheck -notmatch 'dict\(encoding=sys\.stdout\.encoding, text=''Povinn\\u00fd d\\u016fkaz') {
    throw 'PowerShell-5.1-safe Python probe quoting is missing.'
}

git commit -m 'fix(test): preserve Python probe quotes in PowerShell 5.1'
if ($LASTEXITCODE -ne 0) { throw 'Failed to create REM-008 commit.' }
$newSha = (git rev-parse HEAD).Trim()
if ((git rev-parse HEAD^).Trim() -ne $ExpectedSha) { throw 'REM-008 parent SHA mismatch.' }

foreach ($suite in @('component', 'regression', 'lint')) {
    & (Join-Path $root 'ddda.ps1') test -Suite $suite -NonInteractive
    if ($LASTEXITCODE -ne 0) { throw "$suite suite failed: $LASTEXITCODE" }
}

$windowsPowerShell = (Get-Command powershell.exe -ErrorAction Stop).Source
& $windowsPowerShell -NoProfile -ExecutionPolicy Bypass -File $testPath -PlatformPath $root
if ($LASTEXITCODE -ne 0) { throw "Windows PowerShell 5.1 Miro automation test failed: $LASTEXITCODE" }

if (-not [string]::IsNullOrWhiteSpace((git status --porcelain | Out-String))) { throw 'Repository changed during REM-008 validation.' }
$remoteBeforePush = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($remoteBeforePush -ne $ExpectedSha) { throw "Remote branch changed before push: '$remoteBeforePush'." }
git push origin "HEAD:refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'REM-008 push failed.' }
$remoteAfterPush = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($remoteAfterPush -ne $newSha) { throw 'Remote SHA does not match REM-008 commit.' }

Write-Host "REM-PR8-HVA-CC-008 pushed: $newSha"
