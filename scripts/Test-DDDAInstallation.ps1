[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$WorkspaceRoot,
    [string]$ProjectPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$failures = [System.Collections.Generic.List[string]]::new()

function Add-Failure {
    param([string]$Message)
    $script:failures.Add($Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Add-Success {
    param([string]$Message)
    Write-Host "[ OK ] $Message" -ForegroundColor Green
}

$platformFull = [System.IO.Path]::GetFullPath($PlatformPath)

try {
    $gitRoot = (& git -C $platformFull rev-parse --show-toplevel 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw $gitRoot }
    Add-Success "Platformní Git repozitář: $gitRoot"
} catch {
    Add-Failure "PlatformPath není dostupný Git repozitář: $($_.Exception.Message)"
}

$requiredFiles = @(
    "README.md",
    "USAGE.md",
    "schemas/workspace.schema.json",
    "schemas/project.schema.json",
    "schemas/ddda-lock.schema.json",
    "templates/workspace/workspace.yaml",
    "templates/project/project.yaml",
    "templates/project/ddda-lock.template.yaml",
    "scripts/Initialize-DDDAWorkspace.ps1",
    "scripts/New-DDDAProject.ps1",
    "scripts/Test-DDDARepositoryScope.ps1",
    "scripts/Update-DDDAProject.ps1"
)

foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $platformFull $relativePath
    if (Test-Path $fullPath) {
        Add-Success "Soubor existuje: $relativePath"
    } else {
        Add-Failure "Chybí povinný soubor: $relativePath"
    }
}

Get-ChildItem -Path (Join-Path $platformFull "schemas") -Filter "*.json" -File -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Get-Content $_.FullName -Raw | ConvertFrom-Json | Out-Null
        Add-Success "JSON je syntakticky validní: $($_.Name)"
    } catch {
        Add-Failure "Neplatný JSON $($_.FullName): $($_.Exception.Message)"
    }
}

Get-ChildItem -Path (Join-Path $platformFull "scripts") -Filter "*.ps1" -File -ErrorAction SilentlyContinue | ForEach-Object {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
    if ($parseErrors.Count -eq 0) {
        Add-Success "PowerShell parser: $($_.Name)"
    } else {
        foreach ($parseError in $parseErrors) {
            Add-Failure "PowerShell chyba $($_.Name): $($parseError.Message)"
        }
    }
}

if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $workspaceFull = [System.IO.Path]::GetFullPath($WorkspaceRoot)
    foreach ($name in @("workspace.yaml", "DDDA.code-workspace", "projects")) {
        $path = Join-Path $workspaceFull $name
        if (Test-Path $path) {
            Add-Success "Workspace položka existuje: $path"
        } else {
            Add-Failure "Workspace položka chybí: $path"
        }
    }
}

if (-not [string]::IsNullOrWhiteSpace($ProjectPath)) {
    $projectFull = [System.IO.Path]::GetFullPath($ProjectPath)
    foreach ($name in @(".git", "project.yaml", "ddda.lock.yaml", "artifacts", "ingestion", "decisions")) {
        $path = Join-Path $projectFull $name
        if (Test-Path $path) {
            Add-Success "Projektová položka existuje: $path"
        } else {
            Add-Failure "Projektová položka chybí: $path"
        }
    }
}

Write-Host ""
if ($failures.Count -gt 0) {
    Write-Host "DDDA diagnostika selhala: $($failures.Count) problémů." -ForegroundColor Red
    exit 1
}

Write-Host "DDDA diagnostika proběhla úspěšně." -ForegroundColor Green
exit 0
