[CmdletBinding()]
param([string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PlatformPath "scripts/platform/DDDAPlatformSupport.ps1")
. (Join-Path $PlatformPath "scripts/platform/DDDAReleasePublicationSupport.ps1")

function Assert-True {
    param([Parameter(Mandatory = $true)][bool]$Condition, [Parameter(Mandatory = $true)][string]$Message)
    if (-not $Condition) { throw $Message }
}

$root = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-release-publication-" + [Guid]::NewGuid().ToString("N"))
try {
    New-Item -ItemType Directory -Path $root -Force | Out-Null
    $package = Join-Path $root "package.zip"
    $reportJson = Join-Path $root "result.json"
    $reportMarkdown = Join-Path $root "result.md"
    $changelog = Join-Path $root "CHANGELOG.md"
    [System.IO.File]::WriteAllText($package, "canonical package fixture")
    [System.IO.File]::WriteAllText($reportJson, '{"status":"PASS"}')
    [System.IO.File]::WriteAllText($reportMarkdown, "# PASS")
    [System.IO.File]::WriteAllText($changelog, "# Changelog`n`n## [Unreleased]`n`n## [1.2.3] - 2026-08-28`n`n### Added`n`n- A new governed capability.`n`n### Fixed`n`n- A release defect.")

    $descriptors = @(Get-DDDAReleasePublicationAssetDescriptors -Version "1.2.3" -PackagePath $package -ReportJsonPath $reportJson -ReportMarkdownPath $reportMarkdown)
    Assert-True -Condition ($descriptors.Count -eq 3) -Message "Publication contract musí mít právě package + dva release report assets."
    Assert-True -Condition ((@($descriptors.name) -join ',') -eq "ddda-1.2.3.zip,ddda-1.2.3-release-report.json,ddda-1.2.3-release-report.md") -Message "Asset names nejsou deterministické podle release verze."
    Assert-True -Condition ($descriptors[0].sha256 -eq (Get-DDDAPlatformFileHash -Path $package)) -Message "Package asset SHA-256 není fyzický hash vstupního package."
    $notes = Get-DDDAReleaseNotes -ChangelogPath $changelog -Version "1.2.3"
    Assert-True -Condition ($notes -match "Co je nové v DDDA 1.2.3" -and $notes -match "A new governed capability" -and $notes -match "A release defect") -Message "GitHub Release notes neobsahují versioned seznam funkcionalit a změn."
    $missingNotesRejected = $false
    [System.IO.File]::WriteAllText($changelog, "# Changelog`n`n## [Unreleased]`n`n## [1.2.3] - 2026-08-28")
    try { $null = Get-DDDAReleaseNotes -ChangelogPath $changelog -Version "1.2.3" } catch { $missingNotesRejected = $true }
    Assert-True -Condition $missingNotesRejected -Message "Prázdné release notes musí failnout před publikací."

    $goodAsset = [pscustomobject]@{ digest = "sha256:$($descriptors[0].sha256)"; browser_download_url = "https://example.invalid/package" }
    $badAsset = [pscustomobject]@{ digest = "sha256:$(('0' * 64))"; browser_download_url = "https://example.invalid/package" }
    Assert-True -Condition (Test-DDDAGitHubReleaseAssetHash -Asset $goodAsset -ExpectedSha256 $descriptors[0].sha256 -Token "not-used-for-digest") -Message "GitHub digest matching nebyl akceptován."
    Assert-True -Condition (-not (Test-DDDAGitHubReleaseAssetHash -Asset $badAsset -ExpectedSha256 $descriptors[0].sha256 -Token "not-used-for-digest")) -Message "Nesprávný GitHub digest nebyl odmítnut."

    $missingRejected = $false
    try { $null = Get-DDDAReleasePublicationAssetDescriptors -Version "1.2.3" -PackagePath $package -ReportJsonPath (Join-Path $root "missing.json") -ReportMarkdownPath $reportMarkdown } catch { $missingRejected = $true }
    Assert-True -Condition $missingRejected -Message "Chybějící publication input musí failnout před side effectem."

    $support = Get-Content -LiteralPath (Join-Path $PlatformPath "scripts/platform/DDDAReleasePublicationSupport.ps1") -Raw -Encoding UTF8
    $promotion = Get-Content -LiteralPath (Join-Path $PlatformPath "scripts/platform/Invoke-DDDAPromotePr.ps1") -Raw -Encoding UTF8
    $recovery = Get-Content -LiteralPath (Join-Path $PlatformPath "scripts/platform/Invoke-DDDARecoverGitHubRelease.ps1") -Raw -Encoding UTF8
    Assert-True -Condition ($support -match 'Fresh GitHub read-back' -and $support -match 'assets\?name=' -and $support -match 'se nesmí přepsat') -Message "Publication support nemá fail-closed read-back/asset contract."
    Assert-True -Condition ($promotion -match 'PortablePaths\s*=\s*\$true' -and $promotion -match 'Publish-DDDACanonicalGitHubRelease' -and $promotion -match 'ChangelogPath') -Message "Promotion nepublikuje portable validated evidence a versioned release notes po tagu."
    Assert-True -Condition ($recovery -match '\[switch\]\$ConfirmRecovery' -and $recovery -match 'if \(-not \$ConfirmRecovery\)' -and $recovery -match 'ChangelogPath') -Message "Recovery nemá explicitní authorization boundary a versioned release notes contract."
    Assert-True -Condition ($support -notmatch 'DELETE.+releases|Remove-DDDA.*Release|Delete-DDDA.*Asset') -Message "Publication contract nesmí obsahovat automatické přepsání Release/assets."
}
finally {
    Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "DDDA release publication contract: PASS"
