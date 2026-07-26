[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)][ValidateSet("candidate", "release")][string]$Kind,
    [Parameter(Mandatory = $true)][string]$Version,
    [string]$SourceRef = "HEAD",
    [string]$OutputPath,
    [switch]$Force,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")

$platformRoot = Get-DDDAPlatformGitRoot -Path $PlatformPath
if ($platformRoot -ne [System.IO.Path]::GetFullPath($PlatformPath).TrimEnd('\', '/')) {
    throw "PlatformPath musí být Git root DDDA platformy."
}
Assert-DDDAPlatformCleanGit -Repository $platformRoot

if ($Kind -eq "release") {
    Assert-DDDAPlatformSemanticVersion -Version $Version
}
elseif ([string]::IsNullOrWhiteSpace($Version)) {
    throw "Candidate version nesmí být prázdná."
}

$sourceCommit = Invoke-DDDAPlatformGit -Repository $platformRoot -Arguments @("rev-parse", "$SourceRef^{commit}")
$sourceBranch = Invoke-DDDAPlatformGit -Repository $platformRoot -Arguments @("rev-parse", "--abbrev-ref", $SourceRef)
if ($sourceBranch -eq "HEAD") {
    $sourceBranch = $null
}

$shortCommit = $sourceCommit.Substring(0, 12)
$safeVersion = $Version -replace '[^0-9A-Za-z._-]', '-'
$packageId = "ddda-$Kind-$safeVersion-$shortCommit"
$stateRoot = Get-DDDAPlatformStateRoot
$packageRoot = Join-Path $stateRoot "packages"
New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $packageRoot ($packageId + ".zip")
}
$packagePath = [System.IO.Path]::GetFullPath($OutputPath)

if (Test-Path -LiteralPath $packagePath) {
    if (-not $Force) {
        throw "Package již existuje: $packagePath. Použij -Force pouze pro vědomé nahrazení stejného výstupu."
    }
    Remove-Item -LiteralPath $packagePath -Force
}

$parent = Split-Path -Parent $packagePath
New-Item -ItemType Directory -Path $parent -Force | Out-Null

Write-Host "=== DDDA platform package ==="
Write-Host "Kind:    $Kind"
Write-Host "Version: $Version"
Write-Host "Commit:  $sourceCommit"
Write-Host "Output:  $packagePath"

$null = Invoke-DDDAPlatformNative -Command "git" -Arguments @(
    "-C", $platformRoot,
    "archive",
    "--format=zip",
    "--output", $packagePath,
    $sourceCommit
)

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$manifest = [ordered]@{
    schema_version = 1
    package_id = $packageId
    kind = $Kind
    version = $Version
    source_commit = $sourceCommit
    source_ref = $sourceBranch
    created_at = Get-DDDAPlatformIsoTimestamp
}
$manifestJson = $manifest | ConvertTo-Json -Depth 10

$stream = [System.IO.File]::Open($packagePath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
try {
    $archive = New-Object System.IO.Compression.ZipArchive($stream, [System.IO.Compression.ZipArchiveMode]::Update, $false)
    try {
        $existing = $archive.GetEntry("ddda-package.json")
        if ($null -ne $existing) {
            $existing.Delete()
        }
        $entry = $archive.CreateEntry("ddda-package.json", [System.IO.Compression.CompressionLevel]::Optimal)
        $entryStream = $entry.Open()
        try {
            $writer = New-Object System.IO.StreamWriter($entryStream, (New-Object System.Text.UTF8Encoding($false)))
            try {
                $writer.Write($manifestJson)
                $writer.Write([Environment]::NewLine)
            }
            finally {
                $writer.Dispose()
            }
        }
        finally {
            $entryStream.Dispose()
        }
    }
    finally {
        $archive.Dispose()
    }
}
finally {
    $stream.Dispose()
}

$hash = Get-DDDAPlatformFileHash -Path $packagePath
$result = [ordered]@{
    package_id = $packageId
    kind = $Kind
    version = $Version
    source_commit = $sourceCommit
    source_ref = $sourceBranch
    path = $packagePath
    sha256 = $hash
}

if ($Json) {
    $result | ConvertTo-Json -Depth 10
}
else {
    Write-Host "Package SHA-256: $hash"
    Write-Host "DDDA platform package: PASS"
}
