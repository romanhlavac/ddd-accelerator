[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [Parameter(Mandatory = $true)][ValidateSet("project-steering")][string]$Suite,
    [switch]$WithMiro,
    [switch]$Full,
    [switch]$ResetToken,
    [switch]$KeepReviewBoard,
    [switch]$CleanupOnFailure,
    [switch]$NonInteractive,
    [string]$MiroTeamId,
    [string]$EvidenceOutputPath,
    [switch]$EvidenceWrapperChild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {}

. (Join-Path $PSScriptRoot "private/DDDASteeringSupport.ps1")

$platformRoot = (Resolve-Path $PlatformPath).Path

if ($WithMiro -and -not $EvidenceWrapperChild) {
    $wrapperArguments = @{
        PlatformPath = $platformRoot
        Suite = $Suite
        Full = $Full
        ResetToken = $ResetToken
        KeepReviewBoard = $KeepReviewBoard
        CleanupOnFailure = $CleanupOnFailure
        NonInteractive = $NonInteractive
    }
    if (-not [string]::IsNullOrWhiteSpace($MiroTeamId)) {
        $wrapperArguments["MiroTeamId"] = $MiroTeamId
    }
    if (-not [string]::IsNullOrWhiteSpace($EvidenceOutputPath)) {
        $wrapperArguments["EvidenceOutputPath"] = $EvidenceOutputPath
    }
    & (Join-Path $platformRoot "scripts/platform/Invoke-DDDAMiroAcceptanceEvidence.ps1") @wrapperArguments
    exit $LASTEXITCODE
}

$runId = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss") + "-" + [Guid]::NewGuid().ToString("N").Substring(0, 8)
$workspaceRoot = Join-Path (Get-DDDAStateRoot) ("acceptance/" + $runId)
$projectRoot = Join-Path $workspaceRoot "projects/acceptance-claims-modernization"
$intakeFile = Join-Path $workspaceRoot "acceptance-intake.yaml"
$reportRoot = Join-Path (Get-DDDAStateRoot) ("acceptance-reports/" + $runId)
$reportFile = Join-Path $reportRoot "result.json"
$boardId = $null
$accessToken = $null
$oldMiroToken = $env:MIRO_ACCESS_TOKEN
$oldMiroTeamIdExists = Test-Path Env:\MIRO_TEAM_ID
$oldMiroTeamId = if ($oldMiroTeamIdExists) { [string]$env:MIRO_TEAM_ID } else { $null }
$remoteLayoutStatus = if ($WithMiro) { "FAIL" } else { "NOT_RUN" }
$renderContractVersion = "REM-PR8-HVA-CC-010"
$renderContractStatus = if ($WithMiro) { "FAIL" } else { "NOT_RUN" }
$platformSourceCommit = $null
$scaffoldSha256 = $null
$runtimeProvenanceStatus = if ($WithMiro) { "FAIL" } else { "NOT_RUN" }
$runtimeProvenanceEvidencePath = Join-Path $reportRoot "runtime-provenance.json"
$runtimeProvenance = $null
$remoteItemCount = 0
$overviewChildCount = 0
$starterReferenceCaptionCount = 0
$remoteContentDigest = $null
$reviewTeamSelectionStatus = if (-not $WithMiro) { "NOT_APPLICABLE" } elseif (-not [string]::IsNullOrWhiteSpace($MiroTeamId)) { "EXPLICIT_TEAM" } else { "DEFAULT_TOKEN_TEAM" }
$passed = $false

New-Item -ItemType Directory -Force -Path $workspaceRoot, $reportRoot | Out-Null

function Write-AcceptanceReport {
    param([string]$Status, [string]$ErrorMessage, [string]$GateStatus)
    $technicalSyncStatus = if ($Status -ne "PASS") { "FAIL" } elseif ($WithMiro) { "PASS" } else { "NOT_RUN" }
    $humanVisualStatus = if ($WithMiro) { "PENDING" } else { "NOT_APPLICABLE" }
    $overallStatus = if ($Status -ne "PASS") { "FAIL" } elseif ($WithMiro) { "PENDING_HUMAN_REVIEW" } else { "PASS_OFFLINE" }
    $payload = [ordered]@{
        suite = $Suite
        run_id = $runId
        status = $Status
        technical_sync_status = $technicalSyncStatus
        layout_contract_status = if ($Status -eq "PASS") { "PASS" } else { "FAIL" }
        remote_layout_status = if ($Status -eq "PASS") { $remoteLayoutStatus } else { "FAIL" }
        render_contract_status = if ($Status -eq "PASS") { $renderContractStatus } else { "FAIL" }
        render_contract_version = $renderContractVersion
        platform_source_commit = $platformSourceCommit
        scaffold_sha256 = $scaffoldSha256
        runtime_provenance_status = $runtimeProvenanceStatus
        runtime_provenance = $runtimeProvenance
        remote_item_count = $remoteItemCount
        overview_child_count = $overviewChildCount
        starter_reference_caption_count = $starterReferenceCaptionCount
        remote_content_digest = $remoteContentDigest
        review_team_selection_status = $reviewTeamSelectionStatus
        utf8_status = if ($Status -eq "PASS") { "PASS" } else { "FAIL" }
        human_visual_acceptance_status = $humanVisualStatus
        overall_status = $overallStatus
        platform = $platformRoot
        workspace = $workspaceRoot
        project = $projectRoot
        miro_board_id = $boardId
        miro_board_url = if ([string]::IsNullOrWhiteSpace([string]$boardId)) { $null } else { "https://miro.com/app/board/$boardId/" }
        gate_assertion = [ordered]@{
            gate = "G1"
            expected = "ready_for_review"
            actual = $GateStatus
            human_decision_created = $false
        }
        report_created_at = (Get-Date).ToUniversalTime().ToString("o")
        error = $ErrorMessage
    }
    $payload | ConvertTo-Json -Depth 10 | Set-Content -Path $reportFile -Encoding UTF8
}

function Get-BoardIdFromMap {
    param([Parameter(Mandatory = $true)][string]$MapPath)

    if (-not (Test-Path -LiteralPath $MapPath)) {
        return $null
    }

    $text = Get-Content -LiteralPath $MapPath -Raw -Encoding UTF8
    if ($text -match '(?m)^board_id:\s*["'']?(?<id>[^\s"'']+)["'']?\s*$') {
        return [string]$Matches["id"]
    }
    return $null
}

$g1Status = $null
try {
    Write-Host "=== DDDA acceptance suite: $Suite ==="
    if ($WithMiro) {
        $accessToken = Get-DDDAMiroAccessToken -ResetToken:$ResetToken -NonInteractive:$NonInteractive
        $env:MIRO_ACCESS_TOKEN = $accessToken
        if (-not [string]::IsNullOrWhiteSpace($MiroTeamId)) {
            $env:MIRO_TEAM_ID = $MiroTeamId
        }
        $packageManifestPath = Join-Path $platformRoot "ddda-package.json"
        if (-not (Test-Path -LiteralPath $packageManifestPath -PathType Leaf)) {
            throw "Online acceptance vyžaduje candidate package s ddda-package.json a exact source_commit."
        }
        $packageManifest = Get-Content -LiteralPath $packageManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $platformSourceCommit = [string]$packageManifest.source_commit
        if ($platformSourceCommit -notmatch '^[0-9a-f]{40}$') {
            throw "Candidate package neobsahuje platný exact source_commit."
        }
        $scaffoldPath = Join-Path $platformRoot "scaffolds/miro/strategic-ddd-method-board.yaml"
        if (-not (Test-Path -LiteralPath $scaffoldPath -PathType Leaf)) {
            throw "Candidate package neobsahuje Miro scaffold."
        }
        $scaffoldSha256 = (Get-FileHash -LiteralPath $scaffoldPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }
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
        $smokeArgs = @("-PlatformPath", $platformRoot, "-SkipRuntimeInstall", "-Full")
        if ($NonInteractive) { $smokeArgs += "-NonInteractive" }
        if ($CleanupOnFailure) { $smokeArgs += "-CleanupOnFailure" }
        Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Invoke-DDDAMiroSmokeTest.ps1") -Arguments $smokeArgs
    }

    @"
intake:
  schema_version: 1
  project_id: acceptance-claims-modernization
  name: Acceptance Claims Modernization
  type: legacy-modernization
  business_problem: Vendor lock-in zpomaluje změny a přesouvá znalost mimo organizaci.
  decision_to_enable: Potvrdit cílové doménové hranice a bezpečný první migrační řez.
  goal: Umožnit inkrementální modernizaci bez výpadku provozu.
  scope:
    in: [claim intake, adjudication]
    out: [pricing]
  actors: [claim handler, customer]
  constraints: [continuity of operations]
  assumptions: [audit trail is available]
  quality_attributes: [auditability, availability, recoverability]
  owners:
    business_owner: Acceptance Business Owner
    architecture_owner: Acceptance Architect
"@ | Set-Content -Path $intakeFile -Encoding UTF8

    $oldAuthorName = $env:GIT_AUTHOR_NAME
    $oldAuthorEmail = $env:GIT_AUTHOR_EMAIL
    $oldCommitterName = $env:GIT_COMMITTER_NAME
    $oldCommitterEmail = $env:GIT_COMMITTER_EMAIL
    $env:GIT_AUTHOR_NAME = "DDDA Acceptance"
    $env:GIT_AUTHOR_EMAIL = "ddda-acceptance@example.invalid"
    $env:GIT_COMMITTER_NAME = "DDDA Acceptance"
    $env:GIT_COMMITTER_EMAIL = "ddda-acceptance@example.invalid"
    try {
        Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAProjectFirstRun.ps1") -Arguments @(
            "-PlatformPath", $platformRoot,
            "-WorkspaceRoot", $workspaceRoot,
            "-IntakeFile", $intakeFile,
            "-NonInteractive"
        )
    }
    finally {
        $env:GIT_AUTHOR_NAME = $oldAuthorName
        $env:GIT_AUTHOR_EMAIL = $oldAuthorEmail
        $env:GIT_COMMITTER_NAME = $oldCommitterName
        $env:GIT_COMMITTER_EMAIL = $oldCommitterEmail
    }

    $statusText = & (Join-Path $platformRoot "scripts/Get-DDDAProjectStatus.ps1") -PlatformPath $platformRoot -ProjectPath $projectRoot -Json
    if ($LASTEXITCODE -ne 0) {
        throw "Read-only kontrola project statusu selhala."
    }
    $status = $statusText | ConvertFrom-Json
    if ($status.current_stage -ne "align" -or $status.next_gate -ne "G1") {
        throw "Steering acceptance očekával align/G1 bez lidského schválení, získal $($status.current_stage)/$($status.next_gate)."
    }
    $g1 = @($status.gates | Where-Object { $_.gate -eq "G1" }) | Select-Object -First 1
    $g1Status = if ($null -eq $g1) { $null } else { [string]$g1.status }
    if ($g1Status -ne "ready_for_review") {
        throw "Automatizace musí připravit G1 jako ready_for_review, získáno '$g1Status'."
    }

    $projectManifest = Get-Content -LiteralPath (Join-Path $projectRoot "project.yaml") -Raw -Encoding UTF8
    if ($projectManifest -match '(?ms)completed_gates:\s*\n\s*-\s*G1') {
        throw "Acceptance runner nesmí automaticky zapsat G1 do completed_gates."
    }
    $g1Record = Get-Content -LiteralPath (Join-Path $projectRoot "decisions/gates/G1.yaml") -Raw -Encoding UTF8
    if ($g1Record -match '(?m)^\s*status:\s*passed\s*$' -or $g1Record -match '(?m)^\s*provenance:\s*human\s*$') {
        throw "Acceptance runner nesmí vytvářet produkční lidské G1 rozhodnutí."
    }

    Assert-DDDACleanGitRepository -RepositoryPath $projectRoot -Label "Projektový po read-only status kontrole"

    if ($WithMiro) {
        $miroArgs = @(
            "-PlatformPath", $platformRoot,
            "-WorkspaceRoot", $workspaceRoot,
            "-ProjectId", "acceptance-claims-modernization",
            "-CreateBoard",
            "-SuppressCommitInstructions"
        )
        if ($NonInteractive) { $miroArgs += "-NonInteractive" }
        Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $platformRoot "scripts/Initialize-DDDAProjectMiro.ps1") -Arguments $miroArgs

        $mapPath = Join-Path $projectRoot "miro/miro-map.yaml"
        $statePath = Join-Path $projectRoot "miro/sync-state.yaml"
        $mapText = Get-Content -LiteralPath $mapPath -Raw -Encoding UTF8
        $stateText = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8
        $boardId = Get-BoardIdFromMap -MapPath $mapPath
        if ([string]::IsNullOrWhiteSpace([string]$boardId)) {
            throw "Acceptance runner nenalezl board_id v miro-map.yaml."
        }

        foreach ($artifactId in @("ddda.current-status", "ddda.next-actions", "acceptance-claims-modernization.project-charter")) {
            $escapedArtifactId = [regex]::Escape($artifactId)
            if ($mapText -notmatch $escapedArtifactId) {
                throw "Miro mapping neobsahuje managed artifact '$artifactId'."
            }
            if ($stateText -notmatch $escapedArtifactId) {
                throw "Miro sync state neobsahuje managed artifact '$artifactId'."
            }
            $entryPattern = "(?ms)^  $escapedArtifactId`:\s*\r?\n(?<body>(?:    .*?(?:\r?\n|$))*)(?=^  [^ ]|\z)"
            $entryMatch = [regex]::Match($mapText, $entryPattern)
            if (-not $entryMatch.Success) {
                throw "Miro mapping entry '$artifactId' nelze auditovat."
            }
            $entryBody = $entryMatch.Groups["body"].Value
            if ($entryBody -notmatch '(?m)^    frame_id:\s*control-center\s*$') {
                throw "Managed steering artifact '$artifactId' není v control-center."
            }
            if ($entryBody -notmatch '(?ms)^    position:\s*\r?\n(?:      .*\r?\n)*?      x:\s*-?\d+' -or $entryBody -notmatch '(?m)^      y:\s*-?\d+') {
                throw "Managed steering artifact '$artifactId' nemá deterministické x/y."
            }
        }

        foreach ($contract in @{ layout_contract_status = "PASS"; remote_layout_status = "PASS"; utf8_status = "PASS"; human_visual_acceptance_status = "PENDING"; overall_status = "PENDING_HUMAN_REVIEW" }.GetEnumerator()) {
            $pattern = "(?m)^$([regex]::Escape([string]$contract.Key)):\s*$([regex]::Escape([string]$contract.Value))\s*$"
            if ($mapText -notmatch $pattern) {
                throw "Miro mapping contract '$($contract.Key)' nemá očekávanou hodnotu '$($contract.Value)'."
            }
        }

        foreach ($binding in ([ordered]@{
            render_contract_version = $renderContractVersion
            platform_source_commit = $platformSourceCommit
            scaffold_sha256 = $scaffoldSha256
        }).GetEnumerator()) {
            $pattern = "(?m)^$([regex]::Escape([string]$binding.Key)):[ \t]*(?:\r?\n[ \t]+)?$([regex]::Escape([string]$binding.Value))[ \t]*$"
            if ($mapText -notmatch $pattern) {
                throw "Miro mapping není svázán s candidate package: '$($binding.Key)' neodpovídá '$($binding.Value)'."
            }
        }
        if ($mapText -notmatch '(?m)^remote_content_digest:[ \t]*(?:\r?\n[ \t]+)?[''"]?(?<digest>[0-9a-f]{64})[''"]?[ \t]*$') {
            throw "Miro mapping neobsahuje auditovatelný remote_content_digest."
        }
        $remoteContentDigest = [string]$Matches["digest"]

        $remoteItems = @(Get-DDDAAllMiroItems -BoardId $boardId -AccessToken $accessToken)
        $remoteItemCount = $remoteItems.Count
        if ($remoteItemCount -lt 280) {
            throw "Remote board má pouze $remoteItemCount položek; REM-010 vyžaduje nejméně 280 a nesmí odpovídat 262položkovému odmítnutému boardu."
        }
        $overviewFrames = @($remoteItems | Where-Object {
            $itemType = [string](Get-DDDAObjectPropertyValue -InputObject $_ -Name "type" -DefaultValue "")
            $itemData = Get-DDDAObjectPropertyValue -InputObject $_ -Name "data"
            $itemTitle = [string](Get-DDDAObjectPropertyValue -InputObject $itemData -Name "title" -DefaultValue "")
            $itemType -eq "frame" -and $itemTitle -eq "01 – DDD Starter journey, gates a iterace"
        })
        if ($overviewFrames.Count -ne 1) {
            throw "Remote board nemá právě jeden auditovatelný frame 01."
        }
        $overviewFrameId = [string](Get-DDDAObjectPropertyValue -InputObject $overviewFrames[0] -Name "id")
        $overviewChildCount = @($remoteItems | Where-Object {
            $parent = Get-DDDAObjectPropertyValue -InputObject $_ -Name "parent"
            [string](Get-DDDAObjectPropertyValue -InputObject $parent -Name "id" -DefaultValue "") -eq $overviewFrameId
        }).Count
        if ($overviewChildCount -lt 61) {
            throw "Frame 01 obsahuje pouze $overviewChildCount navigovatelných child items; REM-010 vyžaduje nejméně 61."
        }
        $visibleRemoteTexts = [System.Collections.Generic.List[string]]::new()
        foreach ($remoteItem in $remoteItems) {
            $data = Get-DDDAObjectPropertyValue -InputObject $remoteItem -Name "data"
            $content = [string](Get-DDDAObjectPropertyValue -InputObject $data -Name "content" -DefaultValue "")
            if ([string]::IsNullOrWhiteSpace($content)) {
                $content = [string](Get-DDDAObjectPropertyValue -InputObject $data -Name "title" -DefaultValue "")
            }
            if (-not [string]::IsNullOrWhiteSpace($content)) {
                $visibleRemoteTexts.Add($content)
            }
        }
        $visibleBoardText = [string]::Join("`n", $visibleRemoteTexts)
        foreach ($marker in @(
            "DDDA-RENDER-CONTRACT:$renderContractVersion",
            "DDDA-PLATFORM-SOURCE:$platformSourceCommit",
            "DDDA-SCAFFOLD-SHA256:$scaffoldSha256",
            "PROJECT / GATE STATE",
            "ARTIFACT LIFECYCLE",
            "ARTIFACT PROVENANCE",
            "ARTIFACT REGISTRY",
            "01 – DDD STARTER JOURNEY: REDLINE REWORKED",
            "REDLINE SOURCE: uXjVH2vcvRI=",
            "DDD STARTER SOURCE: uXjVH27wYU4="
        )) {
            if ($visibleBoardText -notmatch [regex]::Escape($marker)) {
                throw "Remote board neobsahuje povinný viditelný marker '$marker'."
            }
        }
        $starterReferenceCaptionCount = @($visibleRemoteTexts | Where-Object {
            $_ -match [regex]::Escape("DDD STARTER SOURCE: uXjVH27wYU4=")
        }).Count
        if ($starterReferenceCaptionCount -lt 11) {
            throw "Remote board obsahuje pouze $starterReferenceCaptionCount viditelných vazeb vzorů na DDD Starter board; REM-010 vyžaduje nejméně 11."
        }
        foreach ($sourceTitle in @(
            "Business model canvas - exercise",
            "Big Picture organized",
            "Process Modelling",
            "Finding Domains and subdomains - group 1",
            "Strategic classification",
            "Context Maps - Examples",
            "Bounded Context Canvas",
            "Domain Message Flow Modelling - Example"
        )) {
            if ($visibleBoardText -notmatch [regex]::Escape($sourceTitle)) {
                throw "Remote board necituje požadovaný DDD Starter artefakt '$sourceTitle'."
            }
        }
        foreach ($heading in @("RECEPT", "HOTOVO KDYŽ", "OTEVŘENÉ OTÁZKY", "HEURISTIKY", "ANTI-PATTERNS")) {
            $headingCount = @($visibleRemoteTexts | Where-Object { $_ -cmatch [regex]::Escape($heading) }).Count
            if ($headingCount -ne 15) {
                throw "Remote board musí obsahovat '$heading' v přesně 15 kanonických pracovních framech; nalezeno $headingCount."
            }
        }
        $workspaceCount = @($visibleRemoteTexts | Where-Object { $_ -match [regex]::Escape("EDITOVATELNÁ PRACOVNÍ PLOCHA") }).Count
        if ($workspaceCount -ne 15) {
            throw "Remote board musí obsahovat 15 viditelných editovatelných pracovních ploch; nalezeno $workspaceCount."
        }
        foreach ($column in @("Artifact", "Type", "Stage", "Lifecycle", "Provenance", "Owner", "Revision", "Last sync", "Detail")) {
            if ($visibleBoardText -notmatch [regex]::Escape($column)) {
                throw "Remote Artifact Registry neobsahuje viditelný sloupec '$column'."
            }
        }
        $renderContractStatus = "PASS"
        $remoteLayoutStatus = "PASS"
        $teamPattern = "(?m)^review_team_selection_status:\s*(?<status>EXPLICIT_TEAM|DEFAULT_TOKEN_TEAM)\s*$"
        if ($mapText -notmatch $teamPattern) {
            throw "Miro mapping neobsahuje review_team_selection_status."
        }
        $reviewTeamSelectionStatus = [string]$Matches["status"]
        if (-not [string]::IsNullOrWhiteSpace($MiroTeamId) -and $reviewTeamSelectionStatus -ne "EXPLICIT_TEAM") {
            throw "Explicitní Miro team nebyl použit pro review board."
        }
        $tracedGates = @([regex]::Matches($mapText, '(?m)^  - starter_step:.*\r?\n    stage:.*\r?\n    gate:\s*G[1-8]\s*$'))
        if ($tracedGates.Count -ne 8) { throw "Miro traceability nepokrývá přesně G1–G8." }
        $journeyItems = @([regex]::Matches($mapText, '(?m)^  journey:G[1-8]:\s*$'))
        if ($journeyItems.Count -ne 8) { throw "Miro mapping neobsahuje persistentní journey G1–G8." }
        foreach ($marker in @('â€“', 'â€”', 'Ă', 'Ĺ', 'Ä', '�')) {
            if ($mapText.Contains($marker) -or $stateText.Contains($marker)) {
                throw "UTF-8 regression: mapping nebo sync state obsahuje mojibake marker '$marker'."
            }
        }
    }

    $passed = $true
    Write-AcceptanceReport -Status "PASS" -ErrorMessage $null -GateStatus $g1Status
    Write-Host ""
    Write-Host "DDDA acceptance ${Suite}: TECHNICAL PASS"
    Write-Host "Gate assertion: G1 ready_for_review; human decision not created"
    if ($WithMiro) {
        Write-Host "Layout contract: PASS"
        Write-Host "Remote Miro layout: PASS"
        Write-Host "Render contract: $renderContractVersion PASS"
        Write-Host "Runtime provenance: $runtimeProvenanceStatus"
        Write-Host "Platform source: $platformSourceCommit"
        Write-Host "Scaffold SHA-256: $scaffoldSha256"
        Write-Host "Remote items: $remoteItemCount"
        Write-Host "Remote content digest: $remoteContentDigest"
        Write-Host "Review team selection: $reviewTeamSelectionStatus"
        Write-Host "UTF-8: PASS"
        Write-Host "Human visual acceptance: PENDING"
        Write-Host "Overall: PENDING_HUMAN_REVIEW"
    }
    Write-Host "Report: $reportFile"
}
catch {
    if ([string]::IsNullOrWhiteSpace([string]$boardId)) {
        $candidateMapPath = Join-Path $projectRoot "miro/miro-map.yaml"
        $boardId = Get-BoardIdFromMap -MapPath $candidateMapPath
    }
    Write-AcceptanceReport -Status "FAIL" -ErrorMessage $_.Exception.Message -GateStatus $g1Status
    if ($WithMiro) {
        Write-Host "Generated Miro project changes are invalid diagnostic output. Do not commit." -ForegroundColor Yellow
    }
    Write-Host "Acceptance workspace zachován pro diagnostiku: $workspaceRoot"
    Write-Host "Report: $reportFile"
    throw
}
finally {
    if ($WithMiro -and -not [string]::IsNullOrWhiteSpace([string]$boardId) -and -not $KeepReviewBoard -and ($passed -or $CleanupOnFailure)) {
        try {
            $boardSegment = [Uri]::EscapeDataString([string]$boardId)
            Invoke-DDDAMiroApi -Method DELETE -Uri "https://api.miro.com/v2/boards/$boardSegment" -AccessToken $accessToken | Out-Null
            $boardId = $null
        }
        catch {
            Write-Warning "Cleanup acceptance Miro boardu selhal: $($_.Exception.Message)"
        }
    }
    if ($null -eq $oldMiroToken) { Remove-Item Env:\MIRO_ACCESS_TOKEN -ErrorAction SilentlyContinue }
    else { $env:MIRO_ACCESS_TOKEN = $oldMiroToken }
    if ($oldMiroTeamIdExists) { $env:MIRO_TEAM_ID = $oldMiroTeamId }
    else { Remove-Item Env:\MIRO_TEAM_ID -ErrorAction SilentlyContinue }
    if ($passed -and -not $KeepReviewBoard -and (Test-Path $workspaceRoot)) {
        Remove-Item -Path $workspaceRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    elseif ($KeepReviewBoard -and $WithMiro) {
        Write-Host "Review board byl zachován. Board ID: $boardId"
        Write-Host "Board URL: https://miro.com/app/board/$boardId/"
        Write-Host "Workspace: $workspaceRoot"
    }
}
