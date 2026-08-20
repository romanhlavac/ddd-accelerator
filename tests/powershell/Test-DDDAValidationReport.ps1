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

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-validation-report-test-" + [Guid]::NewGuid().ToString("N"))
$emptySuites = Join-Path $tempRoot "empty-suites.json"
$passSuites = Join-Path $tempRoot "pass-suites.json"
$packagePath = Join-Path $tempRoot "candidate.zip"
$commit = "0000000000000000000000000000000000000000"

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    Write-DDDAPlatformJson -Value @() -Path $emptySuites
    Write-DDDAPlatformJson -Value @(
        [ordered]@{
            name = "lint"
            status = "PASS"
            duration_ms = 10
            details = "Log: $(Join-Path $tempRoot 'validation/logs/lint.log')"
        }
    ) -Path $passSuites
    Write-DDDAPlatformText -Value "synthetic candidate package" -Path $packagePath

    Assert-True -Condition ((Get-Content -LiteralPath $emptySuites -Raw -Encoding UTF8).Trim() -eq "[]") -Message "Prázdný suites vstup musí být zapsán jako JSON pole."

    $failureRoot = Join-Path $tempRoot "failure-report"
    & (Join-Path $PlatformPath "scripts/platform/New-DDDAValidationReport.ps1") -ValidationId "bootstrap-failure" -Status FAIL -SourceKind pr -Repository "romanhlavac/ddd-accelerator" -Commit $commit -Pr 8 -Branch "feature/test" -SuitesJsonPath $emptySuites -OutputRoot $failureRoot -Diagnostics "clone failed"

    $failureJsonPath = Join-Path $failureRoot "result.json"
    Assert-True -Condition (Test-Path -LiteralPath $failureJsonPath -PathType Leaf) -Message "Bootstrap failure report nebyl vytvořen."
    $failureJsonText = Get-Content -LiteralPath $failureJsonPath -Raw -Encoding UTF8
    $failureReport = $failureJsonText | ConvertFrom-Json
    Assert-True -Condition ($failureReport.status -eq "FAIL") -Message "Failure report nemá status FAIL."
    Assert-True -Condition ($null -eq $failureReport.package) -Message "Pre-package failure report musí mít package=null."
    Assert-True -Condition ($failureJsonText -match '"suites"\s*:\s*\[\s*\]') -Message "Pre-package failure report musí obsahovat suites jako prázdné JSON pole."

    $passWithoutPackageRejected = $false
    try {
        & (Join-Path $PlatformPath "scripts/platform/New-DDDAValidationReport.ps1") -ValidationId "invalid-pass" -Status PASS -SourceKind pr -Repository "romanhlavac/ddd-accelerator" -Commit $commit -Pr 8 -Branch "feature/test" -SuitesJsonPath $passSuites -OutputRoot (Join-Path $tempRoot "invalid-pass")
    }
    catch {
        $passWithoutPackageRejected = $true
    }
    Assert-True -Condition $passWithoutPackageRejected -Message "PASS report bez package musí být odmítnut."

    $passRoot = Join-Path $tempRoot "pass-report"
    & (Join-Path $PlatformPath "scripts/platform/New-DDDAValidationReport.ps1") -ValidationId "valid-pass" -Status PASS -SourceKind pr -Repository "romanhlavac/ddd-accelerator" -Commit $commit -Pr 8 -Branch "feature/test" -PackagePath $packagePath -PackageArtifactName "ddda-candidate-$commit" -WorkflowRunId "123456" -Workspace $tempRoot -SuitesJsonPath $passSuites -OutputRoot $passRoot -Diagnostics (Join-Path $tempRoot 'validation/logs/lint.log') -PortablePaths

    $passJsonPath = Join-Path $passRoot "result.json"
    Assert-True -Condition (Test-Path -LiteralPath $passJsonPath -PathType Leaf) -Message "PASS validation report nebyl vytvořen."
    $passJsonText = Get-Content -LiteralPath $passJsonPath -Raw -Encoding UTF8
    $passReport = $passJsonText | ConvertFrom-Json
    Assert-True -Condition ($passReport.status -eq "PASS") -Message "PASS report nemá status PASS."
    Assert-True -Condition ($passReport.package.sha256 -eq (Get-DDDAPlatformFileHash -Path $packagePath)) -Message "PASS report neobsahuje správný package hash."
    Assert-True -Condition ($passReport.package.path -eq (Split-Path -Leaf $packagePath)) -Message "Portable PASS report musí používat přenositelnou package identity."
    Assert-True -Condition ($passReport.package.artifact_name -eq "ddda-candidate-$commit") -Message "PASS report neobsahuje canonical artifact name."
    Assert-True -Condition ([string]$passReport.package.workflow_run_id -eq "123456") -Message "PASS report neobsahuje source workflow run ID."
    Assert-True -Condition ($passJsonText -notlike "*$tempRoot*") -Message "Publikovaná JSON evidence nesmí obsahovat absolutní test/runner cestu."
    Assert-True -Condition ((Get-Content -LiteralPath (Join-Path $passRoot 'result.md') -Raw -Encoding UTF8) -notlike "*$tempRoot*") -Message "Publikovaná Markdown evidence nesmí obsahovat absolutní test/runner cestu."
    Assert-True -Condition (@($passReport.suites).Count -eq 1) -Message "PASS report neobsahuje očekávanou suite."

    Write-Host "DDDA validation report tests: PASS"
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
