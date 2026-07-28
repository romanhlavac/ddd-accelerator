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
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$apiHeaders = @{
    Accept = "application/vnd.github+json"
    "User-Agent" = "DDDA-Governance-Bootstrap"
    "X-GitHub-Api-Version" = "2022-11-28"
}

function Test-DirectoryWritable {
    param([Parameter(Mandatory = $true)][string]$Path)

    try {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
        $probe = Join-Path $Path ".ddda-write-probe-$([Guid]::NewGuid().ToString('N'))"
        [System.IO.File]::WriteAllText($probe, "ok", $utf8NoBom)
        Remove-Item -LiteralPath $probe -Force
        return $true
    }
    catch {
        return $false
    }
}

function Resolve-UserWritableRoot {
    $currentPath = (Get-Location).Path
    $parentPath = Split-Path -Parent $currentPath
    $candidates = New-Object System.Collections.Generic.List[string]

    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $candidates.Add((Join-Path $env:LOCALAPPDATA "DDDA"))
    }
    if (-not [string]::IsNullOrWhiteSpace($parentPath)) {
        $candidates.Add((Join-Path $parentPath ".ddda-runtime"))
    }
    if (-not [string]::IsNullOrWhiteSpace($env:TEMP)) {
        $candidates.Add((Join-Path $env:TEMP "DDDA"))
    }

    foreach ($candidate in $candidates) {
        if (Test-DirectoryWritable -Path $candidate) {
            return $candidate
        }
    }

    throw "No user-writable runtime directory is available. Checked LOCALAPPDATA, the parent of the current directory, and TEMP."
}

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$AllowFailure
    )

    $output = & $Executable @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($output | ForEach-Object { "$_" }) -join "`n"

    if (($exitCode -ne 0) -and (-not $AllowFailure)) {
        throw "Command failed with exit code $exitCode:`n$Executable $($Arguments -join ' ')`n$text"
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Text = $text
    }
}

