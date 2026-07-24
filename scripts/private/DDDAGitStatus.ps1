Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-DDDAGitPorcelainPath {
    param([Parameter(Mandatory = $true)][string]$Line)

    if ([string]::IsNullOrWhiteSpace($Line)) {
        return $null
    }

    $candidate = $Line.TrimEnd()
    $path = $null

    # Standard porcelain v1 má dva status znaky a mezeru. Invoke-DDDAGit však
    # trimuje celý výstup, takže první řádek může ztratit počáteční mezeru
    # pracovního stromu (např. " M file" se změní na "M file").
    if ($candidate.Length -ge 3 -and $candidate[2] -eq ' ') {
        $path = $candidate.Substring(3)
    }
    elseif ($candidate -match '^[MADRCU?!]{1,2}\s+(?<path>.+)$') {
        $path = $Matches["path"]
    }
    else {
        throw "Nelze rozpoznat Git porcelain řádek: '$Line'"
    }

    if ($path -match ' -> ') {
        $path = ($path -split ' -> ')[-1]
    }

    return $path.Trim().Replace('\', '/')
}

function ConvertFrom-DDDAGitPorcelain {
    param([string]$PorcelainText)

    $entries = [System.Collections.Generic.List[object]]::new()
    foreach ($line in @($PorcelainText -split "`r?`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $entries.Add([pscustomobject]@{
            Line = $line
            Path = Get-DDDAGitPorcelainPath -Line $line
        })
    }

    return @($entries)
}

function Assert-DDDAGitChangesWithinPath {
    param(
        [string]$PorcelainText,
        [Parameter(Mandatory = $true)][string]$AllowedPrefix,
        [Parameter(Mandatory = $true)][string]$Label
    )

    $normalizedPrefix = $AllowedPrefix.Replace('\', '/').TrimStart('/')
    $unexpected = @(
        ConvertFrom-DDDAGitPorcelain -PorcelainText $PorcelainText |
            Where-Object { -not $_.Path.StartsWith($normalizedPrefix, [System.StringComparison]::OrdinalIgnoreCase) }
    )

    if ($unexpected.Count -gt 0) {
        throw "$Label obsahuje změny mimo '$normalizedPrefix':`n$($unexpected.Line -join "`n")"
    }

    return @(ConvertFrom-DDDAGitPorcelain -PorcelainText $PorcelainText)
}
