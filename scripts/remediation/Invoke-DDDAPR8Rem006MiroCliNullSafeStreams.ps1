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

$oldStreamBlock = @'
        $exitCode = $LASTEXITCODE
        $text = ($raw | Out-String).Trim()
        $stderrText = if (Test-Path -LiteralPath $stderrPath -PathType Leaf) {
            (Get-Content -LiteralPath $stderrPath -Raw -Encoding UTF8).Trim()
        }
        else {
            ""
        }
'@

$newStreamBlock = @'
        $exitCode = $LASTEXITCODE
        $text = ([string]($raw | Out-String)).Trim()
        $stderrRaw = if (Test-Path -LiteralPath $stderrPath -PathType Leaf) {
            Get-Content -LiteralPath $stderrPath -Raw -Encoding UTF8
        }
        else {
            $null
        }
        $stderrText = ([string]$stderrRaw).Trim()
'@

$streamCount = ([regex]::Matches($smokeText, [regex]::Escape($oldStreamBlock))).Count
if ($streamCount -ne 1) { throw "Expected one vulnerable stream block, found $streamCount." }
$smokeUpdated = $smokeText.Replace($oldStreamBlock, $newStreamBlock)

$testAnchor = @'
Assert-True -Condition ($smokeText -notmatch '@CommandArguments\s+2>&1') -Message "Miro CLI adapter nesmí slučovat stderr retry telemetry s JSON stdout."
Assert-True -Condition ($smokeText -match '@CommandArguments\s+2>\s+\$stderrPath') -Message "Miro CLI adapter neodděluje stderr do samostatného diagnostického streamu."
Assert-True -Condition ($smokeText -match 'Stdout:.*Stderr:' -or $smokeText -match 'Stdout:`n\{1\}`nStderr:') -Message "Miro CLI parse failure nerozlišuje stdout a stderr."
'@

$testReplacement = @'
Assert-True -Condition ($smokeText -notmatch '@CommandArguments\s+2>&1') -Message "Miro CLI adapter nesmí slučovat stderr retry telemetry s JSON stdout."
Assert-True -Condition ($smokeText -match '@CommandArguments\s+2>\s+\$stderrPath') -Message "Miro CLI adapter neodděluje stderr do samostatného diagnostického streamu."
Assert-True -Condition ($smokeText -match 'Stdout:.*Stderr:' -or $smokeText -match 'Stdout:`n\{1\}`nStderr:') -Message "Miro CLI parse failure nerozlišuje stdout a stderr."
Assert-True -Condition ($smokeText -match '\$stderrRaw\s*=\s*if\s*\(Test-Path') -Message "Miro CLI adapter nemá explicitní null-safe mezivýsledek stderr."
Assert-True -Condition ($smokeText -match '\$stderrText\s*=\s*\(\[string\]\$stderrRaw\)\.Trim\(\)') -Message "Miro CLI adapter nenormalizuje prázdný stderr přes string cast před Trim."
Assert-True -Condition ($smokeText -notmatch '\(Get-Content[^\r\n]+\)\.Trim\(\)') -Message "Miro CLI adapter stále volá Trim přímo nad potenciálně null Get-Content výsledkem."

$emptyStderrPath = Join-Path $env:TEMP ("ddda-empty-stderr-" + [Guid]::NewGuid().ToString("N") + ".log")
try {
    [IO.File]::WriteAllBytes($emptyStderrPath, [byte[]]@())
    $emptyStderrRaw = Get-Content -LiteralPath $emptyStderrPath -Raw -Encoding UTF8
    $emptyStderrText = ([string]$emptyStderrRaw).Trim()
    Assert-Equal -Expected "" -Actual $emptyStderrText -Message "Prázdný stderr musí být bezpečně normalizován na prázdný řetězec."
}
finally {
    Remove-Item -LiteralPath $emptyStderrPath -Force -ErrorAction SilentlyContinue
}
'@

$anchorCount = ([regex]::Matches($testText, [regex]::Escape($testAnchor))).Count
if ($anchorCount -ne 1) { throw "Expected one REM-005 test anchor, found $anchorCount." }
$testUpdated = $testText.Replace($testAnchor, $testReplacement)

[IO.File]::WriteAllText($smokePath, $smokeUpdated, $utf8Bom)
[IO.File]::WriteAllText($testPath, $testUpdated, $utf8Bom)
Remove-Item -LiteralPath $PSCommandPath -Force

git add -- 'scripts/Invoke-DDDAMiroSmokeTest.ps1' 'tests/powershell/Test-DDDAMiroAutomation.ps1' 'scripts/remediation/Invoke-DDDAPR8Rem006MiroCliNullSafeStreams.ps1'
$staged = @(git diff --cached --name-status)
$expectedNames = @('scripts/Invoke-DDDAMiroSmokeTest.ps1', 'tests/powershell/Test-DDDAMiroAutomation.ps1', 'scripts/remediation/Invoke-DDDAPR8Rem006MiroCliNullSafeStreams.ps1')
$stagedNames = @($staged | ForEach-Object { ($_ -split "`t")[-1] })
if ($staged.Count -ne 3 -or @($stagedNames | Where-Object { $_ -notin $expectedNames }).Count -ne 0) {
    throw "Unexpected staged changes: $($staged -join ', ')."
}

$smokeCheck = [IO.File]::ReadAllText($smokePath, [Text.UTF8Encoding]::new($false))
if ($smokeCheck -notmatch '\$stderrText\s*=\s*\(\[string\]\$stderrRaw\)\.Trim\(\)') { throw 'Null-safe stderr normalization is missing.' }
if ($smokeCheck -match '\(Get-Content[^\r\n]+\)\.Trim\(\)') { throw 'Unsafe Get-Content.Trim remains.' }

git commit -m 'fix(miro): handle empty CLI diagnostic streams safely'
if ($LASTEXITCODE -ne 0) { throw 'Failed to create REM-006 commit.' }
$newSha = (git rev-parse HEAD).Trim()
if ((git rev-parse HEAD^).Trim() -ne $ExpectedSha) { throw 'REM-006 parent SHA mismatch.' }

& (Join-Path $root 'ddda.ps1') test -Suite component -NonInteractive
if ($LASTEXITCODE -ne 0) { throw "Component suite failed: $LASTEXITCODE" }
& (Join-Path $root 'ddda.ps1') test -Suite lint -NonInteractive
if ($LASTEXITCODE -ne 0) { throw "Lint suite failed: $LASTEXITCODE" }
if (-not [string]::IsNullOrWhiteSpace((git status --porcelain | Out-String))) { throw 'Repository changed during REM-006 validation.' }

$remoteBeforePush = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($remoteBeforePush -ne $ExpectedSha) { throw "Remote branch changed before push: '$remoteBeforePush'." }
git push origin "HEAD:refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'REM-006 push failed.' }
$remoteAfterPush = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($remoteAfterPush -ne $newSha) { throw 'Remote SHA does not match REM-006 commit.' }

Write-Host "REM-PR8-HVA-CC-006 pushed: $newSha"
