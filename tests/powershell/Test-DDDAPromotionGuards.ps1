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
$policyPath = Join-Path $platformRoot "config/platform/development-policy.yaml"

foreach ($path in @($entryPath, $promotionPath, $policyPath)) {
    Assert-True -Condition (Test-Path -LiteralPath $path -PathType Leaf) -Message "Chybí promotion kontrakt: $path"
}

$entry = Get-Content -LiteralPath $entryPath -Raw -Encoding UTF8
$promotion = Get-Content -LiteralPath $promotionPath -Raw -Encoding UTF8
$policy = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8 | ConvertFrom-Json

Assert-True -Condition ($entry -match 'ValidateSet\("doctor",\s*"test",\s*"validate-pr",\s*"promote-pr"\)') -Message "Root CLI nepublikuje promote-pr."
Assert-True -Condition ($entry -match '\[switch\]\$ConfirmMerge') -Message "Root CLI nemá explicitní ConfirmMerge."
Assert-True -Condition ($entry -match '\[switch\]\$DryRun') -Message "Root CLI nemá promotion DryRun."
Assert-True -Condition ([bool]$policy.require_explicit_confirmation) -Message "Development policy nevyžaduje explicitní confirmation."
Assert-True -Condition ($policy.merge_method -in @("squash", "merge", "rebase")) -Message "Development policy má nepodporovaný merge method."
Assert-True -Condition (@($policy.required_documents).Count -ge 3) -Message "Development policy nemá povinné governance dokumenty."

$dryRunIndex = $promotion.IndexOf('if ($DryRun)', [System.StringComparison]::Ordinal)
$confirmationIndex = $promotion.IndexOf('if ([bool]$policy.require_explicit_confirmation -and -not $ConfirmMerge)', [System.StringComparison]::Ordinal)
$mergeIndex = $promotion.IndexOf('$mergeArguments = @("pr", "merge"', [System.StringComparison]::Ordinal)

Assert-True -Condition ($dryRunIndex -ge 0) -Message "Promotion nemá fail-safe DryRun větev."
Assert-True -Condition ($confirmationIndex -ge 0) -Message "Promotion nemá explicitní confirmation guard."
Assert-True -Condition ($mergeIndex -ge 0) -Message "Promotion neobsahuje kontrolovaný merge příkaz."
Assert-True -Condition ($dryRunIndex -lt $mergeIndex) -Message "DryRun guard musí předcházet sestavení merge příkazu."
Assert-True -Condition ($confirmationIndex -lt $mergeIndex) -Message "Confirmation guard musí předcházet sestavení merge příkazu."
Assert-True -Condition ($promotion -match '--match-head-commit') -Message "Promotion nechrání merge exact head SHA."
Assert-True -Condition ($promotion -match 'validation-reports/pr-\$Pr-\$headSha') -Message "Promotion nehledá validation report podle PR a exact SHA."
Assert-True -Condition ($promotion -match 'actualCandidateHash') -Message "Promotion neověřuje candidate package hash."
Assert-True -Condition ($promotion -match 'if \(-not \$releasePassed\)') -Message "Promotion nemá release validation gate před tagem."

Write-Host "DDDA promotion guards: PASS"
