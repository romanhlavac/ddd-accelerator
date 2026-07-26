[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)][ValidateRange(1, 2147483647)][int]$Pr,
    [switch]$WithMiro,
    [switch]$Full,
    [switch]$CleanupOnFailure,
    [switch]$KeepArtifacts,
    [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")

$platformRoot = Get-DDDAPlatformGitRoot -Path $PlatformPath
if ($platformRoot -ne [System.IO.Path]::GetFullPath($PlatformPath).TrimEnd('\', '/')) {
    throw "PlatformPath musí být Git root DDDA platformy."
}
Assert-DDDAPlatformCleanGit -Repository $platformRoot

$originUrl = Get-DDDAPlatformRepositoryUrl -Repository $platformRoot
$repositorySlug = Get-DDDAPlatformRepositorySlug -RepositoryUrl $originUrl
$remoteRef = "refs/pull/$Pr/head"
$remoteText = Invoke-DDDAPlatformNative -Command "git" -Arguments @("ls-remote", $originUrl, $remoteRef)
if ([string]::IsNullOrWhiteSpace($remoteText) -or $remoteText -notmatch '^(?<sha>[0-9a-f]{40})\s+') {
    throw "PR #$Pr nebyl nalezen nebo není dostupný přes $remoteRef."
}
$headSha = $Matches["sha"]
$shortSha = $headSha.Substring(0, 12)
$branch = "pull/$Pr/head"

if (Get-Command "gh" -ErrorAction SilentlyContinue) {
    try {
        $ghText = Invoke-DDDAPlatformNative -Command "gh" -Arguments @("pr", "view", [string]$Pr, "--repo", $repositorySlug, "--json", "headRefName,headRefOid,state,isDraft")
        $ghPr = $ghText | ConvertFrom-Json
        if ($ghPr.state -ne "OPEN") {
            throw "PR #$Pr není otevřený."
        }
        if ($ghPr.headRefOid -ne $headSha) {
            throw "GitHub PR head SHA neodpovídá refs/pull/$Pr/head."
        }
        $branch = [string]$ghPr.headRefName
    }
    catch {
        Write-Warning "PR metadata přes GitHub CLI nebyla použita: $($_.Exception.Message)"
    }
}

$startedAt = (Get-Date).ToUniversalTime()
$timestamp = Get-DDDAPlatformTimestamp
$validationId = "pr-$Pr-$shortSha-$timestamp"
$stateRoot = Get-DDDAPlatformStateRoot
$validationRoot = Join-Path $stateRoot ("validation/" + $validationId)
$sourceRoot = Join-Path $validationRoot "source"
$packageRoot = Join-Path $validationRoot "package"
$logRoot = Join-Path $validationRoot "logs"
$reportRoot = Join-Path $stateRoot ("validation-reports/pr-$Pr-$headSha/$timestamp")
$packageStore = Join-Path $stateRoot "packages"
$packagePath = Join-Path $packageStore ("ddda-candidate-pr-$Pr-$shortSha-$timestamp.zip")
$suitesPath = Join-Path $validationRoot "suites.json"

New-Item -ItemType Directory -Path $validationRoot, $logRoot, $reportRoot, $packageStore -Force | Out-Null
$suiteResults = [System.Collections.Generic.List[object]]::new()
$diagnostics = [System.Collections.Generic.List[string]]::new()
$miroBoardId = $null
$validationStatus = "FAIL"
$passed = $false

function Invoke-ValidationSuite {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $suiteStarted = [System.Diagnostics.Stopwatch]::StartNew()
    $logPath = Join-Path $logRoot ($Name + ".log")
    $hostExe = (Get-Process -Id $PID).Path
    $hostArguments = @("-NoProfile")
    if (Test-DDDAPlatformIsWindows) {
        $hostArguments += @("-ExecutionPolicy", "Bypass")
    }
    $hostArguments += @("-File", (Join-Path $packageRoot "scripts/platform/Invoke-DDDAPlatformTest.ps1"))
    $hostArguments += @("-PlatformPath", $packageRoot, "-Suite", $Arguments[0])
    if ($Arguments.Count -gt 1) {
        $hostArguments += $Arguments[1..($Arguments.Count - 1)]
    }

    Write-Host "=== Validation suite: $Name ==="
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $hostExe @hostArguments *> $logPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
        $suiteStarted.Stop()
    }

    $logTail = ""
    if (Test-Path -LiteralPath $logPath) {
        $logTail = ((Get-Content -LiteralPath $logPath -Tail 40 -ErrorAction SilentlyContinue) -join [Environment]::NewLine).Trim()
    }
    $suiteStatus = if ($exitCode -eq 0) { "PASS" } else { "FAIL" }
    $suiteResults.Add([ordered]@{
        name = $Name
        status = $suiteStatus
        duration_ms = [int64]$suiteStarted.ElapsedMilliseconds
        details = if ($exitCode -eq 0) { "Log: $logPath" } else { $logTail }
    })
    $diagnostics.Add($logPath)

    if ($Name -eq "miro" -and $logTail -match '(?m)^Board ID:\s*(?<id>\S+)\s*$') {
        $script:miroBoardId = [string]$Matches["id"]
    }

    if ($exitCode -ne 0) {
        throw "Validation suite '$Name' selhala. Log: $logPath`n$logTail"
    }
    Write-Host "Validation suite '$Name': PASS"
}

try {
    Write-Host "=== DDDA validate-pr ==="
    Write-Host "Repository: $repositorySlug"
    Write-Host "PR:         $Pr"
    Write-Host "Branch:     $branch"
    Write-Host "Head SHA:   $headSha"
    Write-Host "Run:        $validationRoot"

    $null = Invoke-DDDAPlatformNative -Command "git" -Arguments @("clone", "--no-checkout", $originUrl, $sourceRoot)
    $null = Invoke-DDDAPlatformGit -Repository $sourceRoot -Arguments @("fetch", "origin", $remoteRef)
    $null = Invoke-DDDAPlatformGit -Repository $sourceRoot -Arguments @("checkout", "--detach", $headSha)
    $actualHead = Invoke-DDDAPlatformGit -Repository $sourceRoot -Arguments @("rev-parse", "HEAD")
    if ($actualHead -ne $headSha) {
        throw "Izolovaný checkout neodpovídá PR head SHA."
    }
    Assert-DDDAPlatformCleanGit -Repository $sourceRoot -Label "Izolovaný PR"

    $candidateVersion = "pr.$Pr.$shortSha.$timestamp"
    $packageText = & (Join-Path $sourceRoot "scripts/platform/New-DDDAPlatformPackage.ps1") -PlatformPath $sourceRoot -Kind candidate -Version $candidateVersion -SourceRef $headSha -OutputPath $packagePath -Json | Out-String
    if ($LASTEXITCODE -ne 0) {
        throw "Vytvoření candidate package selhalo."
    }
    $package = $packageText.Trim() | ConvertFrom-Json
    if ($package.source_commit -ne $headSha) {
        throw "Candidate package není svázán s aktuálním PR head SHA."
    }

    & (Join-Path $sourceRoot "scripts/platform/Test-DDDAPlatformPackage.ps1") -PackagePath $packagePath -ExpectedCommit $headSha -ExpectedKind candidate
    if ($LASTEXITCODE -ne 0) {
        throw "Candidate package validation selhala."
    }

    New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
    Expand-Archive -LiteralPath $packagePath -DestinationPath $packageRoot -Force

    $null = Invoke-DDDAPlatformNative -Command "git" -Arguments @("-C", $packageRoot, "init", "-b", "main")
    $null = Invoke-DDDAPlatformGit -Repository $packageRoot -Arguments @("config", "user.name", "DDDA Package Validation")
    $null = Invoke-DDDAPlatformGit -Repository $packageRoot -Arguments @("config", "user.email", "ddda-package-validation@example.invalid")
    $null = Invoke-DDDAPlatformGit -Repository $packageRoot -Arguments @("remote", "add", "origin", $originUrl)
    $null = Invoke-DDDAPlatformGit -Repository $packageRoot -Arguments @("add", ".")
    $null = Invoke-DDDAPlatformGit -Repository $packageRoot -Arguments @("commit", "-m", "chore: candidate package baseline")
    Assert-DDDAPlatformCleanGit -Repository $packageRoot -Label "Rozbalený candidate package"

    $commonArguments = @("-PackagePath", $packagePath)
    Invoke-ValidationSuite -Name "lint" -Arguments @("lint")
    Invoke-ValidationSuite -Name "schema" -Arguments @("schema")
    Invoke-ValidationSuite -Name "unit" -Arguments @("unit")
    Invoke-ValidationSuite -Name "component" -Arguments @("component")
    Invoke-ValidationSuite -Name "integration" -Arguments (@("integration") + $commonArguments)
    Invoke-ValidationSuite -Name "smoke" -Arguments (@("smoke") + $commonArguments)
    Invoke-ValidationSuite -Name "regression" -Arguments @("regression")
    Invoke-ValidationSuite -Name "security" -Arguments (@("security") + $commonArguments)
    Invoke-ValidationSuite -Name "e2e" -Arguments (@("e2e") + $commonArguments)
    Invoke-ValidationSuite -Name "acceptance" -Arguments @("acceptance", "-CleanupOnFailure", "-NonInteractive")

    if ($WithMiro) {
        $miroArguments = @("acceptance", "-WithMiro", "-CleanupOnFailure")
        if ($Full) { $miroArguments += "-Full" }
        if ($NonInteractive) { $miroArguments += "-NonInteractive" }
        Invoke-ValidationSuite -Name "miro" -Arguments $miroArguments
    }

    Assert-DDDAPlatformCleanGit -Repository $platformRoot -Label "Aktivní platformní"
    Assert-DDDAPlatformCleanGit -Repository $sourceRoot -Label "Izolovaný PR"

    $validationStatus = "PASS"
    $passed = $true
}
catch {
    $diagnostics.Add($_.Exception.Message)
    Write-Host "DDDA validate-pr: FAIL" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}
finally {
    Write-DDDAPlatformJson -Value @($suiteResults) -Path $suitesPath
    $completedAt = (Get-Date).ToUniversalTime()
    $reportArguments = @{
        ValidationId = $validationId
        Status = $validationStatus
        SourceKind = "pr"
        Repository = $repositorySlug
        Commit = $headSha
        Pr = $Pr
        Branch = $branch
        PackagePath = $packagePath
        SuitesJsonPath = $suitesPath
        OutputRoot = $reportRoot
        Diagnostics = @($diagnostics)
        StartedAt = $startedAt
        CompletedAt = $completedAt
    }
    if (-not [string]::IsNullOrWhiteSpace($miroBoardId)) {
        $reportArguments["MiroBoardId"] = $miroBoardId
    }
    & (Join-Path $sourceRoot "scripts/platform/New-DDDAValidationReport.ps1") @reportArguments

    if ($passed -and -not $KeepArtifacts -and (Test-Path -LiteralPath $validationRoot)) {
        Remove-Item -LiteralPath $validationRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    elseif (Test-Path -LiteralPath $validationRoot) {
        Write-Host "Validation diagnostics: $validationRoot"
    }
}

if (-not $passed) {
    Write-Host "Report: $reportRoot"
    exit 1
}

Write-Host ""
Write-Host "========================================"
Write-Host "DDDA PR validation: PASS"
Write-Host "PR:       $Pr"
Write-Host "Branch:   $branch"
Write-Host "Commit:   $headSha"
Write-Host "Package:  $packagePath"
Write-Host "Report:   $reportRoot"
Write-Host "Next:     .\ddda.ps1 promote-pr -Pr $Pr -Version <X.Y.Z> -ConfirmMerge"
Write-Host "========================================"
exit 0
