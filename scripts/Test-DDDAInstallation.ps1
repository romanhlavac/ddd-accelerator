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
$packageManifestPath = Join-Path $platformFull "ddda-package.json"
if (Test-Path -LiteralPath $packageManifestPath -PathType Leaf) {
    try {
        $packageManifest = Get-Content -LiteralPath $packageManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($packageManifest.schema_version -ne 1) { throw "Nepodporovaná schema_version." }
        if ([string]::IsNullOrWhiteSpace([string]$packageManifest.source_commit)) { throw "Chybí source_commit." }
        Add-Success "Rozbalený DDDA package: $($packageManifest.package_id)"
    }
    catch { Add-Failure "Neplatný DDDA package manifest: $($_.Exception.Message)" }
}
elseif (Test-Path -LiteralPath (Join-Path $platformFull ".git")) {
    try {
        $gitRoot = (& git -C $platformFull rev-parse --show-toplevel 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) { throw $gitRoot }
        if ([System.IO.Path]::GetFullPath($gitRoot).TrimEnd('\', '/') -ne $platformFull.TrimEnd('\', '/')) {
            throw "Git root '$gitRoot' neodpovídá PlatformPath '$platformFull'."
        }
        Add-Success "Platformní Git repozitář: $gitRoot"
    }
    catch { Add-Failure "PlatformPath není dostupný DDDA Git root: $($_.Exception.Message)" }
}
else {
    Add-Failure "PlatformPath není Git distribuce ani rozbalený DDDA package: $platformFull"
}

$requiredFiles = @(
    "ddda.ps1", "README.md", "USAGE.md", "CHANGELOG.md", "docs/README.md",
    "docs/getting-started/01-clone-smoke-example.md", "docs/getting-started/02-testovani-pr8.md",
    "docs/capabilities/README.md", "docs/reference/capability-catalog.yaml", "docs/reference/cli.md", "docs/reference/contracts.md",
    "docs/cookbooks/README.md", "docs/cookbooks/11-chat-first-pracovni-rezim.md", "docs/cookbooks/12-miro-troubleshooting.md",
    "docs/cookbooks/13-inicializace-po-clone.md", "docs/cookbooks/14-inicializace-ciloveho-miro-boardu.md",
    "docs/cookbooks/15-prvni-spusteni-a-example-projekt.md", "docs/cookbooks/16-zalozeni-rizeneho-projektu.md", "docs/cookbooks/17-status-gates-a-dalsi-krok.md",
    "docs/methodology/01-metodicky-tok-a-gates.md", "docs/methodology/02-typy-projektu-toky-use-cases.md", "docs/methodology/05-rizeni-projektu-a-tailoring.md",
    "docs/product/01-architektura-ddda.md", "docs/product/04-synchronizace.md", "docs/product/06-migrace-a-kompatibilita.md",
    "docs/adr/0001-platform-development-lifecycle.md", "docs/adr/0002-project-steering-and-gate-semantics.md",
    "docs/migration/pr8-non-breaking-steering-extension.md", "docs/developer-guide/platform-development-lifecycle.md",
    "docs/developer-guide/testing-strategy.md", "docs/user-guide/validate-and-promote-pr.md",
    "knowledge/00-knowledge-index.md", "knowledge/01-operating-model.md", "knowledge/02-ddd-strategic-design.md", "knowledge/03-ddd-tactical-design.md",
    "knowledge/04-architecture-decision-making.md", "knowledge/05-quality-attributes.md", "knowledge/06-architecture-styles-and-tradeoffs.md",
    "knowledge/07-integration-and-data-ownership.md", "knowledge/08-modernization-and-migration.md", "knowledge/09-security-resilience-observability.md",
    "knowledge/10-team-topologies-and-governance.md", "knowledge/11-workshop-playbooks.md", "knowledge/12-output-templates.md",
    "config/steering/project-types.yaml", "config/steering/gates.yaml", "config/steering/journey-map.yaml", "config/steering/mode-policy.yaml", "config/steering/git-policy.yaml",
    "config/platform/development-policy.yaml",
    "examples/life-insurance-greenfield/README.md", "examples/life-insurance-greenfield/project.yaml",
    "examples/minimal/manifest.yaml", "examples/minimal/input/project-intake.yaml", "examples/minimal/input/domain-notes.md", "examples/minimal/expected-invariants.yaml",
    "schemas/workspace.schema.json", "schemas/project.schema.json", "schemas/ddda-lock.schema.json", "schemas/miro-scaffold.schema.json", "schemas/managed-artifact.schema.json",
    "schemas/project-intake.schema.json", "schemas/lifecycle-tailoring.schema.json", "schemas/gate-status.schema.json", "schemas/project-status.schema.json", "schemas/agent-contract.schema.json", "schemas/capability-catalog.schema.json",
    "schemas/ingestion-manifest.schema.json", "schemas/validation-report.schema.json", "schemas/package-manifest.schema.json",
    "scaffolds/miro/strategic-ddd-method-board.yaml",
    "templates/workspace/workspace.yaml", "templates/project/project.yaml", "templates/project/ddda-lock.template.yaml", "templates/project/project-intake.template.yaml",
    "templates/project/miro-map.template.yaml", "templates/project/miro-sync-state.template.yaml",
    "runtime/miro/pyproject.toml", "runtime/miro/ddda_miro/client.py", "runtime/miro/ddda_miro/sync.py",
    "runtime/steering/pyproject.toml", "runtime/steering/read_status.py", "runtime/steering/ddda_steering/engine.py", "runtime/steering/ddda_steering/cli.py",
    "runtime/platform/validate_repository.py", "runtime/platform/tests/test_validate_repository.py",
    "scripts/Initialize-DDDAWorkspace.ps1", "scripts/New-DDDAProject.ps1", "scripts/Test-DDDARepositoryScope.ps1",
    "scripts/Update-DDDAProject.ps1", "scripts/Install-DDDAMiroRuntime.ps1", "scripts/Install-DDDASteeringRuntime.ps1", "scripts/Initialize-DDDAMiroBoard.ps1",
    "scripts/Invoke-DDDAMiroSync.ps1", "scripts/Start-DDDAMiroSyncWorker.ps1", "scripts/Test-DDDAMiroConfiguration.ps1",
    "scripts/Initialize-DDDAAfterClone.ps1", "scripts/Invoke-DDDAMiroSmokeTest.ps1", "scripts/Initialize-DDDAProjectMiro.ps1",
    "scripts/New-DDDAExampleProject.ps1", "scripts/Initialize-DDDAFirstRun.ps1", "scripts/Initialize-DDDAProjectFirstRun.ps1",
    "scripts/Get-DDDAProjectStatus.ps1", "scripts/Test-DDDAGates.ps1", "scripts/Complete-DDDALifecycleStep.ps1", "scripts/Test-DDDAAcceptance.ps1",
    "scripts/private/DDDAMiroSupport.ps1", "scripts/private/DDDAGitStatus.ps1", "scripts/private/DDDASteeringSupport.ps1",
    "scripts/platform/DDDAPlatformSupport.ps1", "scripts/platform/New-DDDAPlatformPackage.ps1", "scripts/platform/Test-DDDAPlatformPackage.ps1",
    "scripts/platform/Invoke-DDDAExampleIngestion.ps1", "scripts/platform/New-DDDAValidationWorkspace.ps1", "scripts/platform/New-DDDAValidationReport.ps1",
    "scripts/platform/Invoke-DDDAPlatformTest.ps1", "scripts/platform/Invoke-DDDAValidatePr.ps1", "scripts/platform/Invoke-DDDAPromotePr.ps1",
    "tests/powershell/Test-DDDAMiroAutomation.ps1", "tests/powershell/Test-DDDAFirstRun.ps1", "tests/powershell/Test-DDDAProjectSteering.ps1",
    "tests/powershell/Test-DDDAPlatformLifecycle.ps1", "tests/powershell/Test-DDDAPlatformSecurity.ps1", "tests/powershell/Test-DDDAPlatformPackaging.ps1"
)

$missingRequiredFiles = @()
foreach ($relativePath in $requiredFiles) {
    if (-not (Test-Path (Join-Path $platformFull $relativePath))) { $missingRequiredFiles += $relativePath }
}
if ($missingRequiredFiles.Count -eq 0) { Add-Success "Povinné soubory: $($requiredFiles.Count)" }
else { foreach ($relativePath in $missingRequiredFiles) { Add-Failure "Chybí povinný soubor: $relativePath" } }

$scriptFiles = @(Get-ChildItem -Path (Join-Path $platformFull "scripts") -Filter "*.ps1" -File -Recurse -ErrorAction SilentlyContinue)
$scriptFiles += @(Get-ChildItem -Path (Join-Path $platformFull "tests/powershell") -Filter "*.ps1" -File -Recurse -ErrorAction SilentlyContinue)
$rootEntry = Join-Path $platformFull "ddda.ps1"
if (Test-Path -LiteralPath $rootEntry) { $scriptFiles += Get-Item -LiteralPath $rootEntry }
$scriptFiles = @($scriptFiles | Sort-Object FullName -Unique)
$scriptValidationFailuresBefore = $failures.Count
foreach ($scriptFile in $scriptFiles) {
    $relativeScript = $scriptFile.FullName.Substring($platformFull.Length).TrimStart('\', '/')
    $bytes = [System.IO.File]::ReadAllBytes($scriptFile.FullName)
    $hasUtf8Bom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
    if (-not $hasUtf8Bom) { Add-Failure "PowerShell skript nemá UTF-8 BOM: $relativeScript" }
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($scriptFile.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
    foreach ($parseError in @($parseErrors)) { Add-Failure "PowerShell chyba $relativeScript na řádku $($parseError.Extent.StartLineNumber): $($parseError.Message)" }
}
if ($failures.Count -eq $scriptValidationFailuresBefore) { Add-Success "PowerShell parser a UTF-8 BOM: $($scriptFiles.Count) skriptů" }

$rootDocs = @(Get-ChildItem -Path (Join-Path $platformFull "docs") -Filter "*.md" -File -ErrorAction SilentlyContinue)
if ($rootDocs.Count -eq 1 -and $rootDocs[0].Name -eq "README.md") { Add-Success "Kořen docs obsahuje pouze index README.md" }
else { Add-Failure "Kořen docs smí obsahovat pouze README.md; nalezeno: $($rootDocs.Name -join ', ')" }

$schemaFiles = @(Get-ChildItem -Path (Join-Path $platformFull "schemas") -Filter "*.json" -File -ErrorAction SilentlyContinue)
$schemaFailuresBefore = $failures.Count
foreach ($schemaFile in $schemaFiles) {
    try { Get-Content $schemaFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null }
    catch { Add-Failure "Neplatný JSON $($schemaFile.FullName): $($_.Exception.Message)" }
}
if ($failures.Count -eq $schemaFailuresBefore) { Add-Success "JSON schémata: $($schemaFiles.Count)" }

if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $workspaceFull = [System.IO.Path]::GetFullPath($WorkspaceRoot)
    foreach ($name in @("workspace.yaml", "DDDA.code-workspace", "projects")) {
        $path = Join-Path $workspaceFull $name
        if (Test-Path $path) { Add-Success "Workspace položka existuje: $path" }
        else { Add-Failure "Workspace položka chybí: $path" }
    }
}

if (-not [string]::IsNullOrWhiteSpace($ProjectPath)) {
    $projectFull = [System.IO.Path]::GetFullPath($ProjectPath)
    foreach ($name in @(".git", "project.yaml", "ddda.lock.yaml", "artifacts", "ingestion", "decisions", "workshops", "workshops/prompts", "miro", "miro/miro-map.yaml", "miro/sync-state.yaml", "miro/conflicts", "reports", "reports/miro-sync", "exports")) {
        $path = Join-Path $projectFull $name
        if (Test-Path $path) { Add-Success "Projektová položka existuje: $path" }
        else { Add-Failure "Projektová položka chybí: $path" }
    }
}

Write-Host ""
if ($failures.Count -gt 0) {
    Write-Host "DDDA diagnostika selhala: $($failures.Count) problémů." -ForegroundColor Red
    exit 1
}
Write-Host "DDDA diagnostika proběhla úspěšně." -ForegroundColor Green
exit 0
