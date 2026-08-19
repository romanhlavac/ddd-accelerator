[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = [System.IO.Path]::GetFullPath($RepositoryRoot).TrimEnd('\','/')
$expectedMain = 'baad4684328262ef94b31f50cef7c51193cf8ad3'
$selfRelative = 'scripts/remediation/REM-68-deterministic-release-tag-identity.ps1'
$selfPath = Join-Path $root $selfRelative
$promotionRelative = 'scripts/platform/Invoke-DDDAPromotePr.ps1'
$testRelative = 'tests/powershell/Test-DDDAPromotionGuards.ps1'
$userGuideRelative = 'docs/user-guide/validate-and-promote-pr.md'
$lifecycleRelative = 'docs/developer-guide/platform-development-lifecycle.md'
$adrRelative = 'docs/adr/0008-human-release-decision-and-release-scope-gate.md'
$changelogRelative = 'CHANGELOG.md'
$expectedFinalPaths = @($promotionRelative,$testRelative,$userGuideRelative,$lifecycleRelative,$adrRelative,$changelogRelative,$selfRelative) | Sort-Object

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $output = @(& git -C $root @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed:`n$($output -join [Environment]::NewLine)"
    }
    return (($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine).Trim()
}

function Write-Text {
    param([string]$Path,[string]$Text,[switch]$Bom)
    $encoding = New-Object System.Text.UTF8Encoding([bool]$Bom)
    [System.IO.File]::WriteAllText($Path,$Text,$encoding)
}

function Replace-ExactOnce {
    param([string]$Text,[string]$Old,[string]$New,[string]$Label)
    $first = $Text.IndexOf($Old,[System.StringComparison]::Ordinal)
    if ($first -lt 0) { throw "$Label: expected source text not found." }
    $second = $Text.IndexOf($Old,$first + $Old.Length,[System.StringComparison]::Ordinal)
    if ($second -ge 0) { throw "$Label: expected source text is not unique." }
    return $Text.Substring(0,$first) + $New + $Text.Substring($first + $Old.Length)
}

$current = Invoke-Git @('rev-parse','HEAD')
$parent = Invoke-Git @('rev-parse','HEAD^')
if ($parent -ne $expectedMain) {
    throw "Staging commit parent '$parent' does not match exact main '$expectedMain'."
}
$statusBefore = Invoke-Git @('status','--porcelain')
if (-not [string]::IsNullOrWhiteSpace($statusBefore)) { throw "Working tree is not clean before remediation:`n$statusBefore" }
$stagingPaths = @(Invoke-Git @('diff','--name-only',$expectedMain,$current) -split "`r?`n" | Where-Object { $_ })
if ($stagingPaths.Count -ne 1 -or $stagingPaths[0] -ne $selfRelative) {
    throw "Staging commit must contain only $selfRelative. Observed: $($stagingPaths -join ', ')"
}

# 1) Product release executor: command-scoped tagger identity, exact target/message checks,
#    and preserved RECOVERY_REQUIRED evidence if the final tag step fails.
$promotionPath = Join-Path $root $promotionRelative
$promotion = Get-Content -LiteralPath $promotionPath -Raw -Encoding UTF8
$oldTagBlock = @'
$null = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("tag", "-a", $tag, $mergeCommit, "-m", "DDDA $Version")
$null = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("push", "origin", $tag)
'@
$newTagBlock = @'
$releaseTaggerName = "DDDA Release Tagger"
$releaseTaggerEmail = "ddda-release-tagger@example.invalid"
$tagRecoveryPath = Join-Path $promotionRoot "tag-recovery.json"
try {
    $null = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @(
        "-c", "user.name=$releaseTaggerName",
        "-c", "user.email=$releaseTaggerEmail",
        "tag", "-a", $tag, $mergeCommit, "-m", "DDDA $Version"
    )

    $localTagTarget = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("rev-list", "-n", "1", $tag)
    if ($localTagTarget -ne $mergeCommit) {
        throw "Local annotated tag '$tag' targets '$localTagTarget', expected '$mergeCommit'."
    }
    $localTagRecord = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @(
        "for-each-ref", "refs/tags/$tag", "--format=%(taggername)|%(taggeremail)|%(contents)"
    )
    $expectedTagRecord = "$releaseTaggerName|<$releaseTaggerEmail>|DDDA $Version"
    if ($localTagRecord -ne $expectedTagRecord) {
        throw "Annotated tag identity/message mismatch. Observed: $localTagRecord"
    }

    $null = Invoke-DDDAPlatformGit -Repository $releaseSource -Arguments @("push", "origin", $tag)
    $remoteTagTarget = Invoke-DDDAPlatformNative -Command "git" -Arguments @(
        "ls-remote", "--tags", $originUrl, "refs/tags/$tag^{}"
    )
    $remoteTagSha = (($remoteTagTarget -split '\s+')[0]).Trim()
    if ($remoteTagSha -ne $mergeCommit) {
        throw "Remote annotated tag '$tag' dereferences to '$remoteTagSha', expected validated release SHA '$mergeCommit'."
    }
}
catch {
    $releasePackageHash = $null
    if (Test-Path -LiteralPath $releasePackagePath -PathType Leaf) {
        $releasePackageHash = Get-DDDAPlatformFileHash -Path $releasePackagePath
    }
    Write-DDDAPlatformJson -Path $tagRecoveryPath -Depth 20 -Value ([ordered]@{
        schema_version = 1
        state = "RECOVERY_REQUIRED"
        repository = $repositorySlug
        pr = $Pr
        version = $Version
        tag = $tag
        validated_release_sha = $mergeCommit
        release_package_sha256 = $releasePackageHash
        release_report = $releaseReports
        tagger_name = $releaseTaggerName
        tagger_email = $releaseTaggerEmail
        failure = $_.Exception.Message
        recovery_invariants = @(
            "same-version",
            "same-validated-release-sha",
            "same-release-report-and-package",
            "no-tag-overwrite",
            "no-force-push",
            "explicit-human-recovery-authorization"
        )
        recorded_at = (Get-Date).ToUniversalTime().ToString("o")
    })
    throw "Release validation PASS, but canonical annotated-tag step failed. State: RECOVERY_REQUIRED. Evidence: $tagRecoveryPath. $($_.Exception.Message)"
}
'@
$promotion = Replace-ExactOnce -Text $promotion -Old $oldTagBlock -New $newTagBlock -Label 'promotion tag block'
Write-Text -Path $promotionPath -Text $promotion -Bom

# 2) Regression: prove a clean Git environment can create the canonical annotated tag
#    without ambient/global identity and guard the recovery contract statically.
$testPath = Join-Path $root $testRelative
$tests = Get-Content -LiteralPath $testPath -Raw -Encoding UTF8
$testMarker = 'Write-Host "DDDA merge/promotion guards: PASS"'
$testInsertion = @'
# Issue #68: annotated release tag identity is command-scoped and deterministic.
Assert-True -Condition ($promotion -match '\$releaseTaggerName\s*=\s*"DDDA Release Tagger"') -Message "Promotion nemá deterministic release tagger name."
Assert-True -Condition ($promotion -match '\$releaseTaggerEmail\s*=\s*"ddda-release-tagger@example\.invalid"') -Message "Promotion nemá deterministic release tagger email."
Assert-True -Condition ($promotion -match '"-c",\s*"user\.name=\$releaseTaggerName"') -Message "Annotated tag nepoužívá command-scoped user.name."
Assert-True -Condition ($promotion -match '"-c",\s*"user\.email=\$releaseTaggerEmail"') -Message "Annotated tag nepoužívá command-scoped user.email."
Assert-True -Condition ($promotion -match 'state\s*=\s*"RECOVERY_REQUIRED"') -Message "Promotion neeviduje TAG failure jako RECOVERY_REQUIRED."
Assert-True -Condition ($promotion -match 'no-tag-overwrite' -and $promotion -match 'no-force-push') -Message "Tag recovery contract neobsahuje no-overwrite/no-force invariant."
Assert-True -Condition ($promotion -notmatch 'Invoke-DDDAPlatformGit\s+-Repository\s+\$releaseSource\s+-Arguments\s+@\("config",\s*"user\.(?:name|email)"') -Message "Release tagger identity nesmí záviset na persistentním release-source Git configu."

$tagIdentityRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-tag-identity-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tagIdentityRoot -Force | Out-Null
$previousGlobal = $env:GIT_CONFIG_GLOBAL
$previousNoSystem = $env:GIT_CONFIG_NOSYSTEM
try {
    $emptyGlobal = Join-Path $tagIdentityRoot "empty.gitconfig"
    [System.IO.File]::WriteAllText($emptyGlobal, "", (New-Object System.Text.UTF8Encoding($false)))
    $env:GIT_CONFIG_GLOBAL = $emptyGlobal
    $env:GIT_CONFIG_NOSYSTEM = "1"

    $repo = Join-Path $tagIdentityRoot "repo"
    $null = Invoke-DDDAPlatformNative -Command "git" -Arguments @("init", "-b", "main", $repo)
    Write-DDDAPlatformText -Value "fixture`n" -Path (Join-Path $repo "fixture.txt")
    $null = Invoke-DDDAPlatformGit -Repository $repo -Arguments @("add", ".")
    $null = Invoke-DDDAPlatformGit -Repository $repo -Arguments @(
        "-c", "user.name=Fixture Committer",
        "-c", "user.email=fixture@example.invalid",
        "commit", "-m", "fixture"
    )
    $fixtureCommit = Invoke-DDDAPlatformGit -Repository $repo -Arguments @("rev-parse", "HEAD")

    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $effectiveNameRaw = @(& git -C $repo config --get user.name 2>$null)
        $nameExit = $LASTEXITCODE
        $effectiveEmailRaw = @(& git -C $repo config --get user.email 2>$null)
        $emailExit = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    $effectiveName = (($effectiveNameRaw | ForEach-Object { $_.ToString() }) -join "").Trim()
    $effectiveEmail = (($effectiveEmailRaw | ForEach-Object { $_.ToString() }) -join "").Trim()
    Assert-True -Condition ($nameExit -eq 1 -and $emailExit -eq 1 -and [string]::IsNullOrWhiteSpace($effectiveName) -and [string]::IsNullOrWhiteSpace($effectiveEmail)) -Message "Fixture omylem zdědila ambientní Git identity."

    $null = Invoke-DDDAPlatformGit -Repository $repo -Arguments @(
        "-c", "user.name=DDDA Release Tagger",
        "-c", "user.email=ddda-release-tagger@example.invalid",
        "tag", "-a", "v9.9.9", $fixtureCommit, "-m", "DDDA 9.9.9"
    )
    $tagTarget = Invoke-DDDAPlatformGit -Repository $repo -Arguments @("rev-list", "-n", "1", "v9.9.9")
    $tagRecord = Invoke-DDDAPlatformGit -Repository $repo -Arguments @(
        "for-each-ref", "refs/tags/v9.9.9", "--format=%(taggername)|%(taggeremail)|%(contents)"
    )
    Assert-True -Condition ($tagTarget -eq $fixtureCommit) -Message "Clean-runner tag netargetuje exact validated commit."
    Assert-True -Condition ($tagRecord -eq "DDDA Release Tagger|<ddda-release-tagger@example.invalid>|DDDA 9.9.9") -Message "Clean-runner annotated tag nemá canonical identity/message: $tagRecord"
}
finally {
    $env:GIT_CONFIG_GLOBAL = $previousGlobal
    $env:GIT_CONFIG_NOSYSTEM = $previousNoSystem
    Remove-Item -LiteralPath $tagIdentityRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "DDDA merge/promotion guards: PASS"
'@
$tests = Replace-ExactOnce -Text $tests -Old $testMarker -New $testInsertion -Label 'promotion guards tail'
Write-Text -Path $testPath -Text $tests -Bom

# 3) User runbook: deterministic identity and bounded recovery after validation PASS.
$userGuidePath = Join-Path $root $userGuideRelative
$userGuide = Get-Content -LiteralPath $userGuidePath -Raw -Encoding UTF8
$oldGuide = 'Při release validation FAIL se tag nevytvoří.'
$newGuide = @'
Při release validation FAIL se tag nevytvoří.

### Annotated tag identity a recovery

Canonical annotated tag používá pouze command-scoped ne-secret identity `DDDA Release Tagger <ddda-release-tagger@example.invalid>`. Release cesta nesmí záviset na runner/global `user.name` nebo `user.email`; message zůstává přesně `DDDA <version>` a tag musí dereferencovat na exact validated release SHA.

Pokud release validation i report skončily PASS, ale vytvoření/push/read-back tagu selže, release není `RELEASED`; stav je `RECOVERY_REQUIRED` a `promotion/.../tag-recovery.json` se zachová. Neopakuj celý promotion ani release validation pouze kvůli mechanickému tag failure.

Recovery je povolena až po samostatné explicitní lidské recovery authorization a pouze pro stejnou verzi, stejný validated release SHA, stejný release report/package a canonical tag. Před zápisem vždy načti remote tag: pokud chybí, lze zopakovat pouze command-scoped annotated-tag step; pokud již existuje a přesně odpovídá očekávanému SHA/message, proveď jen read-back a uzavři recovery; pokud existuje s jiným targetem nebo obsahem, fail closed. Tag se nikdy nepřepisuje a nepoužívá se force push.
'@
$userGuide = Replace-ExactOnce -Text $userGuide -Old $oldGuide -New $newGuide -Label 'user guide recovery section'
Write-Text -Path $userGuidePath -Text $userGuide

# 4) Developer lifecycle: make release state/recovery semantics explicit.
$lifecyclePath = Join-Path $root $lifecycleRelative
$lifecycle = Get-Content -LiteralPath $lifecyclePath -Raw -Encoding UTF8
$oldLifecycle = 'Po canonical release-candidate merge vznikne release package; tag se vytvoří až po package validation, generated release workspace, ingestion, smoke a acceptance PASS.'
$newLifecycle = @'
Po canonical release-candidate merge vznikne release package; tag se vytvoří až po package validation, generated release workspace, ingestion, smoke a acceptance PASS. Annotated tag používá deterministic command-scoped non-secret tagger identity a musí targetovat exact validated release SHA.

Release state po validačním PASS je `RELEASE_VALIDATED`. Úspěšný canonical tag step přejde do `RELEASED`. Selhání vytvoření, push nebo read-back tagu po validačním PASS přejde do `RECOVERY_REQUIRED`; nesmí přepisovat tag ani Git historii. Recovery smí zopakovat pouze tag/read-back side effect pro stejnou verzi, validated SHA a release evidence, a vyžaduje samostatnou explicitní human recovery authorization. Konfliktní existující tag je fail-closed.
'@
$lifecycle = Replace-ExactOnce -Text $lifecycle -Old $oldLifecycle -New $newLifecycle -Label 'developer lifecycle release state'
Write-Text -Path $lifecyclePath -Text $lifecycle

# 5) ADR 0008: prospective state machine; historical 0.1.0 remains unchanged.
$adrPath = Join-Path $root $adrRelative
$adr = Get-Content -LiteralPath $adrPath -Raw -Encoding UTF8
$adrMarker = '## Historical note'
$adrSection = @'
## Release tag state and bounded recovery

Release tagging is an irreversible release side effect and therefore has an explicit state boundary:

```text
RELEASE_VALIDATED
→ canonical annotated tag attempt
→ RELEASED

RELEASE_VALIDATED
→ tag create/push/read-back failure
→ RECOVERY_REQUIRED
```

The tagger identity is deterministic, command-scoped and non-secret. It must not depend on ambient/global Git configuration. Recovery does not repeat implementation merge or release validation. It may only complete or verify the same canonical tag for the same version, validated release SHA and release evidence after explicit human recovery authorization. Existing matching tag is read-back evidence; conflicting tag is a hard failure. Tag overwrite, force push and history rewrite are prohibited.

## Historical note
'@
$adr = Replace-ExactOnce -Text $adr -Old $adrMarker -New $adrSection -Label 'ADR release recovery section'
Write-Text -Path $adrPath -Text $adr

# 6) Changelog.
$changelogPath = Join-Path $root $changelogRelative
$changelog = Get-Content -LiteralPath $changelogPath -Raw -Encoding UTF8
$oldFixed = '- promotion dry-run wrapper nyní používá operation-local výsledek a explicitní post-read-back side-effect assertions; očekávaná `404` absence tagu/GitHub Release je PASS assertion, zatímco auth/network/API chyby zůstávají FAIL, takže PR8-class `semantic PASS / wrapper FAIL` false-negative se nemůže opakovat přes stale `$LASTEXITCODE`.'
$newFixed = $oldFixed + "`n- canonical annotated release tag používá deterministic command-scoped non-secret Git identity, ověřuje exact target/message a při post-validation tag failure zachovává `RECOVERY_REQUIRED` evidence s no-overwrite/no-force recovery invarianty."
$changelog = Replace-ExactOnce -Text $changelog -Old $oldFixed -New $newFixed -Label 'changelog fixed bullet'
Write-Text -Path $changelogPath -Text $changelog

# Self-remove and validate exact changed path set before the final commit.
Remove-Item -LiteralPath $selfPath -Force
$null = Invoke-Git @('add','--',$promotionRelative,$testRelative,$userGuideRelative,$lifecycleRelative,$adrRelative,$changelogRelative,$selfRelative)
$observed = @(Invoke-Git @('diff','--cached','--name-only') -split "`r?`n" | Where-Object { $_ } | Sort-Object)
if (($observed -join "`n") -ne ($expectedFinalPaths -join "`n")) {
    throw "Unexpected staged path set. Expected: $($expectedFinalPaths -join ', '); observed: $($observed -join ', ')"
}

& (Join-Path $root 'tests/powershell/Test-DDDAPromotionGuards.ps1') -PlatformPath $root
if ($LASTEXITCODE -ne 0) { throw "Promotion guard regression failed: $LASTEXITCODE" }
$diffCheck = @(& git -C $root diff --cached --check 2>&1)
if ($LASTEXITCODE -ne 0) { throw "git diff --check failed:`n$($diffCheck -join [Environment]::NewLine)" }

$null = Invoke-Git @('commit','-m','fix(release): make annotated tag identity deterministic')
$after = Invoke-Git @('rev-parse','HEAD')
$count = [int](Invoke-Git @('rev-list','--count',"$current..$after"))
if ($count -ne 1) { throw "Remediation must create exactly one final commit; observed $count." }
$statusAfter = Invoke-Git @('status','--porcelain')
if (-not [string]::IsNullOrWhiteSpace($statusAfter)) { throw "Remediation left dirty working tree:`n$statusAfter" }

Write-Host "REM-68 PASS: final commit $after"
if (-not $NoPush) {
    throw 'This remediation is broker-driven and must be invoked with -NoPush; broker owns the guarded push.'
}
