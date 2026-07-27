[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-True {
    param([bool]$Condition, [Parameter(Mandatory = $true)][string]$Message)
    if (-not $Condition) { throw $Message }
}

$platformRoot = [System.IO.Path]::GetFullPath($PlatformPath).TrimEnd('\', '/')
$entryPath = Join-Path $platformRoot "ddda.ps1"
$promotionPath = Join-Path $platformRoot "scripts/platform/Invoke-DDDAPromotePr.ps1"
$githubSupportPath = Join-Path $platformRoot "scripts/platform/DDDAGitHubSupport.ps1"
$policyPath = Join-Path $platformRoot "config/platform/development-policy.yaml"
$acceptancePath = Join-Path $platformRoot "scripts/Test-DDDAAcceptance.ps1"
$gateCommandPath = Join-Path $platformRoot "scripts/Complete-DDDALifecycleStep.ps1"
$enginePath = Join-Path $platformRoot "runtime/steering/ddda_steering/engine.py"
$gateSchemaPath = Join-Path $platformRoot "schemas/gate-status.schema.json"

foreach ($path in @($entryPath, $promotionPath, $githubSupportPath, $policyPath, $acceptancePath, $gateCommandPath, $enginePath, $gateSchemaPath)) {
    Assert-True -Condition (Test-Path -LiteralPath $path -PathType Leaf) -Message "Chybí promotion nebo gate kontrakt: $path"
}

$entry = Get-Content -LiteralPath $entryPath -Raw -Encoding UTF8
$promotion = Get-Content -LiteralPath $promotionPath -Raw -Encoding UTF8
$githubSupport = Get-Content -LiteralPath $githubSupportPath -Raw -Encoding UTF8
$policy = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8 | ConvertFrom-Json
$acceptance = Get-Content -LiteralPath $acceptancePath -Raw -Encoding UTF8
$gateCommand = Get-Content -LiteralPath $gateCommandPath -Raw -Encoding UTF8
$engine = Get-Content -LiteralPath $enginePath -Raw -Encoding UTF8
$gateSchema = Get-Content -LiteralPath $gateSchemaPath -Raw -Encoding UTF8

Assert-True -Condition ($entry -match 'ValidateSet\("doctor",\s*"test",\s*"validate-pr",\s*"promote-pr"\)') -Message "Root CLI nepublikuje promote-pr."
Assert-True -Condition ($entry -match '\[switch\]\$ConfirmMerge') -Message "Root CLI nemá explicitní ConfirmMerge."
Assert-True -Condition ($entry -match '\[switch\]\$DryRun') -Message "Root CLI nemá promotion DryRun."
Assert-True -Condition ([bool]$policy.require_explicit_confirmation) -Message "Development policy nevyžaduje explicitní confirmation."
Assert-True -Condition ($policy.merge_method -in @("squash", "merge", "rebase")) -Message "Development policy má nepodporovaný merge method."
Assert-True -Condition (@($policy.required_documents).Count -ge 3) -Message "Development policy nemá povinné governance dokumenty."

$dryRunMatch = [regex]::Match($promotion, 'if\s*\(\$DryRun\)', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
$confirmationMatch = [regex]::Match($promotion, 'if\s*\(\[bool\]\$policy\.require_explicit_confirmation\s*-and\s*-not\s*\$ConfirmMerge\)', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
$mergeMatch = [regex]::Match($promotion, 'Merge-DDDAGitHubPullRequest', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
$releaseGateMatch = [regex]::Match($promotion, 'if\s*\(\s*-not\s+\$releasePassed(?:\s*-or\s*-not\s+\$releaseReportCreated)?\s*\)', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
$tagCreationMatch = [regex]::Match($promotion, 'Invoke-DDDAPlatformGit[^\r\n]+@\("tag"', [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)

$dryRunIndex = if ($dryRunMatch.Success) { $dryRunMatch.Index } else { -1 }
$confirmationIndex = if ($confirmationMatch.Success) { $confirmationMatch.Index } else { -1 }
$mergeIndex = if ($mergeMatch.Success) { $mergeMatch.Index } else { -1 }
$releaseGateIndex = if ($releaseGateMatch.Success) { $releaseGateMatch.Index } else { -1 }
$tagCreationIndex = if ($tagCreationMatch.Success) { $tagCreationMatch.Index } else { -1 }

Assert-True -Condition ($dryRunIndex -ge 0) -Message "Promotion nemá fail-safe DryRun větev."
Assert-True -Condition ($confirmationIndex -ge 0) -Message "Promotion nemá explicitní confirmation guard."
Assert-True -Condition ($mergeIndex -ge 0) -Message "Promotion neobsahuje kontrolovaný GitHub API merge."
Assert-True -Condition ($dryRunIndex -lt $mergeIndex) -Message "DryRun guard musí předcházet merge operaci."
Assert-True -Condition ($confirmationIndex -lt $mergeIndex) -Message "Confirmation guard musí předcházet merge operaci."
Assert-True -Condition ($promotion -match '-HeadSha\s+\$headSha') -Message "Promotion nechrání merge exact head SHA."
Assert-True -Condition ($promotion -match 'validation-reports/pr-\$Pr-\$headSha') -Message "Promotion nehledá validation report podle PR a exact SHA."
Assert-True -Condition ($promotion -match 'actualCandidateHash') -Message "Promotion neověřuje candidate package hash."
Assert-True -Condition ($promotion -notmatch 'Get-Command\s+"gh"[^\r\n]+throw') -Message "Promotion nesmí tvrdě vyžadovat instalovaný GitHub CLI."
Assert-True -Condition ($githubSupport -match 'git credential fill') -Message "GitHub support nepoužívá existující Git credential helper jako fallback."
Assert-True -Condition ($githubSupport -match 'GH_TOKEN') -Message "GitHub support nepodporuje GH_TOKEN."
Assert-True -Condition ($githubSupport -match 'GITHUB_TOKEN') -Message "GitHub support nepodporuje GITHUB_TOKEN."
Assert-True -Condition ($githubSupport -match 'Invoke-RestMethod') -Message "GitHub support neobsahuje REST API klienta."
Assert-True -Condition ($releaseGateIndex -ge 0) -Message "Promotion nemá release validation gate před tagem."
Assert-True -Condition ($tagCreationIndex -ge 0) -Message "Promotion neobsahuje kontrolované vytvoření release tagu."
Assert-True -Condition ($releaseGateIndex -lt $tagCreationIndex) -Message "Release validation gate musí předcházet vytvoření tagu."

# Issue #13: promotion may trust acceptance PASS only if acceptance proves that automation did not create a human decision.
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

. $githubSupportPath
$credential = ConvertFrom-DDDAGitCredential -Text "protocol=https`nhost=github.com`nusername=test-user`npassword=test-token`n"
Assert-True -Condition ($credential.Username -eq "test-user") -Message "Git credential parser nevrátil username."
Assert-True -Condition ($credential.Password -eq "test-token") -Message "Git credential parser nevrátil token."

Write-Host "DDDA promotion guards: PASS"
