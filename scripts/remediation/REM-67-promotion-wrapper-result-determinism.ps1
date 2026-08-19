[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = [System.IO.Path]::GetFullPath($RepositoryRoot).TrimEnd('\', '/')
$expectedBase = "43a62152b7fd8be383337c23ffb10d0fda9e7077"
$selfRelative = "scripts/remediation/REM-67-promotion-wrapper-result-determinism.ps1"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $output = @(& git -C $root @Arguments 2>&1)
    $code = $LASTEXITCODE
    $text = ($output | ForEach-Object { $_.ToString() } | Out-String).Trim()
    if ($code -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $code`n$text"
    }
    return $text
}

function Write-Utf8Bom {
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][string]$Content)
    $encoding = New-Object System.Text.UTF8Encoding($true)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Write-Utf8NoBom {
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][string]$Content)
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Assert-Blob {
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][string]$Expected)
    $spec = "$before`:$Path"
    $actual = (Invoke-Git -Arguments @("rev-parse", $spec)).Trim()
    if ($actual -ne $Expected) {
        throw "Integrity mismatch for $Path. Expected Git blob $Expected, actual $actual."
    }
}

$before = (Invoke-Git -Arguments @("rev-parse", "HEAD")).Trim()
$parents = @((Invoke-Git -Arguments @("rev-list", "--parents", "-n", "1", $before)) -split '\s+')
if ($parents.Count -ne 2 -or $parents[1] -ne $expectedBase) {
    throw "Remediation must run on the one bootstrap commit directly above $expectedBase. Current HEAD: $before; parents: $($parents -join ', ')."
}

$bootstrapChanges = @((Invoke-Git -Arguments @("diff", "--name-only", "$expectedBase..$before")) -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if ($bootstrapChanges.Count -ne 1 -or $bootstrapChanges[0] -ne $selfRelative) {
    throw "Bootstrap commit contains unexpected paths: $($bootstrapChanges -join ', ')."
}

Assert-Blob -Path "scripts/platform/Invoke-DDDAGovernedPromotePr.ps1" -Expected "642e1e34159e6db57cfdf8de262f0b6ea44ad6f8"
Assert-Blob -Path "tests/powershell/Test-DDDAPromotionGuards.ps1" -Expected "d9c9aefa30d59779bc6dda80f73ff15a5c614648"
Assert-Blob -Path "docs/user-guide/validate-and-promote-pr.md" -Expected "8a3911c7492fb461e02d2fa941d1417044486e7f"
Assert-Blob -Path "CHANGELOG.md" -Expected "edddcc4b464edcec6aedc8f0eec3ada2fd662599"

$supportPath = Join-Path $root "scripts/platform/DDDAPromotionResultSupport.ps1"
$support = @'
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-DDDAGitHubProbeStatus {
    param(
        [Parameter(Mandatory = $true)][bool]$Succeeded,
        [AllowNull()][object]$HttpStatus,
        [int[]]$ExpectedAbsentStatus = @(404)
    )

    if ($Succeeded) {
        return "PRESENT"
    }
    if ($null -ne $HttpStatus) {
        $status = [int]$HttpStatus
        if ($status -in $ExpectedAbsentStatus) {
            return "ABSENT"
        }
    }
    return "ERROR"
}

function Invoke-DDDAGitHubGetProbe {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Token,
        [int[]]$ExpectedAbsentStatus = @(404)
    )

    if ([string]::IsNullOrWhiteSpace($Token)) {
        throw "GitHub probe token is empty."
    }
    $uri = if ($Path -match '^https://') { $Path } else { "https://api.github.com/" + $Path.TrimStart('/') }
    $headers = @{
        Authorization = "Bearer $Token"
        Accept = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
        "User-Agent" = "DDDA-Platform-Promotion-Probe"
    }

    try {
        $value = Invoke-RestMethod -Method GET -Uri $uri -Headers $headers -ErrorAction Stop
        return [pscustomobject]@{
            status = "PRESENT"
            http_status = 200
            value = $value
            error = $null
        }
    }
    catch {
        $httpStatus = $null
        try {
            if ($null -ne $_.Exception.Response) {
                $httpStatus = [int]$_.Exception.Response.StatusCode
            }
        }
        catch {
        }
        $classification = Resolve-DDDAGitHubProbeStatus -Succeeded $false -HttpStatus $httpStatus -ExpectedAbsentStatus $ExpectedAbsentStatus
        if ($classification -eq "ABSENT") {
            return [pscustomobject]@{
                status = "ABSENT"
                http_status = [int]$httpStatus
                value = $null
                error = $null
            }
        }
        $statusText = if ($null -eq $httpStatus) { "unknown" } else { [string]$httpStatus }
        throw "GitHub probe GET $Path failed unexpectedly. HTTP: $statusText. $($_.Exception.Message)"
    }
}

function Get-DDDAPromotionDryRunSnapshot {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
        [Parameter(Mandatory = $true)][int]$Pr,
        [Parameter(Mandatory = $true)][string]$Tag,
        [Parameter(Mandatory = $true)][string]$Token
    )

    $prInfo = Get-DDDAGitHubPullRequest -RepositorySlug $RepositorySlug -Pr $Pr -Token $Token
    $baseBranch = [string]$prInfo.base.ref
    if ($baseBranch -notmatch '^[A-Za-z0-9._/-]+$') {
        throw "Unsupported base branch name returned by GitHub: $baseBranch"
    }
    if ($Tag -notmatch '^v[0-9A-Za-z._+-]+$') {
        throw "Unsupported release tag for dry-run probe: $Tag"
    }

    $baseProbe = Invoke-DDDAGitHubGetProbe -Path "repos/$RepositorySlug/git/ref/heads/$baseBranch" -Token $Token -ExpectedAbsentStatus @()
    if ([string]$baseProbe.status -ne "PRESENT" -or [string]::IsNullOrWhiteSpace([string]$baseProbe.value.object.sha)) {
        throw "Base branch ref probe did not return a SHA for $baseBranch."
    }
    $tagProbe = Invoke-DDDAGitHubGetProbe -Path "repos/$RepositorySlug/git/ref/tags/$Tag" -Token $Token -ExpectedAbsentStatus @(404)
    $releaseProbe = Invoke-DDDAGitHubGetProbe -Path "repos/$RepositorySlug/releases/tags/$Tag" -Token $Token -ExpectedAbsentStatus @(404)

    return [pscustomobject]@{
        pr_merged = [bool]$prInfo.merged
        head_sha = [string]$prInfo.head.sha
        base_branch = $baseBranch
        base_sha = [string]$baseProbe.value.object.sha
        tag_status = [string]$tagProbe.status
        tag_http_status = $tagProbe.http_status
        github_release_status = [string]$releaseProbe.status
        github_release_http_status = $releaseProbe.http_status
    }
}

function Test-DDDAPromotionDryRunSideEffects {
    param(
        [Parameter(Mandatory = $true)]$Before,
        [Parameter(Mandatory = $true)]$After,
        [Parameter(Mandatory = $true)][string]$ExpectedHeadSha
    )

    $failures = [System.Collections.Generic.List[string]]::new()
    if ([bool]$Before.pr_merged) { $failures.Add("pr_already_merged_before_dry_run") }
    if ([bool]$After.pr_merged) { $failures.Add("pr_merged_by_dry_run") }
    if ([string]$Before.head_sha -ne $ExpectedHeadSha) { $failures.Add("pr_head_mismatch_before_dry_run") }
    if ([string]$After.head_sha -ne $ExpectedHeadSha) { $failures.Add("pr_head_changed_by_dry_run") }
    if ([string]$Before.base_sha -ne [string]$After.base_sha) { $failures.Add("base_sha_changed_by_dry_run") }
    if ([string]$Before.tag_status -ne "ABSENT") { $failures.Add("tag_not_absent_before_dry_run") }
    if ([string]$After.tag_status -ne "ABSENT") { $failures.Add("tag_created_by_dry_run") }
    if ([string]$Before.github_release_status -ne "ABSENT") { $failures.Add("github_release_not_absent_before_dry_run") }
    if ([string]$After.github_release_status -ne "ABSENT") { $failures.Add("github_release_created_by_dry_run") }

    return [pscustomobject]@{
        status = if ($failures.Count -eq 0) { "PASS" } else { "FAIL" }
        failures = @($failures)
        assertions = [ordered]@{
            pr_not_merged = (-not [bool]$After.pr_merged)
            pr_head_unchanged = ([string]$Before.head_sha -eq $ExpectedHeadSha -and [string]$After.head_sha -eq $ExpectedHeadSha)
            base_sha_unchanged = ([string]$Before.base_sha -eq [string]$After.base_sha)
            tag_absent = ([string]$Before.tag_status -eq "ABSENT" -and [string]$After.tag_status -eq "ABSENT")
            github_release_absent = ([string]$Before.github_release_status -eq "ABSENT" -and [string]$After.github_release_status -eq "ABSENT")
            promotion_mutation_absent = ($failures.Count -eq 0)
        }
    }
}
'@
Write-Utf8Bom -Path $supportPath -Content $support

$contractTestPath = Join-Path $root "tests/powershell/Test-DDDAPromotionResultContract.ps1"
$contractTest = @'
[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PlatformPath "scripts/platform/DDDAPromotionResultSupport.ps1")

function Assert-Equal {
    param([AllowNull()]$Actual, [AllowNull()]$Expected, [Parameter(Mandatory = $true)][string]$Message)
    if ([string]$Actual -ne [string]$Expected) {
        throw "$Message Expected '$Expected', actual '$Actual'."
    }
}
function Assert-Contains {
    param([object[]]$Values, [Parameter(Mandatory = $true)][string]$Expected, [Parameter(Mandatory = $true)][string]$Message)
    if ($Expected -notin @($Values | ForEach-Object { [string]$_ })) {
        throw "$Message Missing '$Expected'."
    }
}

Assert-Equal (Resolve-DDDAGitHubProbeStatus -Succeeded $true -HttpStatus 200) "PRESENT" "Successful probe classification failed."
Assert-Equal (Resolve-DDDAGitHubProbeStatus -Succeeded $false -HttpStatus 404 -ExpectedAbsentStatus @(404)) "ABSENT" "Expected 404 must be successful absence."
Assert-Equal (Resolve-DDDAGitHubProbeStatus -Succeeded $false -HttpStatus 401 -ExpectedAbsentStatus @(404)) "ERROR" "401 must remain an error."
Assert-Equal (Resolve-DDDAGitHubProbeStatus -Succeeded $false -HttpStatus 403 -ExpectedAbsentStatus @(404)) "ERROR" "403 must remain an error."
Assert-Equal (Resolve-DDDAGitHubProbeStatus -Succeeded $false -HttpStatus 500 -ExpectedAbsentStatus @(404)) "ERROR" "5xx must remain an error."
Assert-Equal (Resolve-DDDAGitHubProbeStatus -Succeeded $false -HttpStatus $null -ExpectedAbsentStatus @(404)) "ERROR" "Network/unknown failure must remain an error."

$expectedHead = "1111111111111111111111111111111111111111"
$before = [pscustomobject]@{
    pr_merged = $false
    head_sha = $expectedHead
    base_sha = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    tag_status = "ABSENT"
    github_release_status = "ABSENT"
}
$after = [pscustomobject]@{
    pr_merged = $false
    head_sha = $expectedHead
    base_sha = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    tag_status = "ABSENT"
    github_release_status = "ABSENT"
}
$pass = Test-DDDAPromotionDryRunSideEffects -Before $before -After $after -ExpectedHeadSha $expectedHead
Assert-Equal $pass.status "PASS" "Zero-side-effect scenario must PASS."
Assert-Equal $pass.assertions.promotion_mutation_absent $true "Zero-side-effect scenario must expose promotion_mutation_absent=true."

$mutations = @(
    [pscustomobject]@{ Name = "pr_merged_by_dry_run"; Mutate = { param($x) $x.pr_merged = $true } },
    [pscustomobject]@{ Name = "pr_head_changed_by_dry_run"; Mutate = { param($x) $x.head_sha = "2222222222222222222222222222222222222222" } },
    [pscustomobject]@{ Name = "base_sha_changed_by_dry_run"; Mutate = { param($x) $x.base_sha = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" } },
    [pscustomobject]@{ Name = "tag_created_by_dry_run"; Mutate = { param($x) $x.tag_status = "PRESENT" } },
    [pscustomobject]@{ Name = "github_release_created_by_dry_run"; Mutate = { param($x) $x.github_release_status = "PRESENT" } }
)
foreach ($case in $mutations) {
    $candidate = [pscustomobject]@{
        pr_merged = $after.pr_merged
        head_sha = $after.head_sha
        base_sha = $after.base_sha
        tag_status = $after.tag_status
        github_release_status = $after.github_release_status
    }
    & $case.Mutate $candidate
    $result = Test-DDDAPromotionDryRunSideEffects -Before $before -After $candidate -ExpectedHeadSha $expectedHead
    Assert-Equal $result.status "FAIL" "Mutation '$($case.Name)' must FAIL."
    Assert-Contains -Values $result.failures -Expected $case.Name -Message "Mutation '$($case.Name)' not identified."
}

Write-Host "DDDA promotion result contract: PASS"
'@
Write-Utf8Bom -Path $contractTestPath -Content $contractTest

$pythonTestPath = Join-Path $root "runtime/platform/tests/test_promotion_result_contract.py"
$pythonTest = @'
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_promotion_wrapper_has_deterministic_result_contract():
    wrapper = (ROOT / "scripts/platform/Invoke-DDDAGovernedPromotePr.ps1").read_text(encoding="utf-8-sig")
    support = (ROOT / "scripts/platform/DDDAPromotionResultSupport.ps1").read_text(encoding="utf-8-sig")
    for field in (
        "promotion_preflight_status",
        "side_effect_assertions_status",
        "wrapper_status",
        "source_sha",
        "candidate_package_sha256",
        "version",
        "release_scope_gate_status",
    ):
        assert field in wrapper
    assert "Get-DDDAPromotionDryRunSnapshot" in wrapper
    assert "Test-DDDAPromotionDryRunSideEffects" in wrapper
    assert "$LASTEXITCODE" not in wrapper
    assert "$LASTEXITCODE" not in support


def test_expected_absence_is_explicit_and_unexpected_failure_is_not_masked():
    support = (ROOT / "scripts/platform/DDDAPromotionResultSupport.ps1").read_text(encoding="utf-8-sig")
    assert 'return "ABSENT"' in support
    assert 'return "ERROR"' in support
    assert "ExpectedAbsentStatus = @(404)" in support
    assert "failed unexpectedly" in support
    assert "401" not in support  # no hard-coded masking of auth failures


def test_promotion_guard_executes_behavioral_contract_test():
    guards = (ROOT / "tests/powershell/Test-DDDAPromotionGuards.ps1").read_text(encoding="utf-8-sig")
    assert "Test-DDDAPromotionResultContract.ps1" in guards
'@
Write-Utf8NoBom -Path $pythonTestPath -Content $pythonTest

$wrapperPath = Join-Path $root "scripts/platform/Invoke-DDDAGovernedPromotePr.ps1"
$wrapper = Get-Content -LiteralPath $wrapperPath -Raw -Encoding UTF8
$sourceAnchor = '. (Join-Path $PSScriptRoot "DDDAReleaseGovernanceSupport.ps1")'
if ($wrapper -notmatch [regex]::Escape('DDDAPromotionResultSupport.ps1')) {
    if (-not $wrapper.Contains($sourceAnchor)) { throw "Wrapper source anchor not found." }
    $wrapper = $wrapper.Replace($sourceAnchor, $sourceAnchor + [Environment]::NewLine + '. (Join-Path $PSScriptRoot "DDDAPromotionResultSupport.ps1")')
}
$oldTail = @'
# This is the only call into the legacy release executor. No merge/release/tag
# code is reachable until the read-only Release Scope Gate returned PASS.
Invoke-DDDAPlatformChildPowerShell -ScriptPath (Join-Path $PSScriptRoot "Invoke-DDDAPromotePr.ps1") -Arguments $arguments
'@
$newTail = @'
# This is the only call into the legacy release executor. No merge/release/tag
# code is reachable until the read-only Release Scope Gate returned PASS.
$executorPath = Join-Path $PSScriptRoot "Invoke-DDDAPromotePr.ps1"
if (-not $DryRun) {
    Invoke-DDDAPlatformChildPowerShell -ScriptPath $executorPath -Arguments $arguments
    return
}

# Issue #67: promotion dry-run result is operation-local and machine-readable.
# Expected 404 responses for absent tag/GitHub Release are classified as successful
# absence assertions; auth/network/5xx failures remain FAIL and are never inherited
# through ambient $LASTEXITCODE state.
$resultRoot = Join-Path (Get-DDDAPlatformStateRoot) ("promotion/pr-$Pr-$headSha/$Version")
New-Item -ItemType Directory -Path $resultRoot -Force | Out-Null
$resultPath = Join-Path $resultRoot "dry-run-result.json"
$tag = "v$Version"
$beforeSnapshot = $null
$afterSnapshot = $null
$sideEffectResult = $null
$promotionPreflightStatus = "NOT_RUN"
$sideEffectAssertionsStatus = "NOT_RUN"
$wrapperStatus = "FAIL"
$errorMessage = $null

try {
    $beforeSnapshot = Get-DDDAPromotionDryRunSnapshot -RepositorySlug $repositorySlug -Pr $Pr -Tag $tag -Token $githubAuth.Token
    if ([bool]$beforeSnapshot.pr_merged) {
        throw "Dry-run precondition failed: PR #$Pr is already merged."
    }
    if ([string]$beforeSnapshot.head_sha -ne $headSha) {
        throw "Dry-run precondition failed: PR head changed before executor invocation."
    }
    if ([string]$beforeSnapshot.tag_status -ne "ABSENT") {
        throw "Dry-run precondition failed: canonical tag $tag already exists."
    }
    if ([string]$beforeSnapshot.github_release_status -ne "ABSENT") {
        throw "Dry-run precondition failed: GitHub Release for $tag already exists."
    }

    try {
        Invoke-DDDAPlatformChildPowerShell -ScriptPath $executorPath -Arguments $arguments
        $promotionPreflightStatus = "PASS"
    }
    catch {
        $promotionPreflightStatus = "FAIL"
        throw
    }

    $afterSnapshot = Get-DDDAPromotionDryRunSnapshot -RepositorySlug $repositorySlug -Pr $Pr -Tag $tag -Token $githubAuth.Token
    $sideEffectResult = Test-DDDAPromotionDryRunSideEffects -Before $beforeSnapshot -After $afterSnapshot -ExpectedHeadSha $headSha
    $sideEffectAssertionsStatus = [string]$sideEffectResult.status
    if ($sideEffectAssertionsStatus -ne "PASS") {
        throw "Promotion dry-run side-effect assertions failed: $(@($sideEffectResult.failures) -join ', ')"
    }
    $wrapperStatus = "PASS"
}
catch {
    $errorMessage = $_.Exception.Message
    if ($promotionPreflightStatus -eq "PASS" -and $sideEffectAssertionsStatus -eq "NOT_RUN") {
        $sideEffectAssertionsStatus = "FAIL"
    }
}
finally {
    $result = [ordered]@{
        schema_version = 1
        repository = $repositorySlug
        pr = $Pr
        source_sha = $headSha
        candidate_package_sha256 = [string]$validation.PackageSha256
        version = $Version
        release_scope_gate_status = [string]$gate.release_scope_gate_status
        promotion_preflight_status = $promotionPreflightStatus
        side_effect_assertions_status = $sideEffectAssertionsStatus
        wrapper_status = $wrapperStatus
        assertions = if ($null -eq $sideEffectResult) { $null } else { $sideEffectResult.assertions }
        failing_assertions = if ($null -eq $sideEffectResult) { @() } else { @($sideEffectResult.failures) }
        before = $beforeSnapshot
        after = $afterSnapshot
        error = $errorMessage
        evidence_path = $resultPath
    }
    Write-DDDAPlatformJson -Value $result -Path $resultPath -Depth 30
    Write-Host "Promotion dry-run evidence: $resultPath"
}

if ($wrapperStatus -ne "PASS") {
    throw "Governed promotion dry-run FAIL. Evidence: $resultPath. $errorMessage"
}
Write-Host "DDDA governed promotion dry-run: PASS"
Write-Host "Promotion preflight:       $promotionPreflightStatus"
Write-Host "Side-effect assertions:    $sideEffectAssertionsStatus"
Write-Host "Wrapper status:            $wrapperStatus"
'@
if (-not $wrapper.Contains($oldTail)) {
    throw "Governed promotion tail anchor not found or already modified unexpectedly."
}
$wrapper = $wrapper.Replace($oldTail, $newTail)
Write-Utf8Bom -Path $wrapperPath -Content $wrapper

$guardsPath = Join-Path $root "tests/powershell/Test-DDDAPromotionGuards.ps1"
$guards = Get-Content -LiteralPath $guardsPath -Raw -Encoding UTF8
if ($guards -notmatch [regex]::Escape('Test-DDDAPromotionResultContract.ps1')) {
    $append = @'

# Issue #67: execute behavioral dry-run result/absence classification regression in both PS7 and PS5.1 lifecycle jobs.
Invoke-DDDAPlatformChildPowerShell -ScriptPath (Join-Path $platformRoot "tests/powershell/Test-DDDAPromotionResultContract.ps1") -Arguments @("-PlatformPath", $platformRoot)
'@
    $guards = $guards.TrimEnd() + $append + [Environment]::NewLine
    Write-Utf8Bom -Path $guardsPath -Content $guards
}

$guidePath = Join-Path $root "docs/user-guide/validate-and-promote-pr.md"
$guide = Get-Content -LiteralPath $guidePath -Raw -Encoding UTF8
$guideAnchor = "Dry-run neprovede merge release candidate, release ani tag."
if ($guide -notmatch [regex]::Escape('promotion_preflight_status')) {
    if (-not $guide.Contains($guideAnchor)) { throw "Promotion guide dry-run anchor not found." }
    $guideInsert = @'
Dry-run neprovede merge release candidate, release ani tag.

Governed wrapper navíc ukládá deterministickou machine-readable evidence pod DDDA state root `promotion/`. Výsledek rozlišuje:

```text
promotion_preflight_status
side_effect_assertions_status
wrapper_status
source_sha
candidate_package_sha256
version
release_scope_gate_status
```

Před a po dry-runu se čerstvým GitHub read-backem ověřuje, že PR nebyl mergnut, base SHA se nezměnilo a nevznikl canonical tag ani GitHub Release objekt. Očekávaná `404` pro neexistující tag/release je explicitní úspěšná absence assertion; `401/403`, síťová chyba nebo `5xx` zůstávají FAIL a nesmějí zdědit či kontaminovat výsledek jiné operace.
'@
    $guide = $guide.Replace($guideAnchor, $guideInsert)
    Write-Utf8NoBom -Path $guidePath -Content $guide
}

$changelogPath = Join-Path $root "CHANGELOG.md"
$changelog = Get-Content -LiteralPath $changelogPath -Raw -Encoding UTF8
if ($changelog -notmatch [regex]::Escape('promotion dry-run wrapper nyní používá operation-local')) {
    $changelogAnchor = "Změny pro další verzi se během vývoje zapisují sem. Před promotion se všechny položky přesunou do jediné verze `X.Y.Z` s ISO datem a tato sekce zůstane bez release položek."
    if (-not $changelog.Contains($changelogAnchor)) { throw "CHANGELOG Unreleased anchor not found." }
    $changelogInsert = @'
### Fixed

- promotion dry-run wrapper nyní používá operation-local výsledek a explicitní post-read-back side-effect assertions; očekávaná `404` absence tagu/GitHub Release je PASS assertion, zatímco auth/network/API chyby zůstávají FAIL, takže PR8-class `semantic PASS / wrapper FAIL` false-negative se nemůže opakovat přes stale `$LASTEXITCODE`.

Změny pro další verzi se během vývoje zapisují sem. Před promotion se všechny položky přesunou do jediné verze `X.Y.Z` s ISO datem a tato sekce zůstane bez release položek.
'@
    $changelog = $changelog.Replace($changelogAnchor, $changelogInsert)
    Write-Utf8NoBom -Path $changelogPath -Content $changelog
}

$selfPath = Join-Path $root $selfRelative
if (Test-Path -LiteralPath $selfPath -PathType Leaf) {
    Remove-Item -LiteralPath $selfPath -Force
}

$allowed = @(
    "scripts/platform/Invoke-DDDAGovernedPromotePr.ps1",
    "scripts/platform/DDDAPromotionResultSupport.ps1",
    "tests/powershell/Test-DDDAPromotionResultContract.ps1",
    "tests/powershell/Test-DDDAPromotionGuards.ps1",
    "runtime/platform/tests/test_promotion_result_contract.py",
    "docs/user-guide/validate-and-promote-pr.md",
    "CHANGELOG.md",
    $selfRelative
)
$changed = @((Invoke-Git -Arguments @("status", "--porcelain")) -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
foreach ($line in $changed) {
    $path = $line.Substring(3).Trim()
    if ($path -notin $allowed) {
        throw "Unexpected changed path before commit: $path"
    }
}

$null = Invoke-Git -Arguments (@("add", "--") + $allowed)
$staged = @((Invoke-Git -Arguments @("diff", "--cached", "--name-only")) -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
foreach ($path in $staged) {
    if ($path -notin $allowed) { throw "Unexpected staged path: $path" }
}
foreach ($required in @(
    "scripts/platform/Invoke-DDDAGovernedPromotePr.ps1",
    "scripts/platform/DDDAPromotionResultSupport.ps1",
    "tests/powershell/Test-DDDAPromotionResultContract.ps1",
    "tests/powershell/Test-DDDAPromotionGuards.ps1",
    "runtime/platform/tests/test_promotion_result_contract.py",
    "docs/user-guide/validate-and-promote-pr.md",
    "CHANGELOG.md",
    $selfRelative
)) {
    if ($required -notin $staged) { throw "Required staged path missing: $required" }
}

$null = Invoke-Git -Arguments @("commit", "-m", "fix(release): make promotion dry-run result deterministic (#67)")
$after = (Invoke-Git -Arguments @("rev-parse", "HEAD")).Trim()
$commitCount = [int](Invoke-Git -Arguments @("rev-list", "--count", "$before..$after"))
if ($commitCount -ne 1) { throw "Remediation must create exactly one commit; created $commitCount." }
$status = Invoke-Git -Arguments @("status", "--porcelain")
if (-not [string]::IsNullOrWhiteSpace($status)) { throw "Working tree is not clean after remediation:`n$status" }

Write-Host "REM-67 remediation created exact corrective commit: $after"
Write-Host "No push/merge/promotion/release/tag was performed by the remediation script."
