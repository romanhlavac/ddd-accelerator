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
        [Parameter(Mandatory = $true)][string]$Token,
        [string[]]$IgnoredCheckRunNames = @()
    )

    $adapter = Join-Path $PSScriptRoot "Evaluate-DDDACheckRuns.py"
    if (-not (Test-Path -LiteralPath $adapter -PathType Leaf)) {
        throw "Shared mandatory-check adapter neexistuje: $adapter"
    }
    $outputPath = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-check-evidence-" + [guid]::NewGuid().ToString("N") + ".json")
    $arguments = @(
        $adapter,
        "--repository", $RepositorySlug,
        "--commit", $Commit,
        "--output", $outputPath
    )
    foreach ($name in $IgnoredCheckRunNames) {
        $arguments += @("--ignored-check", $name)
    }
    $previousToken = $env:DDDA_CHECKS_GITHUB_TOKEN
    $adapterError = $null
    try {
        $env:DDDA_CHECKS_GITHUB_TOKEN = $Token
        $python = Get-DDDAPlatformPythonCommand
        try {
            Invoke-DDDAPlatformNative -Command $python -Arguments $arguments | Out-Null
        }
        catch {
            $adapterError = $_.Exception.Message
        }
        if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
            if ($null -ne $adapterError) { throw $adapterError }
            throw "Shared mandatory-check adapter nevytvořil rozhodnutí."
        }
        $result = Get-Content -LiteralPath $outputPath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    finally {
        $env:DDDA_CHECKS_GITHUB_TOKEN = $previousToken
        Remove-Item -LiteralPath $outputPath -Force -ErrorAction SilentlyContinue
    }
    if ([string]$result.status -ne "PASS") {
        throw "Mandatory-check adapter odmítl evidence: $(@($result.failures) -join ', ')"
    }
    return [pscustomobject]@{
        CheckRunCount = [int]$result.observed_check_run_count
        EvaluatedCheckRunCount = @($result.summary.latest_results).Count
        CommitStatusCount = [int]$result.observed_commit_status_count
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