function Install-PortableGitHubCli {
    param([Parameter(Mandatory = $true)][string]$ToolRoot)

    $existing = Get-Command gh -ErrorAction SilentlyContinue
    if ($existing) {
        return $existing.Source
    }

    $architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
    $assetArchitecture = switch ($architecture) {
        "x64"   { "amd64" }
        "arm64" { "arm64" }
        "x86"   { "386" }
        default { throw "Unsupported Windows architecture for GitHub CLI: $architecture" }
    }

    Write-Host "GitHub CLI is not installed. Downloading the current portable official release..." -ForegroundColor Yellow

    $release = Invoke-RestMethod `
        -Uri "https://api.github.com/repos/cli/cli/releases/latest" `
        -Headers $apiHeaders `
        -Method Get

    $assetPattern = "^gh_[0-9]+\.[0-9]+\.[0-9]+_windows_$assetArchitecture\.zip$"
    $asset = @($release.assets | Where-Object { $_.name -match $assetPattern }) | Select-Object -First 1
    if (-not $asset) {
        throw "The latest GitHub CLI release does not contain a Windows $assetArchitecture ZIP asset."
    }

    $version = $release.tag_name.TrimStart("v")
    $versionRoot = Join-Path $ToolRoot "tools\gh\$version"
    $archivePath = Join-Path $ToolRoot "downloads\$($asset.name)"
    $downloadDirectory = Split-Path -Parent $archivePath

    New-Item -ItemType Directory -Force -Path $downloadDirectory | Out-Null
    New-Item -ItemType Directory -Force -Path $versionRoot | Out-Null

    $existingPortable = Get-ChildItem -LiteralPath $versionRoot -Filter "gh.exe" -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $existingPortable) {
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $archivePath -Headers @{ "User-Agent" = "DDDA-Governance-Bootstrap" }
        Expand-Archive -LiteralPath $archivePath -DestinationPath $versionRoot -Force
        $existingPortable = Get-ChildItem -LiteralPath $versionRoot -Filter "gh.exe" -Recurse -File | Select-Object -First 1
    }

    if (-not $existingPortable) {
        throw "Portable GitHub CLI was downloaded but gh.exe was not found under $versionRoot."
    }

    $ghDirectory = Split-Path -Parent $existingPortable.FullName
    if (($env:PATH -split ";") -notcontains $ghDirectory) {
        $env:PATH = "$ghDirectory;$env:PATH"
    }

    Write-Host "Portable GitHub CLI ready: $($existingPortable.FullName)" -ForegroundColor Green
    return $existingPortable.FullName
}

function Save-RepositoryFile {
    param(
        [Parameter(Mandatory = $true)][string]$GhPath,
        [Parameter(Mandatory = $true)][string]$RepositoryPath,
        [Parameter(Mandatory = $true)][string]$DestinationPath
    )

    $encodedRef = [Uri]::EscapeDataString($ref)
    $endpoint = "repos/$repository/contents/$RepositoryPath?ref=$encodedRef"
    $result = Invoke-NativeChecked -Executable $GhPath -Arguments @("api", $endpoint)
    $payload = $result.Text | ConvertFrom-Json

    if (-not $payload.content) {
        throw "GitHub returned no file content for '$RepositoryPath'."
    }

    $destinationDirectory = Split-Path -Parent $DestinationPath
    New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null

    $bytes = [Convert]::FromBase64String(($payload.content -replace "\s", ""))
    if ($bytes.Length -eq 0) {
        throw "Downloaded repository file '$RepositoryPath' is empty."
    }

    [System.IO.File]::WriteAllBytes($DestinationPath, $bytes)
}

$runtimeRoot = Resolve-UserWritableRoot
$workRoot = Join-Path $runtimeRoot "governance-runs\ddd-accelerator-governance-run-$timestamp"
$ghPath = Install-PortableGitHubCli -ToolRoot $runtimeRoot

Write-Host "Using GitHub CLI: $ghPath" -ForegroundColor Cyan
Write-Host (Invoke-NativeChecked -Executable $ghPath -Arguments @("--version")).Text

$auth = Invoke-NativeChecked -Executable $ghPath -Arguments @("auth", "status", "--hostname", "github.com") -AllowFailure
if ($auth.ExitCode -ne 0) {
    Write-Host "GitHub authentication is required. A browser login will start now." -ForegroundColor Yellow
    Invoke-NativeChecked -Executable $ghPath -Arguments @(
        "auth", "login",
        "--hostname", "github.com",
        "--git-protocol", "https",
        "--web"
    ) | Out-Null
}

Invoke-NativeChecked -Executable $ghPath -Arguments @("auth", "status", "--hostname", "github.com") | Out-Null

$projectProbe = Invoke-NativeChecked -Executable $ghPath -Arguments @(
    "project", "list",
    "--owner", $projectOwner,
    "--limit", "1",
    "--format", "json"
) -AllowFailure

if ($projectProbe.ExitCode -ne 0) {
    Write-Host "GitHub Projects authorization is missing or expired. A one-time browser authorization will start now." -ForegroundColor Yellow
    Invoke-NativeChecked -Executable $ghPath -Arguments @(
        "auth", "refresh",
        "--hostname", "github.com",
        "-s", "project"
    ) | Out-Null

    Invoke-NativeChecked -Executable $ghPath -Arguments @(
        "project", "list",
        "--owner", $projectOwner,
        "--limit", "1",
        "--format", "json"
    ) | Out-Null
}

New-Item -ItemType Directory -Force -Path $workRoot | Out-Null

$files = @(
    "scripts/platform/Apply-DDDAGitHubGovernance.ps1",
    "scripts/platform/Initialize-DDDAGitHubGovernance.ps1",
    "config/governance/github-bootstrap.json"
)

foreach ($repositoryPath in $files) {
    $destinationPath = Join-Path $workRoot ($repositoryPath -replace "/", "\")
    Save-RepositoryFile -GhPath $ghPath -RepositoryPath $repositoryPath -DestinationPath $destinationPath
}

Get-ChildItem -LiteralPath $workRoot -Recurse -File | Unblock-File -ErrorAction SilentlyContinue

$applyScript = Join-Path $workRoot "scripts\platform\Apply-DDDAGitHubGovernance.ps1"
if (-not (Test-Path -LiteralPath $applyScript -PathType Leaf)) {
    throw "Downloaded governance wrapper was not found: $applyScript"
}
if ((Get-Item -LiteralPath $applyScript).Length -eq 0) {
    throw "Downloaded governance wrapper is empty: $applyScript"
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
