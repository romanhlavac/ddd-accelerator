[CmdletBinding()]
param(
    [switch]$SkipViews,
    [switch]$DoNotOpenProject,
    [switch]$DoNotPublishReport
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repository = "romanhlavac/ddd-accelerator"
$ref = "feature/github-native-backlog-governance"
$projectOwner = "romanhlavac"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$currentPath = (Get-Location).Path
$parentPath = Split-Path -Parent $currentPath

if ([string]::IsNullOrWhiteSpace($parentPath)) {
    throw "Cannot determine the parent directory of the current location: $currentPath"
}

$workRoot = Join-Path $parentPath "ddd-accelerator-governance-run-$timestamp"
$encodedRef = [Uri]::EscapeDataString($ref)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not available on PATH."
    }
}

function Save-RepositoryFile {
    param(
        [Parameter(Mandatory = $true)][string]$RepositoryPath,
        [Parameter(Mandatory = $true)][string]$DestinationPath
    )

    $endpoint = "repos/$repository/contents/$RepositoryPath?ref=$encodedRef"
    $response = & gh api $endpoint 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download '$RepositoryPath' from '$ref'.`n$($response -join "`n")"
    }

    $payload = ($response -join "`n") | ConvertFrom-Json
    if (-not $payload.content) {
        throw "GitHub returned no file content for '$RepositoryPath'."
    }

    $destinationDirectory = Split-Path -Parent $DestinationPath
    New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null

    $bytes = [Convert]::FromBase64String(($payload.content -replace "\s", ""))
    [System.IO.File]::WriteAllBytes($DestinationPath, $bytes)
}

Assert-Command -Name "gh"

$authOutput = & gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI is not authenticated. Run 'gh auth login' and then rerun this block.`n$($authOutput -join "`n")"
}

$projectProbe = & gh project list --owner $projectOwner --limit 1 --format json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "GitHub Projects authorization is missing or expired. Starting one-time authorization..." -ForegroundColor Yellow
    & gh auth refresh -s project
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub Projects authorization failed."
    }
}

New-Item -ItemType Directory -Force -Path $workRoot | Out-Null

$files = @(
    "scripts/platform/Apply-DDDAGitHubGovernance.ps1",
    "scripts/platform/Initialize-DDDAGitHubGovernance.ps1",
    "config/governance/github-bootstrap.json"
)

foreach ($repositoryPath in $files) {
    $destinationPath = Join-Path $workRoot ($repositoryPath -replace "/", "\")
    Save-RepositoryFile -RepositoryPath $repositoryPath -DestinationPath $destinationPath
}

Get-ChildItem -LiteralPath $workRoot -Recurse -File | Unblock-File -ErrorAction SilentlyContinue

$applyScript = Join-Path $workRoot "scripts\platform\Apply-DDDAGitHubGovernance.ps1"
if (-not (Test-Path -LiteralPath $applyScript -PathType Leaf)) {
    throw "Downloaded governance wrapper was not found: $applyScript"
}

Write-Host "Governance runtime prepared in:" -ForegroundColor Cyan
Write-Host $workRoot
Write-Host "The current repository checkout remains untouched." -ForegroundColor Cyan

Push-Location $workRoot
try {
    $arguments = @()
    if ($SkipViews) { $arguments += "-SkipViews" }
    if ($DoNotOpenProject) { $arguments += "-DoNotOpenProject" }
    if ($DoNotPublishReport) { $arguments += "-DoNotPublishReport" }

    & $applyScript @arguments
    if (-not $?) {
        throw "DDDA GitHub governance setup failed."
    }
}
finally {
    Pop-Location
}

Write-Host "Governance automation completed." -ForegroundColor Green
Write-Host "Working directory retained for evidence and diagnostics: $workRoot" -ForegroundColor Green
