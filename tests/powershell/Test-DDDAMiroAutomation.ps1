[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PlatformPath "scripts/private/DDDAMiroSupport.ps1")

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

$frame = [pscustomobject]@{ data = [pscustomobject]@{ title = "Discover" } }
$frameData = Get-DDDAObjectPropertyValue -InputObject $frame -Name "data"
Assert-Equal -Expected "" -Actual (Get-DDDAObjectPropertyValue -InputObject $frameData -Name "content" -DefaultValue "") -Message "Chybějící data.content musí být bezpečné."
Assert-Equal -Expected "Discover" -Actual (Get-DDDAObjectPropertyValue -InputObject $frameData -Name "title" -DefaultValue "") -Message "Frame title nebyl načten."

$projectId = "miro-smoke-1234"
$marker = "DDDA:${projectId}:evt-test"
Assert-Equal -Expected "DDDA:miro-smoke-1234:evt-test" -Actual $marker -Message "PowerShell marker interpolace je chybná."

$encoded = ConvertTo-DDDAJsonUtf8Bytes -Body @{ data = @{ content = "Pojistná smlouva byla vydána" } }
$decoded = [System.Text.Encoding]::UTF8.GetString($encoded.Bytes)
Assert-True -Condition ($decoded -match "Pojistná smlouva byla vydána") -Message "JSON request body není UTF-8."
Assert-True -Condition ($encoded.Json -eq $decoded) -Message "JSON text a UTF-8 bytes se liší."

$encodedBoardId = [Uri]::EscapeDataString("uXjVH4yfs6Y=")
Assert-True -Condition ($encodedBoardId.EndsWith("%3D")) -Message "Board ID není bezpečně URL encoded."

$platformFull = [System.IO.Path]::GetFullPath($PlatformPath).TrimEnd('\', '/')
$secretFull = [System.IO.Path]::GetFullPath((Get-DDDAMiroSecretPath))
Assert-True -Condition (-not $secretFull.StartsWith($platformFull, [System.StringComparison]::OrdinalIgnoreCase)) -Message "Secret store nesmí být uvnitř platformního Git rootu."

$tempRoot = Join-Path $env:TEMP ("ddda-automation-test-" + [Guid]::NewGuid().ToString("N"))
try {
    New-Item -ItemType Directory -Path (Join-Path $tempRoot "projects/sample/miro") -Force | Out-Null
    Set-Content -Path (Join-Path $tempRoot "workspace.yaml") -Encoding UTF8 -Value @(
        "workspace:",
        "  id: test",
        "projects:",
        "  - id: sample",
        "    path: projects/sample",
        "    repository: null",
        "    status: active"
    )
    Set-Content -Path (Join-Path $tempRoot "projects/sample/miro/miro-map.yaml") -Encoding UTF8 -Value @(
        "project_id: sample",
        "board_id: 'board-1'",
        "items:",
        "  item-1:",
        "    miro_item_id: 'item-1'",
        "frames:",
        "  frame-1:",
        "    miro_item_id: 'frame-1'"
    )

    $projectPath = Get-DDDAWorkspaceProjectPath -WorkspaceRoot $tempRoot -ProjectId "sample"
    Assert-Equal -Expected ([System.IO.Path]::GetFullPath((Join-Path $tempRoot "projects/sample"))) -Actual $projectPath -Message "Projekt nebyl nalezen ve workspace registru."

    $snapshot = Get-DDDAMiroMapSnapshot -ProjectPath $projectPath
    Assert-Equal -Expected "board-1" -Actual $snapshot.BoardId -Message "Board ID nebylo načteno z mappingu."
    Assert-Equal -Expected 2 -Actual @($snapshot.ItemIds).Count -Message "Miro item ID nebyla načtena z mappingu."
}
finally {
    if (Test-Path $tempRoot) {
        Remove-Item $tempRoot -Recurse -Force
    }
}

$smokeCommand = Get-Command (Join-Path $PlatformPath "scripts/Invoke-DDDAMiroSmokeTest.ps1")
foreach ($parameterName in @("ResetToken", "KeepArtifacts", "CleanupOnFailure", "Full", "NonInteractive")) {
    Assert-True -Condition $smokeCommand.Parameters.ContainsKey($parameterName) -Message "Smoke runner nemá parametr $parameterName."
}

$projectCommand = Get-Command (Join-Path $PlatformPath "scripts/Initialize-DDDAProjectMiro.ps1")
foreach ($parameterName in @("WorkspaceRoot", "ProjectId", "CreateBoard", "DryRun", "ResetToken")) {
    Assert-True -Condition $projectCommand.Parameters.ContainsKey($parameterName) -Message "Project Miro initializer nemá parametr $parameterName."
}

$smokeText = Get-Content (Join-Path $PlatformPath "scripts/Invoke-DDDAMiroSmokeTest.ps1") -Raw -Encoding UTF8
Assert-True -Condition ($smokeText -notmatch "romanhlavac/ddd-accelerator") -Message "Smoke runner nesmí být svázán s konkrétním origin remote."
Assert-True -Condition ($smokeText -match 'DDDA:\$\{projectId\}:evt-smoke-policy-issued') -Message "Smoke runner nepoužívá bezpečnou interpolaci markeru."

Write-Host "DDDA Miro automation tests: PASS"
