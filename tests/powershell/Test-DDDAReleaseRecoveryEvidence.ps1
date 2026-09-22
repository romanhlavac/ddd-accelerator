[CmdletBinding()]
param([string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

$scriptPath = Join-Path $PlatformPath "scripts/platform/Invoke-DDDARebuildReleaseEvidence.ps1"
Assert-True -Condition (Test-Path -LiteralPath $scriptPath -PathType Leaf) -Message "Chybí release recovery evidence rebuild script."
$content = Get-Content -LiteralPath $scriptPath -Raw -Encoding UTF8
Assert-True -Condition ($content -match 'Candidate validation report není exact PASS evidence' -and $content -match 'Candidate package SHA-256 neodpovídá') -Message "Recovery rebuild musí vázat candidate report a package hash."
Assert-True -Condition ($content -match 'checkout", "--detach", \$ReleaseSourceSha' -and $content -match 'Recovery checkout neodpovídá exact frozen release source SHA') -Message "Recovery rebuild musí checkoutnout exact frozen source SHA."
Assert-True -Condition ($content -match 'Kind = "release"' -and $content -match 'SourceKind = "release"') -Message "Recovery rebuild musí vytvářet release package a release report, ne candidate evidence."
Assert-True -Condition ($content -match '@\("smoke", "e2e", "acceptance"\)') -Message "Recovery rebuild musí znovu provést required release suites."
Assert-True -Condition ($content -notmatch 'Publish-DDDA|Invoke-RestMethod|gh api|git".*push|--delete') -Message "Recovery evidence rebuild nesmí mít GitHub/tag side effect."
Write-Host "DDDA release recovery evidence rebuild: PASS"
