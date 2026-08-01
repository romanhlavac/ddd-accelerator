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

$acceptancePath = Join-Path $root 'scripts\Test-DDDAAcceptance.ps1'
$testPath = Join-Path $root 'tests\powershell\Test-DDDAMiroAutomation.ps1'
$utf8Bom = [Text.UTF8Encoding]::new($true)
$acceptanceText = [IO.File]::ReadAllText($acceptancePath, [Text.UTF8Encoding]::new($false))
$testText = [IO.File]::ReadAllText($testPath, [Text.UTF8Encoding]::new($false))

$oldHeadingCount = '$headingCount = @($visibleRemoteTexts | Where-Object { $_ -match [regex]::Escape($heading) }).Count'
$newHeadingCount = '$headingCount = @($visibleRemoteTexts | Where-Object { $_ -cmatch [regex]::Escape($heading) }).Count'
$headingCount = ([regex]::Matches($acceptanceText, [regex]::Escape($oldHeadingCount))).Count
if ($headingCount -ne 1) { throw "Expected one case-insensitive canonical heading counter, found $headingCount." }
$acceptanceUpdated = $acceptanceText.Replace($oldHeadingCount, $newHeadingCount)

$testAnchor = 'Assert-True -Condition $acceptanceCommand.Parameters.ContainsKey("MiroTeamId") -Message "Acceptance runner neumí explicitně vybrat standardní Miro team."'
$testReplacement = @'
Assert-True -Condition $acceptanceCommand.Parameters.ContainsKey("MiroTeamId") -Message "Acceptance runner neumí explicitně vybrat standardní Miro team."
Assert-True -Condition ($acceptanceText -match '\$_\s+-cmatch\s+\[regex\]::Escape\(\$heading\)') -Message "Acceptance runner nepočítá kanonické guide nadpisy case-sensitive."

$canonicalHeadingProbe = @()
$canonicalHeadingProbe += @(1..15 | ForEach-Object { "<strong>OTEVŘENÉ OTÁZKY</strong>" })
$canonicalHeadingProbe += @(1..15 | ForEach-Object { "Rozlišuj fakta, hypotézy, rozhodnutí a otevřené otázky." })
$caseInsensitiveHeadingCount = @($canonicalHeadingProbe | Where-Object { $_ -match [regex]::Escape("OTEVŘENÉ OTÁZKY") }).Count
$caseSensitiveHeadingCount = @($canonicalHeadingProbe | Where-Object { $_ -cmatch [regex]::Escape("OTEVŘENÉ OTÁZKY") }).Count
Assert-True -Condition ($caseInsensitiveHeadingCount -gt 15) -Message "Regresní fixture neprokazuje původní case-insensitive přepočítání workspace textů."
Assert-Equal -Expected 15 -Actual $caseSensitiveHeadingCount -Message "Case-sensitive canonical heading count musí ignorovat lowercase workspace texty."
'@

$testAnchorCount = ([regex]::Matches($testText, [regex]::Escape($testAnchor))).Count
if ($testAnchorCount -ne 1) { throw "Expected one acceptance test anchor, found $testAnchorCount." }
$testUpdated = $testText.Replace($testAnchor, $testReplacement)

[IO.File]::WriteAllText($acceptancePath, $acceptanceUpdated, $utf8Bom)
[IO.File]::WriteAllText($testPath, $testUpdated, $utf8Bom)
Remove-Item -LiteralPath $PSCommandPath -Force

git add -- 'scripts/Test-DDDAAcceptance.ps1' 'tests/powershell/Test-DDDAMiroAutomation.ps1' 'scripts/remediation/Invoke-DDDAPR8Rem009CanonicalHeadingCase.ps1'
$staged = @(git diff --cached --name-status)
$expectedNames = @('scripts/Test-DDDAAcceptance.ps1', 'tests/powershell/Test-DDDAMiroAutomation.ps1', 'scripts/remediation/Invoke-DDDAPR8Rem009CanonicalHeadingCase.ps1')
$stagedNames = @($staged | ForEach-Object { ($_ -split "`t")[-1] })
if ($staged.Count -ne 3 -or @($stagedNames | Where-Object { $_ -notin $expectedNames }).Count -ne 0) {
    throw "Unexpected staged changes: $($staged -join ', ')."
}

$acceptanceCheck = [IO.File]::ReadAllText($acceptancePath, [Text.UTF8Encoding]::new($false))
if ($acceptanceCheck -notmatch '\$_\s+-cmatch\s+\[regex\]::Escape\(\$heading\)') {
    throw 'Case-sensitive canonical heading acceptance contract is missing.'
}

git commit -m 'fix(acceptance): count canonical headings case-sensitively'
if ($LASTEXITCODE -ne 0) { throw 'Failed to create REM-009 commit.' }
$newSha = (git rev-parse HEAD).Trim()
if ((git rev-parse HEAD^).Trim() -ne $ExpectedSha) { throw 'REM-009 parent SHA mismatch.' }

foreach ($suite in @('component', 'regression', 'lint', 'acceptance')) {
    & (Join-Path $root 'ddda.ps1') test -Suite $suite -NonInteractive
    if ($LASTEXITCODE -ne 0) { throw "$suite suite failed: $LASTEXITCODE" }
}

$windowsPowerShell = (Get-Command powershell.exe -ErrorAction Stop).Source
& $windowsPowerShell -NoProfile -ExecutionPolicy Bypass -File $testPath -PlatformPath $root
if ($LASTEXITCODE -ne 0) { throw "Windows PowerShell 5.1 Miro automation test failed: $LASTEXITCODE" }

if (-not [string]::IsNullOrWhiteSpace((git status --porcelain | Out-String))) { throw 'Repository changed during REM-009 validation.' }
$remoteBeforePush = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($remoteBeforePush -ne $ExpectedSha) { throw "Remote branch changed before push: '$remoteBeforePush'." }
git push origin "HEAD:refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'REM-009 push failed.' }
$remoteAfterPush = ((git ls-remote origin "refs/heads/$Branch") -split "`t")[0].Trim()
if ($remoteAfterPush -ne $newSha) { throw 'Remote SHA does not match REM-009 commit.' }

Write-Host "REM-PR8-HVA-CC-009 pushed: $newSha"
