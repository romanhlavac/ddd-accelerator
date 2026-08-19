[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PlatformPath "scripts/platform/DDDAMergeStrategySupport.ps1")

function Assert-Equal {
    param([AllowNull()]$Actual, [AllowNull()]$Expected, [Parameter(Mandatory = $true)][string]$Message)
    if ([string]$Actual -ne [string]$Expected) {
        throw "$Message Expected '$Expected', actual '$Actual'."
    }
}
function Assert-True {
    param([bool]$Condition, [Parameter(Mandatory = $true)][string]$Message)
    if (-not $Condition) { throw $Message }
}
function Assert-Throws {
    param([Parameter(Mandatory = $true)][scriptblock]$Action, [Parameter(Mandatory = $true)][string]$Message)
    $thrown = $false
    try { & $Action } catch { $thrown = $true }
    if (-not $thrown) { throw $Message }
}

$policy = Get-Content -LiteralPath (Join-Path $PlatformPath "config/platform/development-policy.yaml") -Raw -Encoding UTF8 | ConvertFrom-Json
$baseSha = "1111111111111111111111111111111111111111"
$highBody = @'
Implements #999
<!-- ddda:change-classification:v1 -->
```json
{"schema_version":1,"impact":"HIGH"}
```
'@
$lowBody = @'
Implements #998
<!-- ddda:change-classification:v1 -->
```json
{"schema_version":1,"impact":"LOW"}
```
'@

Assert-Equal (Get-DDDAChangeImpactFromPrBody -Body $highBody) "HIGH" "Impact marker parsing failed."
Assert-Equal (Get-DDDAChangeImpactFromPrBody -Body "Implements #1") "UNKNOWN" "Missing classification must be UNKNOWN."

$highDefault = Resolve-DDDAMergeStrategy -Policy $policy -Impact "HIGH" -Pr 999 -BaseSha $baseSha -PrBody $highBody
Assert-Equal $highDefault.merge_method "merge" "HIGH must default to merge commit."
Assert-Throws -Action {
    Resolve-DDDAMergeStrategy -Policy $policy -Impact "HIGH" -RequestedMethod "squash" -Pr 999 -BaseSha $baseSha -PrBody $highBody | Out-Null
} -Message "HIGH squash must fail closed."
Assert-Throws -Action {
    Resolve-DDDAMergeStrategy -Policy $policy -Impact "BREAKING" -RequestedMethod "squash" -Pr 999 -BaseSha $baseSha -PrBody $highBody | Out-Null
} -Message "BREAKING squash must fail closed."
Assert-Throws -Action {
    Resolve-DDDAMergeStrategy -Policy $policy -Impact "UNKNOWN" -RequestedMethod "squash" -Pr 999 -BaseSha $baseSha -PrBody "" | Out-Null
} -Message "UNKNOWN impact squash must fail closed."

$lowDefault = Resolve-DDDAMergeStrategy -Policy $policy -Impact "LOW" -Pr 998 -BaseSha $baseSha -PrBody $lowBody
Assert-Equal $lowDefault.merge_method "merge" "LOW must default to merge commit."
$lowSquash = Resolve-DDDAMergeStrategy -Policy $policy -Impact "LOW" -RequestedMethod "squash" -Pr 998 -BaseSha $baseSha -PrBody $lowBody
Assert-True $lowSquash.human_squash_exception_required "LOW squash must require human exception."

$transition = $policy.merge_strategy.bootstrap_transition
$bootstrapBody = @'
Implements #70
<!-- ddda:change-classification:v1 -->
```json
{"schema_version":1,"impact":"HIGH"}
```
'@
$bootstrap = Resolve-DDDAMergeStrategy `
    -Policy $policy `
    -Impact "HIGH" `
    -RequestedMethod "squash" `
    -Pr 82 `
    -BaseSha ([string]$transition.legacy_base_sha) `
    -PrBody $bootstrapBody
Assert-True $bootstrap.bootstrap_transition "#70 prospective bootstrap must bind to Change Request relation even when implementation PR number differs."
Assert-Throws -Action {
    Resolve-DDDAMergeStrategy -Policy $policy -Impact "HIGH" -RequestedMethod "squash" -Pr 82 -BaseSha ("f" * 40) -PrBody $bootstrapBody | Out-Null
} -Message "#70 bootstrap must not apply on another base SHA."
$wrongRelationBody = @'
Implements #71
<!-- ddda:change-classification:v1 -->
```json
{"schema_version":1,"impact":"HIGH"}
```
'@
Assert-Throws -Action {
    Resolve-DDDAMergeStrategy -Policy $policy -Impact "HIGH" -RequestedMethod "squash" -Pr 70 -BaseSha ([string]$transition.legacy_base_sha) -PrBody $wrongRelationBody | Out-Null
} -Message "Matching PR number must not substitute for the authoritative Implements/Closes #70 relation."
$duplicateRelationBody = @'
Implements #70
Closes #70
<!-- ddda:change-classification:v1 -->
```json
{"schema_version":1,"impact":"HIGH"}
```
'@
Assert-Throws -Action {
    Resolve-DDDAMergeStrategy -Policy $policy -Impact "HIGH" -RequestedMethod "squash" -Pr 82 -BaseSha ([string]$transition.legacy_base_sha) -PrBody $duplicateRelationBody | Out-Null
} -Message "Bootstrap requires exactly one authoritative #70 relation."

$exceptionComment = [pscustomobject]@{
    body = @'
<!-- ddda:squash-exception:v1 -->
```json
{"schema_version":1,"kind":"squash_exception","repository":"romanhlavac/ddd-accelerator","pr":998,"validated_source_head_sha":"2222222222222222222222222222222222222222","candidate_package_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","impact":"LOW","reason":"Explicit history-cleanliness exception for a low-risk change.","reviewer":"romanhlavac","approved_at":"2026-08-20T00:00:00Z"}
```
'@
}
$record = ConvertFrom-DDDASquashExceptionComment -Comment $exceptionComment
Assert-DDDASquashExceptionRecord `
    -Record $record `
    -CommentAuthor "romanhlavac" `
    -CommentAuthorType "User" `
    -Repository "romanhlavac/ddd-accelerator" `
    -Pr 998 `
    -HeadSha "2222222222222222222222222222222222222222" `
    -CandidatePackageSha256 "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" `
    -Impact "LOW"
Assert-Throws -Action {
    Assert-DDDASquashExceptionRecord -Record $record -CommentAuthor "automation[bot]" -CommentAuthorType "Bot" -Repository "romanhlavac/ddd-accelerator" -Pr 998 -HeadSha "2222222222222222222222222222222222222222" -CandidatePackageSha256 "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" -Impact "LOW"
} -Message "Bot must not authorize squash exception."

Write-Host "DDDA merge strategy contract: PASS"
