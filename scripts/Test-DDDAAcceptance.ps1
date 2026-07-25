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
    param([string]$Status, [string]$ErrorMessage)
    $payload = [ordered]@{
        suite = $Suite
        run_id = $runId
        status = $Status
        platform = $platformRoot
        workspace = $workspaceRoot
        project = $projectRoot
        miro_board_id = $boardId
        report_created_at = (Get-Date).ToUniversalTime().ToString("o")
        error = $ErrorMessage
    }
    $payload | ConvertTo-Json -Depth 10 | Set-Content -Path $reportFile -Encoding UTF8
}

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

    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAProjectFirstRun.ps1") -Arguments @(
        "-PlatformPath", $platformRoot,
        "-WorkspaceRoot", $workspaceRoot,
        "-IntakeFile", $intakeFile,
        "-NonInteractive"
    )

    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Complete-DDDALifecycleStep.ps1") -Arguments @(
        "-PlatformPath", $platformRoot,
        "-ProjectPath", $projectRoot,
        "-Gate", "G1",
        "-Outcome", "passed",
        "-Reviewer", "Acceptance runner",
        "-Note", "Automated evidence review",
        "-Commit"
    )

    $env:GIT_AUTHOR_NAME = $oldAuthorName
    $env:GIT_AUTHOR_EMAIL = $oldAuthorEmail
    $env:GIT_COMMITTER_NAME = $oldCommitterName
    $env:GIT_COMMITTER_EMAIL = $oldCommitterEmail

    $status = Invoke-DDDASteeringJson -PlatformRoot $platformRoot -Arguments @(
        "status", "--platform-root", $platformRoot, "--project-root", $projectRoot
    )
    if ($status.current_stage -ne "discover" -or $status.next_gate -ne "G2") {
        throw "Steering acceptance očekávalo discover/G2, získalo $($status.current_stage)/$($status.next_gate)."
    }

    if ($WithMiro) {
        $miroArgs = @(
            "-PlatformPath", $platformRoot,
            "-WorkspaceRoot", $workspaceRoot,
            "-ProjectId", "acceptance-claims-modernization",
            "-CreateBoard"
        )
        if ($NonInteractive) { $miroArgs += "-NonInteractive" }
        Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAProjectMiro.ps1") -Arguments $miroArgs

        $mapText = Get-Content (Join-Path $projectRoot "miro/miro-map.yaml") -Raw -Encoding UTF8
        if ($mapText -notmatch '(?m)^board_id:\s*["'']?(?<id>[^\s"'']+)["'']?\s*$') {
            throw "Acceptance runner nenalezl board_id v miro-map.yaml."
        }
        $boardId = $Matches["id"]
        if ($mapText -notmatch 'ddda\.current-status' -or $mapText -notmatch 'ddda\.next-actions') {
            throw "Miro mapping neobsahuje status a next-actions artefakty."
        }
    }

    $passed = $true
    Write-AcceptanceReport -Status "PASS" -ErrorMessage $null
    Write-Host ""
    Write-Host "DDDA acceptance $Suite: PASS"
    Write-Host "Report: $reportFile"
}
catch {
    Write-AcceptanceReport -Status "FAIL" -ErrorMessage $_.Exception.Message
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
        Write-Host "Workspace: $workspaceRoot"
    }
}
