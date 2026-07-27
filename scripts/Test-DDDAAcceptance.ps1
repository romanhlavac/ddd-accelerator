[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [Parameter(Mandatory = $true)][ValidateSet("project-steering")][string]$Suite,
    [switch]$WithMiro,
    [switch]$Full,
    [switch]$ResetToken,
    [switch]$KeepReviewBoard,
    [switch]$CleanupOnFailure,
    [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {}

. (Join-Path $PSScriptRoot "private/DDDASteeringSupport.ps1")

$platformRoot = (Resolve-Path $PlatformPath).Path
$runId = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss") + "-" + [Guid]::NewGuid().ToString("N").Substring(0, 8)
$workspaceRoot = Join-Path (Get-DDDAStateRoot) ("acceptance/" + $runId)
$projectRoot = Join-Path $workspaceRoot "projects/acceptance-claims-modernization"
$intakeFile = Join-Path $workspaceRoot "acceptance-intake.yaml"
$reportRoot = Join-Path (Get-DDDAStateRoot) ("acceptance-reports/" + $runId)
$reportFile = Join-Path $reportRoot "result.json"
$boardId = $null
$accessToken = $null
$oldMiroToken = $env:MIRO_ACCESS_TOKEN
$passed = $false

New-Item -ItemType Directory -Force -Path $workspaceRoot, $reportRoot | Out-Null

function Write-AcceptanceReport {
    param([string]$Status, [string]$ErrorMessage, [string]$GateStatus)
    $payload = [ordered]@{
        suite = $Suite
        run_id = $runId
        status = $Status
        platform = $platformRoot
        workspace = $workspaceRoot
        project = $projectRoot
        miro_board_id = $boardId
        gate_assertion = [ordered]@{
            gate = "G1"
            expected = "ready_for_review"
            actual = $GateStatus
            human_decision_created = $false
        }
        report_created_at = (Get-Date).ToUniversalTime().ToString("o")
        error = $ErrorMessage
    }
    $payload | ConvertTo-Json -Depth 10 | Set-Content -Path $reportFile -Encoding UTF8
}

function Get-BoardIdFromMap {
    param([Parameter(Mandatory = $true)][string]$MapPath)

    if (-not (Test-Path -LiteralPath $MapPath)) {
        return $null
    }

    $text = Get-Content -LiteralPath $MapPath -Raw -Encoding UTF8
    if ($text -match '(?m)^board_id:\s*["'']?(?<id>[^\s"'']+)["'']?\s*$') {
        return [string]$Matches["id"]
    }
    return $null
}

$g1Status = $null
try {
    Write-Host "=== DDDA acceptance suite: $Suite ==="
    if ($WithMiro) {
        $accessToken = Get-DDDAMiroAccessToken -ResetToken:$ResetToken -NonInteractive:$NonInteractive
        $env:MIRO_ACCESS_TOKEN = $accessToken
    }
    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAAfterClone.ps1") -Arguments @("-PlatformPath", $platformRoot, "-NonInteractive")
    if ($WithMiro -and $Full) {
        $smokeArgs = @("-PlatformPath", $platformRoot, "-SkipRuntimeInstall", "-Full")
        if ($NonInteractive) { $smokeArgs += "-NonInteractive" }
        if ($CleanupOnFailure) { $smokeArgs += "-CleanupOnFailure" }
        Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Invoke-DDDAMiroSmokeTest.ps1") -Arguments $smokeArgs
    }

    @"
intake:
  schema_version: 1
  project_id: acceptance-claims-modernization
  name: Acceptance Claims Modernization
  type: legacy-modernization
  business_problem: Vendor lock-in zpomaluje změny a přesouvá znalost mimo organizaci.
  decision_to_enable: Potvrdit cílové doménové hranice a bezpečný první migrační řez.
  goal: Umožnit inkrementální modernizaci bez výpadku provozu.
  scope:
    in: [claim intake, adjudication]
    out: [pricing]
  actors: [claim handler, customer]
  constraints: [continuity of operations]
  assumptions: [audit trail is available]
  quality_attributes: [auditability, availability, recoverability]
  owners:
    business_owner: Acceptance Business Owner
    architecture_owner: Acceptance Architect
"@ | Set-Content -Path $intakeFile -Encoding UTF8

    $oldAuthorName = $env:GIT_AUTHOR_NAME
    $oldAuthorEmail = $env:GIT_AUTHOR_EMAIL
    $oldCommitterName = $env:GIT_COMMITTER_NAME
    $oldCommitterEmail = $env:GIT_COMMITTER_EMAIL
    $env:GIT_AUTHOR_NAME = "DDDA Acceptance"
    $env:GIT_AUTHOR_EMAIL = "ddda-acceptance@example.invalid"
    $env:GIT_COMMITTER_NAME = "DDDA Acceptance"
    $env:GIT_COMMITTER_EMAIL = "ddda-acceptance@example.invalid"
    try {
        Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAProjectFirstRun.ps1") -Arguments @(
            "-PlatformPath", $platformRoot,
            "-WorkspaceRoot", $workspaceRoot,
            "-IntakeFile", $intakeFile,
            "-NonInteractive"
        )
    }
    finally {
        $env:GIT_AUTHOR_NAME = $oldAuthorName
        $env:GIT_AUTHOR_EMAIL = $oldAuthorEmail
        $env:GIT_COMMITTER_NAME = $oldCommitterName
        $env:GIT_COMMITTER_EMAIL = $oldCommitterEmail
    }

    $statusText = & (Join-Path $platformRoot "scripts/Get-DDDAProjectStatus.ps1") -PlatformPath $platformRoot -ProjectPath $projectRoot -Json
    if ($LASTEXITCODE -ne 0) {
        throw "Read-only kontrola project statusu selhala."
    }
    $status = $statusText | ConvertFrom-Json
    if ($status.current_stage -ne "align" -or $status.next_gate -ne "G1") {
        throw "Steering acceptance očekával align/G1 bez lidského schválení, získal $($status.current_stage)/$($status.next_gate)."
    }
    $g1 = @($status.gates | Where-Object { $_.gate -eq "G1" }) | Select-Object -First 1
    $g1Status = if ($null -eq $g1) { $null } else { [string]$g1.status }
    if ($g1Status -ne "ready_for_review") {
        throw "Automatizace musí připravit G1 jako ready_for_review, získáno '$g1Status'."
    }

    $projectManifest = Get-Content -LiteralPath (Join-Path $projectRoot "project.yaml") -Raw -Encoding UTF8
    if ($projectManifest -match '(?ms)completed_gates:\s*\n\s*-\s*G1') {
        throw "Acceptance runner nesmí automaticky zapsat G1 do completed_gates."
    }
    $g1Record = Get-Content -LiteralPath (Join-Path $projectRoot "decisions/gates/G1.yaml") -Raw -Encoding UTF8
    if ($g1Record -match '(?m)^\s*status:\s*passed\s*$' -or $g1Record -match '(?m)^\s*provenance:\s*human\s*$') {
        throw "Acceptance runner nesmí vytvářet produkční lidské G1 rozhodnutí."
    }

    Assert-DDDACleanGitRepository -RepositoryPath $projectRoot -Label "Projektový po read-only status kontrole"

    if ($WithMiro) {
        $miroArgs = @(
            "-PlatformPath", $platformRoot,
            "-WorkspaceRoot", $workspaceRoot,
            "-ProjectId", "acceptance-claims-modernization",
            "-CreateBoard"
        )
        if ($NonInteractive) { $miroArgs += "-NonInteractive" }
        Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAProjectMiro.ps1") -Arguments $miroArgs

        $mapPath = Join-Path $projectRoot "miro/miro-map.yaml"
        $statePath = Join-Path $projectRoot "miro/sync-state.yaml"
        $mapText = Get-Content -LiteralPath $mapPath -Raw -Encoding UTF8
        $stateText = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8
        $boardId = Get-BoardIdFromMap -MapPath $mapPath
        if ([string]::IsNullOrWhiteSpace([string]$boardId)) {
            throw "Acceptance runner nenalezl board_id v miro-map.yaml."
        }

        foreach ($artifactId in @("ddda.current-status", "ddda.next-actions")) {
            $escapedArtifactId = [regex]::Escape($artifactId)
            if ($mapText -notmatch $escapedArtifactId) {
                throw "Miro mapping neobsahuje managed artifact '$artifactId'."
            }
            if ($stateText -notmatch $escapedArtifactId) {
                throw "Miro sync state neobsahuje managed artifact '$artifactId'."
            }
        }
    }

    $passed = $true
    Write-AcceptanceReport -Status "PASS" -ErrorMessage $null -GateStatus $g1Status
    Write-Host ""
    Write-Host "DDDA acceptance ${Suite}: PASS"
    Write-Host "Gate assertion: G1 ready_for_review; human decision not created"
    Write-Host "Report: $reportFile"
}
catch {
    if ([string]::IsNullOrWhiteSpace([string]$boardId)) {
        $candidateMapPath = Join-Path $projectRoot "miro/miro-map.yaml"
        $boardId = Get-BoardIdFromMap -MapPath $candidateMapPath
    }
    Write-AcceptanceReport -Status "FAIL" -ErrorMessage $_.Exception.Message -GateStatus $g1Status
    Write-Host "Acceptance workspace zachován pro diagnostiku: $workspaceRoot"
    Write-Host "Report: $reportFile"
    throw
}
finally {
    if ($WithMiro -and -not [string]::IsNullOrWhiteSpace([string]$boardId) -and -not $KeepReviewBoard -and ($passed -or $CleanupOnFailure)) {
        try {
            $boardSegment = [Uri]::EscapeDataString([string]$boardId)
            Invoke-DDDAMiroApi -Method DELETE -Uri "https://api.miro.com/v2/boards/$boardSegment" -AccessToken $accessToken | Out-Null
            $boardId = $null
        }
        catch {
            Write-Warning "Cleanup acceptance Miro boardu selhal: $($_.Exception.Message)"
        }
    }
    if ($null -eq $oldMiroToken) { Remove-Item Env:\MIRO_ACCESS_TOKEN -ErrorAction SilentlyContinue }
    else { $env:MIRO_ACCESS_TOKEN = $oldMiroToken }
    if ($passed -and -not $KeepReviewBoard -and (Test-Path $workspaceRoot)) {
        Remove-Item -Path $workspaceRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    elseif ($KeepReviewBoard -and $WithMiro) {
        Write-Host "Review board byl zachován. Board ID: $boardId"
        Write-Host "Board URL: https://miro.com/app/board/$boardId/"
        Write-Host "Workspace: $workspaceRoot"
    }
}
