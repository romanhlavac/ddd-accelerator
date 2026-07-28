Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-DDDAMiroEvidencePropertyValue {
    param(
        [object]$InputObject,
        [Parameter(Mandatory = $true)][string]$Name,
        [object]$DefaultValue = $null
    )

    if ($null -eq $InputObject) {
        return $DefaultValue
    }
    if ($InputObject -is [System.Collections.IDictionary]) {
        if ($InputObject.Contains($Name)) {
            return $InputObject[$Name]
        }
        return $DefaultValue
    }
    $property = $InputObject.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $DefaultValue
    }
    return $property.Value
}

function New-DDDANotRunMiroEvidence {
    param(
        [string]$Workspace,
        [string[]]$Diagnostics = @()
    )

    return [pscustomobject][ordered]@{
        status = "NOT_RUN"
        board_id = $null
        board_url = $null
        workspace = if ([string]::IsNullOrWhiteSpace($Workspace)) { $null } else { [System.IO.Path]::GetFullPath($Workspace) }
        managed_artifacts = [string[]]@()
        mapping = [pscustomobject][ordered]@{
            status = "NOT_RUN"
            path = $null
            verified_count = 0
        }
        sync_state = [pscustomobject][ordered]@{
            status = "NOT_RUN"
            path = $null
            verified_count = 0
        }
        idempotence = [pscustomobject][ordered]@{
            status = "NOT_RUN"
            verification = $null
            board_id_stable = $null
            item_count_before = $null
            item_count_after = $null
            second_run_create_board_operations = $null
            second_run_mutating_operations = $null
        }
        cleanup = [pscustomobject][ordered]@{
            state = "not_created"
            attempted_at = $null
            completed_at = $null
            error = $null
            reason = "miro_not_requested"
        }
        diagnostics = [string[]]@($Diagnostics)
    }
}

function New-DDDALegacyMiroEvidence {
    param(
        [Parameter(Mandatory = $true)][string]$BoardId,
        [string]$Workspace
    )

    return [pscustomobject][ordered]@{
        status = "PASS"
        board_id = $BoardId
        board_url = "https://miro.com/app/board/$BoardId/"
        workspace = if ([string]::IsNullOrWhiteSpace($Workspace)) { $null } else { [System.IO.Path]::GetFullPath($Workspace) }
        managed_artifacts = [string[]]@()
        mapping = [pscustomobject][ordered]@{
            status = "NOT_RUN"
            path = $null
            verified_count = 0
        }
        sync_state = [pscustomobject][ordered]@{
            status = "NOT_RUN"
            path = $null
            verified_count = 0
        }
        idempotence = [pscustomobject][ordered]@{
            status = "NOT_RUN"
            verification = "legacy_board_id_only"
            board_id_stable = $null
            item_count_before = $null
            item_count_after = $null
            second_run_create_board_operations = $null
            second_run_mutating_operations = $null
        }
        cleanup = [pscustomobject][ordered]@{
            state = "preserved"
            attempted_at = $null
            completed_at = $null
            error = $null
            reason = "legacy_board_id_only"
        }
        diagnostics = [string[]]@("Compatibility evidence contains board identity only.")
    }
}

function Assert-DDDAMiroEvidenceContract {
    param([Parameter(Mandatory = $true)][object]$Evidence)

    foreach ($required in @(
        "status",
        "board_id",
        "board_url",
        "workspace",
        "managed_artifacts",
        "mapping",
        "sync_state",
        "idempotence",
        "cleanup",
        "diagnostics"
    )) {
        $property = $Evidence.PSObject.Properties[$required]
        $dictionaryHasValue = ($Evidence -is [System.Collections.IDictionary]) -and $Evidence.Contains($required)
        if ($null -eq $property -and -not $dictionaryHasValue) {
            throw "Miro evidence neobsahuje povinné pole '$required'."
        }
    }

    $status = [string](Get-DDDAMiroEvidencePropertyValue -InputObject $Evidence -Name "status")
    if ($status -notin @("PASS", "FAIL", "NOT_RUN")) {
        throw "Miro evidence má nepodporovaný status '$status'."
    }

    $cleanup = Get-DDDAMiroEvidencePropertyValue -InputObject $Evidence -Name "cleanup"
    $cleanupState = [string](Get-DDDAMiroEvidencePropertyValue -InputObject $cleanup -Name "state")
    if ($cleanupState -notin @("preserved", "deleted", "cleanup_failed", "not_created")) {
        throw "Miro evidence má nepodporovaný cleanup state '$cleanupState'."
    }

    $boardId = [string](Get-DDDAMiroEvidencePropertyValue -InputObject $Evidence -Name "board_id")
    if ($cleanupState -in @("preserved", "deleted") -and [string]::IsNullOrWhiteSpace($boardId)) {
        throw "Cleanup state '$cleanupState' vyžaduje zachované board_id."
    }

    $cleanupError = [string](Get-DDDAMiroEvidencePropertyValue -InputObject $cleanup -Name "error")
    if ($cleanupState -eq "cleanup_failed" -and [string]::IsNullOrWhiteSpace($cleanupError)) {
        throw "cleanup_failed vyžaduje auditní error bez secretu."
    }

    $idempotence = Get-DDDAMiroEvidencePropertyValue -InputObject $Evidence -Name "idempotence"
    $idempotenceStatus = [string](Get-DDDAMiroEvidencePropertyValue -InputObject $idempotence -Name "status")
    if ($idempotenceStatus -eq "PASS") {
        if (-not [bool](Get-DDDAMiroEvidencePropertyValue -InputObject $idempotence -Name "board_id_stable" -DefaultValue $false)) {
            throw "PASS idempotence vyžaduje board_id_stable=true."
        }
        foreach ($field in @("second_run_create_board_operations", "second_run_mutating_operations")) {
            if ([int](Get-DDDAMiroEvidencePropertyValue -InputObject $idempotence -Name $field -DefaultValue -1) -ne 0) {
                throw "PASS idempotence vyžaduje $field=0."
            }
        }
    }

    $json = $Evidence | ConvertTo-Json -Depth 30 -Compress
    if ($json -match '(?i)"[^"]*(token|secret|authorization|credential|password)[^"]*"\s*:') {
        throw "Miro evidence obsahuje zakázaný secret-like název pole."
    }
    if ($json -match '(?i)Bearer\s+[A-Za-z0-9._~+/=-]{8,}|MIRO_ACCESS_TOKEN\s*=|gh[pousr]_[A-Za-z0-9]{16,}') {
        throw "Miro evidence obsahuje pravděpodobný secret."
    }

    return $Evidence
}

function Import-DDDAMiroEvidence {
    param([Parameter(Mandatory = $true)][string]$Path)

    $fullPath = (Resolve-Path -LiteralPath $Path).Path
    $root = Get-Content -LiteralPath $fullPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $miroProperty = $root.PSObject.Properties["miro"]
    $evidence = if ($null -eq $miroProperty) { $root } else { $miroProperty.Value }
    $null = Assert-DDDAMiroEvidenceContract -Evidence $evidence
    return $evidence
}
