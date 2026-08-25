Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-DDDAReleasePublicationAssetDescriptors {
    param(
        [Parameter(Mandatory = $true)][string]$Version,
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)][string]$ReportJsonPath,
        [Parameter(Mandatory = $true)][string]$ReportMarkdownPath
    )

    foreach ($item in @(
        [pscustomobject]@{ role = "package"; path = $PackagePath; name = "ddda-$Version.zip"; content_type = "application/zip" },
        [pscustomobject]@{ role = "release_report_json"; path = $ReportJsonPath; name = "ddda-$Version-release-report.json"; content_type = "application/json" },
        [pscustomobject]@{ role = "release_report_markdown"; path = $ReportMarkdownPath; name = "ddda-$Version-release-report.md"; content_type = "text/markdown" }
    )) {
        if (-not (Test-Path -LiteralPath $item.path -PathType Leaf)) {
            throw "Release publication asset '$($item.role)' neexistuje: $($item.path)"
        }
        [pscustomobject]@{
            role = $item.role
            path = (Resolve-Path -LiteralPath $item.path).Path
            name = $item.name
            content_type = $item.content_type
            sha256 = Get-DDDAPlatformFileHash -Path $item.path
        }
    }
}

function Get-DDDAGitHubReleaseByTag {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
        [Parameter(Mandatory = $true)][string]$Tag,
        [Parameter(Mandatory = $true)][string]$Token
    )

    try {
        return Invoke-DDDAGitHubApi -Method GET -Path "repos/$RepositorySlug/releases/tags/$Tag" -Token $Token
    }
    catch {
        if ($_.Exception.Message -match 'HTTP:\s*404') { return $null }
        throw
    }
}

function Assert-DDDACanonicalReleaseTagReadBack {
    param(
        [Parameter(Mandatory = $true)][string]$OriginUrl,
        [Parameter(Mandatory = $true)][string]$Tag,
        [Parameter(Mandatory = $true)][string]$ExpectedCommit
    )

    $lines = @(Invoke-DDDAPlatformNative -Command "git" -Arguments @("ls-remote", "--tags", $OriginUrl, "refs/tags/$Tag", "refs/tags/$Tag^{}"))
    $peeled = @($lines | Where-Object { $_ -match ("refs/tags/" + [regex]::Escape($Tag) + "\\^\\{\\}$") }) | Select-Object -First 1
    if ($null -eq $peeled) {
        throw "Fresh remote read-back neprokázal annotated canonical tag $Tag."
    }
    $actualCommit = ([string]$peeled -split "\s+")[0].Trim()
    if ($actualCommit -ne $ExpectedCommit) {
        throw "Canonical tag $Tag ukazuje na $actualCommit, očekáváno $ExpectedCommit."
    }
    return $actualCommit
}

function Assert-DDDAGitHubReleaseIdentity {
    param(
        [Parameter(Mandatory = $true)]$Release,
        [Parameter(Mandatory = $true)][string]$Tag,
        [Parameter(Mandatory = $true)][string]$Title
    )

    if ([string]$Release.tag_name -ne $Tag) { throw "GitHub Release tag neodpovídá $Tag." }
    if ([string]$Release.name -ne $Title) { throw "GitHub Release title neodpovídá '$Title'." }
    if ([bool]$Release.draft -or [bool]$Release.prerelease) { throw "GitHub Release musí být publikovaný finální release." }
}

function Test-DDDAGitHubReleaseAssetHash {
    param(
        [Parameter(Mandatory = $true)]$Asset,
        [Parameter(Mandatory = $true)][string]$ExpectedSha256,
        [Parameter(Mandatory = $true)][string]$Token
    )

    $digest = [string]$Asset.digest
    if ($digest -match '^sha256:(?<hash>[0-9a-fA-F]{64})$') {
        return $Matches['hash'].ToLowerInvariant() -eq $ExpectedSha256.ToLowerInvariant()
    }

    $downloadPath = [System.IO.Path]::GetTempFileName()
    try {
        Invoke-WebRequest -Method GET -Uri ([string]$Asset.browser_download_url) -Headers @{ Authorization = "Bearer $Token"; Accept = "application/octet-stream"; "User-Agent" = "DDDA-Platform-Release-Publication" } -OutFile $downloadPath -ErrorAction Stop | Out-Null
        return (Get-DDDAPlatformFileHash -Path $downloadPath) -eq $ExpectedSha256
    }
    finally {
        Remove-Item -LiteralPath $downloadPath -Force -ErrorAction SilentlyContinue
    }
}

function Publish-DDDAGitHubReleaseAsset {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
        [Parameter(Mandatory = $true)][int64]$ReleaseId,
        [Parameter(Mandatory = $true)]$Descriptor,
        [Parameter(Mandatory = $true)][string]$Token
    )

    $escapedName = [uri]::EscapeDataString([string]$Descriptor.name)
    $uri = "https://uploads.github.com/repos/$RepositorySlug/releases/$ReleaseId/assets?name=$escapedName"
    $headers = @{ Authorization = "Bearer $Token"; Accept = "application/vnd.github+json"; "X-GitHub-Api-Version" = "2022-11-28"; "User-Agent" = "DDDA-Platform-Release-Publication" }
    return Invoke-RestMethod -Method POST -Uri $uri -Headers $headers -ContentType ([string]$Descriptor.content_type) -InFile ([string]$Descriptor.path) -ErrorAction Stop
}

