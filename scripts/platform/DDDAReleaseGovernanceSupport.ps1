Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:DDDAHrdrMarker = "<!-- ddda:human-release-decision:v1 -->"
$script:DDDAHumanPrReviewMarker = "<!-- ddda:human-pr-review:v1 -->"

function Get-DDDACandidateValidationEvidence {
    param(
        [Parameter(Mandatory = $true)][int]$Pr,
        [Parameter(Mandatory = $true)][string]$HeadSha,
        [string]$ValidationReportPath,
        [string]$PackagePath
    )

    $hasReportPath = -not [string]::IsNullOrWhiteSpace($ValidationReportPath)
    $hasPackagePath = -not [string]::IsNullOrWhiteSpace($PackagePath)
    if ($hasReportPath -ne $hasPackagePath) {
        throw "Isolated candidate evidence vyžaduje současně -ValidationReportPath i -PackagePath."
    }

    $validationReports = @()
    if ($hasReportPath) {
        if (-not (Test-Path -LiteralPath $ValidationReportPath -PathType Leaf)) {
            throw "Validation report neexistuje: $ValidationReportPath"
        }
        if (-not (Test-Path -LiteralPath $PackagePath -PathType Leaf)) {
            throw "Canonical candidate package neexistuje: $PackagePath"
        }
        $validationReports = @((Get-Item -LiteralPath $ValidationReportPath))
    }
    else {
        $validationRoot = Join-Path (Get-DDDAPlatformStateRoot) ("validation-reports/pr-$Pr-$HeadSha")
        if (Test-Path -LiteralPath $validationRoot) {
            $validationReports = @(
                Get-ChildItem -LiteralPath $validationRoot -Filter "result.json" -File -Recurse -ErrorAction SilentlyContinue |
                    Sort-Object LastWriteTimeUtc -Descending
            )
        }
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
        $candidatePackagePath = if ($hasPackagePath) {
            (Resolve-Path -LiteralPath $PackagePath).Path
        }
        else {
            $reportedPath = [string]$candidateReport.package.path
            if ([System.IO.Path]::IsPathRooted($reportedPath)) {
                $reportedPath
            }
            else {
                Join-Path $candidate.Directory.FullName $reportedPath
            }
        }
        if (-not (Test-Path -LiteralPath $candidatePackagePath -PathType Leaf)) {
            continue
        }
        $actualHash = Get-DDDAPlatformFileHash -Path $candidatePackagePath
        if ($actualHash -ne [string]$candidateReport.package.sha256) {
            throw "Canonical candidate package hash neodpovídá validation reportu: $candidatePackagePath"
        }
        return [pscustomobject]@{
            ReportPath = $candidate.FullName
            Report = $candidateReport
            PackagePath = $candidatePackagePath
            PackageSha256 = $actualHash
            ArtifactName = if ($candidateReport.package.PSObject.Properties.Name -contains "artifact_name") { [string]$candidateReport.package.artifact_name } else { "" }
            WorkflowRunId = if ($candidateReport.package.PSObject.Properties.Name -contains "workflow_run_id") { [string]$candidateReport.package.workflow_run_id } else { "" }
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
        $response = Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/milestones?state=all&per_page=100&page=$page" -Token $Token
        $batch = @($response)
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
        $response = Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/issues?state=all&milestone=$([int]$milestone.number)&per_page=100&page=$page" -Token $Token
        $batch = @($response)
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
        $response = Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/issues/$Pr/comments?per_page=100&page=$page" -Token $Token
        $batch = @($response)
        foreach ($comment in $batch) {
            if ([string]$comment.body -like "*$script:DDDAHrdrMarker*") {
                $matches.Add($comment)
            }
        }
        if ($batch.Count -lt 100) { break }
    }
    return @($matches)
}

function Get-DDDAHumanPrReviewComments {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
        [Parameter(Mandatory = $true)][int]$Pr,
        [Parameter(Mandatory = $true)][string]$Token
    )

    $matches = [System.Collections.Generic.List[object]]::new()
    for ($page = 1; ; $page++) {
        # Invoke-RestMethod intentionally returns a JSON array as one pipeline
        # object. Assign it first and only then materialize its items; wrapping
        # the command directly in @() preserves a nested Object[] and causes
        # PowerShell member enumeration to concatenate all comment authors.
        $response = Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/issues/$Pr/comments?per_page=100&page=$page" -Token $Token
        $batch = @($response)
        foreach ($comment in $batch) {
            if ([string]$comment.body -like "*$script:DDDAHumanPrReviewMarker*") {
                $matches.Add($comment)
            }
        }
        if ($batch.Count -lt 100) { break }
    }
    return @($matches)
}

function Assert-DDDAHumanPrReviewCommentProvenance {
    param(
        [Parameter(Mandatory = $true)][object]$Comment,
        [Parameter(Mandatory = $true)][object]$Review
    )

    $users = @($Comment.user)
    if ($users.Count -ne 1) {
        throw "Human Review comment nemá právě jednu GitHub user identity."
    }

    $logins = @($users[0].login)
    if ($logins.Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$logins[0])) {
        throw "Human Review comment nemá právě jeden neprázdný canonical GitHub user.login."
    }
    $commentAuthor = [string]$logins[0]

    $authorTypes = @($users[0].type)
    if (
        $authorTypes.Count -ne 1 -or
        [string]::IsNullOrWhiteSpace([string]$authorTypes[0]) -or
        [string]$authorTypes[0] -eq "Bot" -or
        $commentAuthor -match '\[bot\]$'
    ) {
        throw "Human Review musí mít lidskou GitHub provenance."
    }

    $reviewers = @($Review.reviewer)
    if ($reviewers.Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$reviewers[0])) {
        throw "Human Review nemá právě jednoho neprázdného reviewer login."
    }
    if ([string]$reviewers[0] -ne $commentAuthor) {
        throw "Human Review reviewer '$([string]$reviewers[0])' neodpovídá human comment authorovi '$commentAuthor'."
    }

    return $commentAuthor
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

function ConvertFrom-DDDAHumanPrReviewComment {
    param([Parameter(Mandatory = $true)][object]$Comment)

    $body = [string]$Comment.body
    $pattern = '(?s)```json\s*(?<json>\{.*?\})\s*```'
    $match = [regex]::Match($body, $pattern, [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
    if (-not $match.Success) {
        throw "Authoritativní Human Review comment neobsahuje očekávaný fenced JSON objekt."
    }
    try {
        $record = $match.Groups["json"].Value | ConvertFrom-Json
    }
    catch {
        throw "Authoritativní Human Review JSON nelze parse: $($_.Exception.Message)"
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

> Automation may scaffold and validate this record. Only an explicit human action may change decision from pending to a release decision or alter accepted risks.

``````json
$json
``````
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
