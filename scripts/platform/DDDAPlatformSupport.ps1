Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-DDDAPlatformIsWindows {
    return ($env:OS -eq "Windows_NT" -or $PSVersionTable.PSEdition -eq "Desktop")
}

function Get-DDDAPlatformStateRoot {
    if (Test-DDDAPlatformIsWindows) {
        if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
            throw "LOCALAPPDATA není dostupné; nelze určit lokální DDDA state adresář."
        }
        return (Join-Path $env:LOCALAPPDATA "DDDA")
    }

    if (-not [string]::IsNullOrWhiteSpace($env:XDG_STATE_HOME)) {
        return (Join-Path $env:XDG_STATE_HOME "ddda")
    }

    $homePath = [Environment]::GetFolderPath("UserProfile")
    if ([string]::IsNullOrWhiteSpace($homePath)) {
        throw "Nelze určit domovský adresář pro DDDA state."
    }
    return (Join-Path $homePath ".local/state/ddda")
}

function Invoke-DDDAPlatformNative {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory
    )

    $previousPreference = $ErrorActionPreference
    $previousLocation = $null
    $exitCode = 1
    $output = @()
    try {
        $ErrorActionPreference = "Continue"
        if (-not [string]::IsNullOrWhiteSpace($WorkingDirectory)) {
            $previousLocation = Get-Location
            Set-Location -LiteralPath $WorkingDirectory
        }
        $output = @(& $Command @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        if ($null -ne $previousLocation) {
            Set-Location -LiteralPath $previousLocation.Path
        }
        $ErrorActionPreference = $previousPreference
    }

    $text = ($output | ForEach-Object { $_.ToString() } | Out-String).Trim()
    if ($exitCode -ne 0) {
        throw ("Příkaz selhal: {0} {1}`nExit code: {2}`n{3}" -f $Command, ($Arguments -join " "), $exitCode, $text)
    }

    return $text
}

function Invoke-DDDAPlatformGit {
    param(
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    return Invoke-DDDAPlatformNative -Command "git" -Arguments (@("-C", $Repository) + $Arguments)
}

function Assert-DDDAPlatformCleanGit {
    param(
        [Parameter(Mandatory = $true)][string]$Repository,
        [string]$Label = "Platformní"
    )

    $status = Invoke-DDDAPlatformGit -Repository $Repository -Arguments @("status", "--porcelain")
    if (-not [string]::IsNullOrWhiteSpace($status)) {
        throw "$Label repozitář není čistý:`n$status"
    }
}

function Get-DDDAPlatformGitRoot {
    param([Parameter(Mandatory = $true)][string]$Path)

    $root = Invoke-DDDAPlatformGit -Repository $Path -Arguments @("rev-parse", "--show-toplevel")
    return [System.IO.Path]::GetFullPath($root).TrimEnd('\', '/')
}

function Get-DDDAPlatformRepositoryUrl {
    param([Parameter(Mandatory = $true)][string]$Repository)

    return Invoke-DDDAPlatformGit -Repository $Repository -Arguments @("remote", "get-url", "origin")
}

function Get-DDDAPlatformRepositorySlug {
    param([Parameter(Mandatory = $true)][string]$RepositoryUrl)

    $value = $RepositoryUrl.Trim()
    if ($value -match '^https://github\.com/(?<slug>[^/]+/[^/]+?)(?:\.git)?$') {
        return $Matches["slug"]
    }
    if ($value -match '^git@github\.com:(?<slug>[^/]+/[^/]+?)(?:\.git)?$') {
        return $Matches["slug"]
    }
    if ($value -match '^ssh://git@github\.com/(?<slug>[^/]+/[^/]+?)(?:\.git)?$') {
        return $Matches["slug"]
    }
    throw "Origin remote není podporovaný GitHub repository URL: $RepositoryUrl"
}

function Assert-DDDAPlatformPathWithin {
    param(
        [Parameter(Mandatory = $true)][string]$CandidatePath,
        [Parameter(Mandatory = $true)][string]$AllowedRoot,
        [string]$Label = "Cesta"
    )

    $candidate = [System.IO.Path]::GetFullPath($CandidatePath)
    $root = [System.IO.Path]::GetFullPath($AllowedRoot).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    if (-not $candidate.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label opouští povolený root. Cesta: $candidate; root: $AllowedRoot"
    }
    return $candidate
}

function New-DDDAPlatformCleanDirectory {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$AllowedRoot
    )

    $full = Assert-DDDAPlatformPathWithin -CandidatePath $Path -AllowedRoot $AllowedRoot -Label "Adresář"
    if (Test-Path -LiteralPath $full) {
        Remove-Item -LiteralPath $full -Recurse -Force
    }
    New-Item -ItemType Directory -Path $full -Force | Out-Null
    return $full
}

function Get-DDDAPlatformFileHash {
    param([Parameter(Mandatory = $true)][string]$Path)

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-DDDAPlatformTimestamp {
    return (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
}

function Get-DDDAPlatformIsoTimestamp {
    return (Get-Date).ToUniversalTime().ToString("o")
}

function Write-DDDAPlatformJson {
    param(
        [Parameter(Mandatory = $true)][AllowNull()][object]$Value,
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$Depth = 30
    )

    $json = ConvertTo-Json -InputObject $Value -Depth $Depth
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $json + [Environment]::NewLine, $utf8)
}

function Write-DDDAPlatformText {
    param(
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Value, $utf8)
}

function Invoke-DDDAPlatformChildPowerShell {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string[]]$Arguments = @()
    )

    $hostExe = (Get-Process -Id $PID).Path
    $hostArguments = @("-NoProfile")
    if (Test-DDDAPlatformIsWindows) {
        $hostArguments += @("-ExecutionPolicy", "Bypass")
    }
    $hostArguments += @("-File", $ScriptPath)
    $hostArguments += $Arguments

    $previousPreference = $ErrorActionPreference
    $exitCode = 1
    try {
        $ErrorActionPreference = "Continue"
        & $hostExe @hostArguments
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    if ($exitCode -ne 0) {
        throw "PowerShell skript selhal: $ScriptPath. Exit code: $exitCode"
    }
}

function Get-DDDAPlatformPythonCommand {
    foreach ($candidate in @("python", "py")) {
        if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) {
            continue
        }
        try {
            $null = Invoke-DDDAPlatformNative -Command $candidate -Arguments @("--version")
            return $candidate
        }
        catch {
        }
    }
    throw "Nebyl nalezen funkční Python. DDDA vyžaduje Python 3.11 nebo novější."
}

function Assert-DDDAPlatformSemanticVersion {
    param([Parameter(Mandatory = $true)][string]$Version)

    if ($Version -notmatch '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$') {
        throw "Neplatná Semantic Version: $Version"
    }
}
