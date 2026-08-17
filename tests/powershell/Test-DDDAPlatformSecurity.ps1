[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PlatformPath "scripts/platform/DDDAPlatformSupport.ps1")

function Assert-True {
    param([bool]$Condition, [Parameter(Mandatory = $true)][string]$Message)
    if (-not $Condition) { throw $Message }
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-security-test-" + [Guid]::NewGuid().ToString("N"))
try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    $allowedRoot = Join-Path $tempRoot "allowed"
    New-Item -ItemType Directory -Path $allowedRoot -Force | Out-Null

    $inside = Join-Path $allowedRoot "child/file.txt"
    $resolvedInside = Assert-DDDAPlatformPathWithin -CandidatePath $inside -AllowedRoot $allowedRoot -Label "Test"
    Assert-True -Condition ($resolvedInside -eq [System.IO.Path]::GetFullPath($inside)) -Message "Povolená cesta nebyla přijata."

    $escaped = $false
    try {
        $null = Assert-DDDAPlatformPathWithin -CandidatePath (Join-Path $allowedRoot "../outside.txt") -AllowedRoot $allowedRoot -Label "Test"
    }
    catch {
        $escaped = $true
    }
    Assert-True -Condition $escaped -Message "Path escape musí být odmítnut."

    $invalidVersionRejected = $false
    try {
        Assert-DDDAPlatformSemanticVersion -Version "release-latest"
    }
    catch {
        $invalidVersionRejected = $true
    }
    Assert-True -Condition $invalidVersionRejected -Message "Neplatná release verze musí být odmítnuta."

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $maliciousZip = Join-Path $tempRoot "malicious.zip"
    $stream = [System.IO.File]::Open($maliciousZip, [System.IO.FileMode]::CreateNew)
    try {
        $archive = New-Object System.IO.Compression.ZipArchive($stream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
        try {
            foreach ($entryName in @("ddda.ps1", "README.md", "USAGE.md", "examples/minimal/manifest.yaml", ".git/config")) {
                $entry = $archive.CreateEntry($entryName)
                $writer = New-Object System.IO.StreamWriter($entry.Open(), (New-Object System.Text.UTF8Encoding($false)))
                try { $writer.Write("test") } finally { $writer.Dispose() }
            }
            $manifestEntry = $archive.CreateEntry("ddda-package.json")
            $manifestWriter = New-Object System.IO.StreamWriter($manifestEntry.Open(), (New-Object System.Text.UTF8Encoding($false)))
            try {
                $manifestWriter.Write('{"schema_version":1,"package_id":"test","kind":"candidate","version":"test","source_commit":"0000000000000000000000000000000000000000","source_ref":null,"created_at":"2026-07-26T00:00:00Z"}')
            }
            finally { $manifestWriter.Dispose() }
        }
        finally { $archive.Dispose() }
    }
    finally { $stream.Dispose() }

    $maliciousRejected = $false
    try {
        & (Join-Path $PlatformPath "scripts/platform/Test-DDDAPlatformPackage.ps1") -PackagePath $maliciousZip
        if ($LASTEXITCODE -ne 0) { throw "Rejected" }
    }
    catch {
        $maliciousRejected = $true
    }
    Assert-True -Condition $maliciousRejected -Message "Package obsahující .git musí být odmítnut."

    Write-Host "DDDA platform security and isolation tests: PASS"
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
