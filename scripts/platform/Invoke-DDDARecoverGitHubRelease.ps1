[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$ReleaseSourceSha,
    [Parameter(Mandatory = $true)][string]$ReleasePackagePath,
    [Parameter(Mandatory = $true)][string]$ReleaseReportJsonPath,
    [Parameter(Mandatory = $true)][string]$ReleaseReportMarkdownPath,
    [switch]$ConfirmRecovery
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "DDDAPlatformSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAGitHubSupport.ps1")
. (Join-Path $PSScriptRoot "DDDAReleasePublicationSupport.ps1")

if (-not $ConfirmRecovery) {
    throw "GitHub Release recovery vyžaduje explicitní -ConfirmRecovery authorization."
}
Assert-DDDAPlatformSemanticVersion -Version $Version
if ($ReleaseSourceSha -notmatch '^[0-9a-f]{40}$') { throw "ReleaseSourceSha není plný SHA." }
$platformRoot = Get-DDDAPlatformGitRoot -Path $PlatformPath
Assert-DDDAPlatformCleanGit -Repository $platformRoot
$originUrl = Get-DDDAPlatformRepositoryUrl -Repository $platformRoot
$repositorySlug = Get-DDDAPlatformRepositorySlug -RepositoryUrl $originUrl
$githubAuth = Get-DDDAGitHubAuthentication
$tag = "v$Version"
$evidenceRoot = Join-Path (Get-DDDAPlatformStateRoot) ("release-publication-recovery/$Version/" + (Get-DDDAPlatformTimestamp))
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

$publication = Publish-DDDACanonicalGitHubRelease `
    -RepositorySlug $repositorySlug `
    -OriginUrl $originUrl `
    -Version $Version `
    -Tag $tag `
    -ReleaseSourceSha $ReleaseSourceSha `
    -PackagePath $ReleasePackagePath `
    -ReportJsonPath $ReleaseReportJsonPath `
    -ReportMarkdownPath $ReleaseReportMarkdownPath `
    -Token $githubAuth.Token `
    -PublicationEvidencePath (Join-Path $evidenceRoot "publication.json")

Write-Host "DDDA GitHub Release recovery: PASS"
Write-Host "Release: $($publication.github_release.url)"
Write-Host "Evidence: $(Join-Path $evidenceRoot 'publication.json')"
