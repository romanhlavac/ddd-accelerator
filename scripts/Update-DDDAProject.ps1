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

function Replace-First {
    param(
        [Parameter(Mandatory = $true)][string]$InputText,
        [Parameter(Mandatory = $true)][string]$Pattern,
        [Parameter(Mandatory = $true)][string]$Replacement
    )
    $regex = [regex]::new($Pattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
    return $regex.Replace($InputText, $Replacement, 1)
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
    $migrationPath = Join-Path $platformRoot ("migrations/{0}-to-{1}.ps1" -f $from, $to)
    if (-not (Test-Path $migrationPath)) {
        throw "Chybí povinná migrace: $migrationPath"
    }

    Write-Host "Spouštím migraci schématu $from -> $to"
    & $migrationPath -ProjectPath $projectRoot
    $nextSchemaVersion = $to
}

$lockedAt = (Get-Date).ToUniversalTime().ToString("o")
$updatedLock = $lock
$updatedLock = Replace-First -InputText $updatedLock -Pattern "^(\s*ref:\s*).*$" -Replacement "`${1}$TargetRef"
$updatedLock = Replace-First -InputText $updatedLock -Pattern "^(\s*commit:\s*).*$" -Replacement "`${1}$targetCommit"
$updatedLock = Replace-First -InputText $updatedLock -Pattern "^(\s*schema_version:\s*).*$" -Replacement "`${1}$TargetSchemaVersion"
$updatedLock = Replace-First -InputText $updatedLock -Pattern "^(\s*locked_at:\s*).*$" -Replacement "`${1}$lockedAt"
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
