[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PlatformPath "scripts/platform/DDDAPlatformSupport.ps1")

$platformRoot = Get-DDDAPlatformGitRoot -Path $PlatformPath
if (Test-Path -LiteralPath (Join-Path $platformRoot "ddda-package.json")) {
    throw "Packaging reproducibility test musí běžet nad source repository, ne nad rozbaleným package."
}
Assert-DDDAPlatformCleanGit -Repository $platformRoot

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-packaging-test-" + [Guid]::NewGuid().ToString("N"))
$firstPackage = Join-Path $tempRoot "first.zip"
$secondPackage = Join-Path $tempRoot "second.zip"
$version = "test.reproducible"

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

    $firstText = & (Join-Path $platformRoot "scripts/platform/New-DDDAPlatformPackage.ps1") -PlatformPath $platformRoot -Kind candidate -Version $version -OutputPath $firstPackage -Json | Out-String
    if ($LASTEXITCODE -ne 0) { throw "První package build selhal." }
    $first = $firstText.Trim() | ConvertFrom-Json

    $secondText = & (Join-Path $platformRoot "scripts/platform/New-DDDAPlatformPackage.ps1") -PlatformPath $platformRoot -Kind candidate -Version $version -OutputPath $secondPackage -Json | Out-String
    if ($LASTEXITCODE -ne 0) { throw "Druhý package build selhal." }
    $second = $secondText.Trim() | ConvertFrom-Json

    if ($first.source_commit -ne $second.source_commit) {
        throw "Reproducibility test použil rozdílné source commits."
    }
    if ($first.sha256 -ne $second.sha256) {
        throw "Stejný source commit a verze vytvořily rozdílný package hash. První: $($first.sha256); druhý: $($second.sha256)"
    }

    & (Join-Path $platformRoot "scripts/platform/Test-DDDAPlatformPackage.ps1") -PackagePath $firstPackage -ExpectedCommit $first.source_commit -ExpectedKind candidate
    if ($LASTEXITCODE -ne 0) { throw "Validace reprodukovatelného package selhala." }

    Write-Host "DDDA platform package reproducibility: PASS"
    Write-Host "Source commit: $($first.source_commit)"
    Write-Host "SHA-256:      $($first.sha256)"
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
