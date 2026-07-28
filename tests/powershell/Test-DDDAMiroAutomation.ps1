[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PlatformPath "scripts/private/DDDAMiroSupport.ps1")
. (Join-Path $PlatformPath "scripts/private/DDDAGitStatus.ps1")

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

Assert-Equal -Expected "miro/miro-map.yaml" -Actual (Get-DDDAGitPorcelainPath -Line " M miro/miro-map.yaml") -Message "Standardní Git porcelain řádek nebyl rozpoznán."
Assert-Equal -Expected "miro/miro-map.yaml" -Actual (Get-DDDAGitPorcelainPath -Line "M miro/miro-map.yaml") -Message "Trimovaný první Git porcelain řádek nebyl rozpoznán."
Assert-Equal -Expected "miro/new-map.yaml" -Actual (Get-DDDAGitPorcelainPath -Line "R  miro/old-map.yaml -> miro/new-map.yaml") -Message "Git rename porcelain řádek nebyl rozpoznán."

$allowedEntries = @(Assert-DDDAGitChangesWithinPath -PorcelainText "M miro/miro-map.yaml`n?? miro/report.yaml" -AllowedPrefix "miro/" -Label "Test")
Assert-Equal -Expected 2 -Actual $allowedEntries.Count -Message "Povolené Miro změny nebyly správně rozpoznány."

$controlledEntries = @(Assert-DDDAGitChangesWithinPath -PorcelainText "M miro/miro-map.yaml`n?? reports/miro-sync/sync-test.yaml" -AllowedPrefix @("miro/", "reports/miro-sync/") -Label "Test")
Assert-Equal -Expected 2 -Actual $controlledEntries.Count -Message "Více povolených Miro sync cest nebylo správně rozpoznáno."

$outsideRejected = $false
try {
    $null = Assert-DDDAGitChangesWithinPath -PorcelainText "M project.yaml" -AllowedPrefix @("miro/", "reports/miro-sync/") -Label "Test"
}
catch {
    $outsideRejected = $true
}
Assert-True -Condition $outsideRejected -Message "Změna mimo řízené Miro cesty musí být v resume režimu odmítnuta."

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
foreach ($parameterName in @("WorkspaceRoot", "ProjectId", "CreateBoard", "DryRun", "ResetToken", "Resume")) {
    Assert-True -Condition $projectCommand.Parameters.ContainsKey($parameterName) -Message "Project Miro initializer nemá parametr $parameterName."
}

$projectInitializerText = Get-Content (Join-Path $PlatformPath "scripts/Initialize-DDDAProjectMiro.ps1") -Raw -Encoding UTF8
Assert-True -Condition ($projectInitializerText -match '"sync",\s*"--direction",\s*"push"') -Message "Project Miro initializer neprovádí počáteční managed artifact push."
Assert-True -Condition ($projectInitializerText -match 'reports/miro-sync/') -Message "Project Miro initializer nepovoluje auditní sync reporty."

$smokeText = Get-Content (Join-Path $PlatformPath "scripts/Invoke-DDDAMiroSmokeTest.ps1") -Raw -Encoding UTF8
Assert-True -Condition ($smokeText -notmatch "romanhlavac/ddd-accelerator") -Message "Smoke runner nesmí být svázán s konkrétním origin remote."
Assert-True -Condition ($smokeText -match 'DDDA:\$\{projectId\}:evt-smoke-policy-issued') -Message "Smoke runner nepoužívá bezpečnou interpolaci markeru."


$scaffoldPath = Join-Path $PlatformPath "scaffolds/miro/strategic-ddd-method-board.yaml"
$renderPath = Join-Path $PlatformPath "runtime/miro/ddda_miro/render.py"
$syncPath = Join-Path $PlatformPath "runtime/miro/ddda_miro/sync.py"
$acceptancePath = Join-Path $PlatformPath "scripts/Test-DDDAAcceptance.ps1"
foreach ($path in @($scaffoldPath, $renderPath, $syncPath, $acceptancePath)) {
    Assert-True -Condition (Test-Path -LiteralPath $path -PathType Leaf) -Message "Chybí Miro layout contract soubor: $path"
}
$scaffoldText = Get-Content -LiteralPath $scaffoldPath -Raw -Encoding UTF8
$renderText = Get-Content -LiteralPath $renderPath -Raw -Encoding UTF8
$syncText = Get-Content -LiteralPath $syncPath -Raw -Encoding UTF8
$acceptanceText = Get-Content -LiteralPath $acceptancePath -Raw -Encoding UTF8

