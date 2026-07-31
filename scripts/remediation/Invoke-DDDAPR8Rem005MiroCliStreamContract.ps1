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

$smokePath = Join-Path $root 'scripts\Invoke-DDDAMiroSmokeTest.ps1'
$testPath = Join-Path $root 'tests\powershell\Test-DDDAMiroAutomation.ps1'
$utf8Bom = [Text.UTF8Encoding]::new($true)
$smokeText = [IO.File]::ReadAllText($smokePath, [Text.UTF8Encoding]::new($false))
$testText = [IO.File]::ReadAllText($testPath, [Text.UTF8Encoding]::new($false))

$oldFunction = @'
function Invoke-MiroCli {
    param([Parameter(Mandatory = $true)][string[]]$CommandArguments)

    $raw = & $script:MiroPython -m ddda_miro --project $script:ProjectRoot --platform $script:PlatformRoot @CommandArguments 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($raw | Out-String).Trim()

    if ($exitCode -ne 0) {
        throw ("DDDA Miro CLI selhalo: {0}`n{1}" -f ($CommandArguments -join " "), $text)
    }

    try {
        return ($text | ConvertFrom-Json)
    }
    catch {
        throw ("DDDA Miro CLI nevrátilo platný JSON.`nPříkaz: {0}`nVýstup:`n{1}" -f ($CommandArguments -join " "), $text)
    }
}
'@

$newFunction = @'
function Invoke-MiroCli {
    param([Parameter(Mandatory = $true)][string[]]$CommandArguments)

    $stderrPath = Join-Path $env:TEMP ("ddda-miro-cli-{0}.stderr.log" -f [Guid]::NewGuid().ToString("N"))
    try {
        $raw = & $script:MiroPython -m ddda_miro --project $script:ProjectRoot --platform $script:PlatformRoot @CommandArguments 2> $stderrPath
        $exitCode = $LASTEXITCODE
        $text = ($raw | Out-String).Trim()
        $stderrText = if (Test-Path -LiteralPath $stderrPath -PathType Leaf) {
            (Get-Content -LiteralPath $stderrPath -Raw -Encoding UTF8).Trim()
        }
        else {
            ""
        }

        if (-not [string]::IsNullOrWhiteSpace($stderrText)) {
            Write-Host $stderrText
        }

        if ($exitCode -ne 0) {
            $diagnostic = @($text, $stderrText) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) }
            throw ("DDDA Miro CLI selhalo: {0}`n{1}" -f ($CommandArguments -join " "), ($diagnostic -join "`n"))
        }

        try {
            return ($text | ConvertFrom-Json)
        }
        catch {
            throw ("DDDA Miro CLI nevrátilo platný JSON.`nPříkaz: {0}`nStdout:`n{1}`nStderr:`n{2}" -f ($CommandArguments -join " "), $text, $stderrText)
        }
    }
    finally {
        Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue
    }
}
'@

$functionCount = ([regex]::Matches($smokeText, [regex]::Escape($oldFunction))).Count
if ($functionCount -ne 1) { throw "Expected one Invoke-MiroCli block, found $functionCount." }
$smokeUpdated = $smokeText.Replace($oldFunction, $newFunction)

$testAnchor = @'
Assert-True -Condition ($smokeText -notmatch "romanhlavac/ddd-accelerator") -Message "Smoke runner nesmí být svázán s konkrétním origin remote."
Assert-True -Condition ($smokeText -match 'DDDA:\$\{projectId\}:evt-smoke-policy-issued') -Message "Smoke runner nepoužívá bezpečnou interpolaci markeru."
'@
$testReplacement = @'
Assert-True -Condition ($smokeText -notmatch "romanhlavac/ddd-accelerator") -Message "Smoke runner nesmí být svázán s konkrétním origin remote."
Assert-True -Condition ($smokeText -match 'DDDA:\$\{projectId\}:evt-smoke-policy-issued') -Message "Smoke runner nepoužívá bezpečnou interpolaci markeru."
Assert-True -Condition ($smokeText -notmatch '@CommandArguments\s+2>&1') -Message "Miro CLI adapter nesmí slučovat stderr retry telemetry s JSON stdout."
Assert-True -Condition ($smokeText -match '@CommandArguments\s+2>\s+\$stderrPath') -Message "Miro CLI adapter neodděluje stderr do samostatného diagnostického streamu."
Assert-True -Condition ($smokeText -match 'Stdout:.*Stderr:' -or $smokeText -match 'Stdout:`n\{1\}`nStderr:') -Message "Miro CLI parse failure nerozlišuje stdout a stderr."
'@
$anchorCount = ([regex]::Matches($testText, [regex]::Escape($testAnchor))).Count
if ($anchorCount -ne 1) { throw "Expected one Miro smoke test anchor, found $anchorCount." }
$testUpdated = $testText.Replace($testAnchor, $testReplacement)

[IO.File]::WriteAllText($smokePath, $smokeUpdated, $utf8Bom)
[IO.File]::WriteAllText($testPath, $testUpdated, $utf8Bom)
Remove-Item -LiteralPath $PSCommandPath -Force

git add -- 'scripts/Invoke-DDDAMiroSmokeTest.ps1' 'tests/powershell/Test-DDDAMiroAutomation.ps1' 'scripts/remediation/Invoke-DDDAPR8Rem005MiroCliStreamContract.ps1'
$staged = @(git diff --cached --name-status)
$expectedNames = @('scripts/Invoke-DDDAMiroSmokeTest.ps1', 'tests/powershell/Test-DDDAMiroAutomation.ps1', 'scripts/remediation/Invoke-DDDAPR8Rem005MiroCliStreamContract.ps1')
$stagedNames = @($staged | ForEach-Object { ($_ -split "`t")[-1] })
if ($staged.Count -ne 3 -or @($stagedNames | Where-Object { $_ -notin $expectedNames }).Count -ne 0) {
    throw "Unexpected staged changes: $($staged -join ', ')."
}

$smokeCheck = [IO.File]::ReadAllText($smokePath, [Text.UTF8Encoding]::new($false))
if ($smokeCheck -match '@CommandArguments\s+2>&1') { throw 'Merged stderr/stdout invocation remains.' }
if ($smokeCheck -notmatch '@CommandArguments\s+2>\s+\$stderrPath') { throw 'Separated stderr invocation is missing.' }

git commit -m 'fix(miro): preserve JSON stdout when retry telemetry is emitted'
if ($LASTEXITCODE -ne 0) { throw 'Failed to create REM-005 commit.' }
$newSha = (git rev-parse HEAD).Trim()
if ((git rev-parse HEAD^).Trim() -ne $ExpectedSha) { throw 'REM-005 parent SHA mismatch.' }

& (Join-Path $root 'ddda.ps1') test -Suite component -NonInteractive
if ($LASTEXITCODE -ne 0) { throw "Component suite failed: $LASTEXITCODE" }
& (Join-Path $root 'ddda.ps1') test -Suite lint -NonInteractive
if ($LASTEXITCODE -ne 0) { throw "Lint suite failed: $LASTEXITCODE" }
if (-not [string]::IsNullOrWhiteSpace((git status --porcelain | Out-String))) { throw 'Repository changed during REM-005 validation.' }

$remoteBeforePush = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($remoteBeforePush -ne $ExpectedSha) { throw "Remote branch changed before push: '$remoteBeforePush'." }
git push origin "HEAD:refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'REM-005 push failed.' }
$remoteAfterPush = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($remoteAfterPush -ne $newSha) { throw 'Remote SHA does not match REM-005 commit.' }

Write-Host "REM-PR8-HVA-CC-005 pushed: $newSha"
