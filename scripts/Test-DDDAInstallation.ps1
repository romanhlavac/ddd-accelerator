[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$WorkspaceRoot,
    [string]$ProjectPath
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$failures = [System.Collections.Generic.List[string]]::new()
function Add-Failure { param([string]$Message) $script:failures.Add($Message); Write-Host "[FAIL] $Message" -ForegroundColor Red }
function Add-Success { param([string]$Message) Write-Host "[ OK ] $Message" -ForegroundColor Green }
$platformFull = [System.IO.Path]::GetFullPath($PlatformPath)
try {
    $gitRoot = (& git -C $platformFull rev-parse --show-toplevel 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw $gitRoot }
    Add-Success "Platformní Git repozitář: $gitRoot"
} catch { Add-Failure "PlatformPath není dostupný Git repozitář: $($_.Exception.Message)" }
$requiredFiles = @(
    "README.md", "USAGE.md", "docs/README.md",
    "docs/cookbooks/README.md", "docs/cookbooks/11-chat-first-pracovni-rezim.md", "docs/cookbooks/12-miro-troubleshooting.md",
    "docs/cookbooks/13-inicializace-po-clone.md", "docs/cookbooks/14-inicializace-ciloveho-miro-boardu.md",
    "docs/methodology/01-metodicky-tok-a-gates.md", "docs/methodology/02-typy-projektu-toky-use-cases.md",
    "docs/product/01-architektura-ddda.md", "docs/product/04-synchronizace.md", "docs/product/06-migrace-a-kompatibilita.md",
    "examples/life-insurance-greenfield/README.md", "examples/life-insurance-greenfield/project.yaml",
    "schemas/workspace.schema.json", "schemas/project.schema.json", "schemas/ddda-lock.schema.json",
    "schemas/miro-scaffold.schema.json", "schemas/managed-artifact.schema.json",
    "scaffolds/miro/strategic-ddd-method-board.yaml",
    "templates/workspace/workspace.yaml", "templates/project/project.yaml", "templates/project/ddda-lock.template.yaml",
    "templates/project/miro-map.template.yaml", "templates/project/miro-sync-state.template.yaml",
    "runtime/miro/pyproject.toml", "runtime/miro/ddda_miro/client.py", "runtime/miro/ddda_miro/sync.py",
    "scripts/Initialize-DDDAWorkspace.ps1", "scripts/New-DDDAProject.ps1", "scripts/Test-DDDARepositoryScope.ps1",
    "scripts/Update-DDDAProject.ps1", "scripts/Install-DDDAMiroRuntime.ps1", "scripts/Initialize-DDDAMiroBoard.ps1",
    "scripts/Invoke-DDDAMiroSync.ps1", "scripts/Start-DDDAMiroSyncWorker.ps1", "scripts/Test-DDDAMiroConfiguration.ps1",
    "scripts/Initialize-DDDAAfterClone.ps1", "scripts/Invoke-DDDAMiroSmokeTest.ps1", "scripts/Initialize-DDDAProjectMiro.ps1",
    "scripts/private/DDDAMiroSupport.ps1", "tests/powershell/Test-DDDAMiroAutomation.ps1"
)
foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $platformFull $relativePath
    if (Test-Path $fullPath) { Add-Success "Soubor existuje: $relativePath" }
    else { Add-Failure "Chybí povinný soubor: $relativePath" }
}
$rootDocs = @(Get-ChildItem -Path (Join-Path $platformFull "docs") -Filter "*.md" -File -ErrorAction SilentlyContinue)
if ($rootDocs.Count -eq 1 -and $rootDocs[0].Name -eq "README.md") { Add-Success "Kořen docs obsahuje pouze index README.md" }
else { Add-Failure "Kořen docs smí obsahovat pouze README.md; nalezeno: $($rootDocs.Name -join ', ')" }
Get-ChildItem -Path (Join-Path $platformFull "schemas") -Filter "*.json" -File -ErrorAction SilentlyContinue | ForEach-Object {
    try { Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null; Add-Success "JSON je syntakticky validní: $($_.Name)" }
    catch { Add-Failure "Neplatný JSON $($_.FullName): $($_.Exception.Message)" }
}
Get-ChildItem -Path (Join-Path $platformFull "scripts") -Filter "*.ps1" -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    $hasUtf8Bom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
    $relativeScript = $_.FullName.Substring($platformFull.Length).TrimStart('\', '/')
    if ($hasUtf8Bom) { Add-Success "UTF-8 BOM: $relativeScript" } else { Add-Failure "PowerShell skript nemá UTF-8 BOM: $relativeScript" }
    $tokens = $null; $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
    if ($parseErrors.Count -eq 0) { Add-Success "PowerShell parser: $relativeScript" }
    else { foreach ($parseError in $parseErrors) { Add-Failure "PowerShell chyba $relativeScript: $($parseError.Message)" } }
}
if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $workspaceFull = [System.IO.Path]::GetFullPath($WorkspaceRoot)
    foreach ($name in @("workspace.yaml", "DDDA.code-workspace", "projects")) {
        $path = Join-Path $workspaceFull $name
        if (Test-Path $path) { Add-Success "Workspace položka existuje: $path" } else { Add-Failure "Workspace položka chybí: $path" }
    }
}
if (-not [string]::IsNullOrWhiteSpace($ProjectPath)) {
    $projectFull = [System.IO.Path]::GetFullPath($ProjectPath)
    foreach ($name in @(".git", "project.yaml", "ddda.lock.yaml", "artifacts", "ingestion", "decisions", "workshops", "workshops/prompts", "miro", "miro/miro-map.yaml", "miro/sync-state.yaml", "miro/conflicts", "reports", "reports/miro-sync", "exports")) {
        $path = Join-Path $projectFull $name
        if (Test-Path $path) { Add-Success "Projektová položka existuje: $path" } else { Add-Failure "Projektová položka chybí: $path" }
    }
}
Write-Host ""
if ($failures.Count -gt 0) { Write-Host "DDDA diagnostika selhala: $($failures.Count) problémů." -ForegroundColor Red; exit 1 }
Write-Host "DDDA diagnostika proběhla úspěšně." -ForegroundColor Green
exit 0
