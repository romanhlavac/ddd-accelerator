[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$platformRoot = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $PlatformPath).Path)
$runRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-runtime-isolation-" + [Guid]::NewGuid().ToString("N"))
$fakeRoot = Join-Path $runRoot "ambient"
$fakePackage = Join-Path $fakeRoot "ddda_miro"
$passEvidence = Join-Path $runRoot "pass.json"
$failEvidence = Join-Path $runRoot "fail.json"
$oldPythonPath = $env:PYTHONPATH

try {
    New-Item -ItemType Directory -Path $fakePackage -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $fakePackage "__init__.py") -Encoding UTF8 -Value ""
    Set-Content -LiteralPath (Join-Path $fakePackage "render.py") -Encoding UTF8 -Value @'
RENDER_CONTRACT_VERSION = "OLD-CONTAMINATED-RENDERER"
'@

    & (Join-Path $platformRoot "scripts/Initialize-DDDAAfterClone.ps1") -PlatformPath $platformRoot -NonInteractive
    if ($LASTEXITCODE -ne 0) {
        throw "Runtime initialization failed."
    }

    $renderPath = Join-Path $platformRoot "runtime/miro/ddda_miro/render.py"
    $renderText = Get-Content -LiteralPath $renderPath -Raw -Encoding UTF8
    if ($renderText -notmatch 'RENDER_CONTRACT_VERSION\s*=\s*"(?<version>[^"]+)"') {
        throw "Renderer contract was not found."
    }
    $expectedContract = [string]$Matches["version"]

    $packageManifestPath = Join-Path $platformRoot "ddda-package.json"
    if (Test-Path -LiteralPath $packageManifestPath -PathType Leaf) {
        $packageManifest = Get-Content -LiteralPath $packageManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $sourceCommit = [string]$packageManifest.source_commit
    }
    else {
        $sourceCommit = (& git -C $platformRoot rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0) {
            throw "Exact source SHA was not resolved from Git."
        }
    }
    if ($sourceCommit -notmatch '^[0-9a-f]{40}$') {
        throw "Exact source SHA has invalid format: '$sourceCommit'."
    }

    $scaffoldHash = (Get-FileHash -LiteralPath (Join-Path $platformRoot "scaffolds/miro/strategic-ddd-method-board.yaml") -Algorithm SHA256).Hash.ToLowerInvariant()

    $env:PYTHONPATH = $fakeRoot + [System.IO.Path]::PathSeparator + (Join-Path $platformRoot "runtime/miro")
    $json = & (Join-Path $platformRoot "scripts/platform/Assert-DDDAMiroRuntimeProvenance.ps1") `
        -PlatformPath $platformRoot `
        -ExpectedRenderContractVersion $expectedContract `
        -ExpectedSourceCommit $sourceCommit `
        -ExpectedScaffoldSha256 $scaffoldHash `
        -EvidencePath $passEvidence `
        -Json | Out-String
    if ($LASTEXITCODE -ne 0) {
        throw "Runtime provenance pass scenario failed."
    }
    $pass = $json.Trim() | ConvertFrom-Json
    if ($pass.status -ne "PASS") {
        throw "Runtime provenance did not return PASS."
    }
    if (-not [bool]$pass.inherited_pythonpath_present) {
        throw "Test did not prove an ambient PYTHONPATH was present."
    }
    $expectedPath = [System.IO.Path]::GetFullPath($renderPath)
    $comparison = if ($env:OS -eq "Windows_NT") {
        [System.StringComparison]::OrdinalIgnoreCase
    }
    else {
        [System.StringComparison]::Ordinal
    }
    if (-not [string]$pass.imported_module_path -or
        -not ([string]$pass.imported_module_path).Equals($expectedPath, $comparison)) {
        throw "Isolated runtime imported a module outside the platform root: $($pass.imported_module_path)"
    }

    $remoteWriteCount = 0
    $negativeFailed = $false
    try {
        & (Join-Path $platformRoot "scripts/platform/Assert-DDDAMiroRuntimeProvenance.ps1") `
            -PlatformPath $platformRoot `
            -ExpectedRenderContractVersion "INTENTIONALLY-WRONG" `
            -ExpectedSourceCommit $sourceCommit `
            -ExpectedScaffoldSha256 $scaffoldHash `
            -EvidencePath $failEvidence | Out-Null
        $remoteWriteCount++
    }
    catch {
        $negativeFailed = $true
    }
    if (-not $negativeFailed) {
        throw "Negative provenance scenario did not fail."
    }
    if ($remoteWriteCount -ne 0) {
        throw "A remote write sentinel was reached after provenance failure."
    }
    $failure = Get-Content -LiteralPath $failEvidence -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($failure.status -ne "FAIL" -or -not [bool]$failure.checked_before_remote_write) {
        throw "Negative evidence is not fail-closed."
    }

    Write-Host "DDDA runtime isolation tests: PASS"
}
finally {
    if ($null -eq $oldPythonPath) {
        Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $oldPythonPath
    }
    if (Test-Path -LiteralPath $runRoot) {
        Remove-Item -LiteralPath $runRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
