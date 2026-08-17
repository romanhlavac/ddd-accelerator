[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PlatformPath "scripts/private/DDDAMiroSupport.ps1")

function Assert-True {
    param(
        [bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Assert-Equal {
    param(
        [object]$Expected,
        [object]$Actual,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($Expected -ne $Actual) {
        throw "$Message Očekáváno: '$Expected'; skutečnost: '$Actual'."
    }
}

function Get-FileSha256 {
    param([Parameter(Mandatory = $true)][string]$Path)

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-OptionalOriginUrl {
    param([Parameter(Mandatory = $true)][string]$RepositoryPath)

    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = @(& git -C $RepositoryPath remote get-url origin 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    if ($exitCode -ne 0) {
        return $null
    }

    return (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
}

function Get-ChangedPaths {
    param([Parameter(Mandatory = $true)][string]$RepositoryPath)

    $lines = @(& git -C $RepositoryPath status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) {
        throw "Nelze načíst Git status projektu."
    }

    $paths = @()
    foreach ($line in $lines) {
        $text = [string]$line
        if ([string]::IsNullOrWhiteSpace($text)) {
            continue
        }
        $path = $text.Substring(3).Trim()
        if ($path -match ' -> (?<target>.+)$') {
            $path = [string]$Matches["target"]
        }
        $paths += $path.Replace('\', '/')
    }

    return @($paths | Sort-Object -Unique)
}

function Write-Utf8Text {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Value
    )

    $parent = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    Set-Content -LiteralPath $Path -Value $Value -Encoding UTF8
}

$platformRoot = (Resolve-Path $PlatformPath).Path
$fixturePath = Join-Path $platformRoot "tests/fixtures/legacy-workspace/baseline.json"
$fixture = Get-Content -LiteralPath $fixturePath -Raw -Encoding UTF8 | ConvertFrom-Json

$tempRoot = Join-Path $env:TEMP ("ddda-legacy-compat-" + [Guid]::NewGuid().ToString("N"))
$workspaceRoot = Join-Path $tempRoot "workspace"
$projectId = [string]$fixture.workspace.project_id
$projectRoot = Join-Path $workspaceRoot ([string]$fixture.workspace.project_path)
$intakePath = Join-Path $tempRoot "legacy-intake.yaml"

try {
    New-Item -ItemType Directory -Force -Path $projectRoot | Out-Null

    Write-Utf8Text -Path (Join-Path $workspaceRoot "workspace.yaml") -Value @"
workspace:
  id: legacy-workspace
  name: "Synthetic Legacy Workspace"
  schema_version: 1

platform:
  path: ../../platform-not-used-by-fixture
  repository: synthetic/ddda-platform
  ref: legacy-baseline
  commit: 0000000000000000000000000000000000000000

projects:
  - id: legacy-claims
    path: projects/legacy-claims
    repository: "https://example.invalid/synthetic/legacy-claims.git"
    status: active
"@

    Write-Utf8Text -Path (Join-Path $workspaceRoot "DDDA.code-workspace") -Value @"
{
  "folders": [
    {
      "name": "Synthetic Legacy Claims",
      "path": "projects/legacy-claims"
    }
  ],
  "settings": {
    "git.openRepositoryInParentFolders": "always"
  }
}
"@

    Write-Utf8Text -Path (Join-Path $projectRoot "project.yaml") -Value @"
project:
  id: legacy-claims
  name: Synthetic Legacy Claims
  type: legacy-modernization
  schema_version: 1

ddda:
  repository: synthetic/ddda-platform
  required_ref: legacy-v0
  lock_file: ddda.lock.yaml

artifacts:
  canonical_source: yaml
  root: artifacts

legacy:
  owner: Claims Operations
  contract_version: pre-steering-v1
"@

    Write-Utf8Text -Path (Join-Path $projectRoot "ddda.lock.yaml") -Value @"
lock:
  schema_version: 1
  platform_ref: legacy-v0
  platform_commit: 1111111111111111111111111111111111111111
  locked_at: 2025-01-01T00:00:00Z
"@

    Write-Utf8Text -Path (Join-Path $projectRoot "artifacts/legacy/claims-model.yaml") -Value @"
legacy_model:
  id: synthetic-claims-model
  owner: Claims Operations
  status: active
"@

    Write-Utf8Text -Path (Join-Path $projectRoot "ingestion/legacy-notes.md") -Value @"
# Synthetic legacy notes

This fixture contains no client or production data.
"@

    Write-Utf8Text -Path (Join-Path $projectRoot "decisions/legacy-adr.md") -Value @"
# Synthetic legacy ADR

The project repository owns its domain model and decisions.
"@

    Write-Utf8Text -Path (Join-Path $projectRoot "workshops/prompts/legacy-discovery.md") -Value @"
# Synthetic workshop prompt
"@

    Write-Utf8Text -Path (Join-Path $projectRoot "miro/miro-map.yaml") -Value @"
schema_version: 1
project_id: legacy-claims
board_id: legacy-board-synthetic
items:
  legacy:model:
    miro_item_id: legacy-item-synthetic
frames:
  legacy:frame:
    miro_item_id: legacy-frame-synthetic
"@

    Write-Utf8Text -Path (Join-Path $projectRoot "miro/sync-state.yaml") -Value @"
schema_version: 1
project_id: legacy-claims
items:
  legacy:model:
    last_synced_hash: synthetic
"@

    foreach ($directory in @(
        "miro/conflicts",
        "reports",
        "reports/miro-sync",
        "exports"
    )) {
        New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot $directory) | Out-Null
        Write-Utf8Text -Path (Join-Path $projectRoot "$directory/.gitkeep") -Value ""
    }

    Write-Utf8Text -Path $intakePath -Value @"
intake:
  schema_version: 1
  project_id: legacy-claims
  name: Synthetic Legacy Claims
  type: legacy-modernization
  business_problem: Legacy coupling slows safe claims changes.
  decision_to_enable: Confirm domain boundaries and the first migration slice.
  goal: Adopt steering metadata without rewriting existing project assets.
  scope:
    in: [claim intake, adjudication]
    out: [pricing]
  actors: [claim handler, customer]
  constraints: [continuity of operations]
  assumptions: [legacy audit trail is available]
  quality_attributes: [auditability, availability]
  existing_systems: [synthetic legacy claims platform]
  teams: [claims operations]
  sources: [synthetic fixture]
  owners:
    business_owner: Claims Operations
    architecture_owner: Synthetic Architect
  classification:
    data_sensitivity: internal
    contains_health_data: false
"@

    & git -C $projectRoot init -b main 2>$null
    if ($LASTEXITCODE -ne 0) {
        & git -C $projectRoot init | Out-Null
        & git -C $projectRoot checkout -b main | Out-Null
    }
    & git -C $projectRoot config user.name "DDDA Legacy Compatibility Test"
    & git -C $projectRoot config user.email "ddda-legacy-test@example.invalid"
    & git -C $projectRoot remote add origin "https://example.invalid/synthetic/legacy-claims.git"
    & git -C $projectRoot add .
    & git -C $projectRoot commit -m "test: synthetic pre-steering baseline" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Nelze vytvořit syntetický legacy baseline commit."
    }

    $baselineHead = (& git -C $projectRoot rev-parse HEAD | Out-String).Trim()
    $baselineOrigin = Get-OptionalOriginUrl -RepositoryPath $projectRoot
    $workspaceHash = Get-FileSha256 -Path (Join-Path $workspaceRoot "workspace.yaml")

    $preservedHashes = @{}
    foreach ($relativePath in @($fixture.preserved_paths)) {
        $fullPath = Join-Path $projectRoot ([string]$relativePath)
        Assert-True -Condition (Test-Path -LiteralPath $fullPath -PathType Leaf) -Message "Baseline preserved path neexistuje: $relativePath"
        $preservedHashes[[string]$relativePath] = Get-FileSha256 -Path $fullPath
    }

    foreach ($relativePath in @($fixture.forbidden_implicit_paths)) {
        Assert-True -Condition (-not (Test-Path -LiteralPath (Join-Path $projectRoot ([string]$relativePath)))) -Message "Pre-steering fixture již obsahuje steering metadata: $relativePath"
    }

    & (Join-Path $platformRoot "scripts/Test-DDDAInstallation.ps1") `
        -PlatformPath $platformRoot `
        -WorkspaceRoot $workspaceRoot `
        -ProjectPath $projectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Read-only installation diagnostics legacy workspace odmítla."
    }

    $resolvedProject = Get-DDDAWorkspaceProjectPath -WorkspaceRoot $workspaceRoot -ProjectId $projectId
    Assert-Equal -Expected ([System.IO.Path]::GetFullPath($projectRoot)) -Actual ([System.IO.Path]::GetFullPath($resolvedProject)) -Message "Workspace registry nerozpoznal legacy projekt."

    $statusReadFailed = $false
    try {
        & (Join-Path $platformRoot "scripts/Get-DDDAProjectStatus.ps1") `
            -PlatformPath $platformRoot `
            -ProjectPath $projectRoot `
            -Json | Out-Null
    }
    catch {
        $statusReadFailed = $_.Exception.Message -match "Status report neexistuje"
    }
    Assert-True -Condition $statusReadFailed -Message "Read-only status nad pre-steering projektem má pouze vysvětlit chybějící explicitní adopci."

    $changesAfterReadOnly = @(Get-ChangedPaths -RepositoryPath $projectRoot)
    Assert-Equal -Expected 0 -Actual $changesAfterReadOnly.Count -Message "Read-only operace změnila legacy projekt."

    $resumeRequired = $false
    try {
        & (Join-Path $platformRoot "scripts/Initialize-DDDAProjectFirstRun.ps1") `
            -PlatformPath $platformRoot `
            -WorkspaceRoot $workspaceRoot `
            -IntakeFile $intakePath `
            -NoInitialCommit `
            -NonInteractive
    }
    catch {
        $resumeRequired = $_.Exception.Message -match "Pro bezpečné pokračování použij -Resume"
    }
    Assert-True -Condition $resumeRequired -Message "Existující projekt bez -Resume nebyl bezpečně odmítnut."
    Assert-Equal -Expected 0 -Actual (@(Get-ChangedPaths -RepositoryPath $projectRoot)).Count -Message "Odmítnutý běh bez -Resume změnil legacy projekt."

    & (Join-Path $platformRoot "scripts/Initialize-DDDAProjectFirstRun.ps1") `
        -PlatformPath $platformRoot `
        -WorkspaceRoot $workspaceRoot `
        -IntakeFile $intakePath `
        -Resume `
        -NoInitialCommit `
        -NonInteractive
    if ($LASTEXITCODE -ne 0) {
        throw "Explicitní legacy adoption přes -Resume selhala."
    }

    Assert-Equal -Expected $baselineHead -Actual ((& git -C $projectRoot rev-parse HEAD | Out-String).Trim()) -Message "Resume bez initial commit změnil Git HEAD."
    Assert-Equal -Expected $baselineOrigin -Actual (Get-OptionalOriginUrl -RepositoryPath $projectRoot) -Message "Repository ownership/origin se změnil."
    Assert-Equal -Expected $workspaceHash -Actual (Get-FileSha256 -Path (Join-Path $workspaceRoot "workspace.yaml")) -Message "Workspace registry se při adopci změnil."

    foreach ($relativePath in @($fixture.preserved_paths)) {
        $actualHash = Get-FileSha256 -Path (Join-Path $projectRoot ([string]$relativePath))
        Assert-Equal -Expected $preservedHashes[[string]$relativePath] -Actual $actualHash -Message "Explicitní adopce změnila preserved path: $relativePath"
    }

    $changedPaths = @(Get-ChangedPaths -RepositoryPath $projectRoot)
    $expectedPaths = @($fixture.expected_additive_paths | ForEach-Object { [string]$_ } | Sort-Object -Unique)
    $missingPaths = @($expectedPaths | Where-Object { $_ -notin $changedPaths })
    $unexpectedPaths = @($changedPaths | Where-Object { $_ -notin $expectedPaths })

    Assert-Equal -Expected 0 -Actual $missingPaths.Count -Message "Explicitní adopce nevytvořila očekávané aditivní soubory: $($missingPaths -join ', ')"
    Assert-Equal -Expected 0 -Actual $unexpectedPaths.Count -Message "Explicitní adopce změnila nedokumentované cesty: $($unexpectedPaths -join ', ')"

    foreach ($gate in 1..8) {
        $gatePath = Join-Path $projectRoot ("decisions/gates/G{0}.yaml" -f $gate)
        $gateText = Get-Content -LiteralPath $gatePath -Raw -Encoding UTF8
        Assert-True -Condition ($gateText -notmatch '(?m)^\s*status:\s*passed\s*$') -Message "G$gate byla automaticky označena passed."
        Assert-True -Condition ($gateText -notmatch '(?m)^\s*provenance:\s*human\s*$') -Message "G$gate obsahuje falešnou human provenance."
    }

    $projectText = Get-Content -LiteralPath (Join-Path $projectRoot "project.yaml") -Raw -Encoding UTF8
    Assert-True -Condition ($projectText -notmatch '(?m)^\s*completed_gates:\s*$') -Message "Legacy project.yaml byl doplněn o completed_gates."
    Assert-True -Condition ($projectText -notmatch '(?m)^\s*workflow:\s*$') -Message "Legacy project.yaml byl při adopci přepsán workflow blokem."

    $mapText = Get-Content -LiteralPath (Join-Path $projectRoot "miro/miro-map.yaml") -Raw -Encoding UTF8
    Assert-True -Condition ($mapText -match '(?m)^board_id:\s*legacy-board-synthetic\s*$') -Message "Původní Miro board ID nebylo zachováno."
    Assert-True -Condition ($mapText -match 'legacy-item-synthetic') -Message "Původní Miro mapping byl ztracen."

    $statusText = & (Join-Path $platformRoot "scripts/Get-DDDAProjectStatus.ps1") `
        -PlatformPath $platformRoot `
        -ProjectPath $projectRoot `
        -Json
    if ($LASTEXITCODE -ne 0) {
        throw "Read-only status po explicitní adopci selhal."
    }
    $status = $statusText | ConvertFrom-Json
    Assert-Equal -Expected "G1" -Actual ([string]$status.next_gate) -Message "Adopce nemá začínat na G1."
    Assert-True -Condition ((@($status.gates | Where-Object { $_.status -eq "passed" })).Count -eq 0) -Message "Adopce automaticky schválila gate."

    $fixtureSourcePaths = @($fixturePath, $intakePath)
    foreach ($relativePath in @($fixture.preserved_paths)) {
        $fixtureSourcePaths += Join-Path $projectRoot ([string]$relativePath)
    }
    $fixtureSourceText = @(
        $fixtureSourcePaths |
            Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
            ForEach-Object { Get-Content -LiteralPath $_ -Raw -Encoding UTF8 -ErrorAction SilentlyContinue }
    ) -join "`n"
    $secretPattern = '(?i)MIRO_ACCESS_TOKEN|Bearer\s+[A-Za-z0-9._-]{12,}'
    $windowsUserPathPattern = '(?i)[A-Z]:\\' + 'Users\\[^\\\s]+\\'
    $unixUserPathPattern = '(?i)/(' + 'Users|home' + ')/[^/\s]+/'
    Assert-True -Condition ($fixtureSourceText -notmatch $secretPattern) -Message "Versioned legacy fixture obsahuje secret."
    Assert-True -Condition ($fixtureSourceText -notmatch $windowsUserPathPattern) -Message "Versioned legacy fixture obsahuje Windows user-specific path."
    Assert-True -Condition ($fixtureSourceText -notmatch $unixUserPathPattern) -Message "Versioned legacy fixture obsahuje Unix user-specific path."

    Write-Host "DDDA legacy workspace compatibility test: PASS"
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
