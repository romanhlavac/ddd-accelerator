[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path,
    [switch]$PrePromotionCandidate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-True {
    param([bool]$Condition, [Parameter(Mandatory = $true)][string]$Message)
    if (-not $Condition) { throw $Message }
}

function Assert-Throws {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Action,
        [Parameter(Mandatory = $true)][string]$Message
    )
    $threw = $false
    try {
        & $Action
    }
    catch {
        $threw = $true
    }
    Assert-True -Condition $threw -Message $Message
}

$platformRoot = [System.IO.Path]::GetFullPath($PlatformPath).TrimEnd('\', '/')
$entryPath = Join-Path $platformRoot "ddda.ps1"
$governedMergePath = Join-Path $platformRoot "scripts/platform/Invoke-DDDAGovernedMergePr.ps1"
$governedPromotionPath = Join-Path $platformRoot "scripts/platform/Invoke-DDDAGovernedPromotePr.ps1"
$promotionPath = Join-Path $platformRoot "scripts/platform/Invoke-DDDAPromotePr.ps1"
$releaseGovernanceSupportPath = Join-Path $platformRoot "scripts/platform/DDDAReleaseGovernanceSupport.ps1"
$validatePrPath = Join-Path $platformRoot "scripts/platform/Invoke-DDDAValidatePr.ps1"
$validationReportPath = Join-Path $platformRoot "scripts/platform/New-DDDAValidationReport.ps1"
$platformCiPath = Join-Path $platformRoot ".github/workflows/platform-ci.yml"
$secondaryCiPath = Join-Path $platformRoot ".github/workflows/validate-ddda.yml"
$remoteBrokerPath = Join-Path $platformRoot ".github/workflows/assistant-command.yml"
$releaseScopeCollectorPath = Join-Path $platformRoot "scripts/platform/Test-DDDAReleaseScope.py"
$mergeEligibilityCollectorPath = Join-Path $platformRoot "scripts/platform/Test-DDDAMergeReleaseEligibility.py"
$releaseGovernanceRuntimePath = Join-Path $platformRoot "runtime/platform/release_governance.py"
$hrdrSchemaPath = Join-Path $platformRoot "schemas/human-release-decision.schema.json"
$githubSupportPath = Join-Path $platformRoot "scripts/platform/DDDAGitHubSupport.ps1"
$platformSupportPath = Join-Path $platformRoot "scripts/platform/DDDAPlatformSupport.ps1"
$changelogPath = Join-Path $platformRoot "CHANGELOG.md"
$policyPath = Join-Path $platformRoot "config/platform/development-policy.yaml"
$acceptancePath = Join-Path $platformRoot "scripts/Test-DDDAAcceptance.ps1"
$gateCommandPath = Join-Path $platformRoot "scripts/Complete-DDDALifecycleStep.ps1"
$enginePath = Join-Path $platformRoot "runtime/steering/ddda_steering/engine.py"
$gateSchemaPath = Join-Path $platformRoot "schemas/gate-status.schema.json"

foreach ($path in @($entryPath, $governedMergePath, $governedPromotionPath, $promotionPath, $releaseGovernanceSupportPath, $validatePrPath, $validationReportPath, $platformCiPath, $secondaryCiPath, $remoteBrokerPath, $releaseScopeCollectorPath, $mergeEligibilityCollectorPath, $releaseGovernanceRuntimePath, $hrdrSchemaPath, $githubSupportPath, $platformSupportPath, $changelogPath, $policyPath, $acceptancePath, $gateCommandPath, $enginePath, $gateSchemaPath)) {
    Assert-True -Condition (Test-Path -LiteralPath $path -PathType Leaf) -Message "Chybí merge/promotion nebo gate kontrakt: $path"
}

$entry = Get-Content -LiteralPath $entryPath -Raw -Encoding UTF8
$governedMerge = Get-Content -LiteralPath $governedMergePath -Raw -Encoding UTF8
$governedPromotion = Get-Content -LiteralPath $governedPromotionPath -Raw -Encoding UTF8
$promotion = Get-Content -LiteralPath $promotionPath -Raw -Encoding UTF8
$releaseGovernanceSupport = Get-Content -LiteralPath $releaseGovernanceSupportPath -Raw -Encoding UTF8
$validatePr = Get-Content -LiteralPath $validatePrPath -Raw -Encoding UTF8
$validationReport = Get-Content -LiteralPath $validationReportPath -Raw -Encoding UTF8
$platformCi = Get-Content -LiteralPath $platformCiPath -Raw -Encoding UTF8
$secondaryCi = Get-Content -LiteralPath $secondaryCiPath -Raw -Encoding UTF8
$remoteBroker = Get-Content -LiteralPath $remoteBrokerPath -Raw -Encoding UTF8
$releaseScopeCollector = Get-Content -LiteralPath $releaseScopeCollectorPath -Raw -Encoding UTF8
$mergeEligibilityCollector = Get-Content -LiteralPath $mergeEligibilityCollectorPath -Raw -Encoding UTF8
$releaseGovernanceRuntime = Get-Content -LiteralPath $releaseGovernanceRuntimePath -Raw -Encoding UTF8
$hrdrSchema = Get-Content -LiteralPath $hrdrSchemaPath -Raw -Encoding UTF8
$githubSupport = Get-Content -LiteralPath $githubSupportPath -Raw -Encoding UTF8
$platformSupport = Get-Content -LiteralPath $platformSupportPath -Raw -Encoding UTF8
$changelog = Get-Content -LiteralPath $changelogPath -Raw -Encoding UTF8
$policy = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$acceptance = Get-Content -LiteralPath $acceptancePath -Raw -Encoding UTF8
$gateCommand = Get-Content -LiteralPath $gateCommandPath -Raw -Encoding UTF8
$engine = Get-Content -LiteralPath $enginePath -Raw -Encoding UTF8
$gateSchema = Get-Content -LiteralPath $gateSchemaPath -Raw -Encoding UTF8

. $platformSupportPath
. $githubSupportPath
. $releaseGovernanceSupportPath

# Issue #9: root CLI must expose separate implementation merge and release promotion boundaries.
Assert-True -Condition ($entry -match 'ValidateSet\("doctor",\s*"test",\s*"validate-pr",\s*"merge-pr",\s*"review-pr",\s*"promote-pr"\)') -Message "Root CLI nepublikuje oddělený merge-pr + review-pr + promote-pr contract."
Assert-True -Condition ($entry -match 'Invoke-DDDAGovernedMergePr\.ps1') -Message "Root CLI neroutuje merge-pr přes governed implementation merge."
Assert-True -Condition ($entry -match 'Invoke-DDDAGovernedPromotePr\.ps1') -Message "Root CLI obchází governed release promotion wrapper."
Assert-True -Condition ($entry -match '\[switch\]\$ConfirmMerge') -Message "Root CLI nemá explicitní ConfirmMerge."
Assert-True -Condition ($entry -match '\[switch\]\$DryRun') -Message "Root CLI nemá DryRun."
Assert-True -Condition ($entry -match 'PackageArtifactName') -Message "Root CLI nepředává canonical artifact identity do validate-pr."
Assert-True -Condition ($entry -match 'ValidationReportPath') -Message "Root CLI nepředává přenositelnou validation evidence do merge-pr."
Assert-True -Condition ([bool]$policy.require_explicit_confirmation) -Message "Development policy nevyžaduje explicitní confirmation."
Assert-True -Condition ($policy.merge_method -in @("squash", "merge", "rebase")) -Message "Development policy má nepodporovaný merge method."
Assert-True -Condition (@($policy.required_documents).Count -ge 3) -Message "Development policy nemá povinné governance dokumenty."

# Governed implementation merge: exact evidence + human review + explicit confirmation; no release path.
$mergeDryRunMatch = [regex]::Match($governedMerge, 'if\s*\(\$DryRun\)', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
$mergeConfirmationMatch = [regex]::Match($governedMerge, 'require_explicit_confirmation[^\r\n]+\$ConfirmMerge', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
$mergeApiMatch = [regex]::Match($governedMerge, 'Merge-DDDAGitHubPullRequest', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
Assert-True -Condition ($mergeDryRunMatch.Success) -Message "merge-pr nemá fail-safe DryRun větev."
Assert-True -Condition ($mergeConfirmationMatch.Success) -Message "merge-pr nemá explicitní confirmation guard."
Assert-True -Condition ($mergeApiMatch.Success) -Message "merge-pr neobsahuje controlled GitHub API merge."
Assert-True -Condition ($mergeDryRunMatch.Index -lt $mergeApiMatch.Index) -Message "merge-pr DryRun musí předcházet merge side effectu."
Assert-True -Condition ($mergeConfirmationMatch.Index -lt $mergeApiMatch.Index) -Message "merge-pr confirmation musí předcházet merge side effectu."
Assert-True -Condition ($governedMerge -match 'Get-DDDACandidateValidationEvidence') -Message "merge-pr není vázán na exact-SHA validate-pr evidence."
Assert-True -Condition ($governedMerge -match 'PackageSha256') -Message "merge-pr neověřuje candidate package hash."
Assert-True -Condition ($governedMerge -match 'Get-DDDAHumanPrReviewComments') -Message "merge-pr nenačítá authoritativní Human Review."
Assert-True -Condition ($governedMerge -match 'candidate_package_sha256') -Message "merge-pr neváže Human Review na candidate package hash."
Assert-True -Condition ($governedMerge -match 'reviewed_sha') -Message "merge-pr neváže Human Review na exact PR SHA."
Assert-True -Condition ($governedMerge -match 'verdict[^\r\n]+pass') -Message "merge-pr nevyžaduje Human Review PASS."
Assert-True -Condition ($governedMerge -match '"repos/\{0\}/contents/\{1\}\?ref=\{2\}"\s+-f\s+\$repositorySlug,\s*\$relative,\s*\$headSha') -Message "merge-pr musí sestavit contents API URL bez PowerShell variable-name ambiguity."
Assert-True -Condition ($governedMerge -notmatch '\$relative\?ref') -Message "merge-pr nesmí interpretovat query delimiter jako součást názvu proměnné."
Assert-True -Condition ($governedMerge -match '-HeadSha\s+\$headSha') -Message "merge-pr nechrání GitHub merge exact head SHA."
Assert-True -Condition ($governedMerge -match 'Release Scope Gate:\s+NOT APPLICABLE') -Message "merge-pr nedeklaruje Release Scope Gate jako N/A na implementation boundary."
Assert-True -Condition ($governedMerge -notmatch 'Get-DDDAHrdrComments') -Message "merge-pr nesmí vyžadovat HRDR."
Assert-True -Condition ($governedMerge -notmatch 'Test-DDDAReleaseScope') -Message "merge-pr nesmí vyhodnocovat Release Scope Gate collector."
Assert-True -Condition ($governedMerge -notmatch 'Invoke-DDDAPromotePr\.ps1') -Message "merge-pr nesmí volat release promotion executor."
Assert-True -Condition ($governedMerge -notmatch 'New-DDDAPlatformPackage') -Message "merge-pr nesmí vytvářet release package."
Assert-True -Condition ($governedMerge -notmatch 'release-workspace') -Message "merge-pr nesmí vytvářet release validation workspace."
Assert-True -Condition ($governedMerge -notmatch '@\("tag"') -Message "merge-pr nesmí vytvářet Git tag."
Assert-True -Condition ($releaseGovernanceSupport -match 'ddda:human-pr-review:v1') -Message "Governance support nemá stabilní Human Review marker."
Assert-True -Condition ($releaseGovernanceSupport -match 'Get-DDDAHumanPrReviewComments') -Message "Governance support neumí načíst Human Review evidence."
Assert-True -Condition ($releaseGovernanceSupport -notmatch 'Set-DDDAHumanPrReview') -Message "Automation support nesmí publikovat Human Review PASS setter."

# Cross-stream integration assertions require the canonical main CI surface. A controlled
# recovery candidate proves its own source before promotion, without requiring unrelated
# future-release infrastructure.
if (-not $PrePromotionCandidate) {
    # Issue #88 regression: REST JSON arrays must be materialized before marker and
    # author extraction; only user.login is canonical and display name is ignored.
    $humanComment = [pscustomobject]@{
        body = '<!-- ddda:human-pr-review:v1 -->'
        user = [pscustomobject]@{
            login = 'romanhlavac'
            name = 'romanhlavac'
            type = 'User'
        }
    }
    $humanReview = [pscustomobject]@{ reviewer = 'romanhlavac' }
    $canonicalLogin = Assert-DDDAHumanPrReviewCommentProvenance -Comment $humanComment -Review $humanReview
    Assert-True -Condition ($canonicalLogin -eq 'romanhlavac') -Message "Canonical Human Review author musí být pouze GitHub user.login."
    Assert-True -Condition ($canonicalLogin -notmatch '\s') -Message "Display name nesmí být concatenován do canonical GitHub loginu."

    $missingLoginComment = [pscustomobject]@{ user = [pscustomobject]@{ name = 'romanhlavac'; type = 'User' } }
    Assert-Throws -Action {
        Assert-DDDAHumanPrReviewCommentProvenance -Comment $missingLoginComment -Review $humanReview
    } -Message "Chybějící Human Review user.login musí failnout closed."

    $ambiguousLoginComment = [pscustomobject]@{
        user = [pscustomobject]@{ login = @('romanhlavac', 'other-user'); name = 'romanhlavac'; type = 'User' }
    }
    Assert-Throws -Action {
        Assert-DDDAHumanPrReviewCommentProvenance -Comment $ambiguousLoginComment -Review $humanReview
    } -Message "Víceznačný Human Review user.login musí failnout closed."

    $botComment = [pscustomobject]@{ user = [pscustomobject]@{ login = 'reviewer[bot]'; name = 'Reviewer'; type = 'Bot' } }
    Assert-Throws -Action {
        Assert-DDDAHumanPrReviewCommentProvenance -Comment $botComment -Review ([pscustomobject]@{ reviewer = 'reviewer[bot]' })
    } -Message "Bot Human Review author musí failnout closed."

    Assert-Throws -Action {
        Assert-DDDAHumanPrReviewCommentProvenance -Comment $humanComment -Review ([pscustomobject]@{ reviewer = 'other-user' })
    } -Message "Human Review reviewer/user.login mismatch musí failnout closed."

    $reviewMarker = '<!-- ddda:human-pr-review:v1 -->'
    $script:humanReviewCommentApiResponse = @(
        $humanComment,
        [pscustomobject]@{
            body = '<!-- ddda:human-pr-review-duplicate:v1 --> non-authoritative ddda:human-pr-review:v1'
            user = [pscustomobject]@{ login = 'romanhlavac'; name = 'romanhlavac'; type = 'User' }
        },
        [pscustomobject]@{
            body = '<!-- ddda:human-pr-review-superseded:v1 --> historical record'
            user = [pscustomobject]@{ login = 'romanhlavac'; name = 'romanhlavac'; type = 'User' }
        }
    )
    $originalGitHubApi = (Get-Command Invoke-DDDAGitHubApi).ScriptBlock
    try {
        Set-Item -Path Function:Invoke-DDDAGitHubApi -Value {
            param($Method, $Path, $Token, $Body)
            Write-Output -NoEnumerate $script:humanReviewCommentApiResponse
        }
        $selectedHumanComments = @(Get-DDDAHumanPrReviewComments -RepositorySlug 'romanhlavac/ddd-accelerator' -Pr 92 -Token 'test-only')
    }
    finally {
        Set-Item -Path Function:Invoke-DDDAGitHubApi -Value $originalGitHubApi
    }
    Assert-True -Condition ($selectedHumanComments.Count -eq 1) -Message "Právě jeden authoritative Human Review marker musí projít selection."
    Assert-True -Condition ($selectedHumanComments[0].body -eq $reviewMarker) -Message "Duplicate/superseded Human Review marker musí být ignorován."
    Assert-True -Condition ($releaseGovernanceSupport -match '\$response\s*=\s*Invoke-DDDAGitHubApi[\s\S]+?\$batch\s*=\s*@\(\$response\)') -Message "GitHub Issues Comments REST array musí být materializován před iterací."

    # Issue #88: one exact-SHA validation decision must preserve one canonical candidate identity.
    Assert-True -Condition ($validatePr -match '\[string\]\$PackagePath') -Message "validate-pr nemá řízený PackagePath input."
    Assert-True -Condition (([regex]::Matches($validatePr, 'New-DDDAPlatformPackage\.ps1')).Count -eq 1) -Message "validate-pr obsahuje více než jednu package build cestu."
    Assert-True -Condition ($validatePr -match 'if\s*\(\[string\]::IsNullOrWhiteSpace\(\$PackagePath\)\)') -Message "validate-pr neomezuje package build pouze na chybějící PackagePath."
    Assert-True -Condition ($validatePr -match 'ExpectedCommit[^\r\n]+\$headSha') -Message "validate-pr neověřuje source_commit předaného package."
    Assert-True -Condition ($validatePr -match 'ExpectedKind[^\r\n]+candidate') -Message "validate-pr neověřuje kind=candidate."
    Assert-True -Condition ($validationReport -match 'PackageArtifactName' -and $validationReport -match 'WorkflowRunId') -Message "Validation report neuchovává canonical artifact/run identity."
    Assert-True -Condition ($validationReport -match 'PortablePaths') -Message "Validation report neumí odstranit runner-local cesty z publikované evidence."
    Assert-True -Condition ($releaseGovernanceSupport -match '\[string\]\$ValidationReportPath' -and $releaseGovernanceSupport -match '\[string\]\$PackagePath') -Message "Merge evidence resolver neumí explicitní artifact/report z čistého runneru."
    Assert-True -Condition ($governedMerge -match 'ExpectedCommit[^\r\n]+\$headSha' -and $governedMerge -match 'ExpectedKind[^\r\n]+candidate') -Message "merge-pr znovu neověřuje candidate kind/source_commit."
    Assert-True -Condition ($platformCi -match '(?s)validate-pr-command:\s+name: One-command PR validation\s+needs: validate-platform') -Message "validate-pr-command nezávisí na canonical package jobu."
    Assert-True -Condition ($platformCi -match 'Download canonical candidate package') -Message "validate-pr-command nestahuje canonical candidate artifact."
    Assert-True -Condition ($platformCi -match '-PackagePath \$packages\[0\]\.FullName') -Message "CI nepředává stažený canonical package do validate-pr."
    Assert-True -Condition ($platformCi -match '\$version = ''candidate\.''' -and $platformCi -notmatch '\$version = ''ci\.''' ) -Message "Candidate metadata není stabilně odvozeno pouze z exact SHA."
    Assert-True -Condition ($secondaryCi -notmatch 'New-DDDAPlatformPackage\.ps1') -Message "Sekundární CI workflow nesmí vytvářet nezávislý candidate package."
    $workflowCandidateBuilders = @(
        Get-ChildItem -LiteralPath (Join-Path $platformRoot '.github/workflows') -Filter '*.yml' -File |
            Select-String -Pattern 'New-DDDAPlatformPackage\.ps1'
    )
    Assert-True -Condition ($workflowCandidateBuilders.Count -eq 1 -and $workflowCandidateBuilders[0].Path -eq $platformCiPath) -Message "Repository musí mít právě jeden CI candidate builder v canonical platform workflow."
    $humanReadinessJob = [regex]::Match($platformCi, '(?ms)^  human-review-readiness:\r?\n(?<body>.*?)(?=^  governed-merge-dry-run:)')
    $mergeDryRunJob = [regex]::Match($platformCi, '(?ms)^  governed-merge-dry-run:\r?\n(?<body>.*)\z')
    Assert-True -Condition $humanReadinessJob.Success -Message "Standard CI nemá samostatný Human Review readiness coordinator."
    Assert-True -Condition $mergeDryRunJob.Success -Message "Standard CI nemá samostatný governed merge dry-run job."
    $humanReadinessBody = $humanReadinessJob.Groups['body'].Value
    $mergeDryRunBody = $mergeDryRunJob.Groups['body'].Value
    Assert-True -Condition ($humanReadinessBody -match 'name: Human Review readiness') -Message "Readiness coordinator není jednoznačně pojmenovaný."
    Assert-True -Condition ($humanReadinessBody -match 'ready:\s+\$\{\{\s*steps\.human-review\.outputs\.ready\s*\}\}') -Message "Readiness coordinator nepublikuje machine-readable ready output."
    Assert-True -Condition ($humanReadinessBody -match 'PENDING.+Governed merge dry-run.+NOT_RUN') -Message "Pre-HR stav není explicitně reportován jako PENDING / NOT_RUN."
    Assert-True -Condition ($humanReadinessBody -notmatch 'ddda\.ps1 merge-pr') -Message "Readiness coordinator nesmí být současně merge preflight."
    Assert-True -Condition ($mergeDryRunBody -match '(?s)needs:.+?- human-review-readiness') -Message "Governed merge dry-run nezávisí na readiness coordinatoru."
    Assert-True -Condition ($mergeDryRunBody -match "if: github\.event_name == 'pull_request' && needs\.human-review-readiness\.outputs\.ready == 'true'") -Message "Governed merge dry-run není na job-level blokovaný Human Review readiness."
    Assert-True -Condition ($mergeDryRunBody -notmatch 'steps\.human-review\.outputs\.ready') -Message "Governed merge dry-run stále používá step-level skip, který může vytvořit false PASS."
    Assert-True -Condition ($mergeDryRunBody -match 'Download exact-run canonical candidate' -and $mergeDryRunBody -match 'Download exact-run validation evidence') -Message "Governed merge dry-run nestahuje exact-run candidate a report."
    Assert-True -Condition ($mergeDryRunBody -match '\.\\ddda\.ps1 merge-pr' -and $mergeDryRunBody -match '-ValidationReportPath \$reports\[0\]\.FullName' -and $mergeDryRunBody -match '-DryRun') -Message "Governed merge dry-run neprovádí skutečný isolated merge-pr -DryRun."
    Assert-True -Condition ($mergeDryRunBody -notmatch 'New-DDDAPlatformPackage\.ps1') -Message "Post-HR merge dry-run nesmí znovu sestavit candidate package."
    Assert-True -Condition ($mergeDryRunBody -match 'packages\.Count -ne 1' -and $mergeDryRunBody -match 'reports\.Count -ne 1') -Message "Artifact resolution není fail-closed pro chybějící/víceznačnou evidence."
    Assert-True -Condition ($remoteBroker -match 'actions: read') -Message "Remote broker nemá read-only přístup k canonical Actions artifactu."
    Assert-True -Condition ($remoteBroker -match 'Download exact-SHA canonical candidate' -and $remoteBroker -match '-PackageWorkflowRunId') -Message "Remote broker stále vytváří nezávislou candidate identity."


}

# Public release promotion must stay strictly gated before the release executor is reachable.
$scopeGateMatch = [regex]::Match($governedPromotion, 'release_scope_gate_status[^\r\n]+PASS', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
$sideEffectsMatch = [regex]::Match($governedPromotion, 'side_effects_allowed', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
$legacyExecutorMatch = [regex]::Match($governedPromotion, 'Invoke-DDDAPromotePr\.ps1', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
Assert-True -Condition ($scopeGateMatch.Success) -Message "Governed promotion nevyžaduje Release Scope Gate PASS."
Assert-True -Condition ($sideEffectsMatch.Success) -Message "Governed promotion neověřuje side_effects_allowed."
Assert-True -Condition ($legacyExecutorMatch.Success) -Message "Governed promotion nevolá canonical release executor až po gate."
Assert-True -Condition ($scopeGateMatch.Index -lt $legacyExecutorMatch.Index) -Message "Release Scope Gate musí předcházet release executor side effects."
Assert-True -Condition ($governedPromotion -match 'Get-DDDAHrdrComments') -Message "Governed promotion nenačítá authoritativní HRDR."
Assert-True -Condition ($governedPromotion -match 'commentAuthorType\s*-eq\s*"Bot"') -Message "Governed promotion neodmítá bot HRDR provenance."
Assert-True -Condition ($governedPromotion -match 'DDDA_GITHUB_PROJECT_TOKEN') -Message "Release Scope Gate nevyžaduje Project V2 read-back token."
Assert-True -Condition ($releaseGovernanceSupport -match 'ddda:human-release-decision:v1') -Message "HRDR support nemá stabilní authoritative marker."
Assert-True -Condition ($releaseGovernanceSupport -match 'decision\s*=\s*"pending"' -or $hrdrSchema -match '"pending"') -Message "HRDR contract neobsahuje pending human state."
Assert-True -Condition ($releaseScopeCollector -match 'dependencies/blocked_by') -Message "Release Scope collector nečte native blockers."
Assert-True -Condition ($releaseScopeCollector -match 'Project V2') -Message "Release Scope collector neobsahuje Project V2 read-back."
Assert-True -Condition ($releaseScopeCollector -match 'previous_release_tag' -and $releaseScopeCollector -match 'compare/') -Message "Release Scope collector neodvozuje physical source od předchozího release tagu."
Assert-True -Condition ($releaseScopeCollector -match 'commits/.+/pulls' -and $releaseScopeCollector -match 'primary_change_requests') -Message "Release Scope collector nemapuje shipping commity na primary CR."
Assert-True -Condition ($releaseGovernanceRuntime -match 'RECOVERY_DECISION_REQUIRED') -Message "Physical scope mismatch nemá explicitní human recovery boundary."
Assert-True -Condition ($governedMerge -match 'Test-DDDAMergeReleaseEligibility\.py') -Message "Governed merge nevolá releasable-main eligibility guard."
Assert-True -Condition ($releaseGovernanceRuntime -match 'MERGE_ELIGIBILITY_OUTSIDE_ACTIVE_RELEASE') -Message "Merge eligibility guard neblokuje PR mimo aktivní release train."

$dryRunMatch = [regex]::Match($promotion, 'if\s*\(\$DryRun\)', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
$confirmationMatch = [regex]::Match($promotion, 'if\s*\(\[bool\]\$policy\.require_explicit_confirmation\s*-and\s*-not\s*\$ConfirmMerge\)', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
$promotionMergeMatch = [regex]::Match($promotion, 'Merge-DDDAGitHubPullRequest', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
$releaseGateMatch = [regex]::Match($promotion, 'if\s*\(\s*-not\s+\$releasePassed(?:\s*-or\s*-not\s+\$releaseReportCreated)?\s*\)', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
$tagCreationMatch = [regex]::Match($promotion, 'Invoke-DDDAPlatformGit[^\r\n]+@\("tag"', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
$changelogGuardMatch = [regex]::Match($promotion, 'Assert-DDDAPlatformChangelogRelease', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)

$dryRunIndex = if ($dryRunMatch.Success) { $dryRunMatch.Index } else { -1 }
$confirmationIndex = if ($confirmationMatch.Success) { $confirmationMatch.Index } else { -1 }
$promotionMergeIndex = if ($promotionMergeMatch.Success) { $promotionMergeMatch.Index } else { -1 }
$releaseGateIndex = if ($releaseGateMatch.Success) { $releaseGateMatch.Index } else { -1 }
$tagCreationIndex = if ($tagCreationMatch.Success) { $tagCreationMatch.Index } else { -1 }
$changelogGuardIndex = if ($changelogGuardMatch.Success) { $changelogGuardMatch.Index } else { -1 }

Assert-True -Condition ($dryRunIndex -ge 0) -Message "Promotion nemá fail-safe DryRun větev."
Assert-True -Condition ($confirmationIndex -ge 0) -Message "Promotion nemá explicitní confirmation guard."
Assert-True -Condition ($promotionMergeIndex -ge 0) -Message "Promotion neobsahuje kontrolovaný release-candidate merge."
Assert-True -Condition ($dryRunIndex -lt $promotionMergeIndex) -Message "Promotion DryRun guard musí předcházet merge operaci."
Assert-True -Condition ($confirmationIndex -lt $promotionMergeIndex) -Message "Promotion confirmation guard musí předcházet merge operaci."
Assert-True -Condition ($promotion -match '-HeadSha\s+\$headSha') -Message "Promotion nechrání merge exact head SHA."
Assert-True -Condition ($promotion -match 'validation-reports/pr-\$Pr-\$headSha') -Message "Promotion nehledá validation report podle PR a exact SHA."
Assert-True -Condition ($promotion -match 'actualCandidateHash') -Message "Promotion neověřuje candidate package hash."
Assert-True -Condition ($changelogGuardIndex -ge 0) -Message "Promotion neověřuje changelog release contract."
Assert-True -Condition ($changelogGuardIndex -lt $dryRunIndex) -Message "Changelog release contract musí být ověřen před DryRun PASS."
Assert-True -Condition ($changelogGuardIndex -lt $promotionMergeIndex) -Message "Changelog release contract musí být ověřen před release-candidate merge."
Assert-True -Condition ($platformSupport -match 'function\s+Assert-DDDAPlatformChangelogRelease') -Message "Platform support neobsahuje changelog release validator."
Assert-True -Condition ($promotion -match '\$tag\s*=\s*\[string\]\$changelogRelease\.Tag') -Message "Release tag není odvozen ze stejného changelog/version kontraktu."
Assert-True -Condition ($changelog -match '(?m)^## \[Unreleased\]\s*$') -Message "Changelog nemá kanonickou [Unreleased] sekci."
$versionHeadingPattern = '(?m)^## \[(?<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))\] - (?<date>\d{4}-\d{2}-\d{2})\s*$'
$versionHeading = [regex]::Match($changelog, $versionHeadingPattern, [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
Assert-True -Condition $versionHeading.Success -Message "Changelog nemá platný versioned release cut."
if ($versionHeading.Success) {
    Assert-True -Condition ($versionHeading.Groups["version"].Value -match '^\d+\.\d+\.\d+$') -Message "Changelog release heading nemá SemVer."
}
Assert-True -Condition ($promotion -notmatch 'Get-Command\s+"gh"[^\r\n]+throw') -Message "Promotion nesmí tvrdě vyžadovat instalovaný GitHub CLI."
Assert-True -Condition ($githubSupport -match 'git credential fill') -Message "GitHub support nepoužívá existující Git credential helper jako fallback."
Assert-True -Condition ($githubSupport -match 'GH_TOKEN') -Message "GitHub support nepodporuje GH_TOKEN."
Assert-True -Condition ($githubSupport -match 'GITHUB_TOKEN') -Message "GitHub support nepodporuje GITHUB_TOKEN."
Assert-True -Condition ($githubSupport -match 'Invoke-RestMethod') -Message "GitHub support neobsahuje REST API klienta."
$authGhTokenIndex = $githubSupport.IndexOf('Name = "GH_TOKEN"', [System.StringComparison]::Ordinal)
$authGithubTokenIndex = $githubSupport.IndexOf('Name = "GITHUB_TOKEN"', [System.StringComparison]::Ordinal)
$authGhCliIndex = $githubSupport.IndexOf('Source = "gh auth token"', [System.StringComparison]::Ordinal)
$authCredentialIndex = $githubSupport.IndexOf('Source = "git credential helper"', [System.StringComparison]::Ordinal)
Assert-True -Condition ($authGhTokenIndex -ge 0 -and $authGhTokenIndex -lt $authGithubTokenIndex) -Message "GH_TOKEN musí být první auth provider."
Assert-True -Condition ($authGithubTokenIndex -lt $authGhCliIndex) -Message "GITHUB_TOKEN musí předcházet gh auth token."
Assert-True -Condition ($authGhCliIndex -lt $authCredentialIndex) -Message "gh auth token musí předcházet Git credential helper fallbacku."
Assert-True -Condition ($releaseGateIndex -ge 0) -Message "Promotion nemá release validation gate před tagem."
Assert-True -Condition ($tagCreationIndex -ge 0) -Message "Promotion neobsahuje kontrolované vytvoření release tagu."
Assert-True -Condition ($releaseGateIndex -lt $tagCreationIndex) -Message "Release validation gate musí předcházet vytvoření tagu."

# Issue #13: automation must not manufacture human decisions.
Assert-True -Condition ($acceptance -notmatch '-Outcome\s+["'']?passed') -Message "Acceptance runner stále automaticky vytváří passed."
Assert-True -Condition ($acceptance -match 'ready_for_review') -Message "Acceptance runner neověřuje ready_for_review."
Assert-True -Condition ($acceptance -match 'human_decision_created\s*=\s*\$false') -Message "Acceptance report nedokládá, že nebylo vytvořeno lidské rozhodnutí."
Assert-True -Condition ($gateCommand -match '\[switch\]\$HumanDecision') -Message "Gate command nemá explicitní HumanDecision boundary."
Assert-True -Condition ($gateCommand -match 'Automatizace nesmí vytvářet produkční gate decision') -Message "Gate command nemá fail-closed guard proti automatickému rozhodnutí."
Assert-True -Condition ($engine -match 'AUTOMATION_IDENTITY') -Message "Steering engine neblokuje spoofed automation identity."
Assert-True -Condition ($engine -match 'provenance != "human"') -Message "Steering engine nevynucuje human provenance."
Assert-True -Condition ($engine -match 'artifact_hashes') -Message "Steering engine neváže rozhodnutí na evidence hashes."
Assert-True -Condition ($gateSchema -match 'decision_owner') -Message "Gate schema nemá decision ownera."
Assert-True -Condition ($gateSchema -match 'project_commit') -Message "Gate schema nemá project commit vazbu."
Assert-True -Condition ($gateSchema -match 'test_simulation') -Message "Gate schema nerozlišuje test-only simulation."

$credential = ConvertFrom-DDDAGitCredential -Text "protocol=https`nhost=github.com`nusername=test-user`npassword=test-token`n"
Assert-True -Condition ($credential.Username -eq "test-user") -Message "Git credential parser nevrátil username."
Assert-True -Condition ($credential.Password -eq "test-token") -Message "Git credential parser nevrátil token."

$evidenceRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-candidate-evidence-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
try {
    $evidencePr = 88
    $evidenceSha = "1111111111111111111111111111111111111111"
    $evidencePackage = Join-Path $evidenceRoot "canonical-candidate.zip"
    $evidenceReport = Join-Path $evidenceRoot "result.json"
    Write-DDDAPlatformText -Value "canonical candidate fixture" -Path $evidencePackage
    $evidenceHash = Get-DDDAPlatformFileHash -Path $evidencePackage
    Write-DDDAPlatformJson -Path $evidenceReport -Value ([ordered]@{
        schema_version = 1
        status = "PASS"
        source = [ordered]@{ repository = "romanhlavac/ddd-accelerator"; pr = $evidencePr; commit = $evidenceSha }
        package = [ordered]@{ path = "canonical-candidate.zip"; sha256 = $evidenceHash; artifact_name = "ddda-candidate-$evidenceSha"; workflow_run_id = "123456" }
    })

    $isolatedEvidence = Get-DDDACandidateValidationEvidence -Pr $evidencePr -HeadSha $evidenceSha -ValidationReportPath $evidenceReport -PackagePath $evidencePackage
    Assert-True -Condition ($isolatedEvidence.PackageSha256 -eq $evidenceHash) -Message "Isolated evidence resolver neověřil exact candidate hash."

    $mismatchReport = Join-Path $evidenceRoot "mismatch.json"
    Write-DDDAPlatformJson -Path $mismatchReport -Value ([ordered]@{
        schema_version = 1
        status = "PASS"
        source = [ordered]@{ repository = "romanhlavac/ddd-accelerator"; pr = $evidencePr; commit = $evidenceSha }
        package = [ordered]@{ path = "canonical-candidate.zip"; sha256 = (("0" * 64) -join "") }
    })
    $mismatchRejected = $false
    try { $null = Get-DDDACandidateValidationEvidence -Pr $evidencePr -HeadSha $evidenceSha -ValidationReportPath $mismatchReport -PackagePath $evidencePackage } catch { $mismatchRejected = $true }
    Assert-True -Condition $mismatchRejected -Message "Artifact/report hash mismatch nebyl fail-closed."

    $missingRejected = $false
    try { $null = Get-DDDACandidateValidationEvidence -Pr $evidencePr -HeadSha $evidenceSha -ValidationReportPath $evidenceReport -PackagePath (Join-Path $evidenceRoot "missing.zip") } catch { $missingRejected = $true }
    Assert-True -Condition $missingRejected -Message "Chybějící canonical artifact nebyl fail-closed."

    $partialInputRejected = $false
    try { $null = Get-DDDACandidateValidationEvidence -Pr $evidencePr -HeadSha $evidenceSha -ValidationReportPath $evidenceReport } catch { $partialInputRejected = $true }
    Assert-True -Condition $partialInputRejected -Message "Neúplná isolated evidence nebyla fail-closed."
}
finally {
    Remove-Item -LiteralPath $evidenceRoot -Recurse -Force -ErrorAction SilentlyContinue
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-changelog-contract-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
try {
    $tempChangelog = Join-Path $tempRoot "CHANGELOG.md"
    @'
# Changelog

Auth: GH_TOKEN -> GITHUB_TOKEN -> gh auth token -> Git credential helper

## [Unreleased]

Development notes only.

## [1.2.3] - 2026-07-28

### Added

- deterministic release contract.
'@ | Set-Content -LiteralPath $tempChangelog -Encoding UTF8

    $release = Assert-DDDAPlatformChangelogRelease -Path $tempChangelog -Version "1.2.3"
    Assert-True -Condition ($release.Version -eq "1.2.3") -Message "Changelog validator nevrátil release verzi."
    Assert-True -Condition ($release.Date -eq "2026-07-28") -Message "Changelog validator nevrátil release datum."
    Assert-True -Condition ($release.Tag -eq "v1.2.3") -Message "Changelog validator neodvodil tag."

    $mismatchRejected = $false
    try { $null = Assert-DDDAPlatformChangelogRelease -Path $tempChangelog -Version "1.2.4" } catch { $mismatchRejected = $true }
    Assert-True -Condition $mismatchRejected -Message "Changelog validator neodmítl neshodu promotion verze."

    $unreleasedText = Get-Content -LiteralPath $tempChangelog -Raw -Encoding UTF8
    $unreleasedText = $unreleasedText.Replace("Development notes only.", "- unassigned release item.")
    Set-Content -LiteralPath $tempChangelog -Encoding UTF8 -Value $unreleasedText
    $unreleasedRejected = $false
    try { $null = Assert-DDDAPlatformChangelogRelease -Path $tempChangelog -Version "1.2.3" } catch { $unreleasedRejected = $true }
    Assert-True -Condition $unreleasedRejected -Message "Promotion changelog guard neodmítl nepřiřazenou Unreleased položku."

    $invalidDateText = $unreleasedText.Replace("- unassigned release item.", "Development notes only.").Replace("2026-07-28", "2026-02-30")
    Set-Content -LiteralPath $tempChangelog -Encoding UTF8 -Value $invalidDateText
    $invalidDateRejected = $false
    try { $null = Assert-DDDAPlatformChangelogRelease -Path $tempChangelog -Version "1.2.3" } catch { $invalidDateRejected = $true }
    Assert-True -Condition $invalidDateRejected -Message "Changelog validator neodmítl neplatné ISO datum."
}
finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "DDDA merge/promotion guards: PASS"
