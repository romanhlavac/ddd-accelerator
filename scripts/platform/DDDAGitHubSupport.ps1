Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function ConvertFrom-DDDAGitCredential {
    param([string]$Text)

    $values = @{}
    foreach ($line in @($Text -split "`r?`n")) {
        if ($line -match '^(?<key>[^=]+)=(?<value>.*)$') {
            $values[$Matches["key"]] = $Matches["value"]
        }
    }

    return [pscustomobject]@{
        Username = if ($values.ContainsKey("username")) { [string]$values["username"] } else { $null }
        Password = if ($values.ContainsKey("password")) { [string]$values["password"] } else { $null }
    }
}

function Get-DDDAGitHubAuthentication {
    param([string]$HostName = "github.com")

    foreach ($candidate in @(
        [pscustomobject]@{ Name = "GH_TOKEN"; Value = $env:GH_TOKEN },
        [pscustomobject]@{ Name = "GITHUB_TOKEN"; Value = $env:GITHUB_TOKEN }
    )) {
        if (-not [string]::IsNullOrWhiteSpace([string]$candidate.Value)) {
            return [pscustomobject]@{
                Token = [string]$candidate.Value
                Source = [string]$candidate.Name
                HostName = $HostName
            }
        }
    }

    if (Get-Command "gh" -ErrorAction SilentlyContinue) {
        try {
            $token = Invoke-DDDAPlatformNative -Command "gh" -Arguments @("auth", "token", "--hostname", $HostName)
            if (-not [string]::IsNullOrWhiteSpace($token)) {
                return [pscustomobject]@{
                    Token = $token.Trim()
                    Source = "gh auth token"
                    HostName = $HostName
                }
            }
        }
        catch {
        }
    }

    if (Get-Command "git" -ErrorAction SilentlyContinue) {
        $previousPreference = $ErrorActionPreference
        $exitCode = 1
        $raw = @()
        try {
            $ErrorActionPreference = "Continue"
            $credentialRequest = "protocol=https`nhost=$HostName`n`n"
            $raw = @($credentialRequest | & git credential fill 2>&1)
            $exitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $previousPreference
        }

        if ($exitCode -eq 0) {
            $credentialText = ($raw | ForEach-Object { $_.ToString() } | Out-String).Trim()
            $credential = ConvertFrom-DDDAGitCredential -Text $credentialText
            if (-not [string]::IsNullOrWhiteSpace([string]$credential.Password)) {
                return [pscustomobject]@{
                    Token = [string]$credential.Password
                    Source = "git credential helper"
                    HostName = $HostName
                }
            }
        }
    }

    throw "GitHub autentizace není dostupná. Použij existující Git credential helper, nastav GH_TOKEN/GITHUB_TOKEN, nebo proveď 'gh auth login'. Token nikdy nepředávej jako CLI argument."
}

function Invoke-DDDAGitHubApi {
    param(
        [Parameter(Mandatory = $true)][ValidateSet("GET", "POST", "PUT", "PATCH", "DELETE")][string]$Method,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Token,
        [AllowNull()][object]$Body = $null
    )

    if ([string]::IsNullOrWhiteSpace($Token)) {
        throw "GitHub API token je prázdný."
    }

    if ($Path -match '^https://') {
        $uri = $Path
    }
    else {
        $uri = "https://api.github.com/" + $Path.TrimStart('/')
    }

    if ([Net.ServicePointManager]::SecurityProtocol -band [Net.SecurityProtocolType]::Tls12 -eq 0) {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    }

    $headers = @{
        Authorization = "Bearer $Token"
        Accept = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
        "User-Agent" = "DDDA-Platform-Lifecycle"
    }

    $parameters = @{
        Method = $Method
        Uri = $uri
        Headers = $headers
        ErrorAction = "Stop"
    }
    if ($null -ne $Body) {
        $parameters["Body"] = ConvertTo-Json -InputObject $Body -Depth 30 -Compress
        $parameters["ContentType"] = "application/json"
    }

    try {
        return Invoke-RestMethod @parameters
    }
    catch {
        $status = $null
        try {
            if ($null -ne $_.Exception.Response) {
                $status = [int]$_.Exception.Response.StatusCode
            }
        }
        catch {
        }
        $statusText = if ($null -eq $status) { "unknown" } else { [string]$status }
        throw "GitHub API $Method $Path selhalo. HTTP: $statusText. $($_.Exception.Message)"
    }
}

