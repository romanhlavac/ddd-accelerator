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
