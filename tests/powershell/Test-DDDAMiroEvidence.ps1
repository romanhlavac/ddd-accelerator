[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PlatformPath "scripts/platform/DDDAMiroEvidenceSupport.ps1")

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

function Assert-True {
    param(
        [bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

$dddaCommand = Get-Command (Join-Path $PlatformPath "ddda.ps1")
Assert-True -Condition $dddaCommand.Parameters.ContainsKey("KeepReviewBoard") -Message "ddda.ps1 nemá KeepReviewBoard."

$platformTestCommand = Get-Command (Join-Path $PlatformPath "scripts/platform/Invoke-DDDAPlatformTest.ps1")
foreach ($parameterName in @("KeepReviewBoard", "MiroTeamId", "MiroEvidenceOutputPath")) {
    Assert-True -Condition $platformTestCommand.Parameters.ContainsKey($parameterName) -Message "Platform test runner nemá parametr $parameterName."
}

foreach ($commandPath in @(
    (Join-Path $PlatformPath "scripts/platform/Invoke-DDDAValidatePr.ps1"),
    (Join-Path $PlatformPath "scripts/platform/Invoke-DDDAPromotePr.ps1")
)) {
    $command = Get-Command $commandPath
    Assert-True -Condition $command.Parameters.ContainsKey("KeepReviewBoard") -Message "Command $commandPath nemá KeepReviewBoard."
}

$wrapperCommand = Get-Command (Join-Path $PlatformPath "scripts/platform/Invoke-DDDAMiroAcceptanceEvidence.ps1")
foreach ($parameterName in @("KeepReviewBoard", "MiroTeamId", "EvidenceOutputPath", "CleanupOnFailure")) {
    Assert-True -Condition $wrapperCommand.Parameters.ContainsKey($parameterName) -Message "Miro evidence wrapper nemá parametr $parameterName."
}

$partialFailureOutput = @(
    "DDDA Miro runtime provenance: PASS",
    "DDDA_MIRO_BOARD_ID_HANDOFF:uXjV-PartialFailure=",
    "DDDA Miro error: synthetic failure after board creation"
)
$partialHandoff = Get-DDDAMiroBoardIdentityHandoff -ChildOutput $partialFailureOutput
Assert-Equal -Expected "uXjV-PartialFailure=" -Actual $partialHandoff.board_id -Message "Failure-path handoff nezachoval board ID."
Assert-Equal -Expected "https://miro.com/app/board/uXjV-PartialFailure=/" -Actual $partialHandoff.board_url -Message "Failure-path handoff nevytvořil board URL."

$conflictingHandoffRejected = $false
try {
    $null = Get-DDDAMiroBoardIdentityHandoff -ChildOutput @(
        "DDDA_MIRO_BOARD_ID_HANDOFF:uXjV-One=",
        "DDDA_MIRO_BOARD_ID_HANDOFF:uXjV-Two="
    )
}
catch {
    $conflictingHandoffRejected = $true
}
Assert-True -Condition $conflictingHandoffRejected -Message "Conflicting board identity handoff musí fail-closed."

$tempRoot = Join-Path $env:TEMP ("ddda-miro-evidence-test-" + [Guid]::NewGuid().ToString("N"))
try {
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    $packagePath = Join-Path $tempRoot "candidate.zip"
    $suitesPath = Join-Path $tempRoot "suites.json"
    $evidencePath = Join-Path $tempRoot "acceptance.json"
    $outputRoot = Join-Path $tempRoot "report"

    Set-Content -LiteralPath $packagePath -Value "synthetic package" -Encoding UTF8
    @(
        [pscustomobject]@{
            name = "miro"
            status = "PASS"
            duration_ms = 1
            details = "synthetic"
        }
    ) | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $suitesPath -Encoding UTF8

    $syntheticEvidence = [pscustomobject][ordered]@{
        status = "PASS"
        board_id = "uXjV-Audit="
        board_url = "https://miro.com/app/board/uXjV-Audit=/"
        workspace = $tempRoot
        managed_artifacts = [string[]]@(
            "ddda.current-status",
            "ddda.next-actions",
            "sample.project-charter"
        )
        mapping = [pscustomobject][ordered]@{
            status = "PASS"
            path = (Join-Path $tempRoot "miro-map.yaml")
            verified_count = 3
        }
        sync_state = [pscustomobject][ordered]@{
            status = "PASS"
            path = (Join-Path $tempRoot "sync-state.yaml")
            verified_count = 3
        }
        idempotence = [pscustomobject][ordered]@{
            status = "PASS"
            verification = "synthetic invariant"
            board_id_stable = $true
            item_count_before = 10
            item_count_after = 10
            second_run_create_board_operations = 0
            second_run_mutating_operations = 0
        }
        cleanup = [pscustomobject][ordered]@{
            state = "deleted"
            attempted_at = "2026-07-28T08:00:00Z"
            completed_at = "2026-07-28T08:00:01Z"
            error = $null
            reason = "successful_run_cleanup"
        }
        diagnostics = [string[]]@((Join-Path $tempRoot "acceptance-result.json"))
    }
    $null = Assert-DDDAMiroEvidenceContract -Evidence $syntheticEvidence
    [pscustomobject][ordered]@{ miro = $syntheticEvidence } |
        ConvertTo-Json -Depth 30 |
        Set-Content -LiteralPath $evidencePath -Encoding UTF8

    & (Join-Path $PlatformPath "scripts/platform/New-DDDAValidationReport.ps1") `
        -ValidationId "miro-evidence-test" `
        -Status PASS `
        -SourceKind working-tree `
        -Repository "synthetic/repository" `
        -Commit ("a" * 40) `
        -Branch "test" `
        -PackagePath $packagePath `
        -Workspace $tempRoot `
        -MiroEvidencePath $evidencePath `
        -SuitesJsonPath $suitesPath `
        -OutputRoot $outputRoot | Out-Null

    $report = Get-Content -LiteralPath (Join-Path $outputRoot "result.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-Equal -Expected "uXjV-Audit=" -Actual $report.miro.board_id -Message "Validation report nezachoval board ID po DELETE."
    Assert-Equal -Expected "deleted" -Actual $report.miro.cleanup.state -Message "Validation report nezachoval cleanup state."
    Assert-Equal -Expected 3 -Actual @($report.miro.managed_artifacts).Count -Message "Validation report nezachoval managed artifacts."
    Assert-Equal -Expected 0 -Actual $report.miro.idempotence.second_run_mutating_operations -Message "Validation report nezachoval idempotence evidence."
    Assert-Equal -Expected "uXjV-Audit=" -Actual $report.miro_board_id -Message "Compatibility alias miro_board_id se liší."

    $unsafeEvidence = New-DDDANotRunMiroEvidence
    $unsafeEvidence | Add-Member -NotePropertyName access_token -NotePropertyValue "Bearer example-secret-value"
    $secretRejected = $false
    try {
        $null = Assert-DDDAMiroEvidenceContract -Evidence $unsafeEvidence
    }
    catch {
        $secretRejected = $true
    }
    Assert-True -Condition $secretRejected -Message "Miro evidence contract neodmítl secret-like pole."

    foreach ($state in @("preserved", "deleted", "cleanup_failed", "not_created")) {
        $schemaText = Get-Content -LiteralPath (Join-Path $PlatformPath "schemas/miro-acceptance-report.schema.json") -Raw -Encoding UTF8
        Assert-True -Condition ($schemaText -match [regex]::Escape('"' + $state + '"')) -Message "Schema neobsahuje cleanup state $state."
    }
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}

Write-Host "DDDA Miro evidence tests: PASS"
