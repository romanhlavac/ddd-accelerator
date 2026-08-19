Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:DDDAChangeClassificationMarker = "<!-- ddda:change-classification:v1 -->"
$script:DDDASquashExceptionMarker = "<!-- ddda:squash-exception:v1 -->"

function Get-DDDAMarkedJsonRecord {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Marker,
        [Parameter(Mandatory = $true)][string]$Label,
        [switch]$AllowMissing
    )

    $escapedMarker = [regex]::Escape($Marker)
    $pattern = '(?s)' + $escapedMarker + '\s*```json\s*(?<json>\{.*?\})\s*```'
    $matches = [regex]::Matches($Text, $pattern, [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
    if ($matches.Count -eq 0) {
        if ($AllowMissing) { return $null }
        throw "$Label marker chybí."
    }
    if ($matches.Count -ne 1) {
        throw "$Label musí být právě jeden. Nalezeno: $($matches.Count)."
    }

    try {
        return $matches[0].Groups["json"].Value | ConvertFrom-Json
    }
    catch {
        throw "$Label JSON nelze parse: $($_.Exception.Message)"
    }
}

function Get-DDDAChangeImpactFromPrBody {
    param([AllowEmptyString()][string]$Body = "")

    $record = Get-DDDAMarkedJsonRecord `
        -Text $Body `
        -Marker $script:DDDAChangeClassificationMarker `
        -Label "Change classification" `
        -AllowMissing
    if ($null -eq $record) {
        return "UNKNOWN"
    }
    if ([int]$record.schema_version -ne 1) {
        throw "Change classification má nepodporovaný schema_version."
    }
    $impact = ([string]$record.impact).ToUpperInvariant()
    if ($impact -notin @("LOW", "MEDIUM", "HIGH", "BREAKING")) {
        throw "Change classification impact '$impact' není podporovaný."
    }
    return $impact
}

function Test-DDDABootstrapMergeTransition {
    param(
        [Parameter(Mandatory = $true)][object]$MergeStrategy,
        [Parameter(Mandatory = $true)][int]$Pr,
        [Parameter(Mandatory = $true)][string]$BaseSha,
        [AllowEmptyString()][string]$PrBody = "",
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$MergeMethod
    )

    $property = $MergeStrategy.PSObject.Properties["bootstrap_transition"]
    if ($null -eq $property -or $null -eq $property.Value) {
        return $false
    }
    $transition = $property.Value
    if (-not [bool]$transition.prospective_after_integration) { return $false }
    if ($Pr -ne [int]$transition.change_issue) { return $false }
    if ($BaseSha -ne [string]$transition.legacy_base_sha) { return $false }
    if ($MergeMethod -ne [string]$transition.legacy_merge_method) { return $false }
    if ($Impact -notin @("HIGH", "BREAKING")) { return $false }
    $issue = [int]$transition.change_issue
    if ($PrBody -notmatch "(?im)\b(?:Implements|Closes)\s+#$issue\b") { return $false }
    return $true
}

function Resolve-DDDAMergeStrategy {
    param(
        [Parameter(Mandatory = $true)][object]$Policy,
        [Parameter(Mandatory = $true)][string]$Impact,
        [AllowEmptyString()][string]$RequestedMethod = "",
        [Parameter(Mandatory = $true)][int]$Pr,
        [Parameter(Mandatory = $true)][string]$BaseSha,
        [AllowEmptyString()][string]$PrBody = ""
    )

    $mergeStrategyProperty = $Policy.PSObject.Properties["merge_strategy"]
    if ($null -eq $mergeStrategyProperty -or $null -eq $mergeStrategyProperty.Value) {
        throw "Platform development policy neobsahuje merge_strategy contract."
    }
    $strategy = $mergeStrategyProperty.Value
    if ([int]$strategy.schema_version -ne 1) {
        throw "Nepodporovaný merge_strategy schema_version."
    }

    $impactValue = $Impact.ToUpperInvariant()
    $method = if ([string]::IsNullOrWhiteSpace($RequestedMethod)) {
        [string]$strategy.default_method
    }
    else {
        $RequestedMethod.ToLowerInvariant()
    }
    if ($method -notin @("merge", "squash")) {
        throw "Canonical DDDA merge method '$method' není podporovaný. Rebase není povolen, protože nezachovává exact validated PR HEAD identity."
    }

    if ($impactValue -eq "UNKNOWN") {
        $allowed = @($strategy.unknown_impact_allowed_methods | ForEach-Object { ([string]$_).ToLowerInvariant() })
        if ($method -notin $allowed) {
            throw "PR bez autoritativní impact classification smí použít pouze: $($allowed -join ', ')."
        }
        return [pscustomobject][ordered]@{
            impact = $impactValue
            merge_method = $method
            human_squash_exception_required = $false
            bootstrap_transition = $false
        }
    }

    $impactProperty = $strategy.impacts.PSObject.Properties[$impactValue]
    if ($null -eq $impactProperty) {
        throw "Merge strategy neobsahuje pravidlo pro impact '$impactValue'."
    }
    $rule = $impactProperty.Value
    $allowedMethods = @($rule.allowed_methods | ForEach-Object { ([string]$_).ToLowerInvariant() })
    if ($method -notin $allowedMethods) {
        $bootstrap = Test-DDDABootstrapMergeTransition `
            -MergeStrategy $strategy `
            -Pr $Pr `
            -BaseSha $BaseSha `
            -PrBody $PrBody `
            -Impact $impactValue `
            -MergeMethod $method
        if (-not $bootstrap) {
            throw "Merge method '$method' není povolen pro impact '$impactValue'. Povolené: $($allowedMethods -join ', ')."
        }
        return [pscustomobject][ordered]@{
            impact = $impactValue
            merge_method = $method
            human_squash_exception_required = $false
            bootstrap_transition = $true
        }
    }

    $requiresException = (
        $method -eq "squash" -and
        [bool]$rule.squash_requires_human_exception
    )
    return [pscustomobject][ordered]@{
        impact = $impactValue
        merge_method = $method
        human_squash_exception_required = $requiresException
        bootstrap_transition = $false
    }
}

function ConvertFrom-DDDASquashExceptionComment {
    param([Parameter(Mandatory = $true)][object]$Comment)

    return Get-DDDAMarkedJsonRecord `
        -Text ([string]$Comment.body) `
        -Marker $script:DDDASquashExceptionMarker `
        -Label "Squash exception"
}

function Assert-DDDASquashExceptionRecord {
    param(
        [Parameter(Mandatory = $true)][object]$Record,
        [Parameter(Mandatory = $true)][string]$CommentAuthor,
        [Parameter(Mandatory = $true)][string]$CommentAuthorType,
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][int]$Pr,
        [Parameter(Mandatory = $true)][string]$HeadSha,
        [Parameter(Mandatory = $true)][string]$CandidatePackageSha256,
        [Parameter(Mandatory = $true)][string]$Impact
    )

    if ([string]::IsNullOrWhiteSpace($CommentAuthor) -or $CommentAuthorType -eq "Bot" -or $CommentAuthor -match '\[bot\]$') {
        throw "Squash exception musí mít lidskou GitHub provenance."
    }
    if ([int]$Record.schema_version -ne 1 -or [string]$Record.kind -ne "squash_exception") {
        throw "Squash exception má nepodporovaný contract."
    }
    if ([string]$Record.repository -ne $Repository -or [int]$Record.pr -ne $Pr) {
        throw "Squash exception repository/PR identity neodpovídá aktuálnímu PR."
    }
    if ([string]$Record.validated_source_head_sha -ne $HeadSha) {
        throw "Squash exception validated_source_head_sha neodpovídá current PR head."
    }
    if ([string]$Record.candidate_package_sha256 -ne $CandidatePackageSha256) {
        throw "Squash exception candidate package hash neodpovídá validate-pr evidence."
    }
    if (([string]$Record.impact).ToUpperInvariant() -ne $Impact.ToUpperInvariant()) {
        throw "Squash exception impact neodpovídá PR classification."
    }
    if ([string]$Record.reviewer -ne $CommentAuthor) {
        throw "Squash exception reviewer neodpovídá human comment authorovi."
    }
    if ([string]::IsNullOrWhiteSpace([string]$Record.reason)) {
        throw "Squash exception vyžaduje neprázdný reason."
    }
    if ([string]::IsNullOrWhiteSpace([string]$Record.approved_at)) {
        throw "Squash exception vyžaduje approved_at."
    }
    $approvedAt = [DateTimeOffset]::MinValue
    if (-not [DateTimeOffset]::TryParse([string]$Record.approved_at, [ref]$approvedAt)) {
        throw "Squash exception approved_at není platný timestamp."
    }
}
