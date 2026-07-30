[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $RepositoryRoot).Path).TrimEnd('\', '/')
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Get-NormalizedText {
    param([Parameter(Mandatory = $true)][string]$RelativePath)

    $path = Join-Path $root $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required file does not exist: $RelativePath"
    }
    return [System.IO.File]::ReadAllText($path).Replace("`r`n", "`n")
}

function Write-NormalizedText {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string]$Text
    )

    $path = Join-Path $root $RelativePath
    $parent = Split-Path -Parent $path
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($path, $Text.Replace("`r`n", "`n"), $utf8)
}

function Replace-ExactOnce {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string]$OldText,
        [Parameter(Mandatory = $true)][string]$NewText
    )

    $text = Get-NormalizedText -RelativePath $RelativePath
    $old = $OldText.Replace("`r`n", "`n")
    $new = $NewText.Replace("`r`n", "`n")
    $count = [regex]::Matches($text, [regex]::Escape($old)).Count
    if ($count -ne 1) {
        throw "Expected exactly one replacement target in '$RelativePath'; found $count."
    }
    Write-NormalizedText -RelativePath $RelativePath -Text $text.Replace($old, $new)
}

function Write-Base64File {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string]$Base64
    )

    $bytes = [Convert]::FromBase64String($Base64)
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    Write-NormalizedText -RelativePath $RelativePath -Text $text
}

$actualRoot = (& git -C $root rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or [System.IO.Path]::GetFullPath($actualRoot).TrimEnd('\', '/') -ne $root) {
    throw "RepositoryRoot is not the DDDA Git root."
}
$changesBefore = (& git -C $root status --porcelain | Out-String).Trim()
if (-not [string]::IsNullOrWhiteSpace($changesBefore)) {
    throw "Repository must be clean before REM-003:`n$changesBefore"
}

Replace-ExactOnce -RelativePath "scripts/platform/Invoke-DDDAValidatePr.ps1" -OldText @'
    Write-Host "=== Validation suite: $Name ==="
    $previousPreference = $ErrorActionPreference
    $exitCode = 1
    try {
        $ErrorActionPreference = "Continue"
        & $hostExe @hostArguments *> $logPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
        $suiteStarted.Stop()
    }
'@ -NewText @'
    Write-Host "=== Validation suite: $Name ==="
    $sanitizedEnvironmentNames = @(
        "PYTHONPATH",
        "PYTHONHOME",
        "DDDA_PLATFORM_ROOT",
        "DDDA_REPO_ROOT"
    )
    $savedEnvironment = @{}
    $previousPreference = $ErrorActionPreference
    $exitCode = 1
    try {
        foreach ($environmentName in $sanitizedEnvironmentNames) {
            $environmentPath = "Env:\$environmentName"
            if (Test-Path -LiteralPath $environmentPath) {
                $savedEnvironment[$environmentName] = [string](Get-Item -LiteralPath $environmentPath).Value
                Remove-Item -LiteralPath $environmentPath
            }
        }
        $ErrorActionPreference = "Continue"
        & $hostExe @hostArguments *> $logPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        foreach ($environmentName in $sanitizedEnvironmentNames) {
            Remove-Item -LiteralPath "Env:\$environmentName" -ErrorAction SilentlyContinue
            if ($savedEnvironment.ContainsKey($environmentName)) {
                Set-Item -LiteralPath "Env:\$environmentName" -Value $savedEnvironment[$environmentName]
            }
        }
        $ErrorActionPreference = $previousPreference
        $suiteStarted.Stop()
    }
'@

Replace-ExactOnce -RelativePath "scripts/Initialize-DDDAAfterClone.ps1" -OldText @'
& $steeringPython -m ddda_steering --help *> $null
Assert-DDDALastExitCode -Operation "Ověření DDDA steering CLI"
& $miroPython -m ddda_miro --help *> $null
'@ -NewText @'
& $steeringPython -I -m ddda_steering --help *> $null
Assert-DDDALastExitCode -Operation "Ověření DDDA steering CLI"
& $miroPython -I -m ddda_miro --help *> $null
'@

Replace-ExactOnce -RelativePath "scripts/Initialize-DDDAProjectMiro.ps1" -OldText @'
    [switch]$NonInteractive,
    [switch]$Resume
)
'@ -NewText @'
    [switch]$NonInteractive,
    [switch]$Resume,
    [switch]$SuppressCommitInstructions
)
'@

Replace-ExactOnce -RelativePath "scripts/Initialize-DDDAProjectMiro.ps1" -OldText @'
        $raw = @(& $script:MiroPython -m ddda_miro --project $script:ProjectRoot --platform $script:PlatformRoot @CommandArguments 2>&1)
'@ -NewText @'
        $raw = @(& $script:MiroPython -I -m ddda_miro --project $script:ProjectRoot --platform $script:PlatformRoot @CommandArguments 2>&1)
'@

Replace-ExactOnce -RelativePath "scripts/Initialize-DDDAProjectMiro.ps1" -OldText @'
    if (-not (Test-Path $script:MiroPython)) {
        throw "DDDA Miro runtime nebyl vytvořen: $($script:MiroPython)"
    }

    Write-Host "=== Projektový Miro preflight ==="
