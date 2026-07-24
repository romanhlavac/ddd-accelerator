[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$WorkspaceRoot,
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$RemoteUrl,
    [switch]$NoInitialCommit
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

$projectId = "life-insurance-greenfield"
$projectName = "Greenfield životní pojišťovna"
$platformRoot = (Resolve-Path $PlatformPath).Path
$workspaceFull = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$workspaceFile = Join-Path $workspaceFull "workspace.yaml"
$exampleRoot = Join-Path $platformRoot "examples/life-insurance-greenfield"
$projectRoot = Join-Path (Join-Path $workspaceFull "projects") $projectId

if (-not (Test-Path $workspaceFile)) {
    throw "Workspace není inicializován: $workspaceFile"
}
if (-not (Test-Path (Join-Path $exampleRoot "project.yaml"))) {
    throw "Referenční example nebyl nalezen: $exampleRoot"
}
if (Test-Path $projectRoot) {
    throw "Cílový example projekt již existuje: $projectRoot"
}

Assert-DDDACleanGitRepository -RepositoryPath $platformRoot -Label "Platformní"

$exampleManifest = Get-Content (Join-Path $exampleRoot "project.yaml") -Raw -Encoding UTF8
if ($exampleManifest -notmatch "(?m)^\s*id:\s*$([regex]::Escape($projectId))\s*$") {
    throw "Referenční example nemá očekávané project.id '$projectId'."
}

$newProjectArguments = @(
    "-WorkspaceRoot", $workspaceFull,
    "-ProjectId", $projectId,
    "-Name", $projectName,
    "-Type", "portfolio-program",
    "-TypeAlias", "greenfield-portfolio",
    "-NoInitialCommit"
)
if (-not [string]::IsNullOrWhiteSpace($RemoteUrl)) {
    $newProjectArguments += @("-RemoteUrl", $RemoteUrl)
}

Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/New-DDDAProject.ps1") -Arguments $newProjectArguments

try {
    Copy-Item -Path (Join-Path $exampleRoot "*") -Destination $projectRoot -Recurse -Force

    $mapPath = Join-Path $projectRoot "miro/miro-map.yaml"
    $mapText = Get-Content $mapPath -Raw -Encoding UTF8
    if ($mapText -notmatch "(?m)^board_id:\s*null\s*$") {
        throw "Referenční Miro mapping musí před prvním během obsahovat board_id: null."
    }

    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Test-DDDAInstallation.ps1") -Arguments @(
        "-PlatformPath", $platformRoot,
        "-WorkspaceRoot", $workspaceFull,
        "-ProjectPath", $projectRoot
    )

    if (-not $NoInitialCommit) {
        Invoke-DDDAGit -RepositoryPath $projectRoot -Arguments @("add", ".") | Out-Null
        try {
            Invoke-DDDAGit -RepositoryPath $projectRoot -Arguments @("commit", "-m", "chore: initialize DDDA reference example") | Out-Null
        }
        catch {
            throw "Example projekt byl vytvořen, ale první commit selhal. Ověř git config user.name a user.email. $($_.Exception.Message)"
        }
    }
}
catch {
    throw "Materializace referenčního example projektu selhala. Projekt zůstal pro diagnostiku v '$projectRoot'. $($_.Exception.Message)"
}

Write-Host ""
Write-Host "Referenční example projekt je připraven."
Write-Host "Project ID: $projectId"
Write-Host "Projekt:    $projectRoot"
Write-Host "Workspace:  $workspaceFull"
if ($NoInitialCommit) {
    Write-Host "Initial commit: přeskočen"
}
else {
    Write-Host "Initial commit: vytvořen"
}
