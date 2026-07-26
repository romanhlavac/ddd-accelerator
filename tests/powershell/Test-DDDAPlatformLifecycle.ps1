[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PackagePath,
    [string]$ExpectedCommit,
    [switch]$KeepArtifacts,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$packageFull = (Resolve-Path -LiteralPath $PackagePath).Path
$bootstrapRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-package-lifecycle-" + [Guid]::NewGuid().ToString("N"))
$platformRoot = Join-Path $bootstrapRoot "platform"
$workspaceRoot = Join-Path $bootstrapRoot "workspace"
$passed = $false

try {
    New-Item -ItemType Directory -Path $platformRoot -Force | Out-Null
    Expand-Archive -LiteralPath $packageFull -DestinationPath $platformRoot -Force

    $supportScript = Join-Path $platformRoot "scripts/platform/DDDAPlatformSupport.ps1"
    if (-not (Test-Path -LiteralPath $supportScript)) {
        throw "Package neobsahuje platform lifecycle support."
    }
    . $supportScript

    Invoke-DDDAPlatformChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/platform/Test-DDDAPlatformPackage.ps1") -Arguments @(
        "-PackagePath", $packageFull
    )

    if (-not (Test-Path -LiteralPath (Join-Path $platformRoot ".git"))) {
        $null = Invoke-DDDAPlatformNative -Command "git" -Arguments @("-C", $platformRoot, "init", "-b", "main")
        $null = Invoke-DDDAPlatformGit -Repository $platformRoot -Arguments @("config", "user.name", "DDDA Package Validation")
        $null = Invoke-DDDAPlatformGit -Repository $platformRoot -Arguments @("config", "user.email", "ddda-package-validation@example.invalid")
        $null = Invoke-DDDAPlatformGit -Repository $platformRoot -Arguments @("add", ".")
        $null = Invoke-DDDAPlatformGit -Repository $platformRoot -Arguments @("commit", "-m", "chore: package validation baseline")
    }

    $manifest = Get-Content -LiteralPath (Join-Path $platformRoot "ddda-package.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not [string]::IsNullOrWhiteSpace($ExpectedCommit) -and $manifest.source_commit -ne $ExpectedCommit) {
        throw "Package source_commit '$($manifest.source_commit)' neodpovídá očekávanému '$ExpectedCommit'."
    }

    $workspaceText = & (Join-Path $platformRoot "scripts/platform/New-DDDAValidationWorkspace.ps1") -PlatformPath $platformRoot -WorkspaceRoot $workspaceRoot -Json | Out-String
    if ([string]::IsNullOrWhiteSpace($workspaceText)) {
        throw "Generování validation workspace nevrátilo JSON."
    }
    $workspace = $workspaceText.Trim() | ConvertFrom-Json
    if ($workspace.status -ne "PASS") {
        throw "Generování validation workspace nevrátilo PASS."
    }

    $oldAuthorName = $env:GIT_AUTHOR_NAME
    $oldAuthorEmail = $env:GIT_AUTHOR_EMAIL
    $oldCommitterName = $env:GIT_COMMITTER_NAME
    $oldCommitterEmail = $env:GIT_COMMITTER_EMAIL
    $env:GIT_AUTHOR_NAME = "DDDA Lifecycle Test"
    $env:GIT_AUTHOR_EMAIL = "ddda-lifecycle@example.invalid"
    $env:GIT_COMMITTER_NAME = "DDDA Lifecycle Test"
    $env:GIT_COMMITTER_EMAIL = "ddda-lifecycle@example.invalid"
    try {
        Invoke-DDDAPlatformChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Complete-DDDALifecycleStep.ps1") -Arguments @(
            "-PlatformPath", $platformRoot,
            "-ProjectPath", [string]$workspace.project,
            "-Gate", "G1",
            "-Outcome", "passed",
            "-Reviewer", "DDDA platform lifecycle test",
            "-Note", "Synthetic package-first validation",
            "-Commit"
        )
    }
    finally {
        if ($null -eq $oldAuthorName) { Remove-Item Env:\GIT_AUTHOR_NAME -ErrorAction SilentlyContinue } else { $env:GIT_AUTHOR_NAME = $oldAuthorName }
        if ($null -eq $oldAuthorEmail) { Remove-Item Env:\GIT_AUTHOR_EMAIL -ErrorAction SilentlyContinue } else { $env:GIT_AUTHOR_EMAIL = $oldAuthorEmail }
        if ($null -eq $oldCommitterName) { Remove-Item Env:\GIT_COMMITTER_NAME -ErrorAction SilentlyContinue } else { $env:GIT_COMMITTER_NAME = $oldCommitterName }
        if ($null -eq $oldCommitterEmail) { Remove-Item Env:\GIT_COMMITTER_EMAIL -ErrorAction SilentlyContinue } else { $env:GIT_COMMITTER_EMAIL = $oldCommitterEmail }
    }

    $statusText = & (Join-Path $platformRoot "scripts/Get-DDDAProjectStatus.ps1") -PlatformPath $platformRoot -ProjectPath ([string]$workspace.project) -Json | Out-String
    if ([string]::IsNullOrWhiteSpace($statusText)) {
        throw "Kontrola statusu po G1 nevrátila JSON."
    }
    $status = $statusText.Trim() | ConvertFrom-Json
    if ($status.current_stage -ne "discover" -or $status.next_gate -ne "G2") {
        throw "Package lifecycle očekával discover/G2, získal $($status.current_stage)/$($status.next_gate)."
    }

    $projectStatus = Invoke-DDDAPlatformGit -Repository ([string]$workspace.project) -Arguments @("status", "--porcelain")
    if (-not [string]::IsNullOrWhiteSpace($projectStatus)) {
        throw "Projektový repozitář po lifecycle testu není čistý:`n$projectStatus"
    }

    $passed = $true
    $result = [ordered]@{
        status = "PASS"
        package = $packageFull
        package_sha256 = Get-DDDAPlatformFileHash -Path $packageFull
        source_commit = [string]$manifest.source_commit
        workspace = $workspaceRoot
        project = [string]$workspace.project
        current_stage = [string]$status.current_stage
        next_gate = [string]$status.next_gate
    }

    if ($Json) {
        $result | ConvertTo-Json -Depth 10
    }
    else {
        Write-Host "DDDA package-first platform lifecycle: PASS"
        Write-Host "Commit:    $($result.source_commit)"
        Write-Host "Stage:     $($result.current_stage)"
        Write-Host "Next gate: $($result.next_gate)"
    }
}
finally {
    if ($passed -and -not $KeepArtifacts -and (Test-Path -LiteralPath $bootstrapRoot)) {
        Remove-Item -LiteralPath $bootstrapRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    elseif (Test-Path -LiteralPath $bootstrapRoot) {
        Write-Host "Lifecycle diagnostics: $bootstrapRoot"
    }
}