'@ -NewText @'
    if (-not (Test-Path $script:MiroPython)) {
        throw "DDDA Miro runtime nebyl vytvořen: $($script:MiroPython)"
    }

    $packageManifestPath = Join-Path $script:PlatformRoot "ddda-package.json"
    if (Test-Path -LiteralPath $packageManifestPath -PathType Leaf) {
        $packageManifest = Get-Content -LiteralPath $packageManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $sourceCommit = [string]$packageManifest.source_commit
        $renderPath = Join-Path $script:PlatformRoot "runtime/miro/ddda_miro/render.py"
        $renderText = Get-Content -LiteralPath $renderPath -Raw -Encoding UTF8
        if ($renderText -notmatch 'RENDER_CONTRACT_VERSION\s*=\s*"(?<version>[^"]+)"') {
            throw "Candidate package renderer neobsahuje RENDER_CONTRACT_VERSION."
        }
        $expectedContract = [string]$Matches["version"]
        $scaffoldPath = Join-Path $script:PlatformRoot "scaffolds/miro/strategic-ddd-method-board.yaml"
        $scaffoldHash = (Get-FileHash -LiteralPath $scaffoldPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $provenanceEvidencePath = Join-Path $script:ProjectRoot "reports/miro-sync/runtime-provenance.json"
        $provenanceText = & (Join-Path $script:PlatformRoot "scripts/platform/Assert-DDDAMiroRuntimeProvenance.ps1") `
            -PlatformPath $script:PlatformRoot `
            -ExpectedRenderContractVersion $expectedContract `
            -ExpectedSourceCommit $sourceCommit `
            -ExpectedScaffoldSha256 $scaffoldHash `
            -EvidencePath $provenanceEvidencePath `
            -Json | Out-String
        if ($LASTEXITCODE -ne 0) {
            throw "Miro runtime provenance guard selhal před prvním vzdáleným zápisem."
        }
        $provenance = $provenanceText.Trim() | ConvertFrom-Json
        if ([string]$provenance.status -ne "PASS" -or -not [bool]$provenance.checked_before_remote_write) {
            throw "Miro runtime provenance guard nevrátil PASS."
        }
    }

    Write-Host "=== Projektový Miro preflight ==="
'@

Replace-ExactOnce -RelativePath "scripts/Initialize-DDDAProjectMiro.ps1" -OldText @'
        Write-Host "Zkontroluj diff a commitni Miro mapping, sync state a sync report v projektovém repozitáři:"
        Write-Host "  git -C `"$($script:ProjectRoot)`" diff -- miro/ reports/miro-sync/"
        Write-Host "  git -C `"$($script:ProjectRoot)`" add miro/miro-map.yaml miro/sync-state.yaml reports/miro-sync/"
        Write-Host "  git -C `"$($script:ProjectRoot)`" commit -m `"chore: initialize project Miro board and managed artifacts`""
'@ -NewText @'
        if ($SuppressCommitInstructions) {
            Write-Host "Projektové změny jsou diagnostický výstup acceptance běhu."
            Write-Host "Necommituj je, dokud nadřazený acceptance report není technicky PASS."
        }
        else {
            Write-Host "Zkontroluj diff a commitni Miro mapping, sync state a sync report v projektovém repozitáři:"
            Write-Host "  git -C `"$($script:ProjectRoot)`" diff -- miro/ reports/miro-sync/"
            Write-Host "  git -C `"$($script:ProjectRoot)`" add miro/miro-map.yaml miro/sync-state.yaml reports/miro-sync/"
            Write-Host "  git -C `"$($script:ProjectRoot)`" commit -m `"chore: initialize project Miro board and managed artifacts`""
        }
'@

Replace-ExactOnce -RelativePath "scripts/Test-DDDAAcceptance.ps1" -OldText @'
$platformSourceCommit = $null
$scaffoldSha256 = $null
$remoteItemCount = 0
'@ -NewText @'
$platformSourceCommit = $null
$scaffoldSha256 = $null
$runtimeProvenanceStatus = if ($WithMiro) { "FAIL" } else { "NOT_RUN" }
$runtimeProvenanceEvidencePath = Join-Path $reportRoot "runtime-provenance.json"
$runtimeProvenance = $null
$remoteItemCount = 0
'@

Replace-ExactOnce -RelativePath "scripts/Test-DDDAAcceptance.ps1" -OldText @'
        platform_source_commit = $platformSourceCommit
        scaffold_sha256 = $scaffoldSha256
        remote_item_count = $remoteItemCount
'@ -NewText @'
        platform_source_commit = $platformSourceCommit
        scaffold_sha256 = $scaffoldSha256
        runtime_provenance_status = $runtimeProvenanceStatus
        runtime_provenance = $runtimeProvenance
        remote_item_count = $remoteItemCount
'@

Replace-ExactOnce -RelativePath "scripts/Test-DDDAAcceptance.ps1" -OldText @'
    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAAfterClone.ps1") -Arguments @("-PlatformPath", $platformRoot, "-NonInteractive")
    if ($WithMiro -and $Full) {
'@ -NewText @'
    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAAfterClone.ps1") -Arguments @("-PlatformPath", $platformRoot, "-NonInteractive")
    if ($WithMiro) {
        $provenanceText = & (Join-Path $platformRoot "scripts/platform/Assert-DDDAMiroRuntimeProvenance.ps1") `
            -PlatformPath $platformRoot `
            -ExpectedRenderContractVersion $renderContractVersion `
            -ExpectedSourceCommit $platformSourceCommit `
            -ExpectedScaffoldSha256 $scaffoldSha256 `
            -EvidencePath $runtimeProvenanceEvidencePath `
            -Json | Out-String
        if ($LASTEXITCODE -ne 0) {
            throw "Miro runtime provenance guard selhal před prvním vzdáleným zápisem."
        }
        $runtimeProvenance = $provenanceText.Trim() | ConvertFrom-Json
        if ([string]$runtimeProvenance.status -ne "PASS") {
            throw "Miro runtime provenance guard nevrátil PASS."
        }
        if (-not [bool]$runtimeProvenance.checked_before_remote_write) {
            throw "Miro runtime provenance nebyla ověřena před vzdáleným zápisem."
        }
        $runtimeProvenanceStatus = "PASS"
    }
    if ($WithMiro -and $Full) {
'@

Replace-ExactOnce -RelativePath "scripts/Test-DDDAAcceptance.ps1" -OldText @'
            "-ProjectId", "acceptance-claims-modernization",
            "-CreateBoard"
        )
'@ -NewText @'
            "-ProjectId", "acceptance-claims-modernization",
            "-CreateBoard",
            "-SuppressCommitInstructions"
        )
'@

Replace-ExactOnce -RelativePath "scripts/Test-DDDAAcceptance.ps1" -OldText @'
        Write-Host "Render contract: $renderContractVersion PASS"
        Write-Host "Platform source: $platformSourceCommit"
'@ -NewText @'
        Write-Host "Render contract: $renderContractVersion PASS"
        Write-Host "Runtime provenance: $runtimeProvenanceStatus"
        Write-Host "Platform source: $platformSourceCommit"
'@

Replace-ExactOnce -RelativePath "scripts/Test-DDDAAcceptance.ps1" -OldText @'
    Write-AcceptanceReport -Status "FAIL" -ErrorMessage $_.Exception.Message -GateStatus $g1Status
    Write-Host "Acceptance workspace zachován pro diagnostiku: $workspaceRoot"
'@ -NewText @'
    Write-AcceptanceReport -Status "FAIL" -ErrorMessage $_.Exception.Message -GateStatus $g1Status
    if ($WithMiro) {
        Write-Host "Generated Miro project changes are invalid diagnostic output. Do not commit." -ForegroundColor Yellow
    }
    Write-Host "Acceptance workspace zachován pro diagnostiku: $workspaceRoot"
'@

Replace-ExactOnce -RelativePath "scripts/platform/Invoke-DDDAPlatformTest.ps1" -OldText @'
            Invoke-RepositoryValidator -ValidationSuite "security"
            Invoke-TestScript -RelativePath "tests/powershell/Test-DDDAPlatformSecurity.ps1" -Arguments @("-PlatformPath", $platformRoot)
            if (-not [string]::IsNullOrWhiteSpace($PackagePath)) {
'@ -NewText @'
            Invoke-RepositoryValidator -ValidationSuite "security"
            Invoke-TestScript -RelativePath "tests/powershell/Test-DDDAPlatformSecurity.ps1" -Arguments @("-PlatformPath", $platformRoot)
            Invoke-TestScript -RelativePath "tests/powershell/Test-DDDARuntimeIsolation.ps1" -Arguments @("-PlatformPath", $platformRoot)
            if (-not [string]::IsNullOrWhiteSpace($PackagePath)) {
'@

$policyPath = "config/platform/development-policy.yaml"
$policy = Get-NormalizedText -RelativePath $policyPath | ConvertFrom-Json
if ($null -ne $policy.PSObject.Properties["remote_execution"]) {
    throw "development-policy.yaml already contains remote_execution."
}
$remoteExecution = [pscustomobject][ordered]@{
    schema_version = 1
    enabled = $true
    allowed_actors = @("romanhlavac")
    same_repository_only = $true
    exact_sha_required = $true
    miro_team_id = "3458764678971681560"
    required_secret_names = @("MIRO_ACCESS_TOKEN")
    allowed_validate_commands = @("/ddda validate-pr --with-miro --full --keep-review-board")
    remediation = [pscustomobject][ordered]@{
        enabled = $true
        allowed_path_prefix = "scripts/remediation/"
        require_no_push_switch = $true
        maximum_new_commits = 1
    }
    forbidden_operations = @("merge", "tag", "release", "promotion", "force-push")
    evidence_retention_days = 14
}
$policy | Add-Member -NotePropertyName remote_execution -NotePropertyValue $remoteExecution
Write-NormalizedText -RelativePath $policyPath -Text (($policy | ConvertTo-Json -Depth 20) + "`n")

$platformCiPath = ".github/workflows/platform-ci.yml"
$platformCi = Get-NormalizedText -RelativePath $platformCiPath
if ($platformCi -match '(?m)^  online-miro-acceptance:\s*$') {
    throw "platform-ci.yml already contains online-miro-acceptance."
}
$onlineJob = @'

  online-miro-acceptance:
    name: Online Miro acceptance
    if: >-
      github.event_name == 'pull_request' &&
      github.event.action == 'synchronize' &&
      github.event.pull_request.number == 8 &&
      github.actor == 'romanhlavac' &&
      github.event.pull_request.head.repo.full_name == github.repository
    runs-on: windows-latest
    timeout-minutes: 120
    permissions:
      contents: read
      issues: write
      pull-requests: write
    env:
      SOURCE_SHA: ${{ github.event.pull_request.head.sha }}
      PR_NUMBER: ${{ github.event.pull_request.number }}
      MIRO_TEAM_ID: "3458764678971681560"

    steps:
      - name: Checkout exact PR head
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          ref: ${{ env.SOURCE_SHA }}

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Check online secret availability
        id: online-secret
        shell: pwsh
        env:
          MIRO_ACCESS_TOKEN: ${{ secrets.MIRO_ACCESS_TOKEN }}
        run: |
          if ([string]::IsNullOrWhiteSpace($env:MIRO_ACCESS_TOKEN)) {
            "available=false" | Out-File -FilePath $env:GITHUB_OUTPUT -Encoding utf8 -Append
            "MIRO_ACCESS_TOKEN is not configured; online acceptance is skipped." | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
          }
          else {
            "available=true" | Out-File -FilePath $env:GITHUB_OUTPUT -Encoding utf8 -Append
          }

      - name: Run exact-SHA online acceptance
        if: steps.online-secret.outputs.available == 'true'
        shell: pwsh
        env:
          MIRO_ACCESS_TOKEN: ${{ secrets.MIRO_ACCESS_TOKEN }}
          GH_TOKEN: ${{ github.token }}
        run: |
          $ErrorActionPreference = 'Stop'
          $actual = (git rev-parse HEAD).Trim()
          if ($actual -ne $env:SOURCE_SHA) {
            throw "Checkout SHA '$actual' neodpovídá PR head '$env:SOURCE_SHA'."
          }
          .\ddda.ps1 validate-pr `
            -Pr ([int]$env:PR_NUMBER) `
            -WithMiro `
            -Full `
            -KeepReviewBoard `
            -MiroTeamId $env:MIRO_TEAM_ID `
            -NonInteractive

      - name: Stage online acceptance evidence
        if: always() && steps.online-secret.outputs.available == 'true'
        shell: pwsh
        run: |
          $target = Join-Path $env:RUNNER_TEMP 'online-miro-acceptance'
          New-Item -ItemType Directory -Path $target -Force | Out-Null
          foreach ($source in @(
            (Join-Path $env:LOCALAPPDATA "DDDA\validation-reports"),
            (Join-Path $env:LOCALAPPDATA "DDDA\acceptance-reports")
          )) {
            if (Test-Path -LiteralPath $source) {
              Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
            }
          }

      - name: Upload online acceptance evidence
        if: always() && steps.online-secret.outputs.available == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: online-miro-acceptance-${{ env.PR_NUMBER }}-${{ env.SOURCE_SHA }}
          path: ${{ runner.temp }}/online-miro-acceptance/**
          if-no-files-found: warn
          retention-days: 14
'@
Write-NormalizedText -RelativePath $platformCiPath -Text ($platformCi.TrimEnd() + $onlineJob + "`n")

Replace-ExactOnce -RelativePath "CHANGELOG.md" -OldText @'
### Fixed

- lidské visual review už nemůže zaměnit gate state za lifecycle nebo provenance artefaktu;
'@ -NewText @'
### Fixed

- candidate-package validation sanitizuje ambientní `PYTHONPATH`, `PYTHONHOME` a DDDA root proměnné před spuštěním child procesů;
- Miro CLI běží v Python isolated mode a před prvním vzdáleným zápisem ověřuje skutečně importovaný modul, jeho SHA-256 a render contract;
- GitHub Actions remote-execution broker umožňuje oprávněnému actorovi spouštět exact-SHA validation/acceptance bez předání Miro tokenu do ChatGPT runtime;
- lidské visual review už nemůže zaměnit gate state za lifecycle nebo provenance artefaktu;
'@

Write-Base64File -RelativePath "scripts/platform/Assert-DDDAMiroRuntimeProvenance.ps1" -Base64 "W0NtZGxldEJpbmRpbmcoKV0KcGFyYW0oCiAgICBbUGFyYW1ldGVyKE1hbmRhdG9yeSA9ICR0cnVlKV1bc3RyaW5nXSRQbGF0Zm9ybVBhdGgsCiAgICBbUGFyYW1ldGVyKE1hbmRhdG9yeSA9ICR0cnVlKV1bc3RyaW5nXSRFeHBlY3RlZFJlbmRlckNvbnRyYWN0VmVyc2lvbiwKICAgIFtQYXJhbWV0ZXIoTWFuZGF0b3J5ID0gJHRydWUpXVtWYWxpZGF0ZVBhdHRlcm4oJ15bMC05YS1mXXs0MH0kJyldW3N0cmluZ10kRXhwZWN0ZWRTb3VyY2VDb21taXQsCiAgICBbUGFyYW1ldGVyKE1hbmRhdG9yeSA9ICR0cnVlKV1bVmFsaWRhdGVQYXR0ZXJuKCdeWzAtOWEtZl17NjR9JCcpXVtzdHJpbmddJEV4cGVjdGVkU2NhZmZvbGRTaGEyNTYsCiAgICBbUGFyYW1ldGVyKE1hbmRhdG9yeSA9ICR0cnVlKVtzdHJpbmddJEV2aWRlbmNlUGF0aCwKICAgIFtzd2l0Y2hdJEpzb24KKQoKU2V0LVN0cmljdE1vZGUgLVZlcnNpb24gTGF0ZXN0CiRFcnJvckFjdGlvblByZWZlcmVuY2UgPSAiU3RvcCIKCiRwbGF0Zm9ybVJvb3QgPSBbU3lzdGVtLklPLlBhdGhdOjpHZXRGdWxsUGF0aCgoUmVzb2x2ZS1QYXRoIC1MaXRlcmFsUGF0aCAkUGxhdGZvcm1QYXRoKS5QYXRoKS5UcmltRW5kKCdcJywgJy8nKQokcHl0aG9uUGF0aCA9IGlmICgkZW52Ok9TIC1lcSAiV2luZG93c19OVCIpIHsKICAgIEpvaW4tUGF0aCAkcGxhdGZvcm1Sb290ICIuZGRkYS9ydW50aW1lL21pcm8tdmVudi9TY3JpcHRzL3B5dGhvbi5leGUiCn0KZWxzZSB7CiAgICBKb2luLVBhdGggJHBsYXRmb3JtUm9vdCAiLmRkZGEvcnVudGltZS9taXJvLXZlbnYvYmluL3B5dGhvbiIKfQokZXhwZWN0ZWRNb2R1bGVQYXRoID0gW1N5c3RlbS5JTy5QYXRoXTo6R2V0RnVsbFBhdGgoKEpvaW4tUGF0aCAkcGxhdGZvcm1Sb290ICJydW50aW1lL21pcm8vZGRkYV9taXJvL3JlbmRlci5weSIpKQokZXZpZGVuY2VGdWxsUGF0aCA9IFtTeXN0ZW0uSU8uUGF0aF06OkdldEZ1bGxQYXRoKCRFdmlkZW5jZVBhdGgpCiRldmlkZW5jZVJvb3QgPSBTcGxpdC1QYXRoIC1QYXJlbnQgJGV2aWRlbmNlRnVsbFBhdGgKTmV3LUl0ZW0gLUl0ZW1UeXBlIERpcmVjdG9yeSAtUGF0aCAkZXZpZGVuY2VSb290IC1Gb3JjZSB8IE91dC1OdWxsCgokZXZpZGVuY2UgPSBbb3JkZXJlZF1AewogICAgc3RhdHVzID0gIkZBSUwiCiAgICBjaGVja2VkX2JlZm9yZV9yZW1vdGVfd3JpdGUgPSAkdHJ1ZQogICAgcHl0aG9uX2V4ZWN1dGFibGUgPSAkcHl0aG9uUGF0aAogICAgc3lzX3ByZWZpeCA9ICRudWxsCiAgICBpbXBvcnRlZF9tb2R1bGVfcGF0aCA9ICRudWxsCiAgICBleHBlY3RlZF9tb2R1bGVfcGF0aCA9ICRleHBlY3RlZE1vZHVsZVBhdGgKICAgIGltcG9ydGVkX21vZHVsZV9zaGEyNTYgPSAkbnVsbAogICAgZXhwZWN0ZWRfbW9kdWxlX3NoYTI1NiA9ICRudWxsCiAgICByZW5kZXJfY29udHJhY3RfdmVyc2lvbiA9ICRudWxsCiAgICBleHBlY3RlZF9yZW5kZXJfY29udHJhY3RfdmVyc2lvbiA9ICRFeHBlY3RlZFJlbmRlckNvbnRyYWN0VmVyc2lvbgogICAgY2Fub25pY2FsX2d1aWRlX2hlYWRpbmdzX3ByZXNlbnQgPSAkZmFsc2UKICAgIHNvdXJjZV9jb21taXQgPSAkRXhwZWN0ZWRTb3VyY2VDb21taXQKICAgIHNjYWZmb2xkX3NoYTI1NiA9ICRFeHBlY3RlZFNjYWZmb2xkU2hhMjU2CiAgICBpbmhlcml0ZWRfcHl0aG9ucGF0aF9wcmVzZW50ID0gLW5vdCBbc3RyaW5nXTo6SXNOdWxsT3JXaGl0ZVNwYWNlKCRlbnY6UFlUSE9OUEFUSCkKICAgIGlzb2xhdGVkX21vZGUgPSAkdHJ1ZQogICAgZXJyb3IgPSAkbnVsbAogICAgY2hlY2tlZF9hdCA9IChHZXQtRGF0ZSkuVG9Vbml2ZXJzYWxUaW1lKCkuVG9TdHJpbmcoIm8iKQp9CgpmdW5jdGlvbiBXcml0ZS1Qcm92ZW5hbmNlRXZpZGVuY2UgewogICAgcGFyYW0oW1BhcmFtZXRlcihNYW5kYXRvcnkgPSAkdHJ1ZSldJFZhbHVlKQoKICAgICR1dGY4ID0gTmV3LU9iamVjdCBTeXN0ZW0uVGV4dC5VVEY4RW5jb2RpbmcoJGZhbHNlKQogICAgJHRleHQgPSBDb252ZXJ0VG8tSnNvbiAtSW5wdXRPYmplY3QgJFZhbHVlIC1EZXB0aCAyMAogICAgW1N5c3RlbS5JTy5GaWxlXTo6V3JpdGVBbGxUZXh0KCRldmlkZW5jZUZ1bGxQYXRoLCAkdGV4dCArIFtFbnZpcm9ubWVudF06Ok5ld0xpbmUsICR1dGY4KQp9CgokZW52aXJvbm1lbnROYW1lcyA9IEAoIlBZVEhPTlBBVEgiLCAiUFlUSE9OSE9NRSIsICJERERBX1BMQVRGT1JNX1JPT1QiLCAiREREQV9SRVBPX1JPT1QiKQokc2F2ZWRFbnZpcm9ubWVudCA9IEB7fQoKdHJ5IHsKICAgIGlmICgtbm90IChUZXN0LVBhdGggLUxpdGVyYWxQYXRoICRweXRob25QYXRoIC1QYXRoVHlwZSBMZWFmKSkgewogICAgICAgIHRocm93ICJDYW5kaWRhdGUgTWlybyBQeXRob24gcnVudGltZSBuZWV4aXN0dWplOiAkcHl0aG9uUGF0aCIKICAgIH0KICAgIGlmICgtbm90IChUZXN0LVBhdGggLUxpdGVyYWxQYXRoICRleHBlY3RlZE1vZHVsZVBhdGggLVBhdGhUeXBlIExlYWYpKSB7CiAgICAgICAgdGhyb3cgIkNhbmRpZGF0ZSByZW5kZXIgbW9kdWxlIG5lZXhpc3R1amU6ICRleHBlY3RlZE1vZHVsZVBhdGgiCiAgICB9CgogICAgJGV2aWRlbmNlLmV4cGVjdGVkX21vZHVsZV9zaGEyNTYgPSAoR2V0LUZpbGVIYXNoIC1MaXRlcmFsUGF0aCAkZXhwZWN0ZWRNb2R1bGVQYXRoIC1BbGdvcml0aG0gU0hBMjU2KS5IYXNoLlRvTG93ZXJJbnZhcmlhbnQoKQoKICAgIGZvcmVhY2ggKCRuYW1lIGluICRlbnZpcm9ubWVudE5hbWVzKSB7CiAgICAgICAgJHBhdGggPSAiRW52OlwkbmFtZSIKICAgICAgICBpZiAoVGVzdC1QYXRoIC1MaXRlcmFsUGF0aCAkcGF0aCkgewogICAgICAgICAgICAkc2F2ZWRFbnZpcm9ubWVudFsKICAgICAgICAgICAgICAgICRuYW1lCiAgICAgICAgICAgIF0gPSBbc3RyaW5nXShHZXQtSXRlbSAtTGl0ZXJhbFBhdGggJHBhdGgpLlZhbHVlCiAgICAgICAgICAgIFJlbW92ZS1JdGVtIC1MaXRlcmFsUGF0aCAkcGF0aAogICAgICAgIH0KICAgIH0KCiAgICAkcHJvYmUgPSBAJwppbXBvcnQgaGFzaGxpYgppbXBvcnQganNvbgppbXBvcnQgcGF0aGxpYgppbXBvcnQgc3lzCmltcG9ydCBkZGRhX21pcm8ucmVuZGVyIGFzIHJlbmRlcgoKcGF0aCA9IHBhdGhsaWIuUGF0aChyZW5kZXIuX19maWxlX18pLnJlc29sdmUoKQpwYXlsb2FkID0gewogICAgInB5dGhvbl9leGVjdXRhYmxlIjogc3RyKHBhdGhsaWIuUGF0aChzeXMuZXhlY3V0YWJsZSkucmVzb2x2ZSgpKSwKICAgICJzeXNfcHJlZml4Ijogc3RyKHBhdGhsaWIuUGF0aChzeXMucHJlZml4KS5yZXNvbHZlKCkpLAogICAgImltcG9ydGVkX21vZHVsZV9wYXRoIjogc3RyKHBhdGgpLAogICAgImltcG9ydGVkX21vZHVsZV9zaGEyNTYiOiBoYXNobGliLnNoYTI1NihwYXRoLnJlYWRfYnl0ZXMoKSkuaGV4ZGlnZXN0KCksCiAgICAicmVuZGVyX2NvbnRyYWN0X3ZlcnNpb24iOiBnZXRhdHRyKHJlbmRlciwgIlJFTkRFUl9DT05UUkFDVF9WRVJTSU9OIiwgTm9uZSksCiAgICAiY2Fub25pY2FsX2d1aWRlX2hlYWRpbmdzX3ByZXNlbnQiOiBib29sKGdldGF0dHIocmVuZGVyLCAiQ0FOT05JQ0FMX0dVSURFX0hFQURJTkdTIiwgTm9uZSkpLAp9CnByaW50KGpzb24uZHVtcHMocGF5bG9hZCwgc29ydF9rZXlzPVRydWUpKQonQAoKICAgICRwcmV2aW91c1ByZWZlcmVuY2UgPSAkRXJyb3JBY3Rpb25QcmVmZXJlbmNlCiAgICB0cnkgewogICAgICAgICRFcnJvckFjdGlvblByZWZlcmVuY2UgPSAiQ29udGludWUiCiAgICAgICAgJHJhdyA9IEAoJiAkcHl0aG9uUGF0aCAtSSAtYyAkcHJvYmUgMj4mMSkKICAgICAgICAkZXhpdENvZGUgPSAkTEFTVEVYSVRDT0RFCiAgICB9CiAgICBmaW5hbGx5IHsKICAgICAgICAkRXJyb3JBY3Rpb25QcmVmZXJlbmNlID0gJHByZXZpb3VzUHJlZmVyZW5jZQogICAgfQogICAgaWYgKCRleGl0Q29kZSAtbmUgMCkgewogICAgICAgIHRocm93ICJJc29sYXRlZCBydW50aW1lIHByb2JlIHNlbGhhbC4gRXhpdCBjb2RlOiAkZXhpdENvZGVgbiQoKCRyYXcgfCBPdXQtU3RyaW5nKS5UcmltKCkpIgogICAgfQoKICAgICRwcm9iZVJlc3VsdCA9ICgoJHJhdyB8IEZvckVhY2gtT2JqZWN0IHsgJF8uVG9TdHJpbmcoKSB9KSAtam9pbiBbRW52aXJvbm1lbnRdOjpOZXdMaW5lKS5UcmltKCkgfCBDb252ZXJ0RnJvbS1Kc29uCiAgICAkZXZpZGVuY2UucHl0aG9uX2V4ZWN1dGFibGUgPSBbc3RyaW5nXSRwcm9iZVJlc3VsdC5weXRob25fZXhlY3V0YWJsZQogICAgJGV2aWRlbmNlLnN5c19wcmVmaXggPSBbc3RyaW5nXSRwcm9iZVJlc3VsdC5zeXNfcHJlZml4CiAgICAkZXZpZGVuY2UuaW1wb3J0ZWRfbW9kdWxlX3BhdGggPSBbc3RyaW5nXSRwcm9iZVJlc3VsdC5pbXBvcnRlZF9tb2R1bGVfcGF0aAogICAgJGV2aWRlbmNlLmltcG9ydGVkX21vZHVsZV9zaGEyNTYgPSBbc3RyaW5nXSRwcm9iZVJlc3VsdC5pbXBvcnRlZF9tb2R1bGVfc2hhMjU2CiAgICAkZXZpZGVuY2UucmVuZGVyX2NvbnRyYWN0X3ZlcnNpb24gPSBbc3RyaW5nXSRwcm9iZVJlc3VsdC5yZW5kZXJfY29udHJhY3RfdmVyc2lvbgogICAgJGV2aWRlbmNlLmNhbm9uaWNhbF9ndWlkZV9oZWFkaW5nc19wcmVzZW50ID0gW2Jvb2xdJHByb2JlUmVzdWx0LmNhbm9uaWNhbF9ndWlkZV9oZWFkaW5nc19wcmVzZW50CgogICAgJGNvbXBhcmlzb24gPSBpZiAoJGVudjpPUyAtZXEgIldpbmRvd3NfTlQiKSB7CiAgICAgICAgW1N5c3RlbS5TdHJpbmdDb21wYXJpc29uXTo6T3JkaW5hbElnbm9yZUNhc2UKICAgIH0KICAgIGVsc2UgewogICAgICAgIFtTeXN0ZW0uU3RyaW5nQ29tcGFyaXNvbl06Ok9yZGluYWwKICAgIH0KICAgIGlmICgtbm90ICRldmlkZW5jZS5pbXBvcnRlZF9tb2R1bGVfcGF0aC5FcXVhbHMoJGV4cGVjdGVkTW9kdWxlUGF0aCwgJGNvbXBhcmlzb24pKSB7CiAgICAgICAgdGhyb3cgIkltcG9ydG92YW7DvSBkZGRhX21pcm8ucmVuZGVyIG5lbGXFo8OtIHYgY2FuZGlkYXRlIHBhY2thZ2UuIEFjdHVhbDogJyQoJGV2aWRlbmNlLmltcG9ydGVkX21vZHVsZV9wYXRoKSc7IGV4cGVjdGVkOiAnJGV4cGVjdGVkTW9kdWxlUGF0aCcuIgogICAgfQogICAgaWYgKCRldmlkZW5jZS5pbXBvcnRlZF9tb2R1bGVfc2hhMjU2IC1uZSAkZXZpZGVuY2UuZXhwZWN0ZWRfbW9kdWxlX3NoYTI1NikgewogICAgICAgIHRocm93ICJJbXBvcnRvdsOhbsO9IGRkZGFfbWlyby5yZW5kZXIgbcOhIGppbsO9IFNIQS0yNTYgbmXFviBjYW5kaWRhdGUgcGFja2FnZS4iCiAgICB9CiAgICBpZiAoJGV2aWRlbmNlLnJlbmRlcl9jb250cmFjdF92ZXJzaW9uIC1uZSAkRXhwZWN0ZWRSZW5kZXJDb250cmFjdFZlcnNpb24pIHsKICAgICAgICB0aHJvdyAiSW1wb3J0b3ZhbsO9IHJlbmRlciBjb250cmFjdCAnJCgkZXZpZGVuY2UucmVuZGVyX2NvbnRyYWN0X3ZlcnNpb24pJyBuZW9kcG92w61kw6EgJyRFeHBlY3RlZFJlbmRlckNvbnRyYWN0VmVyc2lvbicuIgogICAgfQogICAgaWYgKC1ub3QgJGV2aWRlbmNlLmNhbm9uaWNhbF9ndWlkZV9oZWFkaW5nc19wcmVzZW50KSB7CiAgICAgICAgdGhyb3cgIkltcG9ydG92YW7DvSByZW5kZXJlciBuZW9ic2FodWplIENBTk9OSUNBTF9HVUlERV9IRUFESU5HUy4iCiAgICB9CgogICAgJGV2aWRlbmNlLnN0YXR1cyA9ICJQQVNTIgogICAgV3JpdGUtUHJvdmVuYW5jZUV2aWRlbmNlIC1WYWx1ZSAkZXZpZGVuY2UKICAgIGlmICgkSnNvbikgewogICAgICAgICRldmlkZW5jZSB8IENvbnZlcnRUby1Kc29uIC1EZXB0aCAyMAogICAgfQogICAgZWxzZSB7CiAgICAgICAgV3JpdGUtSG9zdCAiREREQSBNaXJvIHJ1bnRpbWUgcHJvdmVuYW5jZTogUEFTUyIKICAgICAgICBXcml0ZS1Ib3N0ICJJbXBvcnRlZCBtb2R1bGU6ICQoJGV2aWRlbmNlLmltcG9ydGVkX21vZHVsZV9wYXRoKSIKICAgICAgICBXcml0ZS1Ib3N0ICJSZW5kZXIgY29udHJhY3Q6ICQoJGV2aWRlbmNlLnJlbmRlcl9jb250cmFjdF92ZXJzaW9uKSIKICAgIH0KfQpjYXRjaCB7CiAgICAkZXZpZGVuY2UuZXJyb3IgPSAkXy5FeGNlcHRpb24uTWVzc2FnZQogICAgV3JpdGUtUHJvdmVuYW5jZUV2aWRlbmNlIC1WYWx1ZSAkZXZpZGVuY2UKICAgIHRocm93Cn0KZmluYWxseSB7CiAgICBmb3JlYWNoICgkbmFtZSBpbiAkZW52aXJvbm1lbnROYW1lcykgewogICAgICAgIFJlbW92ZS1JdGVtIC1MaXRlcmFsUGF0aCAiRW52OlwkbmFtZSIgLUVycm9yQWN0aW9uIFNpbGVudGx5Q29udGludWUKICAgICAgICBpZiAoJHNhdmVkRW52aXJvbm1lbnQuQ29udGFpbnNLZXkoJG5hbWUpKSB7CiAgICAgICAgICAgIFNldC1JdGVtIC1MaXRlcmFsUGF0aCAiRW52OlwkbmFtZSIgLVZhbHVlICRzYXZlZEVudmlyb25tZW50WyRuYW1lXQogICAgICAgIH0KICAgIH0KfQo="
Write-Base64File -RelativePath "tests/powershell/Test-DDDARuntimeIsolation.ps1" -Base64 "W0NtZGxldEJpbmRpbmcoKV0KcGFyYW0oCiAgICBbc3RyaW5nXSRQbGF0Zm9ybVBhdGggPSAoUmVzb2x2ZS1QYXRoIChKb2luLVBhdGggJFBTU2NyaXB0Um9vdCAiLi4vLi4iKSkuUGF0aAopCgpTZXQtU3RyaWN0TW9kZSAtVmVyc2lvbiBMYXRlc3QKJEVycm9yQWN0aW9uUHJlZmVyZW5jZSA9ICJTdG9wIgoKJHBsYXRmb3JtUm9vdCA9IFtTeXN0ZW0uSU8uUGF0aF06OkdldEZ1bGxQYXRoKChSZXNvbHZlLVBhdGggLUxpdGVyYWxQYXRoICRQbGF0Zm9ybVBhdGgpLlBhdGgpCiRydW5Sb290ID0gSm9pbi1QYXRoIChbU3lzdGVtLklPLlBhdGhdOjpHZXRUZW1wUGF0aCgpKSAoImRkZGEtcnVudGltZS1pc29sYXRpb24tIiArIFtHdWlkXTo6TmV3R3VpZCgpLlRvU3RyaW5nKCJOIikpCiRmYWtlUm9vdCA9IEpvaW4tUGF0aCAkcnVuUm9vdCAiYW1iaWVudCIKJGZha2VQYWNrYWdlID0gSm9pbi1QYXRoICRmYWtlUm9vdCAiZGRkYV9taXJvIgokcGFzc0V2aWRlbmNlID0gSm9pbi1QYXRoICRydW5Sb290ICJwYXNzLmpzb24iCiRmYWlsRXZpZGVuY2UgPSBKb2luLVBhdGggJHJ1blJvb3QgImZhaWwuanNvbiIKJG9sZFB5dGhvblBhdGggPSAkZW52OlBZVEhPTlBBVEgKCnRyeSB7CiAgICBOZXctSXRlbSAtSXRlbVR5cGUgRGlyZWN0b3J5IC1QYXRoICRmYWtlUGFja2FnZSAtRm9yY2UgfCBPdXQtTnVsbAogICAgU2V0LUNvbnRlbnQgLUxpdGVyYWxQYXRoIChKb2luLVBhdGggJGZha2VQYWNrYWdlICJfX2luaXRfXy5weSIpIC1FbmNvZGluZyBVVEY4IC1WYWx1ZSAiIgogICAgU2V0LUNvbnRlbnQgLUxpdGVyYWxQYXRoIChKb2luLVBhdGggJGZha2VQYWNrYWdlICJyZW5kZXIucHkiKSAtRW5jb2RpbmcgVVRGOCAtVmFsdWUgQCcKUkVOREVSX0NPTlRSQUNUX1ZFUlNJT04gPSAiT0xELUNPTlRBTUlOQVRFRC1SRU5ERVJFUiIKJ0AKCiAgICAmIChKb2luLVBhdGggJHBsYXRmb3JtUm9vdCAic2NyaXB0cy9Jbml0aWFsaXplLUREREFBZnRlckNsb25lLnBzMSIpIC1QbGF0Zm9ybVBhdGggJHBsYXRmb3JtUm9vdCAtTm9uSW50ZXJhY3RpdmUKICAgIGlmICgkTEFTVEVYSVRDT0RFIC1uZSAwKSB7CiAgICAgICAgdGhyb3cgIlJ1bnRpbWUgaW5pdGlhbGl6YXRpb24gZmFpbGVkLiIKICAgIH0KCiAgICAkcmVuZGVyUGF0aCA9IEpvaW4tUGF0aCAkcGxhdGZvcm1Sb290ICJydW50aW1lL21pcm8vZGRkYV9taXJvL3JlbmRlci5weSIKICAgICRyZW5kZXJUZXh0ID0gR2V0LUNvbnRlbnQgLUxpdGVyYWxQYXRoICRyZW5kZXJQYXRoIC1SYXcgLUVuY29kaW5nIFVURjgKICAgIGlmICgkcmVuZGVyVGV4dCAtbm90bWF0Y2ggJ1JFTkRFUl9DT05UUkFDVF9WRVJTSU9OXHMqPVxzKiIoPzx2ZXJzaW9uPlteIl0rKSInKSB7CiAgICAgICAgdGhyb3cgIlJlbmRlcmVyIGNvbnRyYWN0IHdhcyBub3QgZm91bmQuIgogICAgfQogICAgJGV4cGVjdGVkQ29udHJhY3QgPSBbc3RyaW5nXSRNYXRjaGVzWyJ2ZXJzaW9uIl0KICAgICRzb3VyY2VDb21taXQgPSAoJiBnaXQgLUMgJHBsYXRmb3JtUm9vdCByZXYtcGFyc2UgSEVBRCkuVHJpbSgpCiAgICBpZiAoJExBU1RFWElUQ09ERSAtbmUgMCAtb3IgJHNvdXJjZUNvbW1pdCAtbm90bWF0Y2ggJ15bMC05YS1mXXs0MH0kJykgewogICAgICAgIHRocm93ICJFeGFjdCBzb3VyY2UgU0hBIHdhcyBub3QgcmVzb2x2ZWQuIgogICAgfQogICAgJHNjYWZmb2xkSGFzaCA9IChHZXQtRmlsZUhhc2ggLUxpdGVyYWxQYXRoIChKb2luLVBhdGggJHBsYXRmb3JtUm9vdCAic2NhZmZvbGRzL21pcm8vc3RyYXRlZ2ljLWRkZC1tZXRob2QtYm9hcmQueWFtbCIpIC1BbGdvcml0aG0gU0hBMjU2KS5IYXNoLlRvTG93ZXJJbnZhcmlhbnQoKQoKICAgICRlbnY6UFlUSE9OUEFUSCA9ICRmYWtlUm9vdCArIFtTeXN0ZW0uSU8uUGF0aF06OlBhdGhTZXBhcmF0b3IgKyAoSm9pbi1QYXRoICRwbGF0Zm9ybVJvb3QgInJ1bnRpbWUvbWlybyIpCiAgICAkanNvbiA9ICYgKEpvaW4tUGF0aCAkcGxhdGZvcm1Sb290ICJzY3JpcHRzL3BsYXRmb3JtL0Fzc2VydC1ERERBTWlyb1J1bnRpbWVQcm92ZW5hbmNlLnBzMSIpIGAKICAgICAgICAtUGxhdGZvcm1QYXRoICRwbGF0Zm9ybVJvb3QgYAogICAgICAgIC1FeHBlY3RlZFJlbmRlckNvbnRyYWN0VmVyc2lvbiAkZXhwZWN0ZWRDb250cmFjdCBgCiAgICAgICAgLUV4cGVjdGVkU291cmNlQ29tbWl0ICRzb3VyY2VDb21taXQgYAogICAgICAgIC1FeHBlY3RlZFNjYWZmb2xkU2hhMjU2ICRzY2FmZm9sZEhhc2ggYAogICAgICAgIC1FdmlkZW5jZVBhdGggJHBhc3NFdmlkZW5jZSBgCiAgICAgICAgLUpzb24gfCBPdXQtU3RyaW5nCiAgICBpZiAoJExBU1RFWElUQ09ERSAtbmUgMCkgewogICAgICAgIHRocm93ICJSdW50aW1lIHByb3ZlbmFuY2UgcGFzcyBzY2VuYXJpbyBmYWlsZWQuIgogICAgfQogICAgJHBhc3MgPSAkanNvbi5UcmltKCkgfCBDb252ZXJ0RnJvbS1Kc29uCiAgICBpZiAoJHBhc3Muc3RhdHVzIC1uZSAiUEFTUyIpIHsKICAgICAgICB0aHJvdyAiUnVudGltZSBwcm92ZW5hbmNlIGRpZCBub3QgcmV0dXJuIFBBU1MuIgogICAgfQogICAgaWYgKC1ub3QgW2Jvb2xdJHBhc3MuaW5oZXJpdGVkX3B5dGhvbnBhdGhfcHJlc2VudCkgewogICAgICAgIHRocm93ICJUZXN0IGRpZCBub3QgcHJvdmUgYW4gYW1iaWVudCBQWVRIT05QQVRIIHdhcyBwcmVzZW50LiIKICAgIH0KICAgICRleHBlY3RlZFBhdGggPSBbU3lzdGVtLklPLlBhdGhdOjpHZXRGdWxsUGF0aCgkcmVuZGVyUGF0aCkKICAgIGlmICgtbm90IFtzdHJpbmddJHBhc3MuaW1wb3J0ZWRfbW9kdWxlX3BhdGggLW9yCiAgICAgICAgLW5vdCAoW3N0cmluZ10kcGFzcy5pbXBvcnRlZF9tb2R1bGVfcGF0aCkuRXF1YWxzKCRleHBlY3RlZFBhdGgsIFtTeXN0ZW0uU3RyaW5nQ29tcGFyaXNvbl06Ok9yZGluYWxJZ25vcmVDYXNlKSkgewogICAgICAgIHRocm93ICJJc29sYXRlZCBydW50aW1lIGltcG9ydGVkIGEgbW9kdWxlIG91dHNpZGUgdGhlIHBsYXRmb3JtIHJvb3Q6ICQoJHBhc3MuaW1wb3J0ZWRfbW9kdWxlX3BhdGgpIgogICAgfQoKICAgICRyZW1vdGVXcml0ZUNvdW50ID0gMAogICAgJG5lZ2F0aXZlRmFpbGVkID0gJGZhbHNlCiAgICB0cnkgewogICAgICAgICYgKEpvaW4tUGF0aCAkcGxhdGZvcm1Sb290ICJzY3JpcHRzL3BsYXRmb3JtL0Fzc2VydC1ERERBTWlyb1J1bnRpbWVQcm92ZW5hbmNlLnBzMSIpIGAKICAgICAgICAgICAgLVBsYXRmb3JtUGF0aCAkcGxhdGZvcm1Sb290IGAKICAgICAgICAgICAgLUV4cGVjdGVkUmVuZGVyQ29udHJhY3RWZXJzaW9uICJJTlRFTlRJT05BTExZLVdST05HIiBgCiAgICAgICAgICAgIC1FeHBlY3RlZFNvdXJjZUNvbW1pdCAkc291cmNlQ29tbWl0IGAKICAgICAgICAgICAgLUV4cGVjdGVkU2NhZmZvbGRTaGEyNTYgJHNjYWZmb2xkSGFzaCBgCiAgICAgICAgICAgIC1FdmlkZW5jZVBhdGggJGZhaWxFdmlkZW5jZSB8IE91dC1OdWxsCiAgICAgICAgJHJlbW90ZVdyaXRlQ291bnQrKwogICAgfQogICAgY2F0Y2ggewogICAgICAgICRuZWdhdGl2ZUZhaWxlZCA9ICR0cnVlCiAgICB9CiAgICBpZiAoLW5vdCAkbmVnYXRpdmVGYWlsZWQpIHsKICAgICAgICB0aHJvdyAiTmVnYXRpdmUgcHJvdmVuYW5jZSBzY2VuYXJpbyBkaWQgbm90IGZhaWwuIgogICAgfQogICAgaWYgKCRyZW1vdGVXcml0ZUNvdW50IC1uZSAwKSB7CiAgICAgICAgdGhyb3cgIkEgcmVtb3RlIHdyaXRlIHNlbnRpbmVsIHdhcyByZWFjaGVkIGFmdGVyIHByb3ZlbmFuY2UgZmFpbHVyZS4iCiAgICB9CiAgICAkZmFpbHVyZSA9IEdldC1Db250ZW50IC1MaXRlcmFsUGF0aCAkZmFpbEV2aWRlbmNlIC1SYXcgLUVuY29kaW5nIFVURjggfCBDb252ZXJ0RnJvbS1Kc29uCiAgICBpZiAoJGZhaWx1cmUuc3RhdHVzIC1uZSAiRkFJTCIgLW9yIC1ub3QgW2Jvb2xdJGZhaWx1cmUuY2hlY2tlZF9iZWZvcmVfcmVtb3RlX3dyaXRlKSB7CiAgICAgICAgdGhyb3cgIk5lZ2F0aXZlIGV2aWRlbmNlIGlzIG5vdCBmYWlsLWNsb3NlZC4iCiAgICB9CgogICAgV3JpdGUtSG9zdCAiREREQSBydW50aW1lIGlzb2xhdGlvbiB0ZXN0czogUEFTUyIKfQpmaW5hbGx5IHsKICAgIGlmICgkbnVsbCAtZXEgJG9sZFB5dGhvblBhdGgpIHsKICAgICAgICBSZW1vdmUtSXRlbSBFbnY6XFBZVEhPTlBBVEggLUVycm9yQWN0aW9uIFNpbGVudGx5Q29udGludWUKICAgIH0KICAgIGVsc2UgewogICAgICAgICRlbnY6UFlUSE9OUEFUSCA9ICRvbGRQeXRob25QYXRoCiAgICB9CiAgICBpZiAoVGVzdC1QYXRoIC1MaXRlcmFsUGF0aCAkcnVuUm9vdCkgewogICAgICAgIFJlbW92ZS1JdGVtIC1MaXRlcmFsUGF0aCAkcnVuUm9vdCAtUmVjdXJzZSAtRm9yY2UgLUVycm9yQWN0aW9uIFNpbGVudGx5Q29udGludWUKICAgIH0KfQo="
Write-Base64File -RelativePath "scripts/platform/Test-DDDARemoteExecutionRequest.ps1" -Base64 "W0NtZGxldEJpbmRpbmcoKV0KcGFyYW0oCiAgICBbc3RyaW5nXSRQbGF0Zm9ybVBhdGggPSAoUmVzb2x2ZS1QYXRoIChKb2luLVBhdGggJFBTU2NyaXB0Um9vdCAiLi4vLi4iKSkuUGF0aCwKICAgIFtQYXJhbWV0ZXIoTWFuZGF0b3J5ID0gJHRydWUpXVtzdHJpbmddJFJlcG9zaXRvcnksCiAgICBbUGFyYW1ldGVyKE1hbmRhdG9yeSA9ICR0cnVlKVtzdHJpbmddJEFjdG9yLAogICAgW1BhcmFtZXRlcihNYW5kYXRvcnkgPSAkdHJ1ZSldW1ZhbGlkYXRlUmFuZ2UoMSwgMjE0NzQ4MzY0NyldW2ludF0kUHIsCiAgICBbUGFyYW1ldGVyKE1hbmRhdG9yeSA9ICR0cnVlKVtWYWxpZGF0ZVBhdHRlcm4oJ15bMC05YS1mXXs0MH0kJyldW3N0cmluZ10kSGVhZFNoYSwKICAgIFtQYXJhbWV0ZXIoTWFuZGF0b3J5ID0gJHRydWUpXVtzdHJpbmddJEhlYWRSZXBvc2l0b3J5LAogICAgW1BhcmFtZXRlcihNYW5kYXRvcnkgPSAkdHJ1ZSldW3N0cmluZ10kQ29tbWFuZFRleHQsCiAgICBbc3dpdGNoXSRKc29uCikKClNldC1TdHJpY3RNb2RlIC1WZXJzaW9uIExhdGVzdAokRXJyb3JBY3Rpb25QcmVmZXJlbmNlID0gIlN0b3AiCgokcG9saWN5UGF0aCA9IEpvaW4tUGF0aCAoUmVzb2x2ZS1QYXRoIC1MaXRlcmFsUGF0aCAkUGxhdGZvcm1QYXRoKS5QYXRoICJjb25maWcvcGxhdGZvcm0vZGV2ZWxvcG1lbnQtcG9saWN5LnlhbWwiCiRwb2xpY3kgPSBHZXQtQ29udGVudCAtTGl0ZXJhbFBhdGggJHBvbGljeVBhdGggLVJhdyAtRW5jb2RpbmcgVVRGOCB8IENvbnZlcnRGcm9tLUpzb24KJHJlbW90ZSA9ICRwb2xpY3kucmVtb3RlX2V4ZWN1dGlvbgppZiAoJG51bGwgLWVxICRyZW1vdGUgLW9yIC1ub3QgW2Jvb2xdJHJlbW90ZS5lbmFibGVkKSB7CiAgICB0aHJvdyAiUmVtb3RlIGV4ZWN1dGlvbiBpcyBkaXNhYmxlZCBieSBwbGF0Zm9ybSBwb2xpY3kuIgp9CmlmIChbc3RyaW5nXSRBY3RvciAtbm90aW4gQCgkcmVtb3RlLmFsbG93ZWRfYWN0b3JzIHwgRm9yRWFjaC1PYmplY3QgeyBbc3RyaW5nXSQ_0KICAgIHRocm93ICJBY3RvciAnJEFjdG9yJyBpcyBub3QgYWxsb3dlZCB0byByZXF1ZXN0IHJlbW90ZSBERERBIGV4ZWN1dGlvbi4iCn0KaWYgKFtib29sXSRyZW1vdGUuc2FtZV9yZXBvc2l0b3J5X29ubHkgLWFuZCAkSGVhZFJlcG9zaXRvcnkgLW5lICRSZXBvc2l0b3J5KSB7CiAgICB0aHJvdyAiUmVtb3RlIGV4ZWN1dGlvbiBpcyBhbGxvd2VkIG9ubHkgZm9yIHNhbWUtcmVwb3NpdG9yeSBwdWxsIHJlcXVlc3RzLiIKfQoKJG5vcm1hbGl6ZWQgPSAkQ29tbWFuZFRleHQuVHJpbSgpCiRyZXN1bHQgPSBbb3JkZXJlZF1AewogICAgc3RhdHVzID0gIlBBU1MiCiAgICByZXBvc2l0b3J5ID0gJFJlcG9zaXRvcnkKICAgIGFjdG9yID0gJEFjdG9yCiAgICBwciA9ICRQcgogICAgaGVhZF9zaGEgPSAkSGVhZFNoYQogICAgaGVhZF9yZXBvc2l0b3J5ID0gJEhlYWRSZXBvc2l0b3J5CiAgICBhY3Rpb24gPSAkbnVsbAogICAgcmVtZWRpYXRpb25fc2NyaXB0ID0gJG51bGwKICAgIG1pcm9fdGVhbV9pZCA9IFtzdHJpbmddJHJlbW90ZS5taXJvX3RlYW1faWQKICAgIGtlZXBfcmV2aWV3X2JvYXJkID0gJHRydWUKICAgIG1lcmdlX2FsbG93ZWQgPSAkZmFsc2UKICAgIHByb21vdGlvbl9hbGxvd2VkID0gJGZhbHNlCiAgICByZWxlYXNlX2FsbG93ZWQgPSAkZmFsc2UKfQoKaWYgKCRub3JtYWxpemVkIC1pbiBAKCRyZW1vdGUuYWxsb3dlZF92YWxpZGF0ZV9jb21tYW5kcyB8IEZvckVhY2gtT2JqZWN0IHsgW3N0cmluZ10kXyB9KSkgewogICAgJHJlc3VsdC5hY3Rpb24gPSAidmFsaWRhdGUtcHIiCn0KZWxzZWlmICgkbm9ybWFsaXplZCAtbWF0Y2ggJ14vZGRkYSByZW1lZGlhdGVccysoPzxwYXRoPnNjcmlwdHMvcmVtZWRpYXRpb24vW0EtWmEtejAtOS5fL1wtXStcLnBzMSlccystLWV4cGVjdGVkLXNoYVxzKyg_PHNoYT5bMC05YS1mXXs0MH0pJCcpIHsKICAgIGlmICgtbm90IFtib29sXSRyZW1vdGUucmVtZWRpYXRpb24uZW5hYmxlZCkgewogICAgICAgIHRocm93ICJSZW1vdGUgcmVtZWRpYXRpb24gaXMgZGlzYWJsZWQgYnkgcGxhdGZvcm0gcG9saWN5LiIKICAgIH0KICAgIGlmIChbc3RyaW5nXSRNYXRjaGVzWyJzaGEiXSAtbmUgJEhlYWRTaGEpIHsKICAgICAgICB0aHJvdyAiUmVtZWRpYXRpb24gZXhwZWN0ZWQgU0hBIGRvZXMgbm90IG1hdGNoIHRoZSBjdXJyZW50IFBSIGhlYWQuIgogICAgfQogICAgJHNjcmlwdFBhdGggPSBbc3RyaW5nXSRNYXRjaGVzWyJwYXRoIl0KICAgICRwcmVmaXggPSBbc3RyaW5nXSRyZW1vdGUucmVtZWRpYXRpb24uYWxsb3dlZF9wYXRoX3ByZWZpeAogICAgaWYgKC1ub3QgJHNjcmlwdFBhdGguU3RhcnRzV2l0aCgkcHJlZml4LCBbU3lzdGVtLlN0cmluZ0NvbXBhcmlzb25dOjpPcmRpbmFsKSkgewogICAgICAgIHRocm93ICJSZW1lZGlhdGlvbiBzY3JpcHQgaXMgb3V0c2lkZSB0aGUgYWxsb3dlZCBwYXRoIHByZWZpeC4iCiAgICB9CiAgICAkZnVsbFNjcmlwdFBhdGggPSBbU3lzdGVtLklPLlBhdGhdOjpHZXRGdWxsUGF0aCgoSm9pbi1QYXRoIChSZXNvbHZlLVBhdGggLUxpdGVyYWxQYXRoICRQbGF0Zm9ybVBhdGgpLlBhdGggJHNjcmlwdFBhdGgpCiAgICAkYWxsb3dlZFJvb3QgPSBbU3lzdGVtLklPLlBhdGhdOjpHZXRGdWxsUGF0aCgoSm9pbi1QYXRoIChSZXNvbHZlLVBhdGggLUxpdGVyYWxQYXRoICRQbGF0Zm9ybVBhdGgpLlBhdGggJHByZWZpeCkKICAgIGlmICgtbm90ICRmdWxsU2NyaXB0UGF0aC5TdGFydHNXaXRoKCRhbGxvd2VkUm9vdCwgW1N5c3RlbS5TdHJpbmdDb21wYXJpc29uXTo6T3JkaW5hbElnbm9yZUNhc2UpKSB7CiAgICAgICAgdGhyb3cgIlJlbWVkaWF0aW9uIHNjcmlwdCBlc2NhcGVzIHRoZSBhbGxvd2VkIHJvb3QuIgogICAgfQogICAgaWYgKC1ub3QgKFRlc3QtUGF0aCAtTGl0ZXJhbFBhdGggJGZ1bGxTY3JpcHRQYXRoIC1QYXRoVHlwZSBMZWFmKSkgewogICAgICAgIHRocm93ICJSZW1lZGlhdGlvbiBzY3JpcHQgZG9lcyBub3QgZXhpc3QgYXQgdGhlIGV4YWN0IFBSIGhlYWQ6ICRzY3JpcHRQYXRoIgogICAgfQogICAgJHJlc3VsdC5hY3Rpb24gPSAicmVtZWRpYXRlIgogICAgJHJlc3VsdC5yZW1lZGlhdGlvbl9zY3JpcHQgPSAkc2NyaXB0UGF0aAp9CmVsc2UgewogICAgdGhyb3cgIlVuc3VwcG9ydGVkIHJlbW90ZSBERERBIGNvbW1hbmQuIgp9CgppZiAoJEpzb24pIHsKICAgICRyZXN1bHQgfCBDb252ZXJ0VG8tSnNvbiAtRGVwdGggMjAKfQplbHNlIHsKICAgIFdyaXRlLUhvc3QgIkREREEgcmVtb3RlIGV4ZWN1dGlvbiByZXF1ZXN0OiBQQVNTIgogICAgV3JpdGUtSG9zdCAiQWN0aW9uOiAkKCRyZXN1bHQuYWN0aW9uKSIKICAgIFdyaXRlLUhvc3QgIlBSOiAkUHIiCiAgICBXcml0ZS1Ib3N0ICJTSEE6ICRIZWFkU2hhIgp9Cg=="
Write-Base64File -RelativePath ".github/workflows/assistant-command.yml" -Base64 "bmFtZTogREREQSByZW1vdGUgZXhlY3V0aW9uIGJyb2tlcgoKb246CiAgaXNzdWVfY29tbWVudDoKICAgIHR5cGVzOgogICAgICAtIGNyZWF0ZWQKCnBlcm1pc3Npb25zOgogIGNvbnRlbnRzOiB3cml0ZQogIGlzc3Vlczogd3JpdGUKICBwdWxsLXJlcXVlc3RzOiByZWFkCiAgY2hlY2tzOiByZWFkCgpjb25jdXJyZW5jeToKICBncm91cDogZGRkYS1yZW1vdGUtJHt7IGdpdGh1Yi5ldmVudC5pc3N1ZS5udW1iZXIgfX0KICBjYW5jZWwtaW4tcHJvZ3Jlc3M6IGZhbHNlCgpqb2JzOgogIGV4ZWN1dGU6CiAgICBpZjogPi0KICAgICAgZ2l0aHViLmV2ZW50Lmlzc3VlLnB1bGxfcmVxdWVzdCAmJgogICAgICBzdGFydHNXaXRoKGdpdGh1Yi5ldmVudC5jb21tZW50LmJvZHksICcvZGRkYSAnKQogICAgcnVucy1vbjogd2luZG93cy1sYXRlc3QKICAgIHRpbWVvdXQtbWludXRlczogMTUwCiAgICBlbnY6CiAgICAgIFJFUE9TSVRPUlk6ICR7eyBnaXRodWIucmVwb3NpdG9yeSB9fQogICAgICBQUl9OVU1CRVI6ICR7eyBnaXRodWIuZXZlbnQuaXNzdWUubnVtYmVyIH19CiAgICAgIFJFUVVFU1RfQUNUT1I6ICR7eyBnaXRodWIuYWN0b3IgfX0KICAgICAgQ09NTUFORF9URVhUOiAke3sgZ2l0aHViLmV2ZW50LmNvbW1lbnQuYm9keSB9fQoKICAgIHN0ZXBzOgogICAgICAtIG5hbWU6IENoZWNrb3V0IHRydXN0ZWQgYnJva2VyIGZyb20gZGVmYXVsdCBicmFuY2gKICAgICAgICB1c2VzOiBhY3Rpb25zL2NoZWNrb3V0QHY0CiAgICAgICAgd2l0aDoKICAgICAgICAgIGZldGNoLWRlcHRoOiAwCiAgICAgICAgICByZWY6ICR7eyBnaXRodWIuZXZlbnQucmVwb3NpdG9yeS5kZWZhdWx0X2JyYW5jaCB9fQoKICAgICAgLSBuYW1lOiBSZXNvbHZlIGV4YWN0IFBSIGhlYWQKICAgICAgICBpZDogcHIKICAgICAgICBzaGVsbDogcHdzaAogICAgICAgIGVudjoKICAgICAgICAgIEdIX1RPS0VOOiAke3sgZ2l0aHViLnRva2VuIH19CiAgICAgICAgcnVuOiB8CiAgICAgICAgICAkRXJyb3JBY3Rpb25QcmVmZXJlbmNlID0gJ1N0b3AnCiAgICAgICAgICAkcHIgPSBnaCBhcGkgInJlcG9zLyRlbnY6UkVQT1NJVE9SWS9wdWxscy8kZW52OlBSX05VTUJFUiIgfCBDb252ZXJ0RnJvbS1Kc29uCiAgICAgICAgICAiaGVhZF9zaGE9JCgkcHIuaGVhZC5zaGEpIiB8IE91dC1GaWxlIC1GaWxlUGF0aCAkZW52OkdJVEhVQl9PVVRQVVQgLUVuY29kaW5nIHV0ZjggLUFwcGVuZAogICAgICAgICAgImhlYWRfcmVmPSQoJHByLmhlYWQucmVmKSIgfCBPdXQtRmlsZSAtRmlsZVBhdGggJGVudjpHSVRIVUJfT1VUUFVUIC1FbmNvZGluZyB1dGY4IC1BcHBlbmQKICAgICAgICAgICJoZWFkX3JlcG9zaXRvcnk9JCgkcHIuaGVhZC5yZXBvLmZ1bGxfbmFtZSkiIHwgT3V0LUZpbGUgLUZpbGVQYXRoICRlbnY6R0lUSFVCX09VVFBVVCAtRW5jb2RpbmcgdXRmOCAtQXBwZW5kCgogICAgICAtIG5hbWU6IEF1dGhvcml6ZSBjb21tYW5kIGFnYWluc3QgZ292ZXJuYW5jZSBwb2xpY3kKICAgICAgICBpZDogYXV0aG9yaXphdGlvbgogICAgICAgIHNoZWxsOiBwd3NoCiAgICAgICAgcnVuOiB8CiAgICAgICAgICAkRXJyb3JBY3Rpb25QcmVmZXJlbmNlID0gJ1N0b3AnCiAgICAgICAgICAkanNvbiA9IC5cc2NyaXB0c1xwbGF0Zm9ybVxUZXN0LUREREFSZW1vdGVFeGVjdXRpb25SZXF1ZXN0LnBzMSBgCiAgICAgICAgICAgIC1QbGF0Zm9ybVBhdGggJFBXRC5QYXRoIGAKICAgICAgICAgICAgLVJlcG9zaXRvcnkgJGVudjpSRVBPU0lUT1JZIGAKICAgICAgICAgICAgLUFjdG9yICRlbnY6UkVRVUVTVF9BQ1RPUiBgCiAgICAgICAgICAgIC1QciAoW2ludF0kZW52OlBSX05VTUJFUikgYAogICAgICAgICAgICAtSGVhZFNoYSAnJHt7IHN0ZXBzLnByLm91dHB1dHMuaGVhZF9zaGEgfX0nIGAKICAgICAgICAgICAgLUhlYWRSZXBvc2l0b3J5ICcke3sgc3RlcHMucHIub3V0cHV0cy5oZWFkX3JlcG9zaXRvcnkgfX0nIGAKICAgICAgICAgICAgLUNvbW1hbmRUZXh0ICRlbnY6Q09NTUFORF9URVhUIGAKICAgICAgICAgICAgLUpzb24gfCBPdXQtU3RyaW5nCiAgICAgICAgICAkYXV0aG9yaXphdGlvbiA9ICRqc29uLlRyaW0oKSB8IENvbnZlcnRGcm9tLUpzb24KICAgICAgICAgICJhY3Rpb249JCgkYXV0aG9yaXphdGlvbi5hY3Rpb24pIiB8IE91dC1GaWxlIC1GaWxlUGF0aCAkZW52OkdJVEhVQl9PVVRQVVQgLUVuY29kaW5nIHV0ZjggLUFwcGVuZAogICAgICAgICAgInJlbWVkaWF0aW9uX3NjcmlwdD0kKCRhdXRob3JpemF0aW9uLnJlbWVkaWF0aW9uX3NjcmlwdCkiIHwgT3V0LUZpbGUgLUZpbGVQYXRoICRlbnY6R0lUSFVCX09VVFBVVCAtRW5jb2RpbmcgdXRmOCAtQXBwZW5kCiAgICAgICAgICAibWlyb190ZWFtX2lkPSQoJGF1dGhvcml6YXRpb24ubWlyb190ZWFtX2lkKSIgfCBPdXQtRmlsZSAtRmlsZVBhdGggJGVudjpHSVRIVUJfT1VUUFVUIC1FbmNvZGluZyB1dGY4IC1BcHBlbmQKCiAgICAgIC0gbmFtZTogUmVxdWlyZSBzdWNjZXNzZnVsIGV4YWN0LVNIQSBjaGVja3MgYmVmb3JlIHNlY3JldC1iZWFyaW5nIHZhbGlkYXRpb24KICAgICAgICBpZjogc3RlcHMuYXV0aG9yaXphdGlvbi5vdXRwdXRzLmFjdGlvbiA9PSAndmFsaWRhdGUtcHInCiAgICAgICAgc2hlbGw6IHB3c2gKICAgICAgICBlbnY6CiAgICAgICAgICBHSF9UT0tFTjogJHt7IGdpdGh1Yi50b2tlbiB9fQogICAgICAgICAgSEVBRF9TSEE6ICR7eyBzdGVwcy5wci5vdXRwdXRzLmhlYWRfc2hhIH19CiAgICAgICAgcnVuOiB8CiAgICAgICAgICAkRXJyb3JBY3Rpb25QcmVmZXJlbmNlID0gJ1N0b3AnCiAgICAgICAgICAkY2hlY2tzID0gZ2ggYXBpIC1IICdBY2NlcHQ6IGFwcGxpY2F0aW9uL3ZuZC5naXRodWIranNvbicgInJlcG9zLyRlbnY6UkVQT1NJVE9SWS9jb21taXRzLyRlbnY6SEVBRF9TSEEvY2hlY2stcnVucz9wZXJfcGFnZT0xMDAiIHwgQ29udmVydEZyb20tSnNvbgogICAgICAgICAgJHJlcXVpcmVkID0gQCgnUGxhdGZvcm0gdmFsaWRhdGlvbicsICdPbmUtY29tbWFuZCBQUiB2YWxpZGF0aW9uJykKICAgICAgICAgIGZvcmVhY2ggKCRuYW1lIGluICRyZXF1aXJlZCkgewogICAgICAgICAgICAkbWF0Y2ggPSBAKCRjaGVja3MuY2hlY2tfcnVucyB8IFdoZXJlLU9iamVjdCB7ICRfLm5hbWUgLWVxICRuYW1lIC1hbmQgJF8uY29uY2x1c2lvbiAtZXEgJ3N1Y2Nlc3MnIH0pCiAgICAgICAgICAgIGlmICgkbWF0Y2guQ291bnQgLWVxIDApIHsKICAgICAgICAgICAgICB0aHJvdyAiUmVxdWlyZWQgc3VjY2Vzc2Z1bCBjaGVjayAnJG5hbWUnIGlzIG1pc3NpbmcgZm9yIGV4YWN0IFNIQSAkZW52OkhFQURfU0hBLiIKICAgICAgICAgICAgfQogICAgICAgICAgfQoKICAgICAgLSBuYW1lOiBDaGVja291dCBleGFjdCBQUiBicmFuY2gKICAgICAgICB1c2VzOiBhY3Rpb25zL2NoZWNrb3V0QHY0CiAgICAgICAgd2l0aDoKICAgICAgICAgIGZldGNoLWRlcHRoOiAwCiAgICAgICAgICByZWY6ICR7eyBzdGVwcy5wci5vdXRwdXRzLmhlYWRfcmVmIH19CiAgICAgICAgICBwZXJzaXN0LWNyZWRlbnRpYWxzOiB0cnVlCgogICAgICAtIG5hbWU6IFZlcmlmeSBleGFjdCBjaGVja291dAogICAgICAgIHNoZWxsOiBwd3NoCiAgICAgICAgcnVuOiB8CiAgICAgICAgICAkYWN0dWFsID0gKGdpdCByZXYtcGFyc2UgSEVBRCkuVHJpbSgpCiAgICAgICAgICBpZiAoJGFjdHVhbCAtbmUgJyR7eyBzdGVwcy5wci5vdXRwdXRzLmhlYWRfc2hhIH19JykgewogICAgICAgICAgICB0aHJvdyAiQ2hlY2tvdXQgU0hBICckYWN0dWFsJyBkb2VzIG5vdCBtYXRjaCBhdXRob3JpemVkIFNIQSAnJHt7IHN0ZXBzLnByLm91dHB1dHMuaGVhZF9zaGEgfX0nLiIKICAgICAgICAgIH0KCiAgICAgIC0gbmFtZTogU2V0IHVwIFB5dGhvbiAzLjExCiAgICAgICAgdXNlczogYWN0aW9ucy9zZXR1cC1weXRob25AdjUKICAgICAgICB3aXRoOgogICAgICAgICAgcHl0aG9uLXZlcnNpb246ICIzLjExIgoKICAgICAgLSBuYW1lOiBSdW4gcmVtb3RlIHZhbGlkYXRlLXByIGFuZCBvbmxpbmUgYWNjZXB0YW5jZQogICAgICAgIGlkOiB2YWxpZGF0ZQogICAgICAgIGlmOiBzdGVwcy5hdXRob3JpemF0aW9uLm91dHB1dHMuYWN0aW9uID09ICd2YWxpZGF0ZS1wcicKICAgICAgICBzaGVsbDogcHdzaAogICAgICAgIGVudjoKICAgICAgICAgIE1JUk9fQUNDRVNTX1RPS0VOOiAke3sgc2VjcmV0cy5NSVJPX0FDQ0VTU19UT0tFTiB9fQogICAgICAgICAgR0hfVE9LRU46ICR7eyBnaXRodWIudG9rZW4gfX0KICAgICAgICBydW46IHwKICAgICAgICAgICRFcnJvckFjdGlvblByZWZlcmVuY2UgPSAnU3RvcCcKICAgICAgICAgIGlmIChbc3RyaW5nXTo6SXNOdWxsT3JXaGl0ZVNwYWNlKCRlbnY6TUlST19BQ0NFU1NfVE9LRU4pKSB7CiAgICAgICAgICAgIHRocm93ICdNSVJPX0FDQ0VTU19UT0tFTiByZXBvc2l0b3J5IHNlY3JldCBpcyBub3QgY29uZmlndXJlZC4nCiAgICAgICAgICB9CiAgICAgICAgICAuXGRkZGEucHMxIHZhbGlkYXRlLXByIGAKICAgICAgICAgICAgLVByIChbaW50XSRlbnY6UFJfTlVNQkVSKSBgCiAgICAgICAgICAgIC1XaXRoTWlybyBgCiAgICAgICAgICAgIC1GdWxsIGAKICAgICAgICAgICAgLUtlZXBSZXZpZXdCb2FyZCBgCiAgICAgICAgICAgIC1NaXJvVGVhbUlkICcke3sgc3RlcHMuYXV0aG9yaXphdGlvbi5vdXRwdXRzLm1pcm9fdGVhbV9pZCB9fScgYAogICAgICAgICAgICAtTm9uSW50ZXJhY3RpdmUKCiAgICAgIC0gbmFtZTogUnVuIGd1YXJkZWQgcmVtZWRpYXRpb24gd2l0aG91dCBwdXNoCiAgICAgICAgaWQ6IHJlbWVkaWF0ZQogICAgICAgIGlmOiBzdGVwcy5hdXRob3JpemF0aW9uLm91dHB1dHMuYWN0aW9uID09ICdyZW1lZGlhdGUnCiAgICAgICAgc2hlbGw6IHB3c2gKICAgICAgICBlbnY6CiAgICAgICAgICBBVVRIT1JJWkVEX0hFQURfU0hBOiAke3sgc3RlcHMucHIub3V0cHV0cy5oZWFkX3NoYSB9fQogICAgICAgICAgUkVNRURJQVRJT05fU0NSSVBUOiAke3sgc3RlcHMuYXV0aG9yaXphdGlvbi5vdXRwdXRzLnJlbWVkaWF0aW9uX3NjcmlwdCB9fQogICAgICAgIHJ1bjogfAogICAgICAgICAgJEVycm9yQWN0aW9uUHJlZmVyZW5jZSA9ICdTdG9wJwogICAgICAgICAgZ2l0IGNvbmZpZyB1c2VyLm5hbWUgJ0REREEgUmVtb3RlIFJlbWVkaWF0aW9uJwogICAgICAgICAgZ2l0IGNvbmZpZyB1c2VyLmVtYWlsICdkZGRhLXJlbW90ZS1yZW1lZGlhdGlvbkBleGFtcGxlLmludmFsaWQnCiAgICAgICAgICAkYmVmb3JlID0gKGdpdCByZXYtcGFyc2UgSEVBRCkuVHJpbSgpCiAgICAgICAgICBpZiAoJGJlZm9yZSAtbmUgJGVudjpBVVRIT1JJWkVEX0hFQURfU0hBKSB7CiAgICAgICAgICAgIHRocm93ICdSZW1lZGlhdGlvbiBjaGVja291dCBkcmlmdGVkIGJlZm9yZSBleGVjdXRpb24uJwogICAgICAgICAgfQogICAgICAgICAgJHNjcmlwdCA9IEpvaW4tUGF0aCAkUFdELlBhdGggJGVudjpSRU1FRElBVElPTl9TQ1JJUFQKICAgICAgICAgICYgJHNjcmlwdCAtUmVwb3NpdG9yeVJvb3QgJFBXRC5QYXRoIC1Ob1B1c2gKICAgICAgICAgIGlmICgkTEFTVEVYSVRDT0RFIC1uZSAwKSB7CiAgICAgICAgICAgIHRocm93ICJSZW1lZGlhdGlvbiBzY3JpcHQgZmFpbGVkIHdpdGggZXhpdCBjb2RlICRMQVNURVhJVENPREUuIgogICAgICAgICAgfQogICAgICAgICAgJGNoYW5nZXMgPSBnaXQgc3RhdHVzIC0tcG9yY2VsYWluCiAgICAgICAgICBpZiAoLW5vdCBbc3RyaW5nXTo6SXNOdWxsT3JXaGl0ZVNwYWNlKCgkY2hhbmdlcyAtam9pbiAiYG4iKSkpIHsKICAgICAgICAgICAgdGhyb3cgIlJlbWVkaWF0aW9uIGxlZnQgYSBkaXJ0eSB3b3JraW5nIHRyZWU6YG4kKCRjaGFuZ2VzIC1qb2luICJgbiIpIgogICAgICAgICAgfQogICAgICAgICAgJGFmdGVyID0gKGdpdCByZXYtcGFyc2UgSEVBRCkuVHJpbSgpCiAgICAgICAgICBpZiAoJGFmdGVyIC1lcSAkYmVmb3JlKSB7CiAgICAgICAgICAgIHRocm93ICdSZW1lZGlhdGlvbiBkaWQgbm90IGNyZWF0ZSBhIHZhbGlkYXRlZCBjb21taXQuJwogICAgICAgICAgfQogICAgICAgICAgJGNvbW1pdENvdW50ID0gW2ludF0oZ2l0IHJldi1saXN0IC0tY291bnQgIiRiZWZvcmUuLiRhZnRlciIpCiAgICAgICAgICBpZiAoJGNvbW1pdENvdW50IC1uZSAxKSB7CiAgICAgICAgICAgIHRocm93ICJSZW1vdGUgcmVtZWRpYXRpb24gbXVzdCBjcmVhdGUgZXhhY3RseSBvbmUgY29tbWl0OyBjcmVhdGVkICRjb21taXRDb3VudC4iCiAgICAgICAgICB9CiAgICAgICAgICBnaXQgcHVzaCBvcmlnaW4gIkhFQUQ6JHt7IHN0ZXBzLnByLm91dHB1dHMuaGVhZF9yZWYgfX0iCgogICAgICAtIG5hbWU6IFN0YWdlIGV4ZWN1dGlvbiBldmlkZW5jZQogICAgICAgIGlmOiBhbHdheXMoKQogICAgICAgIHNoZWxsOiBwd3NoCiAgICAgICAgcnVuOiB8CiAgICAgICAgICAkdGFyZ2V0ID0gSm9pbi1QYXRoICRlbnY6UlVOTkVSX1RFTVAgJ2RkZGEtcmVtb3RlLWV2aWRlbmNlJwogICAgICAgICAgTmV3LUl0ZW0gLUl0ZW1UeXBlIERpcmVjdG9yeSAtUGF0aCAkdGFyZ2V0IC1Gb3JjZSB8IE91dC1OdWxsCiAgICAgICAgICBmb3JlYWNoICgkc291cmNlIGluIEAoCiAgICAgICAgICAgIChKb2luLVBhdGggJGVudjpMT0NBTEFQUERBVEEgJ0REREFcdmFsaWRhdGlvbi1yZXBvcnRzJyksCiAgICAgICAgICAgIChKb2luLVBhdGggJGVudjpMT0NBTEFQUERBVEEgJ0REREFcYWNjZXB0YW5jZS1yZXBvcnRzJyksCiAgICAgICAgICAgIChKb2luLVBhdGggJGVudjpMT0NBTEFQUERBVEEgJ0REREFccmVtZWRpYXRpb24tY2hlY2tzJykKICAgICAgICAgICkpIHsKICAgICAgICAgICAgaWYgKFRlc3QtUGF0aCAtTGl0ZXJhbFBhdGggJHNvdXJjZSkgewogICAgICAgICAgICAgIENvcHktSXRlbSAtTGl0ZXJhbFBhdGggJHNvdXJjZSAtRGVzdGluYXRpb24gJHRhcmdldCAtUmVjdXJzZSAtRm9yY2UKICAgICAgICAgICAgfQogICAgICAgICAgfQogICAgICAgICAgQHsKICAgICAgICAgICAgcmVwb3NpdG9yeSA9ICRlbnY6UkVQT1NJVE9SWQogICAgICAgICAgICBwciA9IFtpbnRdJGVudjpQUl9OVU1CRVIKICAgICAgICAgICAgYWN0b3IgPSAkZW52OlJFUVVFU1RfQUNUT1IKICAgICAgICAgICAgY29tbWFuZCA9ICRlbnY6Q09NTUFORF9URVhUCiAgICAgICAgICAgIGF1dGhvcml6ZWRfc2hhID0gJyR7eyBzdGVwcy5wci5vdXRwdXRzLmhlYWRfc2hhIH19JwogICAgICAgICAgICBhY3Rpb24gPSAnJHt7IHN0ZXBzLmF1dGhvcml6YXRpb24ub3V0cHV0cy5hY3Rpb24gfX0nCiAgICAgICAgICAgIHJ1bl9pZCA9ICRlbnY6R0lUSFVCX1JVTl9JRAogICAgICAgICAgfSB8IENvbnZlcnRUby1Kc29uIC1EZXB0aCAxMCB8IFNldC1Db250ZW50IC1MaXRlcmFsUGF0aCAoSm9pbi1QYXRoICR0YXJnZXQgJ3JlcXVlc3QuanNvbicpIC1FbmNvZGluZyBVVEY4CgogICAgICAtIG5hbWU6IFVwbG9hZCBleGVjdXRpb24gZXZpZGVuY2UKICAgICAgICBpZjogYWx3YXlzKCkKICAgICAgICB1c2VzOiBhY3Rpb25zL3VwbG9hZC1hcnRpZmFjdEB2NAogICAgICAgIHdpdGg6CiAgICAgICAgICBuYW1lOiBkZGRhLXJlbW90ZS0ke3sgZW52LlBSX05VTUJFUiB9fS0ke3sgZ2l0aHViLnJ1bl9pZCB9fQogICAgICAgICAgcGF0aDogJHt7IHJ1bm5lci50ZW1wIH19L2RkZGEtcmVtb3RlLWV2aWRlbmNlLyoqCiAgICAgICAgICBpZi1uby1maWxlcy1mb3VuZDogd2FybgogICAgICAgICAgcmV0ZW50aW9uLWRheXM6IDE0CgogICAgICAtIG5hbWU6IENvbW1lbnQgZXhlY3V0aW9uIHJlc3VsdAogICAgICAgIGlmOiBhbHdheXMoKQogICAgICAgIHNoZWxsOiBwd3NoCiAgICAgICAgZW52OgogICAgICAgICAgR0hfVE9LRU46ICR7eyBnaXRodWIudG9rZW4gfX0KICAgICAgICAgIEpPQl9TVEFUVVM6ICR7eyBqb2Iuc3RhdHVzIH19CiAgICAgICAgcnVuOiB8CiAgICAgICAgICAkYm9keSA9IEAiCiAgICAgICAgICBEREEIHJlbW90ZSBleGVjdXRpb246ICoqJGVudjpKT0JfU1RBVFVTKioKCiAgICAgICAgICAtIGFjdGlvbjogYCR7eyBzdGVwcy5hdXRob3JpemF0aW9uLm91dHB1dHMuYWN0aW9uIH19YAogICAgICAgICAgLSBhdXRob3JpemVkIFNIQTogYCR7eyBzdGVwcy5wci5vdXRwdXRzLmhlYWRfc2hhIH19YAogICAgICAgICAgLSB3b3JrZmxvdyBydW46IGAke3sgZ2l0aHViLnNlcnZlcl91cmwgfX0vJHt7IGdpdGh1Yi5yZXBvc2l0b3J5IH19L2FjdGlvbnMvcnVucy8ke3sgZ2l0aHViLnJ1bl9pZCB9fWAKCk5vIG1lcmdlLCB0YWcsIHJlbGVhc2Ugb3IgcHJvbW90aW9uIHdhcyBwZXJmb3JtZWQuCiAgICAgICAgICAiQAogICAgICAgICAgZ2ggcHIgY29tbWVudCAkZW52OlBSX05VTUJFUiAtLXJlcG8gJGVudjpSRVBPU0lUT1JZIC0tYm9keSAkYm9keQo="
Write-Base64File -RelativePath "docs/developer-guide/remote-validation-broker.md" -Base64 "IyBSZW1vdGUgdmFsaWRhdGlvbiBhbmQgcmVtZWRpYXRpb24gYnJva2VyCgpERERBIHBvdcW+w612w6EgR2l0SHViIEFjdGlvbnMgamFrbyDFmcOtemVuw70gdnrDocOhbGVuw70gZXhlY3V0aW9uIHBsYW5lLiBDaGF0R1BUIGFuaSBqaW7DvSBrbGllbnQgbmVkb3N0w6F2w6EgTWlybyB0b2tlbiBuZWJvIEdpdEh1YiB3cml0ZSB0b2tlbi4KCiMjIETFry92b2QKCkxva8OhbG7DrSBQb3dlclNoZWxsIG3Fr8W+ZSBvYnNhaG92YXQgYW1iaWVudG7DrSBgUFlUSE9OUEFUSGAsIHXFvmn2YXRlbHNrw6kgaW5zdGFsYWNlIGEgbG9rw6FsbsOtIHNlY3JldHMuIFRvIGplIHZob2Ruw6kgcHJvIGRldmVsb3BtZW50LCBhbGUgbmVuw60gdG8gc3BvbGVobGl2w70gcGFja2FnZS1maXJzdCBhY2NlcHRhbmNlIHJ1bnRpbWUuCgpSZW1vdGUgYnJva2VyIG9kZMSbbHVqZToKCi0gcG/FvmFkYXZlayBuYSBzcHXFoXTEmW7DrTsKLSBhdXRvcml6YWNpIGEgZXhhY3QtU0hBIGJpbmRpbmc7Ci0gc2VjcmV0LWJlYXJpbmcgZXhlY3V0aW9uOwotIGV2aWRlbmNlIGEgaHVtYW4gcmV2aWV3LgoKIyMgSmVkbm9yw6F6b3bDqSBuYXN0YXZlbsOtCgpSZXBvc2l0b3J5IG5lYm8gZW52aXJvbm1lbnQgc2VjcmV0OgoKYGBgdGV4dApNSVJPX0FDQ0VTU19UT0tFTgpgYGAKClRva2VuIG11c8OtIG3DrXQgamVuIHBvdMWZZWJuw6kgTWlybyBzY29wZXMgYSBiw710IG9tZXplbiBuYSBwb3XFvsOtdmFuw70gdGVhbS4gVG9rZW4gc2UgbmV2a2zDoWTDoSBkbyBjaGF0dSwgc291Ym9ydSBhbmkgR2l0IGhpc3RvcmllLgoKIyMgUMWZw61rYXogcHJvIHZhbGlkYXRpb24gYSBvbmxpbmUgYWNjZXB0YW5jZQoKT3Byw6F2bsSbbsO9IGFjdG9yIHZsb8W+w60gZG8gUFIga29tZW50w6HFmToKCmBgYHRleHQKL2RkZGEgdmFsaWRhdGUtcHIgLS13aXRoLW1pcm8gLS1mdWxsIC0ta2VlcC1yZXZpZXctYm9hcmQKYGBgCgpCcm9rZXI6CgoxLiBuYcSNdGUgcG9saWN5IHogYGNvbmZpZy9wbGF0Zm9ybS9kZXZlbG9wbWVudC1wb2xpY3kueWFtbGA7CjIuIG92xJvFmWkgYWN0b3IsIHNhbWUtcmVwb3NpdG9yeSBQUiBhIGV4YWN0IGhlYWQgU0hBOwozLiB2ecW+YWR1amUgw7pzcMSbxIHFoW7DqSBjaGVja3kgYFBsYXRmb3JtIHZhbGlkYXRpb25gIGEgYE9uZS1jb21tYW5kIFBSIHZhbGlkYXRpb25gOwo0LiBjaGVja291dG5lIGV4YWN0IFNIQTsKNS4gc3B1c3TDrSBgZGRkYS5wczEgdmFsaWRhdGUtcHJgIHMgTWlybyB0b2tlbmVtIHBvdXplIHYgc2VjcmV0LWJlYXJpbmcga3Jva3U7CjYuIHphY2hvdsOhIHJldmlldyBib2FyZDsKNy4gcHVibGlrdWplIGV2aWRlbmNlIGFydGlmYWN0IGEgUFIga29tZW50w6HFmS4KCiMjIFDFmcOta2F6IHBybyByZW1lZGlhdGlvbgoKYGBgdGV4dAovZGRkYSByZW1lZGlhdGUgc2NyaXB0cy9yZW1lZGlhdGlvbi88c2NyaXB0Pi5wczEgLS1leHBlY3RlZC1zaGEgPDQwLWNoYXItc2hhPgpgYGAKClJlbWVkaWF0aW9uIHNrcmlwdCBtdXPDsToKCi0gYsO9dCB2IGBzY3JpcHRzL3JlbWVkaWF0aW9uL2A7Ci0gcG9kcG9yb3ZhdCBgLVJlcG9zaXRvcnlSb290YCBhIGAtTm9QdXNoYDsKLSBvdsSbxZnDrXQgdmxhc3Ruw60gbWFuaWZlc3QsIGJhc2UgU0hBLCBhbGxvd2VkIHBhdGhzIGEgaW50ZWdyaXR5IGhhc2hlczsKLSB2eXR2b8WZaXQgbWF4aW3DoWxuxJsgamVkZW4gY29tbWl0OwotIHNrb27EjWl0IHMgxI1pc3TDvW0gd29ya2luZyB0cmVlOwotIG5lcHJvdsOpc3QgbWVyZ2UsIHRhZywgcmVsZWFzZSwgcHJvbW90aW9uIGFuaSBmb3JjZS1wdXNoLgoKQnJva2VyIHNwdXPDsSBza3JpcHQgYmV6IEdpdEh1YiBBUEkgdG9rZW51LCBvdsSbxZnDrSBqZWRlbiBjb21taXQgYSB0ZXBydmUgcG90b20gcHVzaG5lIHDFmWVzbsO9IGJyYW5jaCBoZWFkLgoKIyMgUnVudGltZSBpc29sYXRpb24KCkNhbmRpZGF0ZSB2YWxpZGF0aW9uIG9kc3RyYcWIYWUgeiBjaGlsZCBwcm9jZXN1OgoKYGBgdGV4dApQWVRIT05QQVRIClBZVEhPTkhPTUUKREREQV9QTEFURk9STV9ST09UCkREREFfUkVQT19ST09UCmBgYAoKTWlybyBDTEkgYsSbxb7DrSBzIGBweXRob24gLUlgLiBQxZllZCBwcnZuw60gdnrDocOhbGVuw70gesOhcGlzZW0gc2Ugb3bEm8WZdWplOgoKLSBza3V0ZcSNbsO9IGBkZGRhX21pcm8ucmVuZGVyLl9fZmlsZV9fYDsKLSBTSEEtMjU2IGltcG9ydG92YW7DqWhvIGEgb8SNZWvDoXZhbsOpaG8gbW9kdWx1OwotIGBSRU5ERVJfQ09OVFJBQ1RfVkVSU0lPTmA7Ci0gYENBTk9OSUNBTF9HVUlERV9IRUFESU5HU2A7Ci0gY2FuZGlkYXRlIHNvdXJjZSBTSEE7Ci0gc2NhZmZvbGQgU0hBLTI1Ni4KCk5lc291bGxhZCBza29uxI3DrSBwxZllZCB2eXR2b8WZZW7DrW0gbmVibyB6bcSbbm91IGJvYXJkdS4KCiMjIEdvdmVybmFuY2UKClJlbW90ZSBicm9rZXIgbmlrZHkgYXV0b21hdGlja3kgbmVwcm92w6Fkw60gbWVyZ2UsIHRhZywgcmVsZWFzZSBhbmkgcHJvbW90aW9uLiBIdW1hbiB2aXN1YWwgYWNjZXB0YW5jZSBhIHJlbGVhc2UgZGVjaXNpb24gesWvc3TDqXZhacsOtIHNhbW9zdGF0bsO9bWkgbGlkc2vDvW1pIGtyb2t5Lgo="

$allowedPaths = @(
    ".github/workflows/assistant-command.yml",
    ".github/workflows/platform-ci.yml",
    "CHANGELOG.md",
    "config/platform/development-policy.yaml",
    "docs/developer-guide/remote-validation-broker.md",
    "scripts/Initialize-DDDAAfterClone.ps1",
    "scripts/Initialize-DDDAProjectMiro.ps1",
    "scripts/Test-DDDAAcceptance.ps1",
    "scripts/platform/Assert-DDDAMiroRuntimeProvenance.ps1",
    "scripts/platform/Invoke-DDDAPlatformTest.ps1",
    "scripts/platform/Invoke-DDDAValidatePr.ps1",
    "scripts/platform/Test-DDDARemoteExecutionRequest.ps1",
    "tests/powershell/Test-DDDARuntimeIsolation.ps1"
)
$changedPaths = @(& git -C $root diff --name-only)
$unexpected = @($changedPaths | Where-Object { $_ -notin $allowedPaths })
if ($unexpected.Count -gt 0) {
    throw "REM-003 changed unexpected paths:`n$($unexpected -join "`n")"
}
foreach ($requiredPath in $allowedPaths) {
    if ($requiredPath -notin $changedPaths) {
        throw "REM-003 did not change required path: $requiredPath"
    }
}

$validateText = Get-NormalizedText -RelativePath "scripts/platform/Invoke-DDDAValidatePr.ps1"
if ($validateText -notmatch 'sanitizedEnvironmentNames' -or $validateText -notmatch 'PYTHONPATH') {
    throw "validate-pr environment sanitization postcondition failed."
}
$projectMiroText = Get-NormalizedText -RelativePath "scripts/Initialize-DDDAProjectMiro.ps1"
if ($projectMiroText -notmatch '\$script:MiroPython -I -m ddda_miro' -or $projectMiroText -notmatch 'SuppressCommitInstructions') {
    throw "Miro CLI isolation postcondition failed."
}
$acceptanceText = Get-NormalizedText -RelativePath "scripts/Test-DDDAAcceptance.ps1"
if ($acceptanceText -notmatch 'runtime_provenance_status' -or $acceptanceText -notmatch 'invalid diagnostic output') {
    throw "Acceptance provenance postcondition failed."
}
$policyCheck = Get-NormalizedText -RelativePath $policyPath | ConvertFrom-Json
if (-not [bool]$policyCheck.remote_execution.enabled -or [string]$policyCheck.remote_execution.miro_team_id -ne "3458764678971681560") {
    throw "Remote execution policy postcondition failed."
}
if (-not (Test-Path -LiteralPath (Join-Path $root ".github/workflows/assistant-command.yml"))) {
    throw "Remote execution broker workflow was not created."
}

Write-Host "REM-PR8-HVA-CC-003 content application: PASS"
Write-Host "Changed paths: $($changedPaths.Count)"
