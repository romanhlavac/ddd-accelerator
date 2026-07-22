[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PlatformPath,
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [Parameter(Mandatory = $true)][ValidateSet("platform", "project")][string]$Scope,
    [switch]$RequireChanges
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([string]$RepositoryPath, [string[]]$Arguments)
    $output = & git -C $RepositoryPath @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Git selhal v '$RepositoryPath': git $($Arguments -join ' ')`n$output"
    }
    return ($output | Out-String).TrimEnd()
}

$platformRoot = Invoke-Git -RepositoryPath $PlatformPath -Arguments @("rev-parse", "--show-toplevel")
$projectRoot = Invoke-Git -RepositoryPath $ProjectPath -Arguments @("rev-parse", "--show-toplevel")

$platformFull = [System.IO.Path]::GetFullPath($platformRoot).TrimEnd('\', '/')
$projectFull = [System.IO.Path]::GetFullPath($projectRoot).TrimEnd('\', '/')

if ($platformFull -eq $projectFull) {
    throw "Platforma a projekt ukazují na stejný Git repozitář. DDDA vyžaduje oddělené repozitáře."
}

$separator = [System.IO.Path]::DirectorySeparatorChar
if ($projectFull.StartsWith($platformFull + $separator, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Projektový Git repozitář je vnořen uvnitř platformního repozitáře. Přesuň jej do sibling adresáře 'projects'."
}

$platformChanges = Invoke-Git -RepositoryPath $platformFull -Arguments @("status", "--porcelain=v1")
$projectChanges = Invoke-Git -RepositoryPath $projectFull -Arguments @("status", "--porcelain=v1")

$platformDirty = -not [string]::IsNullOrWhiteSpace($platformChanges)
$projectDirty = -not [string]::IsNullOrWhiteSpace($projectChanges)

if ($Scope -eq "platform" -and $projectDirty) {
    throw "Scope je 'platform', ale projektový repozitář obsahuje změny:`n$projectChanges`nCommitni, stashni nebo vrať projektové změny před platformním commitem."
}

if ($Scope -eq "project" -and $platformDirty) {
    throw "Scope je 'project', ale platformní repozitář obsahuje změny:`n$platformChanges`nCommitni, stashni nebo vrať platformní změny před projektovým commitem."
}

$selectedDirty = if ($Scope -eq "platform") { $platformDirty } else { $projectDirty }
if ($RequireChanges -and -not $selectedDirty) {
    throw "Vybraný scope '$Scope' neobsahuje žádné změny."
}

Write-Host "Repository scope je konzistentní."
Write-Host "Scope:     $Scope"
Write-Host "Platforma: $platformFull"
Write-Host "Projekt:   $projectFull"

if ($Scope -eq "platform") {
    if ($platformDirty) {
        Write-Host "Platformní změny:"
        Write-Host $platformChanges
    } else {
        Write-Host "Platformní repozitář je čistý."
    }
} else {
    if ($projectDirty) {
        Write-Host "Projektové změny:"
        Write-Host $projectChanges
    } else {
        Write-Host "Projektový repozitář je čistý."
    }
}
