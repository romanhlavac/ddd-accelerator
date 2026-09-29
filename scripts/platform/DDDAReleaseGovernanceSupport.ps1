Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:DDDAHrdrMarker = "<!-- ddda:human-release-decision:v1 -->"
$script:DDDAHumanPrReviewMarker = "<!-- ddda:human-pr-review:v1 -->"

function Test-DDDAControlledReleaseSourceBranch {
    param(
        [Parameter(Mandatory = $true)][string]$Branch,
        [Parameter(Mandatory = $true)][string]$Version
    )

    $canonicalBranch = "release/$Version-controlled-recovery-source"
    $pattern = '^' + [regex]::Escape($canonicalBranch) + '(?:-v(?:[2-9]|[1-9]\d+))?$'
    return [regex]::IsMatch(
        $Branch,
        $pattern,
        [System.Text.RegularExpressions.RegexOptions]::CultureInvariant
    )
}

function Get-DDDACandidateValidationEvidence {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
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

    $restoreAdapter = Join-Path $PSScriptRoot "Restore-DDDACandidateEvidence.py"
    if (-not (Test-Path -LiteralPath $restoreAdapter -PathType Leaf)) {
        throw "Shared candidate evidence restore adapter neexistuje: $restoreAdapter"
    }
    $python = Get-DDDAPlatformPythonCommand
    foreach ($candidate in $validationReports) {
        $adapterOutput = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-candidate-evidence-" + [guid]::NewGuid().ToString("N") + ".json")
        $adapterArguments = @(
            $restoreAdapter,
            "--validation-report", $candidate.FullName,
            "--repository", $RepositorySlug,
            "--pr", [string]$Pr,
            "--source-sha", $HeadSha,
            "--output", $adapterOutput
        )
        if ($hasPackagePath) {
            $adapterArguments += @("--candidate-package", (Resolve-Path -LiteralPath $PackagePath).Path)
        }
        $adapterError = $null
        try {
            Invoke-DDDAPlatformNative -Command $python -Arguments $adapterArguments | Out-Null
        }
        catch {
            $adapterError = $_.Exception.Message
        }
        if (-not (Test-Path -LiteralPath $adapterOutput -PathType Leaf)) {
            if ($null -ne $adapterError) { throw $adapterError }
            throw "Shared candidate evidence adapter nevytvořil rozhodnutí."
        }
        try {
            $restored = Get-Content -LiteralPath $adapterOutput -Raw -Encoding UTF8 | ConvertFrom-Json
        }
        finally {
            Remove-Item -LiteralPath $adapterOutput -Force -ErrorAction SilentlyContinue
        }
        if ([string]$restored.status -ne "PASS") {
            if ($hasPackagePath -or (@($restored.failures) -contains "CONTROLLED_CANDIDATE_PACKAGE_HASH_MISMATCH")) {
                throw "Candidate evidence adapter odmítl validation report/package: $(@($restored.failures) -join ', ')"
            }
            continue
        }
        $candidateReport = Get-Content -LiteralPath ([string]$restored.validation_report_path) -Raw -Encoding UTF8 | ConvertFrom-Json
        return [pscustomobject]@{
            ReportPath = [string]$restored.validation_report_path
            Report = $candidateReport
            PackagePath = [string]$restored.candidate_package_path
            PackageSha256 = [string]$restored.candidate_package_sha256
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
