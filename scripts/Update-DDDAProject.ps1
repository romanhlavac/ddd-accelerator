[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PlatformPath,
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [Parameter(Mandatory = $true)][string]$TargetRef,
    [int]$TargetSchemaVersion = 1,
    [switch]$Commit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([string]$RepositoryPath, [string[]]$Arguments)
    $output = & git -C $RepositoryPath @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Git selhal v '$RepositoryPath': git $($Arguments -join ' ')`n$output"
    }
    return ($output | Out-String).Trim()
}

$platformRoot = Invoke-Git -RepositoryPath $PlatformPath -Arguments @("rev-parse", "--show-toplevel")
$projectRoot = Invoke-Git -RepositoryPath $ProjectPath -Arguments @("rev-parse", "--show-toplevel")

if ([System.IO.Path]::GetFullPath($platformRoot) -eq [System.IO.Path]::GetFullPath($projectRoot)) {
    throw "Platforma a projekt musí být dva nezávislé Git repozitáře."
}

$projectStatus = Invoke-Git -RepositoryPath $projectRoot -Arguments @("status", "--porcelain=v1")
if (-not [string]::IsNullOrWhiteSpace($projectStatus)) {
    throw "Projektový repozitář musí být před upgradem čistý:`n$projectStatus"
}

$platformStatus = Invoke-Git -RepositoryPath $platformRoot -Arguments @("status", "--porcelain=v1")
if (-not [string]::IsNullOrWhiteSpace($platformStatus)) {
    throw "Platformní repozitář musí být před upgradem čistý:`n$platformStatus"
}

try {
    Invoke-Git -RepositoryPath $platformRoot -Arguments @("fetch", "origin", "--tags") | Out-Null
} catch {
    Write-Warning "Fetch origin se nezdařil; pokračuji s lokálně dostupnými refs. $($_.Exception.Message)"
}

$targetCommit = Invoke-Git -RepositoryPath $platformRoot -Arguments @("rev-parse", "$TargetRef^{commit}")
$lockPath = Join-Path $projectRoot "ddda.lock.yaml"
if (-not (Test-Path $lockPath)) {
    throw "Projekt neobsahuje ddda.lock.yaml."
}

$lock = Get-Content $lockPath -Raw
$currentCommitMatch = [regex]::Match($lock, "(?m)^\s*commit:\s*(?<value>[0-9a-f]{7,40})\s*$")
$currentSchemaMatch = [regex]::Match($lock, "(?m)^\s*schema_version:\s*(?<value>\d+)\s*$")

if (-not $currentCommitMatch.Success -or -not $currentSchemaMatch.Success) {
    throw "ddda.lock.yaml nemá očekávaný formát."
}

$currentCommit = $currentCommitMatch.Groups["value"].Value
$currentSchemaVersion = [int]$currentSchemaMatch.Groups["value"].Value

if ($TargetSchemaVersion -lt $currentSchemaVersion) {
    throw "Downgrade schématu není podporován: $currentSchemaVersion -> $TargetSchemaVersion."
}

Write-Host "Projektový upgrade DDDA"
Write-Host "Commit: $currentCommit -> $targetCommit"
Write-Host "Schema: $currentSchemaVersion -> $TargetSchemaVersion"

$nextSchemaVersion = $currentSchemaVersion
while ($nextSchemaVersion -lt $TargetSchemaVersion) {
    $from = $nextSchemaVersion
    $to = $from + 1
    $migrationPath = Join-Path $platformRoot "migrations/$from-to-$to.ps1"
    if (-not (Test-Path $migrationPath)) {
        throw "Chybí povinná migrace: $migrationPath"
    }

    Write-Host "Spouštím migraci schématu $from -> $to"
    & $migrationPath -ProjectPath $projectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Migrace $from -> $to selhala."
    }
    $nextSchemaVersion = $to
}

$lockedAt = (Get-Date).ToUniversalTime().ToString("o")
$updatedLock = $lock
$updatedLock = [regex]::Replace($updatedLock, "(?m)^(\s*ref:\s*).*$", "`${1}$TargetRef", 1)
$updatedLock = [regex]::Replace($updatedLock, "(?m)^(\s*commit:\s*).*$", "`${1}$targetCommit", 1)
$updatedLock = [regex]::Replace($updatedLock, "(?m)^(\s*schema_version:\s*).*$", "`${1}$TargetSchemaVersion", 1)
$updatedLock = [regex]::Replace($updatedLock, "(?m)^(\s*locked_at:\s*).*$", "`${1}$lockedAt", 1)
Set-Content -Path $lockPath -Value $updatedLock -Encoding UTF8

$statusAfter = Invoke-Git -RepositoryPath $projectRoot -Arguments @("status", "--porcelain=v1")
Write-Host ""
Write-Host "Upgrade připraven. Změny:"
Write-Host $statusAfter

if ($Commit) {
    Invoke-Git -RepositoryPath $projectRoot -Arguments @("add", "-A") | Out-Null
    Invoke-Git -RepositoryPath $projectRoot -Arguments @("commit", "-m", "chore(ddda): upgrade accelerator lock") | Out-Null
    Write-Host "Projektový commit byl vytvořen. Push a PR zůstávají explicitním krokem uživatele."
} else {
    Write-Host "Změny nebyly commitnuty. Zkontroluj git diff a vytvoř projektový PR."
}
