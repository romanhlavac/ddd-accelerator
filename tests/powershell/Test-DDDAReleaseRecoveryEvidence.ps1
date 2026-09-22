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
Assert-True -Condition ($content -match 'Join-Path \$platformRoot "scripts/platform/New-DDDAValidationReport.ps1"' -and $content -notmatch 'Join-Path \$sourceRoot "scripts/platform/New-DDDAValidationReport.ps1"') -Message "Portable recovery report musí generovat trusted current control-plane reporter, nikoli historický frozen reporter."
Assert-True -Condition ($content -match "PSObject\.Properties\['workflow_run_id'\]" -and $content -match 'WorkflowRunId = \$workflowRunId' -and $content -notmatch '\$report\.package\.workflow_run_id') -Message "Recovery rebuild musí tolerovat legacy candidate report bez optional package.workflow_run_id i pod StrictMode."
Assert-True -Condition ($content -notmatch 'Publish-DDDA|Invoke-RestMethod|gh api|git".*push|--delete') -Message "Recovery evidence rebuild nesmí mít GitHub/tag side effect."

$workflowPath = Join-Path $PlatformPath ".github/workflows/controlled-release-recovery.yml"
Assert-True -Condition (Test-Path -LiteralPath $workflowPath -PathType Leaf) -Message "Chybí controlled release recovery workflow."
$workflow = Get-Content -LiteralPath $workflowPath -Raw -Encoding UTF8
Assert-True -Condition ($workflow -match 'issue_comment:' -and $workflow -match '/ddda recover-controlled ' -and $workflow -match "author_association == 'OWNER'") -Message "Recovery workflow musí být explicitně human-comment triggered s owner provenance."
Assert-True -Condition ($workflow -match 'Invoke-DDDARebuildReleaseEvidence.ps1' -and $workflow -match 'Invoke-DDDARecoverGitHubRelease.ps1' -and $workflow -match '-ConfirmRecovery') -Message "Recovery workflow musí rebuildnout exact evidence před canonical recovery publication."
Assert-True -Condition ($workflow -match 'Assert-DDDACanonicalReleaseTagReadBack' -and $workflow -match 'Fresh post-recovery read-back') -Message "Recovery workflow musí před i po publikaci ověřit immutable annotated tag a server state."
Assert-True -Condition ($workflow -notmatch 'git\s+tag|git\s+push|--delete') -Message "Recovery workflow nesmí vytvářet, přepisovat ani mazat tag."
Write-Host "DDDA release recovery evidence rebuild: PASS"