function Publish-DDDACanonicalGitHubRelease {
    param(
        [Parameter(Mandatory = $true)][string]$RepositorySlug,
        [Parameter(Mandatory = $true)][string]$OriginUrl,
        [Parameter(Mandatory = $true)][string]$Version,
        [Parameter(Mandatory = $true)][string]$Tag,
        [Parameter(Mandatory = $true)][string]$ReleaseSourceSha,
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)][string]$ReportJsonPath,
        [Parameter(Mandatory = $true)][string]$ReportMarkdownPath,
        [Parameter(Mandatory = $true)][string]$Token,
        [Parameter(Mandatory = $true)][string]$PublicationEvidencePath
    )

    if ($ReleaseSourceSha -notmatch '^[0-9a-f]{40}$') { throw "Release source SHA není platný." }
    $title = "DDDA $Version"
    $tagCommit = Assert-DDDACanonicalReleaseTagReadBack -OriginUrl $OriginUrl -Tag $Tag -ExpectedCommit $ReleaseSourceSha
    $assets = @(Get-DDDAReleasePublicationAssetDescriptors -Version $Version -PackagePath $PackagePath -ReportJsonPath $ReportJsonPath -ReportMarkdownPath $ReportMarkdownPath)
    $report = Get-Content -LiteralPath $ReportJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$report.status -ne "PASS" -or [string]$report.source.kind -ne "release" -or [string]$report.source.repository -ne $RepositorySlug -or [string]$report.source.commit -ne $ReleaseSourceSha) {
        throw "Release report není PASS evidence pro exact canonical release source."
    }
    $package = @($assets | Where-Object { $_.role -eq "package" })[0]
    if ([string]$report.package.sha256 -ne [string]$package.sha256) { throw "Release package SHA-256 neodpovídá release reportu." }

    $release = Get-DDDAGitHubReleaseByTag -RepositorySlug $RepositorySlug -Tag $Tag -Token $Token
    if ($null -eq $release) {
        $release = Invoke-DDDAGitHubApi -Method POST -Path "repos/$RepositorySlug/releases" -Token $Token -Body @{
            tag_name = $Tag
            target_commitish = $ReleaseSourceSha
            name = $title
            body = "Canonical DDDA product package and release evidence for `$Tag. GitHub automatic source archives are convenience source archives, not the canonical DDDA product package."
            draft = $false
            prerelease = $false
            generate_release_notes = $false
        }
    }
    Assert-DDDAGitHubReleaseIdentity -Release $release -Tag $Tag -Title $title

    foreach ($descriptor in $assets) {
        $existing = @($release.assets | Where-Object { [string]$_.name -eq [string]$descriptor.name })
        if ($existing.Count -gt 1) { throw "GitHub Release obsahuje více assets se jménem $($descriptor.name)." }
        if ($existing.Count -eq 1) {
            if (-not (Test-DDDAGitHubReleaseAssetHash -Asset $existing[0] -ExpectedSha256 $descriptor.sha256 -Token $Token)) {
                throw "Existující GitHub Release asset $($descriptor.name) nemá očekávaný SHA-256; asset se nesmí přepsat."
            }
            continue
        }
        $null = Publish-DDDAGitHubReleaseAsset -RepositorySlug $RepositorySlug -ReleaseId ([int64]$release.id) -Descriptor $descriptor -Token $Token
    }

    $readBack = Get-DDDAGitHubReleaseByTag -RepositorySlug $RepositorySlug -Tag $Tag -Token $Token
    if ($null -eq $readBack) { throw "Fresh GitHub read-back nenašel Release pro $Tag." }
    Assert-DDDAGitHubReleaseIdentity -Release $readBack -Tag $Tag -Title $title
    $evidenceAssets = [ordered]@{}
    foreach ($descriptor in $assets) {
        $asset = @($readBack.assets | Where-Object { [string]$_.name -eq [string]$descriptor.name })
        if ($asset.Count -ne 1 -or -not (Test-DDDAGitHubReleaseAssetHash -Asset $asset[0] -ExpectedSha256 $descriptor.sha256 -Token $Token)) {
            throw "Fresh read-back neprokázal správný obsah assetu $($descriptor.name)."
        }
        $evidenceAssets[$descriptor.role] = [ordered]@{ name = [string]$asset[0].name; sha256 = [string]$descriptor.sha256; id = [int64]$asset[0].id; url = [string]$asset[0].browser_download_url }
    }
    $evidence = [ordered]@{
        schema_version = 1
        repository = $RepositorySlug
        version = $Version
        release_source_sha = $ReleaseSourceSha
        tag = $Tag
        tag_read_back_sha = $tagCommit
        github_release = [ordered]@{ id = [int64]$readBack.id; url = [string]$readBack.html_url; title = $title }
        assets = $evidenceAssets
        publication_timestamp = (Get-Date).ToUniversalTime().ToString('o')
        publication_status = "PASS"
        server_read_back_status = "PASS"
    }
    Write-DDDAPlatformJson -Value $evidence -Path $PublicationEvidencePath -Depth 30
    return [pscustomobject]$evidence
}
