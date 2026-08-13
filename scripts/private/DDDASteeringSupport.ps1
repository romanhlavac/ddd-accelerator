Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "DDDAMiroSupport.ps1")

function Get-DDDASteeringPythonExe {
    param([Parameter(Mandatory = $true)][string]$PlatformRoot)

    $platformFull = [System.IO.Path]::GetFullPath($PlatformRoot)
    $windowsPath = Join-Path $platformFull ".ddda/runtime/steering-venv/Scripts/python.exe"
    $unixPath = Join-Path $platformFull ".ddda/runtime/steering-venv/bin/python"
    if (Test-Path $windowsPath) { return $windowsPath }
    if (Test-Path $unixPath) { return $unixPath }
    throw "DDDA steering runtime není nainstalovaný. Spusť Install-DDDASteeringRuntime.ps1 nebo Initialize-DDDAAfterClone.ps1."
}

function Invoke-DDDASteeringJson {
    param(
        [Parameter(Mandatory = $true)][string]$PlatformRoot,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $pythonExe = Get-DDDASteeringPythonExe -PlatformRoot $PlatformRoot
    $output = & $pythonExe -m ddda_steering @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "DDDA steering příkaz selhal:`n$($output | Out-String)"
    }
    $text = ($output | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) {
        throw "DDDA steering příkaz nevrátil výsledek."
    }
    return ($text | ConvertFrom-Json)
}

function Assert-DDDAProjectGitRoot {
    param([Parameter(Mandatory = $true)][string]$ProjectRoot)

    $gitRoot = Invoke-DDDAGit -RepositoryPath $ProjectRoot -Arguments @("rev-parse", "--show-toplevel")
    if ([System.IO.Path]::GetFullPath($gitRoot).TrimEnd('\', '/') -ne [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\', '/')) {
        throw "ProjectPath není Git root projektu. ProjectPath: $ProjectRoot; Git root: $gitRoot"
    }
}