foreach ($gate in 1..8) {
    Assert-True -Condition ($scaffoldText -match "(?m)^\s+gate:\s*G$gate\s*$") -Message "Traceability nepokrývá G$gate."
    Assert-True -Condition ($scaffoldText -match "(?m)^\s*-\s+id:\s*G$gate\s*$") -Message "Journey/gate contract neobsahuje G$gate."
}
foreach ($statusId in @("not_ready", "ready_for_review", "conditional", "rejected", "passed")) {
    Assert-True -Condition ($scaffoldText -match "(?m)^\s*-\s+id:\s*$statusId\s*$") -Message "Miro scaffold neobsahuje gate state $statusId."
}
foreach ($artifactId in @("project-charter", "ddda.current-status", "ddda.next-actions")) {
    Assert-True -Condition ($scaffoldText -match "(?m)^  $([regex]::Escape($artifactId)):\s*$") -Message "Miro scaffold nemá placement pro $artifactId."
}
Assert-True -Condition ($scaffoldText -match '(?m)^\s*-\s+id:\s*control-center\s*$') -Message "Miro scaffold nemá frame 00 – Navigace, legenda a stav artefaktů."
Assert-True -Condition ($scaffoldText -match '(?m)^\s*-\s+id:\s*method-overview\s*$') -Message "Miro scaffold nemá samostatný DDD Starter journey overview."
Assert-True -Condition ($scaffoldText -match '(?m)^stage_visual_templates:\s*$') -Message "Miro scaffold nemá situační stage visual templates."
Assert-True -Condition ($scaffoldText -match '(?m)^example_templates:\s*$') -Message "Miro scaffold nemá vyplněné workshop mini-vzory."
Assert-True -Condition ($scaffoldText -match '(?m)^method_transitions:\s*$') -Message "Miro scaffold nemá metodické přechody a feedback loops."
Assert-True -Condition ($scaffoldText -match '(?m)^    journey: 34\s*$') -Message "Journey font nemá čitelnou minimální velikost."
Assert-True -Condition ($scaffoldText -match 'DDDA kuchařka|cookbook_url') -Message "Miro scaffold nemá odkazy na kuchařky."
Assert-True -Condition ($renderText -match 'validate_remote_layout') -Message "Renderer neověřuje skutečnou remote Miro geometrii."
Assert-True -Condition ($renderText -match 'workshop_guide') -Message "Renderer nevytváří top-left workshop guides."
Assert-True -Condition ($renderText -match 'workshop_example') -Message "Renderer nevytváří workshop mini-vzory."
Assert-True -Condition ($renderText -match 'PENDING_HUMAN_REVIEW') -Message "Renderer nesmí převést technical PASS na celkový PASS bez human review."
Assert-True -Condition ($renderText -match 'journey:\{gate_id\}') -Message "Renderer nevytváří persistentní journey položky."
Assert-True -Condition ($renderText -match 'MOJIBAKE_MARKERS') -Message "Renderer nemá UTF-8/mojibake regression guard."
Assert-True -Condition ($renderText -match 'overlaps work frame') -Message "Renderer nemá overlay guard."
Assert-True -Condition ($syncText -match '_validate_required_placements') -Message "Sync nevynucuje control-center placement povinných artefaktů."
foreach ($field in @("technical_sync_status", "layout_contract_status", "remote_layout_status", "review_team_selection_status", "utf8_status", "human_visual_acceptance_status", "overall_status")) {
    Assert-True -Condition ($acceptanceText -match [regex]::Escape($field)) -Message "Acceptance report nemá pole $field."
}
Assert-True -Condition ($acceptanceText -match 'overall_status = \$overallStatus') -Message "Acceptance report nemá explicitní overall status."
Assert-True -Condition ($acceptanceText -match 'PENDING_HUMAN_REVIEW') -Message "Acceptance report nerozlišuje pending human review."
$acceptanceCommand = Get-Command $acceptancePath
Assert-True -Condition $acceptanceCommand.Parameters.ContainsKey("MiroTeamId") -Message "Acceptance runner neumí explicitně vybrat standardní Miro team."

Write-Host "DDDA Miro automation tests: PASS"
