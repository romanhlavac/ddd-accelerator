[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PlatformPath,
    [Parameter(Mandatory = $true)][string]$ExpectedRenderContractVersion,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{40}$')][string]$ExpectedSourceCommit,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedScaffoldSha256,
    [Parameter(Mandatory = $true)][string]$EvidencePath,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$platformRoot = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $PlatformPath).Path).TrimEnd('\', '/')
$pythonPath = if ($env:OS -eq "Windows_NT") {
    Join-Path $platformRoot ".ddda/runtime/miro-venv/Scripts/python.exe"
}
else {
    Join-Path $platformRoot ".ddda/runtime/miro-venv/bin/python"
}
$expectedModulePath = [System.IO.Path]::GetFullPath((Join-Path $platformRoot "runtime/miro/ddda_miro/render.py"))
$evidenceFullPath = [System.IO.Path]::GetFullPath($EvidencePath)
$evidenceRoot = Split-Path -Parent $evidenceFullPath
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

$evidence = [ordered]@{
    status = "FAIL"
    checked_before_remote_write = $true
    python_executable = $pythonPath
    sys_prefix = $null
    imported_module_path = $null
    expected_module_path = $expectedModulePath
    imported_module_sha256 = $null
    expected_module_sha256 = $null
    render_contract_version = $null
    expected_render_contract_version = $ExpectedRenderContractVersion
    canonical_guide_headings_present = $false
    source_commit = $ExpectedSourceCommit
    scaffold_sha256 = $ExpectedScaffoldSha256
    inherited_pythonpath_present = -not [string]::IsNullOrWhiteSpace($env:PYTHONPATH)
    isolated_mode = $true
    error = $null
    checked_at = (Get-Date).ToUniversalTime().ToString("o")
}

function Write-ProvenanceEvidence {
    param([Parameter(Mandatory = $true)]$Value)

    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $text = ConvertTo-Json -InputObject $Value -Depth 20
    [System.IO.File]::WriteAllText($evidenceFullPath, $text + [Environment]::NewLine, $utf8)
}

$environmentNames = @("PYTHONPATH", "PYTHONHOME", "DDDA_PLATFORM_ROOT", "DDDA_REPO_ROOT")
$savedEnvironment = @{}

try {
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "Candidate Miro Python runtime neexistuje: $pythonPath"
    }
    if (-not (Test-Path -LiteralPath $expectedModulePath -PathType Leaf)) {
        throw "Candidate render module neexistuje: $expectedModulePath"
    }

    $evidence.expected_module_sha256 = (Get-FileHash -LiteralPath $expectedModulePath -Algorithm SHA256).Hash.ToLowerInvariant()

    foreach ($name in $environmentNames) {
        $path = "Env:\$name"
        if (Test-Path -LiteralPath $path) {
            $savedEnvironment[$name] = [string](Get-Item -LiteralPath $path).Value
            Remove-Item -LiteralPath $path
        }
    }

    $probe = @'
import hashlib
import json
import pathlib
import sys
import ddda_miro.render as render

path = pathlib.Path(render.__file__).resolve()
payload = {
    "python_executable": str(pathlib.Path(sys.executable).resolve()),
    "sys_prefix": str(pathlib.Path(sys.prefix).resolve()),
    "imported_module_path": str(path),
    "imported_module_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    "render_contract_version": getattr(render, "RENDER_CONTRACT_VERSION", None),
    "canonical_guide_headings_present": bool(getattr(render, "CANONICAL_GUIDE_HEADINGS", None)),
}
print(json.dumps(payload, sort_keys=True))
'@

    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $raw = @(& $pythonPath -I -c $probe 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($exitCode -ne 0) {
        throw "Isolated runtime probe selhal. Exit code: $exitCode`n$(($raw | Out-String).Trim())"
    }

    $probeResult = (($raw | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine).Trim() | ConvertFrom-Json
    $evidence.python_executable = [string]$probeResult.python_executable
    $evidence.sys_prefix = [string]$probeResult.sys_prefix
    $evidence.imported_module_path = [string]$probeResult.imported_module_path
    $evidence.imported_module_sha256 = [string]$probeResult.imported_module_sha256
    $evidence.render_contract_version = [string]$probeResult.render_contract_version
    $evidence.canonical_guide_headings_present = [bool]$probeResult.canonical_guide_headings_present

    $comparison = if ($env:OS -eq "Windows_NT") {
        [System.StringComparison]::OrdinalIgnoreCase
    }
    else {
        [System.StringComparison]::Ordinal
    }
    if (-not $evidence.imported_module_path.Equals($expectedModulePath, $comparison)) {
        throw "Importovaný ddda_miro.render neleží v candidate package. Actual: '$($evidence.imported_module_path)'; expected: '$expectedModulePath'."
    }
    if ($evidence.imported_module_sha256 -ne $evidence.expected_module_sha256) {
        throw "Importovaný ddda_miro.render má jiný SHA-256 než candidate package."
    }
    if ($evidence.render_contract_version -ne $ExpectedRenderContractVersion) {
        throw "Importovaný render contract '$($evidence.render_contract_version)' neodpovídá '$ExpectedRenderContractVersion'."
    }
    if (-not $evidence.canonical_guide_headings_present) {
        throw "Importovaný renderer neobsahuje CANONICAL_GUIDE_HEADINGS."
    }

    $evidence.status = "PASS"
    Write-ProvenanceEvidence -Value $evidence
    if ($Json) {
        $evidence | ConvertTo-Json -Depth 20
    }
    else {
        Write-Host "DDDA Miro runtime provenance: PASS"
        Write-Host "Imported module: $($evidence.imported_module_path)"
        Write-Host "Render contract: $($evidence.render_contract_version)"
    }
}
catch {
    $evidence.error = $_.Exception.Message
    Write-ProvenanceEvidence -Value $evidence
    throw
}
finally {
    foreach ($name in $environmentNames) {
        Remove-Item -LiteralPath "Env:\$name" -ErrorAction SilentlyContinue
        if ($savedEnvironment.ContainsKey($name)) {
            Set-Item -LiteralPath "Env:\$name" -Value $savedEnvironment[$name]
        }
    }
}
