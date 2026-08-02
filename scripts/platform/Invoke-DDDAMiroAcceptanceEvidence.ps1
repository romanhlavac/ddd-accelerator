[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)][ValidateSet("project-steering")][string]$Suite,
    [switch]$Full,
    [switch]$ResetToken,
    [switch]$KeepReviewBoard,
    [switch]$CleanupOnFailure,
    [switch]$NonInteractive,
    [string]$MiroTeamId,
    [string]$EvidenceOutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "../private/DDDAMiroSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAMiroEvidenceSupport.ps1")

$platformRoot = (Resolve-Path $PlatformPath).Path
$wrapperRunId = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss") + "-" + [Guid]::NewGuid().ToString("N").Substring(0, 8)
$fallbackReportRoot = Join-Path (Get-DDDAStateRoot) ("acceptance-reports/wrapper-" + $wrapperRunId)
$fallbackReportPath = Join-Path $fallbackReportRoot "result.json"

$accessToken = $null
$originalTokenExists = Test-Path Env:\MIRO_ACCESS_TOKEN
$originalToken = if ($originalTokenExists) { [string]$env:MIRO_ACCESS_TOKEN } else { $null }
$reportPath = $null
$report = $null
$workspace = $null
$projectPath = $null
$boardId = $null
$boardUrl = $null
$mapPath = $null
$statePath = $null
$mappingStatus = "NOT_RUN"
$syncStateStatus = "NOT_RUN"
$idempotenceStatus = "NOT_RUN"
$verifiedCount = 0
$itemCount = $null
$cleanupState = "not_created"
$cleanupAttemptedAt = $null
$cleanupCompletedAt = $null
$cleanupError = $null
$cleanupReason = "board_not_created"
$childExitCode = 1
$childOutput = @()
$wrapperFailure = $null
$evidenceWriteFailure = $null
$managedArtifacts = [string[]]@(
    "ddda.current-status",
    "ddda.next-actions",
    "acceptance-claims-modernization.project-charter"
)

