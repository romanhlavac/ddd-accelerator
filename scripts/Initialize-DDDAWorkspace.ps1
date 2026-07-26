[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot,

    [string]$WorkspaceId = "ddda-workspace",

    [string]$WorkspaceName = "DDDA Workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "platform/DDDAPlatformSupport.ps1")

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
$packageManifestPath = Join-Path $platformRoot "ddda-package.json"
$platformCommit = $null
$platformRef = $null
$repositoryName = "romanhlavac/ddd-accelerator"
$distribution = "git"

$gitDirectory = Join-Path $platformRoot ".git"
if (Test-Path -LiteralPath $gitDirectory) {
    $gitRoot = Get-DDDAPlatformGitRoot -Path $platformRoot
    if ($gitRoot -ne [System.IO.Path]::GetFullPath($platformRoot).TrimEnd('\', '/')) {
        throw "Skript musí být spuštěn z DDDA Git rootu. Očekáváno: $platformRoot; nalezeno: $gitRoot"
    }

    $platformCommit = Invoke-DDDAPlatformGit -Repository $platformRoot -Arguments @("rev-parse", "HEAD")
    $platformRef = Invoke-DDDAPlatformGit -Repository $platformRoot -Arguments @("branch", "--show-current")
    if ([string]::IsNullOrWhiteSpace($platformRef)) {
        $platformRef = "detached"
    }

    try {
        $remoteUrl = Get-DDDAPlatformRepositoryUrl -Repository $platformRoot
        $repositoryName = Get-DDDAPlatformRepositorySlug -RepositoryUrl $remoteUrl
    }
    catch {
        $repositoryName = "romanhlavac/ddd-accelerator"
    }
}
elseif (Test-Path -LiteralPath $packageManifestPath -PathType Leaf) {
    $packageManifest = Get-Content -LiteralPath $packageManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($packageManifest.schema_version -ne 1) {
        throw "Nepodporovaná verze package manifestu: $($packageManifest.schema_version)"
    }
    $platformCommit = [string]$packageManifest.source_commit
    $platformRef = "package:$($packageManifest.kind)/$($packageManifest.version)"
    $distribution = "package"
}
else {
    throw "PlatformPath není Git distribuce ani rozbalený DDDA package: $platformRoot"
}

$workspaceFull = [System.IO.Path]::GetFullPath($WorkspaceRoot)
New-Item -ItemType Directory -Force -Path $workspaceFull | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $workspaceFull "projects") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $workspaceFull ".ddda") | Out-Null

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
}
else {
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
}
else {
    Write-Host "Cursor workspace již existuje a nebyl přepsán: $codeWorkspaceFile"
}

Write-Host ""
Write-Host "DDDA workspace je připraven."
Write-Host "Platforma:  $platformRoot"
Write-Host "Distribuce: $distribution"
Write-Host "Commit:     $platformCommit"
Write-Host "Otevření:   cursor `"$codeWorkspaceFile`""
