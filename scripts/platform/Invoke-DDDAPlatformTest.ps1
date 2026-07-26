[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)]
    [ValidateSet("lint", "schema", "unit", "component", "integration", "smoke", "regression", "security", "e2e", "acceptance", "all")]
    [string]$Suite,
    [string]$PackagePath,
    [switch]$WithMiro,
    [switch]$Full,
    [switch]$CleanupOnFailure,
    [switch]$NonInteractive,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")

$platformRoot = [System.IO.Path]::GetFullPath($PlatformPath).TrimEnd('\', '/')
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$status = "PASS"
$details = $null

function Invoke-TestScript {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [string[]]$Arguments = @()
    )

    $path = Join-Path $platformRoot $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Test script neexistuje: $path"
    }
    Invoke-DDDAPlatformChildPowerShell -ScriptPath $path -Arguments $Arguments
}

function Install-TestRuntimes {
    $arguments = @("-PlatformPath", $platformRoot, "-NonInteractive")
    Invoke-TestScript -RelativePath "scripts/Initialize-DDDAAfterClone.ps1" -Arguments $arguments
}

function Get-RuntimePython {
    param([Parameter(Mandatory = $true)][ValidateSet("steering", "miro")][string]$Runtime)

    if (Test-DDDAPlatformIsWindows) {
        return Join-Path $platformRoot ".ddda/runtime/$Runtime-venv/Scripts/python.exe"
    }
    return Join-Path $platformRoot ".ddda/runtime/$Runtime-venv/bin/python"
}

function Invoke-RepositoryValidator {
    param([Parameter(Mandatory = $true)][ValidateSet("lint", "schema", "security", "all")][string]$ValidationSuite)

    Install-TestRuntimes
    $python = Get-RuntimePython -Runtime "steering"
    $validator = Join-Path $platformRoot "runtime/platform/validate_repository.py"
    $null = Invoke-DDDAPlatformNative -Command $python -Arguments @($validator, "--root", $platformRoot, "--suite", $ValidationSuite)
}

