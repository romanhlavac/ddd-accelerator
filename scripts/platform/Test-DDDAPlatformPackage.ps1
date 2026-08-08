[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PackagePath,
    [string]$ExpectedCommit,
    [ValidateSet("candidate", "release")][string]$ExpectedKind,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")

$packageFull = (Resolve-Path -LiteralPath $PackagePath).Path
$failures = [System.Collections.Generic.List[string]]::new()

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$forbiddenPrefixes = @(
    ".git/",
    ".ddda/",
    ".tmp/",
    ".reports/",
    ".releases/",
    "dist/",
    "__pycache__/",
    ".pytest_cache/"
)
$forbiddenNames = @(
    ".env",
    "miro-access-token.xml",
    "credentials.json",
    "secrets.json"
)
$textExtensions = @(
    ".md", ".txt", ".ps1", ".py", ".json", ".yaml", ".yml", ".toml", ".xml", ".csv", ".mmd", ".cml"
)

$stream = [System.IO.File]::OpenRead($packageFull)
try {
    $archive = New-Object System.IO.Compression.ZipArchive($stream, [System.IO.Compression.ZipArchiveMode]::Read, $false)
    try {
        $entries = @($archive.Entries)
        if ($entries.Count -eq 0) {
            $failures.Add("Package je prázdný.")
        }

        $entryNames = @($entries | ForEach-Object { $_.FullName.Replace('\', '/') })
        foreach ($entryName in $entryNames) {
            $normalized = $entryName.TrimStart('/')
            foreach ($prefix in $forbiddenPrefixes) {
                if ($normalized.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase) -or $normalized.IndexOf("/$prefix", [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
                    $failures.Add("Package obsahuje zakázanou cestu: $entryName")
                    break
                }
            }

            $leaf = [System.IO.Path]::GetFileName($normalized)
            if ($forbiddenNames -contains $leaf.ToLowerInvariant()) {
                $failures.Add("Package obsahuje zakázaný soubor: $entryName")
            }
            if ($normalized.EndsWith(".pyc", [System.StringComparison]::OrdinalIgnoreCase) -or $normalized.EndsWith(".pyo", [System.StringComparison]::OrdinalIgnoreCase)) {
                $failures.Add("Package obsahuje Python cache: $entryName")
            }
        }

        foreach ($required in @("ddda.ps1", "README.md", "USAGE.md", "ddda-package.json", "examples/minimal/manifest.yaml")) {
            if ($entryNames -notcontains $required) {
                $failures.Add("Package neobsahuje povinný soubor: $required")
            }
        }

        $manifestEntry = $archive.GetEntry("ddda-package.json")
        $manifest = $null
        if ($null -ne $manifestEntry) {
            $reader = New-Object System.IO.StreamReader($manifestEntry.Open(), [System.Text.Encoding]::UTF8)
            try {
                $manifestText = $reader.ReadToEnd()
            }
            finally {
                $reader.Dispose()
            }
            try {
                $manifest = $manifestText | ConvertFrom-Json
            }
            catch {
                $failures.Add("ddda-package.json není platný JSON: $($_.Exception.Message)")
            }
        }

        if ($null -ne $manifest) {
            if ($manifest.schema_version -ne 1) {
                $failures.Add("Package manifest má nepodporovanou schema_version.")
            }
            if (-not [string]::IsNullOrWhiteSpace($ExpectedCommit) -and $manifest.source_commit -ne $ExpectedCommit) {
                $failures.Add("Package commit '$($manifest.source_commit)' neodpovídá očekávanému '$ExpectedCommit'.")
            }
            if (-not [string]::IsNullOrWhiteSpace($ExpectedKind) -and $manifest.kind -ne $ExpectedKind) {
                $failures.Add("Package kind '$($manifest.kind)' neodpovídá očekávanému '$ExpectedKind'.")
            }
        }

        foreach ($entry in $entries) {
            $extension = [System.IO.Path]::GetExtension($entry.FullName).ToLowerInvariant()
            if ($textExtensions -notcontains $extension) {
                continue
            }
            if ($entry.Length -gt 5MB) {
                continue
            }

            $reader = New-Object System.IO.StreamReader($entry.Open(), [System.Text.Encoding]::UTF8, $true)
            try {
                $text = $reader.ReadToEnd()
            }
            finally {
                $reader.Dispose()
            }

            if ($text -match '(?i)[A-Z]:\\Users\\[^\\\s]+\\') {
                $failures.Add("Package obsahuje uživatelskou absolutní Windows cestu: $($entry.FullName)")
            }
            if ($text -match '(?i)/(Users|home)/[^/\s]+/') {
                $failures.Add("Package obsahuje uživatelskou absolutní Unix cestu: $($entry.FullName)")
            }
            if ($text -match '(?i)MIRO_ACCESS_TOKEN\s*[:=]\s*["''][A-Za-z0-9._-]{20,}["'']') {
                $failures.Add("Package pravděpodobně obsahuje Miro secret: $($entry.FullName)")
            }
        }
    }
    finally {
        $archive.Dispose()
    }
}
finally {
    $stream.Dispose()
}

$result = [ordered]@{
    status = if ($failures.Count -eq 0) { "PASS" } else { "FAIL" }
    package = $packageFull
    sha256 = Get-DDDAPlatformFileHash -Path $packageFull
    failure_count = $failures.Count
    failures = @($failures)
}

if ($Json) {
    $result | ConvertTo-Json -Depth 10
}
else {
    if ($failures.Count -gt 0) {
        foreach ($failure in $failures) {
            Write-Host "[FAIL] $failure" -ForegroundColor Red
        }
        throw "DDDA platform package validation: FAIL ($($failures.Count) problémů)."
    }
    Write-Host "DDDA platform package validation: PASS"
    Write-Host "SHA-256: $($result.sha256)"
}
