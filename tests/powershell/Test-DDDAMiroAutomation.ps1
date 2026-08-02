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

Assert-True -Condition ($projectInitializerText -match '\$script:MiroPython\s+-I\s+-X\s+utf8\s+-m\s+ddda_miro') -Message "Project Miro initializer nevynucuje UTF-8 v izolovaném Python procesu pomocí -X utf8."
Assert-True -Condition ($projectInitializerText -notmatch '@CommandArguments\s+2>&1') -Message "Project Miro initializer nesmí slučovat stderr retry telemetry s JSON stdout."
Assert-True -Condition ($projectInitializerText -match '@CommandArguments\s+2>\s+\$stderrPath') -Message "Project Miro initializer neodděluje stderr do samostatného diagnostického streamu."
Assert-True -Condition ($projectInitializerText -match 'Stdout:`n\{1\}`nStderr:') -Message "Project Miro parse failure nerozlišuje stdout a stderr."
Assert-True -Condition ($projectInitializerText -match '\$stderrRaw\s*=\s*if\s*\(Test-Path') -Message "Project Miro initializer nemá explicitní null-safe mezivýsledek stderr."

$pythonProbeCommand = Resolve-DDDAPythonCommand
$pythonProbeCode = "import json, sys; print(json.dumps(dict(encoding=sys.stdout.encoding, text='Povinn\u00fd d\u016fkaz: k\u00f3dov\u00e1n\u00ed v\u00fdstup\u016f'), ensure_ascii=False))"
$pythonProbeRaw = @(& $pythonProbeCommand -I -X utf8 -c $pythonProbeCode 2>&1)
$pythonProbeExitCode = $LASTEXITCODE
$pythonProbeText = ($pythonProbeRaw | ForEach-Object { $_.ToString() } | Out-String).Trim()
Assert-Equal -Expected 0 -Actual $pythonProbeExitCode -Message "Python UTF-8 stdout probe selhal. Výstup: $pythonProbeText"
$pythonProbe = $pythonProbeText | ConvertFrom-Json
Assert-Equal -Expected "Povinný důkaz: kódování výstupů" -Actual ([string]$pythonProbe.text) -Message "Python UTF-8 stdout probe poškodil český výstup."
Assert-True -Condition (([string]$pythonProbe.encoding).Replace("-", "") -match '^utf8') -Message "Python stdout nepoužívá UTF-8: $($pythonProbe.encoding)"

$retryProbeStderrPath = Join-Path $env:TEMP ("ddda-retry-probe-" + [Guid]::NewGuid().ToString("N") + ".log")
try {
    $retryProbeCode = "import json, sys; print('DDDA Miro retry: status=500', file=sys.stderr); print(json.dumps(dict(status='PASS')))"
    $retryProbeRaw = @(& $pythonProbeCommand -I -X utf8 -c $retryProbeCode 2> $retryProbeStderrPath)
    $retryProbeExitCode = $LASTEXITCODE
    $retryProbeText = ($retryProbeRaw | ForEach-Object { $_.ToString() } | Out-String).Trim()
    $retryProbeStderrRaw = Get-Content -LiteralPath $retryProbeStderrPath -Raw -Encoding UTF8
    $retryProbeStderrText = ""
    if ($null -ne $retryProbeStderrRaw) {
        $retryProbeStderrText = ([string]$retryProbeStderrRaw).Trim()
    }
    Assert-Equal -Expected 0 -Actual $retryProbeExitCode -Message "Retry stream probe selhal."
    Assert-Equal -Expected "PASS" -Actual ([string](($retryProbeText | ConvertFrom-Json).status)) -Message "Retry telemetry kontaminovala JSON stdout."
    Assert-True -Condition ($retryProbeStderrText -match 'DDDA Miro retry: status=500') -Message "Retry telemetry nebyla zachována v stderr."
}
finally {
    Remove-Item -LiteralPath $retryProbeStderrPath -Force -ErrorAction SilentlyContinue
}