function Invoke-PackageWorkspaceCheck {
    if ([string]::IsNullOrWhiteSpace($PackagePath)) {
        throw "Suite '$Suite' vyžaduje -PackagePath."
    }

    $packageFull = (Resolve-Path -LiteralPath $PackagePath).Path
    Invoke-TestScript -RelativePath "scripts/platform/Test-DDDAPlatformPackage.ps1" -Arguments @("-PackagePath", $packageFull)

    $workspaceRoot = Join-Path (Get-DDDAPlatformStateRoot) ("test-workspaces/" + [Guid]::NewGuid().ToString("N"))
    try {
        $validationScript = Join-Path $platformRoot "scripts/platform/New-DDDAValidationWorkspace.ps1"
        $validationText = & $validationScript -PlatformPath $platformRoot -WorkspaceRoot $workspaceRoot -NonInteractive -Json | Out-String
        if ($LASTEXITCODE -ne 0) {
            throw "Generování package validation workspace selhalo."
        }
        $validation = $validationText.Trim() | ConvertFrom-Json

        if ($validation.status -ne "PASS") {
            throw "Validation workspace nevrátil PASS."
        }
        if ($validation.current_stage -ne "align" -or $validation.next_gate -ne "G1") {
            throw "Validation workspace očekával align/G1, získal $($validation.current_stage)/$($validation.next_gate)."
        }
        if (-not (Test-Path -LiteralPath $validation.ingestion_report -PathType Leaf)) {
            throw "Validation workspace nevytvořil ingestion report: $($validation.ingestion_report)"
        }

        $ingestionReport = Get-Content -LiteralPath $validation.ingestion_report -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($ingestionReport.status -ne "PASS" -or @($ingestionReport.files).Count -lt 2) {
            throw "Ingestion report neprokazuje úspěšný manifest-driven ingestion."
        }

        return [pscustomobject]@{
            status = "PASS"
            project = [string]$validation.project
            ingestion_report = [string]$validation.ingestion_report
            current_stage = [string]$validation.current_stage
            next_gate = [string]$validation.next_gate
        }
    }
    finally {
        if (Test-Path -LiteralPath $workspaceRoot) {
            Remove-Item -LiteralPath $workspaceRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

function Invoke-OneSuite {
    param([Parameter(Mandatory = $true)][string]$Name)

    Write-Host "=== DDDA platform test: $Name ==="
    switch ($Name) {
        "lint" {
            Invoke-TestScript -RelativePath "scripts/Test-DDDAInstallation.ps1" -Arguments @("-PlatformPath", $platformRoot)
            Invoke-RepositoryValidator -ValidationSuite "lint"
        }
        "schema" {
            Invoke-RepositoryValidator -ValidationSuite "schema"
        }
        "unit" {
            Install-TestRuntimes
            $steeringPython = Get-RuntimePython -Runtime "steering"
            $miroPython = Get-RuntimePython -Runtime "miro"
            $null = Invoke-DDDAPlatformNative -Command $steeringPython -Arguments @("-m", "pip", "install", "--disable-pip-version-check", "pytest>=8,<9")
            $null = Invoke-DDDAPlatformNative -Command $miroPython -Arguments @("-m", "pip", "install", "--disable-pip-version-check", "pytest>=8,<9")
            $null = Invoke-DDDAPlatformNative -Command $steeringPython -Arguments @("-m", "pytest", "-q", (Join-Path $platformRoot "runtime/steering/tests")) -WorkingDirectory $platformRoot
            $null = Invoke-DDDAPlatformNative -Command $steeringPython -Arguments @("-m", "pytest", "-q", (Join-Path $platformRoot "runtime/platform/tests")) -WorkingDirectory $platformRoot
            $null = Invoke-DDDAPlatformNative -Command $miroPython -Arguments @("-m", "pytest", "-q", (Join-Path $platformRoot "runtime/miro/tests")) -WorkingDirectory $platformRoot
        }
        "component" {
            Invoke-TestScript -RelativePath "tests/powershell/Test-DDDAMiroAutomation.ps1" -Arguments @("-PlatformPath", $platformRoot)
            Invoke-TestScript -RelativePath "tests/powershell/Test-DDDAProjectSteering.ps1" -Arguments @("-PlatformPath", $platformRoot)
        }
        "integration" {
            $integrationResult = Invoke-PackageWorkspaceCheck
            if ($integrationResult.status -ne "PASS") {
                throw "Package integration check nevrátil PASS."
            }
        }
        "smoke" {
            $smokeResult = Invoke-PackageWorkspaceCheck
            if ($smokeResult.current_stage -ne "align" -or $smokeResult.next_gate -ne "G1") {
                throw "Package smoke check nemá očekávaný počáteční stav."
            }
        }
        "regression" {
            Invoke-TestScript -RelativePath "tests/powershell/Test-DDDAFirstRun.ps1" -Arguments @("-PlatformPath", $platformRoot)
            Invoke-TestScript -RelativePath "tests/powershell/Test-DDDAProjectSteering.ps1" -Arguments @("-PlatformPath", $platformRoot)
            Invoke-TestScript -RelativePath "tests/powershell/Test-DDDAMiroAutomation.ps1" -Arguments @("-PlatformPath", $platformRoot)
        }
        "security" {
            Invoke-RepositoryValidator -ValidationSuite "security"
            Invoke-TestScript -RelativePath "tests/powershell/Test-DDDAPlatformSecurity.ps1" -Arguments @("-PlatformPath", $platformRoot)
            if (-not [string]::IsNullOrWhiteSpace($PackagePath)) {
                Invoke-TestScript -RelativePath "scripts/platform/Test-DDDAPlatformPackage.ps1" -Arguments @("-PackagePath", (Resolve-Path -LiteralPath $PackagePath).Path)
            }
        }
        "e2e" {
            if ([string]::IsNullOrWhiteSpace($PackagePath)) {
                throw "Suite 'e2e' vyžaduje -PackagePath."
            }
            Invoke-TestScript -RelativePath "tests/powershell/Test-DDDAPlatformLifecycle.ps1" -Arguments @(
                "-PackagePath", (Resolve-Path -LiteralPath $PackagePath).Path
            )
        }
        "acceptance" {
            $arguments = @(
                "-PlatformPath", $platformRoot,
                "-Suite", "project-steering"
            )
            if ($WithMiro) { $arguments += "-WithMiro" }
            if ($Full) { $arguments += "-Full" }
            if ($CleanupOnFailure) { $arguments += "-CleanupOnFailure" }
            if ($NonInteractive) { $arguments += "-NonInteractive" }
            Invoke-TestScript -RelativePath "scripts/Test-DDDAAcceptance.ps1" -Arguments $arguments
        }
        default {
            throw "Nepodporovaná suite: $Name"
        }
    }
}

try {
    $suiteNames = if ($Suite -eq "all") {
        @("lint", "schema", "unit", "component", "integration", "smoke", "regression", "security", "e2e", "acceptance")
    }
    else {
        @($Suite)
    }

    foreach ($suiteName in $suiteNames) {
        Invoke-OneSuite -Name $suiteName
    }
    $details = "Completed: $($suiteNames -join ', ')"
}
catch {
    $status = "FAIL"
    $details = $_.Exception.Message
    throw
}
finally {
    $stopwatch.Stop()
    $result = [ordered]@{
        name = $Suite
        status = $status
        duration_ms = [int64]$stopwatch.ElapsedMilliseconds
        details = $details
    }
    if ($Json) {
        $result | ConvertTo-Json -Depth 10
    }
    else {
        Write-Host "DDDA platform test '$Suite': $status"
    }
}
