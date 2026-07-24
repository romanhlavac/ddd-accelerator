[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {
}

$platformRoot = (Resolve-Path $PlatformPath).Path
$workspaceRoot = Join-Path $env:TEMP ("ddda-first-run-test-" + [Guid]::NewGuid().ToString("N"))
$projectRoot = Join-Path $workspaceRoot "projects/life-insurance-greenfield"

function Assert-True {
    param(
        [Parameter(Mandatory = $true)][bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

try {
    & (Join-Path $platformRoot "scripts/Initialize-DDDAFirstRun.ps1") -PlatformPath $platformRoot -WorkspaceRoot $workspaceRoot -NoInitialCommit -NonInteractive
    if ($LASTEXITCODE -ne 0) {
        throw "Initialize-DDDAFirstRun.ps1 selhal s exit code $LASTEXITCODE."
    }

    Assert-True -Condition (Test-Path (Join-Path $workspaceRoot "workspace.yaml")) -Message "Chybí workspace.yaml."
    Assert-True -Condition (Test-Path (Join-Path $workspaceRoot "DDDA.code-workspace")) -Message "Chybí DDDA.code-workspace."
    Assert-True -Condition (Test-Path (Join-Path $projectRoot ".git")) -Message "Example projekt není samostatný Git repozitář."
    Assert-True -Condition (Test-Path (Join-Path $projectRoot "ddda.lock.yaml")) -Message "Chybí ddda.lock.yaml."
    Assert-True -Condition (Test-Path (Join-Path $projectRoot "artifacts/align/project-charter.yaml")) -Message "Nebyl materializován project charter example."
    Assert-True -Condition (Test-Path (Join-Path $projectRoot "artifacts/connect/context-map.yaml")) -Message "Nebyl materializován context map example."
    Assert-True -Condition (Test-Path (Join-Path $projectRoot "artifacts/discover/events/policy-issued.yaml")) -Message "Nebyl materializován domain event example."
    Assert-True -Condition (Test-Path (Join-Path $projectRoot "ingestion/catalog.yaml")) -Message "Nebyl materializován ingestion katalog."
    Assert-True -Condition (Test-Path (Join-Path $projectRoot "workshops/prompts/01-intake.md")) -Message "Nebyl materializován intake prompt."

    $workspaceText = Get-Content (Join-Path $workspaceRoot "workspace.yaml") -Raw -Encoding UTF8
    Assert-True -Condition ($workspaceText -match "(?m)^\s*-\s+id:\s*life-insurance-greenfield\s*$") -Message "Example projekt není registrován ve workspace.yaml."

    $projectText = Get-Content (Join-Path $projectRoot "project.yaml") -Raw -Encoding UTF8
    Assert-True -Condition ($projectText -match "(?m)^\s*id:\s*life-insurance-greenfield\s*$") -Message "Example project.yaml má nesprávné project.id."
    Assert-True -Condition ($projectText -match "(?m)^\s*type:\s*portfolio-program\s*$") -Message "Example project.yaml má nesprávný typ."

    $mapText = Get-Content (Join-Path $projectRoot "miro/miro-map.yaml") -Raw -Encoding UTF8
    Assert-True -Condition ($mapText -match "(?m)^board_id:\s*null\s*$") -Message "Offline first run nesmí inicializovat Miro board."

    $platformStatus = (& git -C $platformRoot status --short | Out-String).Trim()
    Assert-True -Condition ([string]::IsNullOrWhiteSpace($platformStatus)) -Message "Platformní repozitář po first-run testu není čistý:`n$platformStatus"

    Write-Host "DDDA first-run automation test: PASS"
}
finally {
    if (Test-Path $workspaceRoot) {
        Remove-Item -Path $workspaceRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