$smokeText = Get-Content (Join-Path $PlatformPath "scripts/Invoke-DDDAMiroSmokeTest.ps1") -Raw -Encoding UTF8
Assert-True -Condition ($smokeText -notmatch "romanhlavac/ddd-accelerator") -Message "Smoke runner nesmí být svázán s konkrétním origin remote."
Assert-True -Condition ($smokeText -match 'DDDA:\$\{projectId\}:evt-smoke-policy-issued') -Message "Smoke runner nepoužívá bezpečnou interpolaci markeru."
Assert-True -Condition ($smokeText -notmatch '@CommandArguments\s+2>&1') -Message "Miro CLI adapter nesmí slučovat stderr retry telemetry s JSON stdout."
Assert-True -Condition ($smokeText -match '@CommandArguments\s+2>\s+\$stderrPath') -Message "Miro CLI adapter neodděluje stderr do samostatného diagnostického streamu."
Assert-True -Condition ($smokeText -match 'Stdout:.*Stderr:' -or $smokeText -match 'Stdout:`n\{1\}`nStderr:') -Message "Miro CLI parse failure nerozlišuje stdout a stderr."
Assert-True -Condition ($smokeText -match '\$stderrRaw\s*=\s*if\s*\(Test-Path') -Message "Miro CLI adapter nemá explicitní null-safe mezivýsledek stderr."
Assert-True -Condition ($smokeText -match 'if\s*\(\$null\s+-ne\s+\$rawText\)') -Message "Miro CLI adapter nechrání normalizaci prázdného stdout explicitní null větví."
Assert-True -Condition ($smokeText -match 'if\s*\(\$null\s+-ne\s+\$stderrRaw\)') -Message "Miro CLI adapter nechrání normalizaci prázdného stderr explicitní null větví."
Assert-True -Condition ($smokeText -notmatch '\(Get-Content[^\r\n]+\)\.Trim\(\)') -Message "Miro CLI adapter stále volá Trim přímo nad potenciálně null Get-Content výsledkem."

$emptyStdoutRaw = @() | Out-String
$emptyStdoutText = ""
if ($null -ne $emptyStdoutRaw) {
    $emptyStdoutText = ([string]$emptyStdoutRaw).Trim()
}
Assert-Equal -Expected "" -Actual $emptyStdoutText -Message "Prázdný stdout musí být bezpečně normalizován na prázdný řetězec."