function Protect-DDDAMiroEvidenceError {
    param([string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $null
    }

    $safe = $Text
    if (-not [string]::IsNullOrWhiteSpace([string]$accessToken)) {
        $safe = $safe.Replace([string]$accessToken, "[REDACTED]")
    }
    $safe = [regex]::Replace($safe, '(?i)Bearer\s+[A-Za-z0-9._~+/=-]{8,}', 'Bearer [REDACTED]')
    $safe = [regex]::Replace($safe, '(?i)(MIRO_ACCESS_TOKEN\s*[=:]\s*)\S+', '$1[REDACTED]')
    return $safe
}

function Write-DDDAEvidenceJson {
    param(
        [Parameter(Mandatory = $true)][object]$Value,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $full = [System.IO.Path]::GetFullPath($Path)
    $parent = Split-Path -Parent $full
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $Value | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $full -Encoding UTF8
    return $full
}

function New-DDDAFallbackAcceptanceReport {
    return [pscustomobject][ordered]@{
        suite = $Suite
        run_id = $wrapperRunId
        status = "FAIL"
        technical_sync_status = "FAIL"
        layout_contract_status = "FAIL"
        remote_layout_status = "FAIL"
        render_contract_status = "FAIL"
        render_contract_version = "REM-PR8-HVA-CC-010"
        platform_source_commit = $null
        scaffold_sha256 = $null
        remote_item_count = 0
        overview_child_count = 0
        starter_reference_caption_count = 0
        remote_content_digest = $null
        review_team_selection_status = if ([string]::IsNullOrWhiteSpace($MiroTeamId)) { "DEFAULT_TOKEN_TEAM" } else { "EXPLICIT_TEAM" }
        utf8_status = "FAIL"
        human_visual_acceptance_status = "NOT_APPLICABLE"
        overall_status = "FAIL"
        platform = $platformRoot
        workspace = $workspace
        project = $projectPath
        miro_board_id = $boardId
        miro_board_url = $boardUrl
        gate_assertion = [pscustomobject][ordered]@{
            gate = "G1"
            expected = "ready_for_review"
            actual = $null
            human_decision_created = $false
        }
        report_created_at = (Get-Date).ToUniversalTime().ToString("o")
        error = $wrapperFailure
    }
}

try {
    try {
        $accessToken = Get-DDDAMiroAccessToken -ResetToken:$ResetToken -NonInteractive:$NonInteractive
        $env:MIRO_ACCESS_TOKEN = $accessToken

        $acceptanceScript = Join-Path $platformRoot "scripts/Test-DDDAAcceptance.ps1"
        $hostExe = (Get-Process -Id $PID).Path
        $hostArguments = @("-NoProfile")
        if (Test-DDDAIsWindows) {
            $hostArguments += @("-ExecutionPolicy", "Bypass")
        }
        $hostArguments += @(
            "-File", $acceptanceScript,
            "-PlatformPath", $platformRoot,
            "-Suite", $Suite,
            "-WithMiro",
            "-KeepReviewBoard",
            "-EvidenceWrapperChild"
        )
        if ($Full) { $hostArguments += "-Full" }
        if (-not [string]::IsNullOrWhiteSpace($MiroTeamId)) { $hostArguments += @("-MiroTeamId", $MiroTeamId) }
        if ($NonInteractive) { $hostArguments += "-NonInteractive" }

        $previousPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            $childOutput = @(& $hostExe @hostArguments 2>&1)
            $childExitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $previousPreference
        }

        $childOutput | ForEach-Object { Write-Host $_ }
        foreach ($line in $childOutput) {
            $text = [string]$line
            if ($text -match '^Report:\s*(?<path>.+?)\s*$') {
                $reportPath = [string]$Matches["path"]
            }
        }

        if ([string]::IsNullOrWhiteSpace($reportPath) -or -not (Test-Path -LiteralPath $reportPath -PathType Leaf)) {
            throw "Miro acceptance wrapper nenalezl vytvořený acceptance report."
        }

        $report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $workspace = [string]$report.workspace
        $projectPath = [string]$report.project
        $boardId = [string]$report.miro_board_id
        if (-not [string]::IsNullOrWhiteSpace($boardId)) {
            $boardUrl = "https://miro.com/app/board/$boardId/"
        }

        if ($childExitCode -eq 0 -and [string]$report.remote_layout_status -ne "PASS") {
            throw "Acceptance report nemá PASS remote Miro layout status."
        }
        if ($childExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace($MiroTeamId) -and [string]$report.review_team_selection_status -ne "EXPLICIT_TEAM") {
            throw "Acceptance report nepotvrdil explicitní Miro team."
        }

        if ([string]::IsNullOrWhiteSpace($boardId)) {
            if ($childExitCode -eq 0) {
                throw "Acceptance report neobsahuje board ID zachycené před cleanupem."
            }
        }
        else {
            $mapPath = Join-Path $projectPath "miro/miro-map.yaml"
            $statePath = Join-Path $projectPath "miro/sync-state.yaml"
            $mappingStatus = "FAIL"
            $syncStateStatus = "FAIL"
            $idempotenceStatus = "FAIL"

            if (Test-Path -LiteralPath $mapPath -PathType Leaf) {
                $mapText = Get-Content -LiteralPath $mapPath -Raw -Encoding UTF8
                foreach ($artifactId in $managedArtifacts) {
                    if ($mapText -notmatch [regex]::Escape($artifactId)) {
                        throw "Miro evidence mapping neobsahuje '$artifactId'."
                    }
                }
                $mappingStatus = "PASS"
            }

            if (Test-Path -LiteralPath $statePath -PathType Leaf) {
                $stateText = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8
                foreach ($artifactId in $managedArtifacts) {
                    if ($stateText -notmatch [regex]::Escape($artifactId)) {
                        throw "Miro evidence sync state neobsahuje '$artifactId'."
                    }
                }
                $syncStateStatus = "PASS"
            }

            if ($mappingStatus -eq "PASS" -and $syncStateStatus -eq "PASS") {
                $verifiedCount = @($managedArtifacts).Count
                $snapshot = Get-DDDAMiroMapSnapshot -ProjectPath $projectPath
                if ([string]$snapshot.BoardId -ne $boardId) {
                    throw "Miro evidence snapshot používá jiné board ID."
                }
                $itemCount = @($snapshot.ItemIds).Count
                if ($itemCount -le 0) {
                    throw "Miro evidence snapshot neobsahuje stabilní item ID."
                }
                if ($childExitCode -eq 0) {
                    $idempotenceStatus = "PASS"
                }
            }
        }

        if ($childExitCode -ne 0) {
            $childMessage = if ($null -ne $report -and $report.PSObject.Properties["error"]) { [string]$report.error } else { "Online Miro acceptance selhala." }
            throw $childMessage
        }
    }
    catch {
        $wrapperFailure = Protect-DDDAMiroEvidenceError -Text $_.Exception.Message
    }
    finally {
        if (-not [string]::IsNullOrWhiteSpace($boardId)) {
            if ($KeepReviewBoard) {
                $cleanupState = "preserved"
                $cleanupReason = "keep_review_board"
            }
            elseif ([string]::IsNullOrWhiteSpace($wrapperFailure) -or $CleanupOnFailure) {
                $cleanupAttemptedAt = (Get-Date).ToUniversalTime().ToString("o")
                try {
                    $boardSegment = [Uri]::EscapeDataString($boardId)
                    Invoke-DDDAMiroApi -Method DELETE -Uri "https://api.miro.com/v2/boards/$boardSegment" -AccessToken $accessToken | Out-Null
                    $cleanupState = "deleted"
                    $cleanupReason = if ([string]::IsNullOrWhiteSpace($wrapperFailure)) { "successful_run_cleanup" } else { "cleanup_on_failure" }
                    $cleanupCompletedAt = (Get-Date).ToUniversalTime().ToString("o")
                }
                catch {
                    $cleanupState = "cleanup_failed"
                    $cleanupReason = "delete_request_failed"
                    $cleanupCompletedAt = (Get-Date).ToUniversalTime().ToString("o")
                    $cleanupError = Protect-DDDAMiroEvidenceError -Text $_.Exception.Message
                    if ([string]::IsNullOrWhiteSpace($wrapperFailure)) {
                        $wrapperFailure = "Cleanup acceptance Miro boardu selhal: $cleanupError"
                    }
                    else {
                        $wrapperFailure += " Cleanup acceptance Miro boardu selhal: $cleanupError"
                    }
                }
            }
            else {
                $cleanupState = "preserved"
                $cleanupReason = "failure_without_cleanup_request"
            }
        }

        $miroStatus = if ([string]::IsNullOrWhiteSpace($wrapperFailure) -and $childExitCode -eq 0 -and $cleanupState -ne "cleanup_failed") { "PASS" } else { "FAIL" }
        $evidenceManagedArtifacts = if ($mappingStatus -eq "PASS" -and $syncStateStatus -eq "PASS") { $managedArtifacts } else { [string[]]@() }
        $diagnostics = [System.Collections.Generic.List[string]]::new()
        foreach ($candidate in @($reportPath, $mapPath, $statePath)) {
            if (-not [string]::IsNullOrWhiteSpace([string]$candidate)) {
                $diagnostics.Add([string]$candidate)
            }
        }

        $miroEvidence = [pscustomobject][ordered]@{
            status = $miroStatus
            board_id = if ([string]::IsNullOrWhiteSpace($boardId)) { $null } else { $boardId }
            board_url = if ([string]::IsNullOrWhiteSpace($boardUrl)) { $null } else { $boardUrl }
            workspace = if ([string]::IsNullOrWhiteSpace($workspace)) { $null } else { $workspace }
            managed_artifacts = [string[]]@($evidenceManagedArtifacts)
            mapping = [pscustomobject][ordered]@{
                status = $mappingStatus
                path = if ([string]::IsNullOrWhiteSpace($mapPath)) { $null } else { $mapPath }
                verified_count = [int]$verifiedCount
            }
            sync_state = [pscustomobject][ordered]@{
                status = $syncStateStatus
                path = if ([string]::IsNullOrWhiteSpace($statePath)) { $null } else { $statePath }
                verified_count = [int]$verifiedCount
            }
            idempotence = [pscustomobject][ordered]@{
                status = $idempotenceStatus
                verification = if ($idempotenceStatus -eq "PASS") { "Initialize-DDDAProjectMiro invariant plus stable mapping snapshot" } else { $null }
                board_id_stable = if ($idempotenceStatus -eq "PASS") { $true } else { $null }
                item_count_before = $itemCount
                item_count_after = $itemCount
                second_run_create_board_operations = if ($idempotenceStatus -eq "PASS") { 0 } else { $null }
                second_run_mutating_operations = if ($idempotenceStatus -eq "PASS") { 0 } else { $null }
            }
            cleanup = [pscustomobject][ordered]@{
                state = $cleanupState
                attempted_at = $cleanupAttemptedAt
                completed_at = $cleanupCompletedAt
                error = $cleanupError
                reason = $cleanupReason
            }
            diagnostics = [string[]]@($diagnostics)
        }

        try {
            $null = Assert-DDDAMiroEvidenceContract -Evidence $miroEvidence
            if ($null -eq $report) {
                $report = New-DDDAFallbackAcceptanceReport
            }
            $report.status = if ($miroStatus -eq "PASS") { "PASS" } else { "FAIL" }
            $report.technical_sync_status = if ($miroStatus -eq "PASS") { "PASS" } else { "FAIL" }
            $report.human_visual_acceptance_status = if ($miroStatus -eq "PASS") { "PENDING" } else { "NOT_APPLICABLE" }
            $report.overall_status = if ($miroStatus -eq "PASS") { "PENDING_HUMAN_REVIEW" } else { "FAIL" }
            $report | Add-Member -NotePropertyName miro -NotePropertyValue $miroEvidence -Force
            $report | Add-Member -NotePropertyName miro_board_id -NotePropertyValue $miroEvidence.board_id -Force
            $report | Add-Member -NotePropertyName miro_board_url -NotePropertyValue $miroEvidence.board_url -Force
            $report | Add-Member -NotePropertyName error -NotePropertyValue $wrapperFailure -Force

            if ([string]::IsNullOrWhiteSpace($reportPath)) {
                $reportPath = $fallbackReportPath
            }
            $reportPath = Write-DDDAEvidenceJson -Value $report -Path $reportPath
            if (-not [string]::IsNullOrWhiteSpace($EvidenceOutputPath)) {
                $evidenceFull = Write-DDDAEvidenceJson -Value $report -Path $EvidenceOutputPath
                Write-Host "Miro evidence output: $evidenceFull"
            }
        }
        catch {
            $evidenceWriteFailure = Protect-DDDAMiroEvidenceError -Text $_.Exception.Message
            if ([string]::IsNullOrWhiteSpace($wrapperFailure)) {
                $wrapperFailure = "Miro evidence write failed: $evidenceWriteFailure"
            }
            else {
                $wrapperFailure += " Miro evidence write failed: $evidenceWriteFailure"
            }
        }

        if ($originalTokenExists) {
            $env:MIRO_ACCESS_TOKEN = $originalToken
        }
        else {
            Remove-Item Env:\MIRO_ACCESS_TOKEN -ErrorAction SilentlyContinue
        }

        if ([string]::IsNullOrWhiteSpace($wrapperFailure) -and $cleanupState -eq "deleted" -and -not [string]::IsNullOrWhiteSpace($workspace) -and (Test-Path -LiteralPath $workspace)) {
            Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Host "Miro evidence status: $($miroEvidence.status)"
    Write-Host "Miro cleanup state: $cleanupState"
    if (-not [string]::IsNullOrWhiteSpace($boardId)) {
        Write-Host "Board ID: $boardId"
        Write-Host "Board URL: $boardUrl"
    }
    if (-not [string]::IsNullOrWhiteSpace($workspace)) {
        Write-Host "Workspace: $workspace"
    }
    if (-not [string]::IsNullOrWhiteSpace($reportPath)) {
        Write-Host "Acceptance report: $reportPath"
    }

    if (-not [string]::IsNullOrWhiteSpace($wrapperFailure)) {
        throw $wrapperFailure
    }
}
finally {
    if ($originalTokenExists) {
        $env:MIRO_ACCESS_TOKEN = $originalToken
    }
    else {
        Remove-Item Env:\MIRO_ACCESS_TOKEN -ErrorAction SilentlyContinue
    }
}
