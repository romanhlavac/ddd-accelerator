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

    $beforeStatusRead = Get-StatusFilesHash -ProjectRoot $projectRoot
    $status = & (Join-Path $platformRoot "scripts/Get-DDDAProjectStatus.ps1") -PlatformPath $platformRoot -ProjectPath $projectRoot -Json | ConvertFrom-Json
    $afterStatusRead = Get-StatusFilesHash -ProjectRoot $projectRoot
    Assert-True -Condition ($beforeStatusRead -eq $afterStatusRead) -Message "Read-only status query změnila generované status soubory."
    Assert-True -Condition ($status.next_gate -eq "G1") -Message "Před gate review musí být další gate G1."

    & (Join-Path $platformRoot "scripts/Complete-DDDALifecycleStep.ps1") -PlatformPath $platformRoot -ProjectPath $projectRoot -Gate G1 -Outcome passed -Reviewer "CI reviewer" -Note "Evidence reviewed"
    if ($LASTEXITCODE -ne 0) { throw "Gate G1 review selhal." }

    $beforeStatusRead = Get-StatusFilesHash -ProjectRoot $projectRoot
    $statusAfter = & (Join-Path $platformRoot "scripts/Get-DDDAProjectStatus.ps1") -PlatformPath $platformRoot -ProjectPath $projectRoot -Json | ConvertFrom-Json
    $afterStatusRead = Get-StatusFilesHash -ProjectRoot $projectRoot
    Assert-True -Condition ($beforeStatusRead -eq $afterStatusRead) -Message "Read-only status query po gate review změnila generované status soubory."
    Assert-True -Condition ($statusAfter.next_gate -eq "G2") -Message "Po G1 musí být další gate G2."
    Assert-True -Condition ($statusAfter.current_stage -eq "discover") -Message "Po G1 musí být aktuální fáze discover."

    $platformStatus = (& git -C $platformRoot status --short | Out-String).Trim()
    Assert-True -Condition ([string]::IsNullOrWhiteSpace($platformStatus)) -Message "Platformní repozitář po steering testu není čistý:`n$platformStatus"
    Write-Host "DDDA project steering test: PASS"
}
finally {
    if (Test-Path $workspaceRoot) { Remove-Item -Path $workspaceRoot -Recurse -Force -ErrorAction SilentlyContinue }
}
