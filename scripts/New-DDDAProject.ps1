[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$WorkspaceRoot,
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)]
    [ValidateSet("portfolio-program", "greenfield-product", "legacy-modernization", "legacy-transformation", "integration-landscape", "purchased-product-adoption", "domain-discovery", "architecture-review", "operating-model-and-teams", "bounded-context-design")]
    [string]$Type,
    [ValidateSet("enterprise-transformation", "transformation-program", "greenfield-portfolio", "new-enterprise", "program-greenfield", "greenfield", "new-product", "modernization", "brownfield", "core-replacement", "business-transformation", "integration-review", "api-program", "cots", "saas-adoption", "package-implementation", "discovery", "strategic-ddd", "review", "architecture-assessment", "team-topologies", "org-design", "tactical-ddd", "bc-design")]
    [string]$TypeAlias,
    [string]$RemoteUrl,
    [switch]$NoInitialCommit
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Invoke-Git {
    param([Parameter(Mandatory = $true)][string]$RepositoryPath, [Parameter(Mandatory = $true)][string[]]$Arguments)
    $output = & git -C $RepositoryPath @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Git selhal v '$RepositoryPath': git $($Arguments -join ' ')`n$output" }
    return ($output | Out-String).Trim()
}
if ($ProjectId -notmatch '^[a-z0-9][a-z0-9-]{1,62}$') { throw "ProjectId musí být lowercase slug, například 'life-insurance-greenfield'." }
$workspaceFull = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$workspaceFile = Join-Path $workspaceFull "workspace.yaml"
$codeWorkspaceFile = Join-Path $workspaceFull "DDDA.code-workspace"
if (-not (Test-Path $workspaceFile)) { throw "Nenalezen workspace.yaml. Nejprve spusť Initialize-DDDAWorkspace.ps1." }
$workspaceText = Get-Content $workspaceFile -Raw -Encoding UTF8
$escapedProjectId = [regex]::Escape($ProjectId)
if ($workspaceText -match "(?m)^\s*-\s+id:\s*$escapedProjectId\s*$") { throw "Projekt '$ProjectId' je již registrován ve workspace.yaml." }
$platformRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$platformCommit = Invoke-Git -RepositoryPath $platformRoot -Arguments @("rev-parse", "HEAD")
$platformRef = Invoke-Git -RepositoryPath $platformRoot -Arguments @("branch", "--show-current")
if ([string]::IsNullOrWhiteSpace($platformRef)) { $platformRef = "detached" }
$projectPath = Join-Path (Join-Path $workspaceFull "projects") $ProjectId
if (Test-Path $projectPath) { throw "Projektový adresář již existuje: $projectPath" }
New-Item -ItemType Directory -Force -Path $projectPath | Out-Null
$projectTemplate = Get-Content (Join-Path $platformRoot "templates/project/project.yaml") -Raw -Encoding UTF8
$escapedName = $Name.Replace('"', '\"')
$typeAliasYaml = if ([string]::IsNullOrWhiteSpace($TypeAlias)) { "null" } else { $TypeAlias }
$miroBoardEnv = (($ProjectId -replace '-', '_').ToUpperInvariant() + "_MIRO_BOARD_ID")
$projectManifest = $projectTemplate.Replace("__PROJECT_ID__", $ProjectId).Replace("__PROJECT_NAME__", $escapedName).Replace("__PROJECT_TYPE__", $Type).Replace("__PROJECT_TYPE_ALIAS__", $typeAliasYaml).Replace("__MIRO_BOARD_ID_ENV__", $miroBoardEnv)
Set-Content -Path (Join-Path $projectPath "project.yaml") -Value $projectManifest -Encoding UTF8
$lockTemplate = Get-Content (Join-Path $platformRoot "templates/project/ddda-lock.template.yaml") -Raw -Encoding UTF8
$lockContent = $lockTemplate.Replace("__PLATFORM_REF__", $platformRef).Replace("__PLATFORM_COMMIT__", $platformCommit).Replace("__LOCKED_AT__", (Get-Date).ToUniversalTime().ToString("o"))
Set-Content -Path (Join-Path $projectPath "ddda.lock.yaml") -Value $lockContent -Encoding UTF8
Copy-Item -Path (Join-Path $platformRoot "templates/project/gitignore.template") -Destination (Join-Path $projectPath ".gitignore")
$directories = @("ingestion", "artifacts", "decisions", "workshops", "workshops/prompts", "miro", "miro/conflicts", "reports", "reports/miro-sync", "exports", ".ddda")
foreach ($directory in $directories) {
    $path = Join-Path $projectPath $directory
    New-Item -ItemType Directory -Force -Path $path | Out-Null
    if ($directory -ne ".ddda") { Set-Content -Path (Join-Path $path ".gitkeep") -Value "" -Encoding UTF8 }
}
$mapTemplate = Get-Content (Join-Path $platformRoot "templates/project/miro-map.template.yaml") -Raw -Encoding UTF8
Set-Content -Path (Join-Path $projectPath "miro/miro-map.yaml") -Value $mapTemplate.Replace("__PROJECT_ID__", $ProjectId) -Encoding UTF8
$stateTemplate = Get-Content (Join-Path $platformRoot "templates/project/miro-sync-state.template.yaml") -Raw -Encoding UTF8
Set-Content -Path (Join-Path $projectPath "miro/sync-state.yaml") -Value $stateTemplate.Replace("__PROJECT_ID__", $ProjectId) -Encoding UTF8
$projectReadme = @"
# $Name

Projekt DDDA typu ``$Type``.

## Začátek práce přes chat

1. Otevři ``DDDA.code-workspace`` v Cursoru.
2. V chatu uveď: ``Scope: project; aktivní projekt: $ProjectId``.
3. Požádej o kontrolu ``project.yaml`` a návrh intake otázek.
4. Vlož zdroje do ``ingestion/`` a požádej o jejich katalogizaci bez domýšlení faktů.
5. Připrav Miro token do environment variable ``MIRO_ACCESS_TOKEN`` a board ID do ``$miroBoardEnv``.
6. Požádej chat o dry-run renderu boardu a poté o jeho vytvoření.

## Kanonické soubory

- ``project.yaml`` — konfigurace projektu a Miro integrace,
- ``ddda.lock.yaml`` — přesná verze platformy DDDA,
- ``ingestion/`` — zdrojové vstupy,
- ``artifacts/`` — verzované doménové a architektonické YAML artefakty,
- ``decisions/`` — ADR a rozhodovací záznamy,
- ``workshops/prompts/`` — schválené chatové a facilitační prompty,
- ``miro/`` — mapování, společná sync báze a konflikty,
- ``reports/miro-sync/`` — auditní reporty synchronizace.

Projektový repozitář nesmí obsahovat obecné změny platformy DDDA.
"@
Set-Content -Path (Join-Path $projectPath "README.md") -Value $projectReadme -Encoding UTF8
& git -C $projectPath init -b main 2>$null
if ($LASTEXITCODE -ne 0) {
    & git -C $projectPath init
    if ($LASTEXITCODE -ne 0) { throw "Nepodařilo se inicializovat Git repozitář projektu." }
    Invoke-Git -RepositoryPath $projectPath -Arguments @("checkout", "-b", "main") | Out-Null
}
if (-not [string]::IsNullOrWhiteSpace($RemoteUrl)) { Invoke-Git -RepositoryPath $projectPath -Arguments @("remote", "add", "origin", $RemoteUrl) | Out-Null }
if (-not $NoInitialCommit) {
    Invoke-Git -RepositoryPath $projectPath -Arguments @("add", ".") | Out-Null
    try { Invoke-Git -RepositoryPath $projectPath -Arguments @("commit", "-m", "chore: initialize DDDA project") | Out-Null }
    catch { throw "Projekt byl vytvořen, ale první commit selhal. Ověř git config user.name a user.email. $($_.Exception.Message)" }
}
$repositoryValue = if ([string]::IsNullOrWhiteSpace($RemoteUrl)) { "null" } else { "`"$RemoteUrl`"" }
$projectEntry = @"
  - id: $ProjectId
    path: projects/$ProjectId
    repository: $repositoryValue
    status: active
"@
if ($workspaceText -match "(?m)^projects:\s*\[\]\s*$") { $workspaceText = [regex]::Replace($workspaceText, "(?m)^projects:\s*\[\]\s*$", "projects:`r`n$projectEntry") }
elseif ($workspaceText -match "(?m)^projects:\s*$") { $workspaceText = $workspaceText.TrimEnd() + "`r`n" + $projectEntry }
else { throw "workspace.yaml nemá podporovaný blok 'projects'. Projekt byl vytvořen; registruj jej ručně." }
Set-Content -Path $workspaceFile -Value $workspaceText -Encoding UTF8
if (Test-Path $codeWorkspaceFile) {
    $codeWorkspace = Get-Content $codeWorkspaceFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $alreadyPresent = @($codeWorkspace.folders | Where-Object { $_.path -eq "projects/$ProjectId" -or $_.path -eq "projects\$ProjectId" }).Count -gt 0
    if (-not $alreadyPresent) {
        $folders = @($codeWorkspace.folders)
        $folders += [pscustomobject]@{ name = $Name; path = "projects/$ProjectId" }
        $codeWorkspace.folders = $folders
        $codeWorkspace | ConvertTo-Json -Depth 10 | Set-Content -Path $codeWorkspaceFile -Encoding UTF8
    }
}
Write-Host "Projekt vytvořen: $projectPath"
Write-Host "Git repozitář: samostatný"
Write-Host "DDDA commit: $platformCommit"
Write-Host "Miro board env: $miroBoardEnv"
if (-not [string]::IsNullOrWhiteSpace($RemoteUrl)) {
    Write-Host "Remote origin: $RemoteUrl"
    Write-Host "Push: git -C `"$projectPath`" push -u origin main"
}
