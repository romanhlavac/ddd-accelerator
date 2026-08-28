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
