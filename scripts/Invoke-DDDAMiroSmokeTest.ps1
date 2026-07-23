[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$ResetToken,
    [switch]$KeepArtifacts,
    [switch]$CleanupOnFailure,
    [switch]$Full,
    [switch]$NonInteractive,
    [switch]$SkipRuntimeInstall,
    [string]$ReportDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {
}

. (Join-Path $PSScriptRoot "private/DDDAMiroSupport.ps1")

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Name)
    $script:CurrentStep = $Name
    Write-Host ""
    Write-Host ("=== {0} ===" -f $Name)
}

function Add-TestResult {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Status,
        [string]$Detail = ""
    )

    $script:TestResults += [pscustomobject]@{ name = $Name; status = $Status; detail = $Detail }
    Write-Host ("{0}: {1}" -f $Name, $Status)
    if (-not [string]::IsNullOrWhiteSpace($Detail)) {
        Write-Host ("  {0}" -f $Detail)
    }
}

function Invoke-MiroCli {
    param([Parameter(Mandatory = $true)][string[]]$CommandArguments)

    $raw = & $script:MiroPython -m ddda_miro --project $script:ProjectRoot --platform $script:PlatformRoot @CommandArguments 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($raw | Out-String).Trim()

    if ($exitCode -ne 0) {
        throw ("DDDA Miro CLI selhalo: {0}`n{1}" -f ($CommandArguments -join " "), $text)
    }

    try {
        return ($text | ConvertFrom-Json)
    }
    catch {
        throw ("DDDA Miro CLI nevrátilo platný JSON.`nPříkaz: {0}`nVýstup:`n{1}" -f ($CommandArguments -join " "), $text)
    }
}

$originalTokenExists = Test-Path Env:\MIRO_ACCESS_TOKEN
$originalToken = $null
if ($originalTokenExists) {
    $originalToken = $env:MIRO_ACCESS_TOKEN
}

$runId = Get-Date -Format "yyyyMMdd-HHmmss"
$runShort = [Guid]::NewGuid().ToString("N").Substring(0, 8)
$script:TestResults = @()
$script:BoardId = $null
$script:WorkspaceRoot = $null
$script:ProjectRoot = $null
$script:PlatformRoot = $null
$script:MiroPython = $null
$script:AccessToken = $null
$script:CurrentStep = "Inicializace"
$success = $false
$failureMessage = $null
$failureStep = $null
$cleanupFailure = $null

$stateRoot = Get-DDDAStateRoot
if ([string]::IsNullOrWhiteSpace($ReportDirectory)) {
    $reportRoot = Join-Path $stateRoot ("smoke-reports/{0}-{1}" -f $runId, $runShort)
}
else {
    $reportRoot = [System.IO.Path]::GetFullPath($ReportDirectory)
}
$reportPath = Join-Path $reportRoot "result.json"

