[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$platformRoot = (Resolve-Path $PlatformPath).Path
$workspaceRoot = Join-Path $env:TEMP ("ddda-steering-test-" + [Guid]::NewGuid().ToString("N"))
$projectRoot = Join-Path $workspaceRoot "projects/claims-modernization"
$intakeFile = Join-Path $workspaceRoot "claims-intake.yaml"

function Assert-True {
    param([Parameter(Mandatory = $true)][bool]$Condition, [Parameter(Mandatory = $true)][string]$Message)
    if (-not $Condition) { throw $Message }
}

function Invoke-TestGit {
    param(
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = @(& git -C $Repository @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($exitCode -ne 0) {
        throw "Git příkaz selhal: git -C $Repository $($Arguments -join ' ')`n$($output -join '`n')"
    }
    return (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
}

function Get-StatusFilesHash {
    param([Parameter(Mandatory = $true)][string]$ProjectRoot)

    $lines = foreach ($relative in @(
        "artifacts/status/current-status.yaml",
        "artifacts/status/next-actions.yaml",
        "reports/project-status.yaml"
    )) {
        $path = Join-Path $ProjectRoot $relative
        $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        "${relative}:${hash}"
    }
    return ($lines -join "`n")
}

try {
    New-Item -ItemType Directory -Force -Path $workspaceRoot | Out-Null
    @"
intake:
  schema_version: 1
  project_id: claims-modernization
  name: Claims modernization
  type: legacy-modernization
  business_problem: Vendor lock-in blokuje změny likvidace škod.
  decision_to_enable: Rozhodnout target boundaries a první migrační řez.
  goal: Převzít know-how a umožnit inkrementální modernizaci.
  scope:
    in:
      - claim intake
      - adjudication
    out:
      - pricing
  actors:
    - claim handler
    - customer
  constraints:
    - nepřerušit provoz
  assumptions:
    - existuje použitelný audit trail
  quality_attributes:
    - auditability
    - availability
  owners:
    business_owner: Head of Claims
    architecture_owner: Chief Architect
"@ | Set-Content -Path $intakeFile -Encoding UTF8

    & (Join-Path $platformRoot "scripts/Initialize-DDDAProjectFirstRun.ps1") -PlatformPath $platformRoot -WorkspaceRoot $workspaceRoot -IntakeFile $intakeFile -NoInitialCommit -NonInteractive
    if ($LASTEXITCODE -ne 0) { throw "Initialize-DDDAProjectFirstRun.ps1 selhal." }

    foreach ($relative in @(
        "project-intake.yaml",
        "project-profile.yaml",
        "lifecycle-tailoring.yaml",
        "artifacts/align/project-charter.yaml",
        "artifacts/status/current-status.yaml",
        "artifacts/status/next-actions.yaml",
        "decisions/gates/G1.yaml",
        ".ddda/session-context.yaml",
        ".ddda/agent-contract.yaml"
    )) {
        Assert-True -Condition (Test-Path (Join-Path $projectRoot $relative)) -Message "Chybí steering výstup: $relative"
    }

    $null = Invoke-TestGit -Repository $projectRoot -Arguments @("config", "core.autocrlf", "false")
    $null = Invoke-TestGit -Repository $projectRoot -Arguments @("config", "user.name", "DDDA Steering Test")
    $null = Invoke-TestGit -Repository $projectRoot -Arguments @("config", "user.email", "ddda-steering-test@example.invalid")
    $null = Invoke-TestGit -Repository $projectRoot -Arguments @("add", ".")
    $null = Invoke-TestGit -Repository $projectRoot -Arguments @("commit", "-m", "test: steering baseline")

    $beforeStatusRead = Get-StatusFilesHash -ProjectRoot $projectRoot
    $status = & (Join-Path $platformRoot "scripts/Get-DDDAProjectStatus.ps1") -PlatformPath $platformRoot -ProjectPath $projectRoot -Json | ConvertFrom-Json
    $afterStatusRead = Get-StatusFilesHash -ProjectRoot $projectRoot
    Assert-True -Condition ($beforeStatusRead -eq $afterStatusRead) -Message "Read-only status query změnila generované status soubory."
    Assert-True -Condition ($status.next_gate -eq "G1") -Message "Před gate review musí být další gate G1."
    $g1Before = @($status.gates | Where-Object { $_.gate -eq "G1" }) | Select-Object -First 1
    Assert-True -Condition ($g1Before.status -eq "ready_for_review") -Message "Automatizace smí připravit pouze ready_for_review."

    $spoofBlocked = $false
    try {
        & (Join-Path $platformRoot "scripts/Complete-DDDALifecycleStep.ps1") `
            -PlatformPath $platformRoot `
            -ProjectPath $projectRoot `
            -Gate G1 `
            -Outcome passed `
            -Reviewer "Acceptance runner" `
            -Approver "CI bot" `
            -DecisionOwner business_owner `
            -Scope "G1 test scope" `
            -HumanDecision
    }
    catch {
        $spoofBlocked = $_.Exception.Message -match "automatizační identita"
    }
    Assert-True -Condition $spoofBlocked -Message "Automatizační identita obešla human provenance guard."

    & (Join-Path $platformRoot "scripts/Complete-DDDALifecycleStep.ps1") `
        -PlatformPath $platformRoot `
        -ProjectPath $projectRoot `
        -Gate G1 `
        -Outcome passed `
        -Reviewer "Roman Reviewer" `
        -Approver "Roman Reviewer" `
        -DecisionOwner business_owner `
        -Scope "G1 project purpose, scope and decision ownership" `
        -HumanDecision `
        -Note "Evidence reviewed" `
        -Commit
    if ($LASTEXITCODE -ne 0) { throw "Gate G1 human review selhal." }

    $beforeStatusRead = Get-StatusFilesHash -ProjectRoot $projectRoot
    $statusAfter = & (Join-Path $platformRoot "scripts/Get-DDDAProjectStatus.ps1") -PlatformPath $platformRoot -ProjectPath $projectRoot -Json | ConvertFrom-Json
    $afterStatusRead = Get-StatusFilesHash -ProjectRoot $projectRoot
    Assert-True -Condition ($beforeStatusRead -eq $afterStatusRead) -Message "Read-only status query po gate review změnila generované status soubory."
    Assert-True -Condition ($statusAfter.next_gate -eq "G2") -Message "Po platném lidském G1 musí být další gate G2."
    Assert-True -Condition ($statusAfter.current_stage -eq "discover") -Message "Po platném lidském G1 musí být aktuální fáze discover."

    $g1Record = Get-Content -LiteralPath (Join-Path $projectRoot "decisions/gates/G1.yaml") -Raw -Encoding UTF8
    foreach ($requiredText in @(
        "provenance: human",
        "decision_owner: business_owner",
        "reviewer: Roman Reviewer",
        "approver: Roman Reviewer",
        "project_commit:",
        "artifact_hashes:"
    )) {
        Assert-True -Condition ($g1Record.Contains($requiredText)) -Message "G1 decision record neobsahuje '$requiredText'."
    }

    $projectStatus = Invoke-TestGit -Repository $projectRoot -Arguments @("status", "--short")
    Assert-True -Condition ([string]::IsNullOrWhiteSpace($projectStatus)) -Message "Projektový repozitář po gate commitu není čistý:`n$projectStatus"
    $platformStatus = Invoke-TestGit -Repository $platformRoot -Arguments @("status", "--short")
    Assert-True -Condition ([string]::IsNullOrWhiteSpace($platformStatus)) -Message "Platformní repozitář po steering testu není čistý:`n$platformStatus"
    Write-Host "DDDA project steering test: PASS"
}
finally {
    if (Test-Path $workspaceRoot) { Remove-Item -Path $workspaceRoot -Recurse -Force -ErrorAction SilentlyContinue }
}