function Get-DDDAGitHubPullRequest {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
        [Parameter(Mandatory = $true)][int]$Pr,
        [Parameter(Mandatory = $true)][string]$Token
    )

    $result = $null
    for ($attempt = 1; $attempt -le 4; $attempt++) {
        $result = Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/pulls/$Pr" -Token $Token
        if ($null -ne $result.mergeable -or [bool]$result.merged) {
            break
        }
        Start-Sleep -Seconds 2
    }
    return $result
}

function Assert-DDDAGitHubChecksPassed {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
        [Parameter(Mandatory = $true)][string]$Commit,
        [Parameter(Mandatory = $true)][string]$Token
    )

    $checkRuns = [System.Collections.Generic.List[object]]::new()
    $page = 1
    do {
        $response = Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/commits/$Commit/check-runs?per_page=100&page=$page" -Token $Token
        $batch = @($response.check_runs)
        foreach ($checkRun in $batch) {
            $checkRuns.Add($checkRun)
        }
        $page++
    } while ($batch.Count -eq 100)

    if ($checkRuns.Count -eq 0) {
        throw "GitHub nevrátil žádné CI check runs pro commit $Commit."
    }

    $allowedConclusions = @("success", "neutral", "skipped")
    $notPassed = @(
        $checkRuns |
            Where-Object {
                [string]$_.status -ne "completed" -or
                [string]$_.conclusion -notin $allowedConclusions
            }
    )
    if ($notPassed.Count -gt 0) {
        $details = @(
            $notPassed |
                ForEach-Object { "{0}: status={1}; conclusion={2}" -f $_.name, $_.status, $_.conclusion }
        )
        throw "CI check runs nejsou všechny PASS:`n$($details -join "`n")"
    }

    $combinedStatus = Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/commits/$Commit/status" -Token $Token
    $commitStatuses = @($combinedStatus.statuses)
    if ($commitStatuses.Count -gt 0 -and [string]$combinedStatus.state -ne "success") {
        $details = @(
            $commitStatuses |
                Where-Object { [string]$_.state -ne "success" } |
                ForEach-Object { "{0}: state={1}" -f $_.context, $_.state }
        )
        throw "Commit status checks nejsou všechny PASS:`n$($details -join "`n")"
    }

    return [pscustomobject]@{
        CheckRunCount = $checkRuns.Count
        CommitStatusCount = $commitStatuses.Count
    }
}

function Get-DDDAGitHubApprovedUsers {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
        [Parameter(Mandatory = $true)][int]$Pr,
        [Parameter(Mandatory = $true)][string]$Token
    )

    $reviews = [System.Collections.Generic.List[object]]::new()
    $page = 1
    do {
        $batch = @(Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/pulls/$Pr/reviews?per_page=100&page=$page" -Token $Token)
        foreach ($review in $batch) {
            $reviews.Add($review)
        }
        $page++
    } while ($batch.Count -eq 100)

    return @(
        $reviews |
            Where-Object { [string]$_.state -eq "APPROVED" } |
            ForEach-Object { [string]$_.user.login } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            Sort-Object -Unique
    )
}

function Merge-DDDAGitHubPullRequest {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
        [Parameter(Mandatory = $true)][int]$Pr,
        [Parameter(Mandatory = $true)][string]$HeadSha,
        [Parameter(Mandatory = $true)][ValidateSet("squash", "merge", "rebase")][string]$MergeMethod,
        [Parameter(Mandatory = $true)][string]$Token
    )

    $result = Invoke-DDDAGitHubApi -Method PUT -Path "repos/$RepositorySlug/pulls/$Pr/merge" -Token $Token -Body @{
        sha = $HeadSha
        merge_method = $MergeMethod
    }
    if (-not [bool]$result.merged) {
        throw "GitHub PR merge odmítl: $([string]$result.message)"
    }
    return $result
}