try {
    Write-Step "Platformní preflight"
    $script:PlatformRoot = (Resolve-Path $PlatformPath).Path
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"

    $gitRoot = Invoke-DDDAGit -RepositoryPath $script:PlatformRoot -Arguments @("rev-parse", "--show-toplevel")
    if ([System.IO.Path]::GetFullPath($gitRoot).TrimEnd('\', '/') -ne [System.IO.Path]::GetFullPath($script:PlatformRoot).TrimEnd('\', '/')) {
        throw "PlatformPath není Git root DDDA. Zadaná cesta: $($script:PlatformRoot); Git root: $gitRoot"
    }

    Assert-DDDACleanGitRepository -RepositoryPath $script:PlatformRoot -Label "Platformní"
    $branch = Invoke-DDDAGit -RepositoryPath $script:PlatformRoot -Arguments @("branch", "--show-current")
    if ([string]::IsNullOrWhiteSpace($branch)) {
        $branch = "detached"
    }
    Add-TestResult -Name "platform-preflight" -Status "PASS" -Detail ("branch={0}" -f $branch)

    Write-Step "Načtení nebo registrace Miro tokenu"
    $script:AccessToken = Get-DDDAMiroAccessToken -ResetToken:$ResetToken -NonInteractive:$NonInteractive
    $env:MIRO_ACCESS_TOKEN = $script:AccessToken
    $null = Assert-DDDAMiroTokenScopes -AccessToken $script:AccessToken
    Add-TestResult -Name "token-context" -Status "PASS" -Detail "scopes boards:read + boards:write"

    Write-Step "Vytvoření izolovaného workspace"
    $script:WorkspaceRoot = Join-Path $env:TEMP ("DDDA/smoke/{0}-{1}" -f $runId, $runShort)
    $projectId = "miro-smoke-$runShort"
    $projectName = "DDDA Miro Smoke $runShort"
    $script:ProjectRoot = Join-Path $script:WorkspaceRoot ("projects/{0}" -f $projectId)

    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $script:PlatformRoot "scripts/Initialize-DDDAWorkspace.ps1") -Arguments @(
        "-WorkspaceRoot", $script:WorkspaceRoot,
        "-WorkspaceId", ("smoke-{0}" -f $runShort),
        "-WorkspaceName", ("DDDA Miro Smoke {0}" -f $runShort)
    )

    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $script:PlatformRoot "scripts/New-DDDAProject.ps1") -Arguments @(
        "-WorkspaceRoot", $script:WorkspaceRoot,
        "-ProjectId", $projectId,
        "-Name", $projectName,
        "-Type", "domain-discovery",
        "-NoInitialCommit"
    )
    Add-TestResult -Name "workspace-bootstrap" -Status "PASS" -Detail $script:ProjectRoot

    Write-Step "Diagnostika instalace"
    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $script:PlatformRoot "scripts/Test-DDDAInstallation.ps1") -Arguments @(
        "-PlatformPath", $script:PlatformRoot,
        "-WorkspaceRoot", $script:WorkspaceRoot,
        "-ProjectPath", $script:ProjectRoot
    )
    Add-TestResult -Name "installation-doctor" -Status "PASS"

    Write-Step "Instalace Miro runtime"
    $pythonCommand = Resolve-DDDAPythonCommand
    if (-not $SkipRuntimeInstall) {
        Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $script:PlatformRoot "scripts/Install-DDDAMiroRuntime.ps1") -Arguments @(
            "-PlatformPath", $script:PlatformRoot,
            "-PythonCommand", $pythonCommand
        )
    }

    $script:MiroPython = Join-Path $script:PlatformRoot ".ddda/runtime/miro-venv/Scripts/python.exe"
    if (-not (Test-Path $script:MiroPython)) {
        throw "Miro Python runtime nebyl vytvořen: $($script:MiroPython)"
    }
    Add-TestResult -Name "runtime-installation" -Status "PASS" -Detail $script:MiroPython

    Write-Step "Offline doctor"
    $doctor = Invoke-MiroCli -CommandArguments @("doctor")
    if (-not (Get-DDDAObjectPropertyValue -InputObject $doctor -Name "scaffold_exists" -DefaultValue $false)) {
        throw "Offline doctor nenašel Miro scaffold."
    }
    if (-not (Get-DDDAObjectPropertyValue -InputObject $doctor -Name "token_present" -DefaultValue $false)) {
        throw "Offline doctor nevidí Miro token."
    }
    Add-TestResult -Name "offline-doctor" -Status "PASS"

    Write-Step "Renderer dry-run"
    $renderDry = Invoke-MiroCli -CommandArguments @("render", "--create-board", "--dry-run")
    $createBoardOps = @(
        (Get-DDDAObjectPropertyValue -InputObject $renderDry -Name "operations" -DefaultValue @()) |
            Where-Object { (Get-DDDAObjectPropertyValue -InputObject $_ -Name "action") -eq "create_board" }
    ).Count
    if ($createBoardOps -ne 1) {
        throw "Renderer dry-run neočekával přesně jednu create_board operaci. Počet: $createBoardOps"
    }
    Add-TestResult -Name "render-dry-run" -Status "PASS" -Detail ("operations={0}" -f (Get-DDDAObjectPropertyValue -InputObject $renderDry -Name "operation_count" -DefaultValue 0))

    Write-Step "Vytvoření Miro boardu"
    $render = Invoke-MiroCli -CommandArguments @("render", "--create-board")
    $script:BoardId = [string](Get-DDDAObjectPropertyValue -InputObject $render -Name "board_id")
    if ([string]::IsNullOrWhiteSpace($script:BoardId)) {
        throw "Renderer nevrátil board_id."
    }
    Add-TestResult -Name "render-board" -Status "PASS" -Detail ("board_id={0}" -f $script:BoardId)

    Write-Step "Online doctor"
    $onlineDoctor = Invoke-MiroCli -CommandArguments @("doctor", "--online")
    if (-not (Get-DDDAObjectPropertyValue -InputObject $onlineDoctor -Name "board")) {
        throw "Online doctor nevrátil board."
    }
    Add-TestResult -Name "online-doctor" -Status "PASS" -Detail ("board_id={0}" -f $script:BoardId)

    Write-Step "YAML -> Miro"
    $artifactDirectory = Join-Path $script:ProjectRoot "artifacts/discover/domain_event"
    New-Item -ItemType Directory -Path $artifactDirectory -Force | Out-Null
    $artifactPath = Join-Path $artifactDirectory "evt-smoke-policy-issued.yaml"
    Set-Content -Path $artifactPath -Encoding UTF8 -Value @(
        "artifact:",
        "  id: evt-smoke-policy-issued",
        "  type: domain_event",
        "  name: Testovací pojistná smlouva byla vydána",
        "  description: Automatický online smoke test.",
        "  status: candidate",
        "  stage: discover",
        "  miro:",
        "    item_type: sticky_note",
        "    frame_id: discover-big-picture-es"
    )

    $pushDry = Invoke-MiroCli -CommandArguments @("sync", "--direction", "push", "--dry-run")
    $pushCreateOps = @(
        (Get-DDDAObjectPropertyValue -InputObject $pushDry -Name "operations" -DefaultValue @()) |
            Where-Object {
                (Get-DDDAObjectPropertyValue -InputObject $_ -Name "action") -eq "push_create_miro" -and
                (Get-DDDAObjectPropertyValue -InputObject $_ -Name "artifact_id") -eq "evt-smoke-policy-issued"
            }
    ).Count
    if ($pushCreateOps -ne 1) {
        throw "Push dry-run neočekával jednu push_create_miro operaci. Počet: $pushCreateOps"
    }

    $push = Invoke-MiroCli -CommandArguments @("sync", "--direction", "push")
    if ((Get-DDDAObjectPropertyValue -InputObject $push -Name "conflict_count" -DefaultValue 0) -ne 0) {
        throw "Push vytvořil konflikt."
    }

    $eventMarker = "DDDA:${projectId}:evt-smoke-policy-issued"
    $eventItem = Find-DDDAMiroItemByMarker -BoardId $script:BoardId -Marker $eventMarker -AccessToken $script:AccessToken
    if (-not $eventItem) {
        throw "Na boardu nebyla nalezena sticky note s markerem $eventMarker"
    }
    Add-TestResult -Name "yaml-to-miro" -Status "PASS" -Detail ("item_id={0}" -f (Get-DDDAObjectPropertyValue -InputObject $eventItem -Name "id"))

    Write-Step "Miro -> YAML"
    $updatedContent = "<p><strong>Testovací pojistná smlouva byla úspěšně vydána</strong></p><p>Automatický online smoke test.</p><p>Typ: domain_event</p><p>Stav: candidate</p><p>Fáze: discover</p><p>$eventMarker</p>"
    $boardSegment = [Uri]::EscapeDataString([string]$script:BoardId)
    $eventItemId = [string](Get-DDDAObjectPropertyValue -InputObject $eventItem -Name "id")
    $eventItemSegment = [Uri]::EscapeDataString($eventItemId)
    $updateUri = "https://api.miro.com/v2/boards/$boardSegment/sticky_notes/$eventItemSegment"
    $null = Invoke-DDDAMiroApi -Method PATCH -Uri $updateUri -AccessToken $script:AccessToken -Body @{ data = @{ content = $updatedContent } }

    $pullDry = Invoke-MiroCli -CommandArguments @("sync", "--direction", "pull", "--dry-run")
    $pullUpdateOps = @(
        (Get-DDDAObjectPropertyValue -InputObject $pullDry -Name "operations" -DefaultValue @()) |
            Where-Object {
                (Get-DDDAObjectPropertyValue -InputObject $_ -Name "action") -eq "pull_update_yaml" -and
                (Get-DDDAObjectPropertyValue -InputObject $_ -Name "artifact_id") -eq "evt-smoke-policy-issued"
            }
    ).Count
    if ($pullUpdateOps -ne 1) {
        throw "Pull dry-run neočekával jednu pull_update_yaml operaci. Počet: $pullUpdateOps"
    }

    $pull = Invoke-MiroCli -CommandArguments @("sync", "--direction", "pull")
    if ((Get-DDDAObjectPropertyValue -InputObject $pull -Name "conflict_count" -DefaultValue 0) -ne 0) {
        throw "Pull vytvořil konflikt."
    }

    $artifactText = Get-Content $artifactPath -Raw -Encoding UTF8
    if ($artifactText -notmatch "Testovací pojistná smlouva byla úspěšně vydána") {
        throw "Změna z Mira se nepromítla do YAML."
    }
    Add-TestResult -Name "miro-to-yaml" -Status "PASS"

    Write-Step "PromoteNew"
    $hotspotMarker = "DDDA:${projectId}:hotspot-medical-evidence"
    $hotspotContent = "<p><strong>Nejasnost v underwriting procesu</strong></p><p>Je nutné vyjasnit, kdo schvaluje chybějící zdravotní podklady.</p><p>Typ: hotspot</p><p>Stav: candidate</p><p>Fáze: discover</p><p>$hotspotMarker</p>"
    $createStickyUri = "https://api.miro.com/v2/boards/$boardSegment/sticky_notes"
    $hotspotItem = Invoke-DDDAMiroApi -Method POST -Uri $createStickyUri -AccessToken $script:AccessToken -Body @{
        data = @{ content = $hotspotContent; shape = "rectangle" }
        style = @{ fillColor = "red" }
    }
    if (-not (Get-DDDAObjectPropertyValue -InputObject $hotspotItem -Name "id")) {
        throw "Miro API nevytvořilo promotion sticky note."
    }

    $promoteDry = Invoke-MiroCli -CommandArguments @("sync", "--direction", "pull", "--promote-new", "--dry-run")
    $promoteOps = @(
        (Get-DDDAObjectPropertyValue -InputObject $promoteDry -Name "operations" -DefaultValue @()) |
            Where-Object {
                (Get-DDDAObjectPropertyValue -InputObject $_ -Name "action") -eq "pull_promote_yaml" -and
                (Get-DDDAObjectPropertyValue -InputObject $_ -Name "artifact_id") -eq "hotspot-medical-evidence"
            }
    ).Count
    if ($promoteOps -ne 1) {
        throw "Promotion dry-run neočekával jednu pull_promote_yaml operaci. Počet: $promoteOps"
    }

    $promote = Invoke-MiroCli -CommandArguments @("sync", "--direction", "pull", "--promote-new")
    if ((Get-DDDAObjectPropertyValue -InputObject $promote -Name "conflict_count" -DefaultValue 0) -ne 0) {
        throw "PromoteNew vytvořil konflikt."
    }

    $promotedPath = Join-Path $script:ProjectRoot "artifacts/discover/hotspot/hotspot-medical-evidence.yaml"
    if (-not (Test-Path $promotedPath)) {
        throw "PromoteNew nevytvořil očekávaný YAML: $promotedPath"
    }
    Add-TestResult -Name "promote-new" -Status "PASS" -Detail $promotedPath

    if ($Full) {
        Write-Step "Polling worker"
        $watchRaw = & $script:MiroPython -m ddda_miro --project $script:ProjectRoot --platform $script:PlatformRoot watch --interval-seconds 30 --max-cycles 2 2>&1
        $watchText = ($watchRaw | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) {
            throw "Polling worker selhal.`n$watchText"
        }
        Add-TestResult -Name "polling-worker" -Status "PASS" -Detail "2 cycles"
    }

    Write-Step "Idempotence"
    $idempotence = Invoke-MiroCli -CommandArguments @("sync", "--direction", "both", "--dry-run")
    $operationCount = Get-DDDAObjectPropertyValue -InputObject $idempotence -Name "operation_count" -DefaultValue 0
    $conflictCount = Get-DDDAObjectPropertyValue -InputObject $idempotence -Name "conflict_count" -DefaultValue 0
    if ($operationCount -ne 0) {
        throw "Idempotence selhala. operation_count=$operationCount"
    }
    if ($conflictCount -ne 0) {
        throw "Idempotence vytvořila konflikty. conflict_count=$conflictCount"
    }
    Add-TestResult -Name "idempotence" -Status "PASS" -Detail "operation_count=0; conflict_count=0"

    Write-Step "Kontrola platformního repozitáře"
    Assert-DDDACleanGitRepository -RepositoryPath $script:PlatformRoot -Label "Platformní"
    Add-TestResult -Name "platform-clean" -Status "PASS"
    $success = $true
}
catch {
    $failureStep = $script:CurrentStep
    $failureMessage = ("Krok '{0}' selhal. {1}" -f $failureStep, $_.Exception.Message)
    Add-TestResult -Name "smoke-test" -Status "FAIL" -Detail $failureMessage
}
finally {
    $script:CurrentStep = "Cleanup"
    Write-Host ""
    Write-Host "=== Cleanup ==="

    $shouldCleanup = (-not $KeepArtifacts) -and ($success -or $CleanupOnFailure)
    if ($shouldCleanup) {
        try {
            if ($script:BoardId -and $script:AccessToken) {
                $boardSegment = [Uri]::EscapeDataString([string]$script:BoardId)
                $deleteBoardUri = "https://api.miro.com/v2/boards/$boardSegment"
                $null = Invoke-DDDAMiroApi -Method DELETE -Uri $deleteBoardUri -AccessToken $script:AccessToken
                Write-Host "Testovací board byl odstraněn: $($script:BoardId)"
            }

            if ($script:WorkspaceRoot -and (Test-Path $script:WorkspaceRoot)) {
                Remove-Item $script:WorkspaceRoot -Recurse -Force
                Write-Host "Dočasný workspace byl odstraněn: $($script:WorkspaceRoot)"
            }
            Add-TestResult -Name "cleanup" -Status "PASS"
        }
        catch {
            $cleanupFailure = $_.Exception.Message
            if ($success) {
                $failureStep = "Cleanup"
                $failureMessage = "Cleanup selhal. $cleanupFailure"
            }
            $success = $false
            Add-TestResult -Name "cleanup" -Status "FAIL" -Detail $cleanupFailure
        }
    }
    elseif ($KeepArtifacts) {
        Write-Host "KeepArtifacts: board a workspace byly ponechány."
    }
    elseif (-not $success) {
        Write-Host "Test selhal; board a workspace byly ponechány pro diagnostiku."
    }

    New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
    $commit = $null
    if ($script:PlatformRoot) {
        try { $commit = Invoke-DDDAGit -RepositoryPath $script:PlatformRoot -Arguments @("rev-parse", "HEAD") } catch {}
    }

    $report = [ordered]@{
        schema_version = 1
        run_id = "$runId-$runShort"
        result = $(if ($success) { "passed" } else { "failed" })
        platform_path = $script:PlatformRoot
        platform_commit = $commit
        workspace_path = $script:WorkspaceRoot
        project_path = $script:ProjectRoot
        board_id = $script:BoardId
        keep_artifacts = [bool]$KeepArtifacts
        cleanup_on_failure = [bool]$CleanupOnFailure
        full = [bool]$Full
        failure_step = $failureStep
        failure = $failureMessage
        cleanup_failure = $cleanupFailure
        tests = $script:TestResults
        completed_at = (Get-Date).ToUniversalTime().ToString("o")
    }
    $report | ConvertTo-Json -Depth 20 | Set-Content -Path $reportPath -Encoding UTF8

    if ($originalTokenExists) {
        $env:MIRO_ACCESS_TOKEN = $originalToken
    }
    else {
        Remove-Item Env:\MIRO_ACCESS_TOKEN -ErrorAction SilentlyContinue
    }

    Write-Host ""
    Write-Host "Report: $reportPath"

    if ($success) {
        Write-Host ""
        Write-Host "DDDA Miro smoke test: PASS"
    }
    else {
        Write-Host ""
        Write-Host "DDDA Miro smoke test: FAIL"
        if ($script:BoardId -and -not $shouldCleanup) {
            Write-Host "Board ponechán: $($script:BoardId)"
        }
        if ($script:WorkspaceRoot -and -not $shouldCleanup) {
            Write-Host "Workspace ponechán: $($script:WorkspaceRoot)"
        }
        if ([string]::IsNullOrWhiteSpace($failureMessage)) {
            $failureMessage = "DDDA Miro smoke test selhal bez detailu."
        }
        throw $failureMessage
    }
}
