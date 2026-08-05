[CmdletBinding()]
param(
    [switch]$SkipViews,
    [switch]$DoNotOpenProject,
    [switch]$DoNotPublishReport
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repository = "romanhlavac/ddd-accelerator"
$ref = "feature/github-native-backlog-governance"
$bootstrapRepositoryPath = "scripts/platform/Bootstrap-DDDAGitHubGovernance.ps1"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$headers = @{
    Accept = "application/vnd.github+json"
    "User-Agent" = "DDDA-Governance-Launcher"
    "X-GitHub-Api-Version" = "2022-11-28"
}

$runtimeRoot = if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    Join-Path $env:LOCALAPPDATA "DDDA\launcher"
}
else {
    Join-Path ([IO.Path]::GetTempPath()) "DDDA\launcher"
}

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
$bootstrapPath = Join-Path $runtimeRoot "Bootstrap-DDDAGitHubGovernance.ps1"

$encodedRef = [Uri]::EscapeDataString($ref)
$endpoint = "https://api.github.com/repos/{0}/contents/{1}?ref={2}" -f $repository, $bootstrapRepositoryPath, $encodedRef

Write-Host "Downloading DDDA governance bootstrap..." -ForegroundColor Cyan
$payload = Invoke-RestMethod -Uri $endpoint -Headers $headers -Method Get

if (-not $payload.content) {
    throw "GitHub returned no content for $bootstrapRepositoryPath."
}

$bytes = [Convert]::FromBase64String(($payload.content -replace "\s", ""))
if ($bytes.Length -eq 0) {
    throw "Downloaded bootstrap is empty."
}

[System.IO.File]::WriteAllBytes($bootstrapPath, $bytes)

# Compatibility repairs for earlier bootstrap revisions. These replacements are
# harmless when the source has already been corrected.
$bootstrapText = [System.IO.File]::ReadAllText($bootstrapPath, $utf8NoBom)
$bootstrapText = $bootstrapText.Replace(
    '$endpoint = "repos/$repository/contents/$RepositoryPath?ref=$encodedRef"',
    '$endpoint = "repos/{0}/contents/{1}?ref={2}" -f $repository, $RepositoryPath, $encodedRef'
)
$bootstrapText = $bootstrapText.Replace('$exitCode:', '${exitCode}:')

$unsafeNativeInvocation = @'
    $output = & $Executable @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($output | ForEach-Object { "$_" }) -join "`n"
'@

$safeNativeInvocation = @'
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = & $Executable @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $text = ($output | ForEach-Object { "$_" }) -join "`n"
'@

$bootstrapText = $bootstrapText.Replace($unsafeNativeInvocation, $safeNativeInvocation)

$capturedLogin = @'
    Invoke-NativeChecked -Executable $ghPath -Arguments @(
        "auth", "login",
        "--hostname", "github.com",
        "--git-protocol", "https",
        "--web"
    ) | Out-Null
'@

$interactiveLogin = @'
    & $ghPath auth login --hostname github.com --git-protocol https --web
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub authentication failed with exit code $LASTEXITCODE."
    }
'@

$bootstrapText = $bootstrapText.Replace($capturedLogin, $interactiveLogin)

$capturedRefresh = @'
    Invoke-NativeChecked -Executable $ghPath -Arguments @(
        "auth", "refresh",
        "--hostname", "github.com",
        "-s", "project"
    ) | Out-Null
'@

$interactiveRefresh = @'
    & $ghPath auth refresh --hostname github.com -s project
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub Projects authorization failed with exit code $LASTEXITCODE."
    }
'@

$bootstrapText = $bootstrapText.Replace($capturedRefresh, $interactiveRefresh)
[System.IO.File]::WriteAllText($bootstrapPath, $bootstrapText, $utf8NoBom)

if ((Get-Item -LiteralPath $bootstrapPath).Length -eq 0) {
    throw "Prepared bootstrap is empty: $bootstrapPath"
}

Unblock-File -LiteralPath $bootstrapPath -ErrorAction SilentlyContinue

$arguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $bootstrapPath)
if ($SkipViews) { $arguments += "-SkipViews" }
if ($DoNotOpenProject) { $arguments += "-DoNotOpenProject" }
if ($DoNotPublishReport) { $arguments += "-DoNotPublishReport" }

Write-Host "Starting DDDA GitHub governance automation..." -ForegroundColor Cyan
& powershell.exe @arguments
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    throw "DDDA GitHub governance automation failed with exit code $exitCode."
}

Write-Host "DDDA GitHub governance automation completed." -ForegroundColor Green
