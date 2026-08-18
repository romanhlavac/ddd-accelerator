Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:DDDAHrdrMarker = "<!-- ddda:human-release-decision:v1 -->"

function Get-DDDACandidateValidationEvidence {
    param(
        [Parameter(Mandatory = $true)][int]$Pr,
        [Parameter(Mandatory = $true)][string]$HeadSha
    )

    $validationRoot = Join-Path (Get-DDDAPlatformStateRoot) ("validation-reports/pr-$Pr-$HeadSha")
    $validationReports = @()
    if (Test-Path -LiteralPath $validationRoot) {
        $validationReports = @(
            Get-ChildItem -LiteralPath $validationRoot -Filter "result.json" -File -Recurse -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTimeUtc -Descending
        )
    }
    if ($validationReports.Count -eq 0) {
        throw "Nenalezen PASS validate-pr report pro PR #$Pr a SHA $HeadSha."
    }

    foreach ($candidate in $validationReports) {
        $candidateReport = Get-Content -LiteralPath $candidate.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        if (
            [string]$candidateReport.status -ne "PASS" -or
            [string]$candidateReport.source.commit -ne $HeadSha -or
            [int]$candidateReport.source.pr -ne $Pr -or
            $null -eq $candidateReport.package
        ) {
            continue
        }
        $packagePath = [string]$candidateReport.package.path
        if (-not (Test-Path -LiteralPath $packagePath -PathType Leaf)) {
            continue
        }
        $actualHash = Get-DDDAPlatformFileHash -Path $packagePath
        if ($actualHash -ne [string]$candidateReport.package.sha256) {
            throw "Candidate package hash neodpovídá validation reportu: $packagePath"
        }
        return [pscustomobject]@{
            ReportPath = $candidate.FullName
            Report = $candidateReport
            PackagePath = $packagePath
            PackageSha256 = $actualHash
        }
    }
    throw "Žádný validation report nemá PASS pro aktuální PR head SHA $HeadSha a validní candidate package."
}

function Get-DDDAReleaseMilestoneScope {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
        [Parameter(Mandatory = $true)][string]$Version,
        [Parameter(Mandatory = $true)][string]$Token
    )

    $wantedTitle = "DDDA $Version"
    $milestones = [System.Collections.Generic.List[object]]::new()
    for ($page = 1; ; $page++) {
        $batch = @(Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/milestones?state=all&per_page=100&page=$page" -Token $Token)
        foreach ($row in $batch) { $milestones.Add($row) }
        if ($batch.Count -lt 100) { break }
    }
    $matches = @($milestones | Where-Object { [string]$_.title -eq $wantedTitle })
    if ($matches.Count -ne 1) {
        throw "Očekáván právě jeden Milestone '$wantedTitle', nalezeno: $($matches.Count)."
    }
    $milestone = $matches[0]

    $issues = [System.Collections.Generic.List[int]]::new()
    for ($page = 1; ; $page++) {
        $batch = @(Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/issues?state=all&milestone=$([int]$milestone.number)&per_page=100&page=$page" -Token $Token)
        foreach ($row in $batch) {
            if ($null -eq $row.PSObject.Properties["pull_request"]) {
                $issues.Add([int]$row.number)
            }
        }
        if ($batch.Count -lt 100) { break }
    }

    return [pscustomobject]@{
        Number = [int]$milestone.number
        Title = [string]$milestone.title
        Issues = @($issues | Sort-Object -Unique)
    }
}

function Get-DDDAHrdrComments {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
        [Parameter(Mandatory = $true)][int]$Pr,
        [Parameter(Mandatory = $true)][string]$Token
    )

    $matches = [System.Collections.Generic.List[object]]::new()
    for ($page = 1; ; $page++) {
        $batch = @(Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/issues/$Pr/comments?per_page=100&page=$page" -Token $Token)
        foreach ($comment in $batch) {
            if ([string]$comment.body -like "*$script:DDDAHrdrMarker*") {
                $matches.Add($comment)
            }
        }
        if ($batch.Count -lt 100) { break }
    }
    return @($matches)
}

function ConvertFrom-DDDAHrdrComment {
    param([Parameter(Mandatory = $true)][object]$Comment)

    $body = [string]$Comment.body
    $pattern = '(?s)```json\s*(?<json>\{.*?\})\s*```'
    $match = [regex]::Match($body, $pattern, [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
    if (-not $match.Success) {
        throw "Authoritativní HRDR comment neobsahuje právě očekávaný fenced JSON objekt."
    }
    try {
        $record = $match.Groups["json"].Value | ConvertFrom-Json
    }
    catch {
        throw "Authoritativní HRDR JSON nelze parse: $($_.Exception.Message)"
    }
    return $record
}

function Format-DDDAHrdrComment {
    param(
        [Parameter(Mandatory = $true)][object]$Record,
        [string]$Heading = "DDDA Human Release Decision Record"
    )

    $json = ConvertTo-Json -InputObject $Record -Depth 30
    return @"
$script:DDDAHrdrMarker
## $Heading

> Automation may scaffold and validate this record. Only an explicit human action may change `decision` from `pending` to a release decision or alter accepted risks.

```json
$json
```
"@
}

function Set-DDDAHrdrComment {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
        [Parameter(Mandatory = $true)][int]$Pr,
        [Parameter(Mandatory = $true)][string]$Token,
        [Parameter(Mandatory = $true)][object]$Record
    )

    $existing = @(Get-DDDAHrdrComments -RepositorySlug $RepositorySlug -Pr $Pr -Token $Token)
    if ($existing.Count -gt 1) {
        throw "PR #$Pr obsahuje více než jeden authoritativní HRDR marker. Fail closed."
    }
    $body = Format-DDDAHrdrComment -Record $Record
    if ($existing.Count -eq 0) {
        return Invoke-DDDAGitHubApi -Method POST -Path "repos/$RepositorySlug/issues/$Pr/comments" -Token $Token -Body @{ body = $body }
    }
    $id = [int64]$existing[0].id
    return Invoke-DDDAGitHubApi -Method PATCH -Path "repos/$RepositorySlug/issues/comments/$id" -Token $Token -Body @{ body = $body }
}
