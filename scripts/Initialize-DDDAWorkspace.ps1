[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot,

    [string]$WorkspaceId = "ddda-workspace",

    [string]$WorkspaceName = "DDDA Workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)][string]$RepositoryPath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $output = & git -C $RepositoryPath @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Git selhal v '$RepositoryPath': git $($Arguments -join ' ')`n$output"
    }
    return ($output | Out-String).Trim()
}

function Get-RelativePathPortable {
    param(
        [Parameter(Mandatory = $true)][string]$BasePath,
        [Parameter(Mandatory = $true)][string]$TargetPath
    )

    $baseFull = [System.IO.Path]::GetFullPath($BasePath).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
    $baseUri = [System.Uri]::new($baseFull)
    $targetUri = [System.Uri]::new($targetFull)
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace('/', [System.IO.Path]::DirectorySeparatorChar)
}

$platformRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$gitRoot = Invoke-Git -RepositoryPath $platformRoot -Arguments @("rev-parse", "--show-toplevel")

if ([System.IO.Path]::GetFullPath($gitRoot).TrimEnd('\', '/') -ne [System.IO.Path]::GetFullPath($platformRoot).TrimEnd('\', '/')) {
    throw "Skript musí být spuštěn z distribuce DDDA. Očekávaný Git root: $platformRoot, nalezeno: $gitRoot"
}

$workspaceFull = [System.IO.Path]::GetFullPath($WorkspaceRoot)
New-Item -ItemType Directory -Force -Path $workspaceFull | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $workspaceFull "projects") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $workspaceFull ".ddda") | Out-Null

$platformCommit = Invoke-Git -RepositoryPath $platformRoot -Arguments @("rev-parse", "HEAD")
$platformRef = Invoke-Git -RepositoryPath $platformRoot -Arguments @("branch", "--show-current")
if ([string]::IsNullOrWhiteSpace($platformRef)) {
    $platformRef = "detached"
}

$remoteUrl = ""
try {
    $remoteUrl = Invoke-Git -RepositoryPath $platformRoot -Arguments @("remote", "get-url", "origin")
} catch {
    $remoteUrl = "https://github.com/romanhlavac/ddd-accelerator.git"
}

$repositoryName = "romanhlavac/ddd-accelerator"
if ($remoteUrl -match "github\.com[:/](?<name>[^/]+/[^/.]+)(\.git)?$") {
    $repositoryName = $Matches["name"]
}

$platformRelative = Get-RelativePathPortable -BasePath $workspaceFull -TargetPath $platformRoot
$platformRelativeYaml = $platformRelative.Replace('\', '/')
$workspaceFile = Join-Path $workspaceFull "workspace.yaml"

if (-not (Test-Path $workspaceFile)) {
    $yaml = @"
workspace:
  id: $WorkspaceId
  name: "$WorkspaceName"
  schema_version: 1

platform:
  path: $platformRelativeYaml
  repository: $repositoryName
  ref: $platformRef
  commit: $platformCommit

projects: []
"@
    Set-Content -Path $workspaceFile -Value $yaml -Encoding UTF8
    Write-Host "Vytvořen registr: $workspaceFile"
} else {
    Write-Host "Registr již existuje a nebyl přepsán: $workspaceFile"
}

$codeWorkspaceFile = Join-Path $workspaceFull "DDDA.code-workspace"
if (-not (Test-Path $codeWorkspaceFile)) {
    $workspaceObject = [ordered]@{
        folders = @(
            [ordered]@{
                name = "DDDA Platform"
                path = $platformRelative
            }
        )
        settings = [ordered]@{
            "git.openRepositoryInParentFolders" = "always"
            "files.exclude" = [ordered]@{
                "**/.ddda/cache" = $true
                "**/.ddda/tmp" = $true
            }
        }
    }
    $workspaceObject | ConvertTo-Json -Depth 10 | Set-Content -Path $codeWorkspaceFile -Encoding UTF8
    Write-Host "Vytvořen Cursor workspace: $codeWorkspaceFile"
} else {
    Write-Host "Cursor workspace již existuje a nebyl přepsán: $codeWorkspaceFile"
}

Write-Host ""
Write-Host "DDDA workspace je připraven."
Write-Host "Platforma: $platformRoot"
Write-Host "Commit:    $platformCommit"
Write-Host "Otevření:  cursor `"$codeWorkspaceFile`""