$emptyStderrPath = Join-Path $env:TEMP ("ddda-empty-stderr-" + [Guid]::NewGuid().ToString("N") + ".log")
try {
    [IO.File]::WriteAllBytes($emptyStderrPath, [byte[]]@())
    $emptyStderrRaw = Get-Content -LiteralPath $emptyStderrPath -Raw -Encoding UTF8
    $emptyStderrText = ""
    if ($null -ne $emptyStderrRaw) {
        $emptyStderrText = ([string]$emptyStderrRaw).Trim()
    }
    Assert-Equal -Expected "" -Actual $emptyStderrText -Message "Prázdný stderr musí být bezpečně normalizován na prázdný řetězec."
}
finally {
    Remove-Item -LiteralPath $emptyStderrPath -Force -ErrorAction SilentlyContinue
}


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
Assert-True -Condition ($acceptanceText -match '\[System\.Net\.WebUtility\]::HtmlDecode\(\$content\)') -Message "Remote acceptance nedekóduje Miro HTML entity před kontrolou viditelných source markerů."

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
Assert-True -Condition ($scaffoldText -match '(?m)^\s*-\s+id:\s*control-center\s*$') -Message "Miro scaffold nemá frame 00 – Control Center / Artifact Registry."
Assert-True -Condition ($scaffoldText -match '(?m)^\s*-\s+id:\s*method-overview\s*$') -Message "Miro scaffold nemá samostatný DDD Starter journey overview."
Assert-True -Condition ($scaffoldText -match '(?m)^stage_visual_templates:\s*$') -Message "Miro scaffold nemá situační stage visual templates."
Assert-True -Condition ($scaffoldText -match '(?m)^example_templates:\s*$') -Message "Miro scaffold nemá vyplněné workshop mini-vzory."
Assert-True -Condition ($scaffoldText -match '(?m)^board_guide:\s*$') -Message "Miro scaffold nemá kompaktní first-user onboarding."
Assert-True -Condition ($scaffoldText -match '(?m)^overview_resources:\s*$') -Message "Miro scaffold nemá základní metodické zdroje."
Assert-True -Condition ($scaffoldText -match '(?m)^artifact_status_tables:\s*$') -Message "Miro scaffold nemá kompatibilní Artifact Registry contract."
Assert-True -Condition ($scaffoldText -match '(?m)^zone_transitions:\s*$') -Message "Miro scaffold nemá konektory mezi vyššími metodickými zónami."
Assert-True -Condition ($scaffoldText -match '(?m)^stage_columns:\s*$') -Message "Miro scaffold nemá deterministické stage columns."
Assert-True -Condition ($scaffoldText -match '(?m)^method_transitions:\s*$') -Message "Miro scaffold nemá metodické přechody a feedback loops."
Assert-True -Condition ($scaffoldText -match '00 – Navigace, legenda a stav artefaktů \(Control Center\)') -Message "Viditelný název frame 00 neodpovídá human-review kontraktu."
Assert-True -Condition ($scaffoldText -match '(?m)^schema_version:\s*[''"]?2\.5[''"]?\s*$') -Message "Miro scaffold nepoužívá schema 2.5."
Assert-True -Condition ($scaffoldText -match '(?m)^\s*render_contract_version:\s*REM-PR8-HVA-CC-010\s*$') -Message "Miro scaffold nemá REM-010 render contract."
Assert-True -Condition ($scaffoldText -match '(?m)^\s*minimum_remote_item_count:\s*280\s*$') -Message "Miro scaffold neumí odlišit REM-010 od 262položkového odmítnutého boardu."
Assert-True -Condition ($scaffoldText -match '(?m)^\s*minimum_overview_child_items:\s*61\s*$') -Message "Miro scaffold nevynucuje navigovatelný obsah frame 01."
foreach ($sourceBoardId in @("uXjVH2vcvRI=", "uXjVH27wYU4=")) {
    Assert-True -Condition ($scaffoldText -match [regex]::Escape($sourceBoardId)) -Message "Miro scaffold nemá exact traceability na zdrojový board $sourceBoardId."
}
foreach ($sourceTitle in @("Business model canvas - exercise", "Big Picture organized", "Process Modelling", "Strategic classification", "Context Maps - Examples", "Bounded Context Canvas", "Domain Message Flow Modelling - Example")) {
    Assert-True -Condition ($scaffoldText -match [regex]::Escape($sourceTitle)) -Message "Miro scaffold necituje DDD Starter artefakt '$sourceTitle'."
}
Assert-True -Condition ($scaffoldText -match 'sync_policy:\s*ignore') -Message "Mini-vzory nemají explicitní sync-ignore kontrakt."
Assert-True -Condition ($scaffoldText -match 'VZOR / LEGENDA') -Message "Pracovní frames nemají oddělený VZOR / LEGENDA panel."
Assert-True -Condition (@([regex]::Matches($scaffoldText, '(?m)^\s+canonical_workshop_shell:\s*true\s*$')).Count -eq 15) -Message "Kanonický třízónový shell nepokrývá přesně frames 20–82."
foreach ($heading in @("recipe_cs", "done_criteria_cs", "open_questions_cs", "heuristics_cs", "anti_patterns_cs")) {
    Assert-True -Condition (@([regex]::Matches($scaffoldText, "(?m)^\s+$heading\s*:")).Count -eq 15) -Message "Kanonické frames nemají ve všech 15 případech pole $heading."
}
foreach ($lifecycle in @("SCAFFOLD", "WORKING", "CANDIDATE", "VALIDATED", "ACCEPTED", "SUPERSEDED")) {
    Assert-True -Condition ($scaffoldText -match "(?m)^\s+label_cs:\s*$lifecycle\s*$") -Message "Artifact Lifecycle legenda neobsahuje $lifecycle."
}
foreach ($provenance in @("GENERATED", "WORKSHOP", "IMPORTED", "MANUAL")) {
    Assert-True -Condition ($scaffoldText -match "(?m)^\s+label_cs:\s*$provenance\s*$") -Message "Artifact Provenance legenda neobsahuje $provenance."
}
foreach ($registryField in @("artifact", "type", "stage", "lifecycle", "provenance", "owner", "revision", "last_sync", "detail")) {
    Assert-True -Condition ($scaffoldText -match "(?m)^\s+- id:\s*$registryField\s*$") -Message "Artifact Registry neobsahuje sloupec $registryField."
}
Assert-True -Condition ($scaffoldText -match 'kicking-off-a-major-program-of-work') -Message "Miro scaffold neodkazuje na základní DDD Starter metodiku."
Assert-True -Condition ($scaffoldText -match '(?m)^    journey: 34\s*$') -Message "Journey font nemá čitelnou minimální velikost."
Assert-True -Condition ($scaffoldText -match 'DDDA kuchařka|cookbook_url') -Message "Miro scaffold nemá odkazy na kuchařky."
Assert-True -Condition ($renderText -match 'validate_remote_layout') -Message "Renderer neověřuje skutečnou remote Miro geometrii."
Assert-True -Condition ($renderText -match 'DDDA-RENDER-CONTRACT') -Message "Renderer nevkládá viditelnou verzi render contractu."
Assert-True -Condition ($renderText -match 'DDDA-PLATFORM-SOURCE') -Message "Renderer nevkládá exact candidate provenance."
Assert-True -Condition ($renderText -match 'DDDA-SCAFFOLD-SHA256') -Message "Renderer nevkládá hash renderovaného scaffoldingu."
Assert-True -Condition ($renderText -match 'remote_content_digest') -Message "Renderer neukládá digest skutečně načteného remote obsahu."
Assert-True -Condition ($renderText -match 'remote board has only') -Message "Renderer nemá regresní guard proti 211položkové baseline."
Assert-True -Condition ($renderText -match 'not a navigable child of overview frame') -Message "Renderer nekontroluje parent vazbu obsahu frame 01."
Assert-True -Condition ($renderText -match 'overview_reference_stage') -Message "Renderer nevytváří viditelnou stage-to-source traceability ve frame 01."
foreach ($visibleMarker in @("EDITOVATELNÁ PRACOVNÍ PLOCHA", "RECEPT", "HOTOVO KDYŽ", "OTEVŘENÉ OTÁZKY", "HEURISTIKY", "ANTI-PATTERNS")) {
    Assert-True -Condition ($renderText -match [regex]::Escape($visibleMarker)) -Message "Renderer neověřuje remote viditelný marker '$visibleMarker'."
}
Assert-True -Condition ($renderText -match 'workshop_guide') -Message "Renderer nevytváří top-left workshop guides."
Assert-True -Condition ($renderText -match 'workshop_example') -Message "Renderer nevytváří workshop mini-vzory."
Assert-True -Condition ($renderText -match 'workshop_example_panel') -Message "Renderer nevytváří oddělené example panely."
Assert-True -Condition ($renderText -match 'workshop_workspace_panel') -Message "Renderer nevytváří editovatelnou pracovní plochu třízónového shellu."
Assert-True -Condition ($renderText -match '_upsert_connector') -Message "Renderer nevytváří skutečné Miro connectors."
Assert-True -Condition ($renderText -match 'artifact_registry_table') -Message "Renderer nevytváří synchronizovaný Artifact Registry shape-grid."
Assert-True -Condition ($renderText -match 'project_gate_state_title') -Message "Renderer neodděluje Project/Gate State."
Assert-True -Condition ($renderText -match 'artifact_lifecycle_legend') -Message "Renderer neodděluje Artifact Lifecycle."
Assert-True -Condition ($renderText -match 'artifact_provenance_legend') -Message "Renderer neodděluje Artifact Provenance."
Assert-True -Condition ($renderText -match 'PENDING_HUMAN_REVIEW') -Message "Renderer nesmí převést technical PASS na celkový PASS bez human review."
Assert-True -Condition ($renderText -match 'journey:\{gate_id\}') -Message "Renderer nevytváří persistentní journey položky."
Assert-True -Condition ($renderText -match 'MOJIBAKE_MARKERS') -Message "Renderer nemá UTF-8/mojibake regression guard."
Assert-True -Condition ($renderText -match 'overlaps work frame') -Message "Renderer nemá overlay guard."
Assert-True -Condition ($syncText -match '_validate_required_placements') -Message "Sync nevynucuje control-center placement povinných artefaktů."
Assert-True -Condition ($syncText -match 'sync_policy') -Message "Sync nemá explicitní guard pro sync-ignore example obsah."
Assert-True -Condition ($syncText -match 'exclude_from_ingestion') -Message "Sync nemá explicitní ingestion-exclusion guard."
foreach ($field in @(
    "technical_sync_status",
    "layout_contract_status",
    "remote_layout_status",
    "render_contract_status",
    "render_contract_version",
    "platform_source_commit",
    "scaffold_sha256",
    "remote_item_count",
    "overview_child_count",
    "starter_reference_caption_count",
    "remote_content_digest",
    "review_team_selection_status",
    "utf8_status",
    "human_visual_acceptance_status",
    "overall_status"
)) {
    Assert-True -Condition ($acceptanceText -match [regex]::Escape($field)) -Message "Acceptance report nemá pole $field."
}
Assert-True -Condition ($acceptanceText -match 'Get-DDDAAllMiroItems') -Message "Acceptance runner nečte nezávislý remote board snapshot přes Miro API."
Assert-True -Condition ($acceptanceText -match 'Remote board má pouze \$remoteItemCount položek') -Message "Acceptance runner neumí odmítnout rejected-board baseline."
Assert-True -Condition ($acceptanceText -match 'Frame 01 obsahuje pouze \$overviewChildCount navigovatelných child items') -Message "Acceptance runner neověřuje skutečné child items frame 01."
Assert-True -Condition ($acceptanceText -match 'DDD STARTER SOURCE: uXjVH27wYU4=') -Message "Acceptance runner neověřuje viditelnou vazbu vzorů na DDD Starter board."
Assert-True -Condition ($acceptanceText -match 'DDDA-PLATFORM-SOURCE:\$platformSourceCommit') -Message "Acceptance runner neověřuje vazbu boardu na exact candidate SHA."
Assert-True -Condition ($acceptanceText -match 'overall_status = \$overallStatus') -Message "Acceptance report nemá explicitní overall status."
Assert-True -Condition ($acceptanceText -match 'PENDING_HUMAN_REVIEW') -Message "Acceptance report nerozlišuje pending human review."
$acceptanceCommand = Get-Command $acceptancePath
Assert-True -Condition $acceptanceCommand.Parameters.ContainsKey("MiroTeamId") -Message "Acceptance runner neumí explicitně vybrat standardní Miro team."
Assert-True -Condition ($acceptanceText -match '\$_\s+-cmatch\s+\[regex\]::Escape\(\$heading\)') -Message "Acceptance runner nepočítá kanonické guide nadpisy case-sensitive."

$canonicalHeadingProbe = @()
$canonicalHeadingProbe += @(1..15 | ForEach-Object { "<strong>OTEVŘENÉ OTÁZKY</strong>" })
$canonicalHeadingProbe += @(1..15 | ForEach-Object { "Rozlišuj fakta, hypotézy, rozhodnutí a otevřené otázky." })
$caseInsensitiveHeadingCount = @($canonicalHeadingProbe | Where-Object { $_ -match [regex]::Escape("OTEVŘENÉ OTÁZKY") }).Count
$caseSensitiveHeadingCount = @($canonicalHeadingProbe | Where-Object { $_ -cmatch [regex]::Escape("OTEVŘENÉ OTÁZKY") }).Count
Assert-True -Condition ($caseInsensitiveHeadingCount -gt 15) -Message "Regresní fixture neprokazuje původní case-insensitive přepočítání workspace textů."
Assert-Equal -Expected 15 -Actual $caseSensitiveHeadingCount -Message "Case-sensitive canonical heading count musí ignorovat lowercase workspace texty."

Write-Host "DDDA Miro automation tests: PASS"
