[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$WorkspaceRoot,
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$CreateBoard,
    [switch]$DryRun,
    [switch]$ResetToken,
    [switch]$ForceRecreateRuntime,
    [switch]$NonInteractive,
    [switch]$Resume,
    [switch]$SuppressCommitInstructions
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {
}

. (Join-Path $PSScriptRoot "private/DDDAMiroSupport.ps1")
. (Join-Path $PSScriptRoot "private/DDDAGitStatus.ps1")

function Invoke-ProjectMiroCli {
    param([Parameter(Mandatory = $true)][string[]]$CommandArguments)

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $raw = @(& $script:MiroPython -I -X utf8 -m ddda_miro --project $script:ProjectRoot --platform $script:PlatformRoot @CommandArguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    $text = ($raw | ForEach-Object { $_.ToString() } | Out-String).Trim()

    if ($exitCode -ne 0) {
        throw ("DDDA Miro CLI selhalo: {0}`nExit code: {1}`n{2}" -f ($CommandArguments -join " "), $exitCode, $text)
    }

    try {
        return ($text | ConvertFrom-Json)
    }
    catch {
        throw ("DDDA Miro CLI nevrátilo platný JSON.`nPříkaz: {0}`nVýstup:`n{1}" -f ($CommandArguments -join " "), $text)
    }
}

function Assert-NoMiroConflicts {
    param(
        [Parameter(Mandatory = $true)]$Result,
        [Parameter(Mandatory = $true)][string]$Label
    )

    $conflictCount = [int](Get-DDDAObjectPropertyValue -InputObject $Result -Name "conflict_count" -DefaultValue 0)
    if ($conflictCount -ne 0) {
        $conflicts = Get-DDDAObjectPropertyValue -InputObject $Result -Name "conflicts" -DefaultValue @()
        throw ("{0} skončil konflikty ({1}):`n{2}" -f $Label, $conflictCount, (@($conflicts) -join "`n"))
    }
}

$originalTokenExists = Test-Path Env:\MIRO_ACCESS_TOKEN
$originalToken = $null
if ($originalTokenExists) {
    $originalToken = $env:MIRO_ACCESS_TOKEN
}

$script:PlatformRoot = (Resolve-Path $PlatformPath).Path
$script:ProjectRoot = Get-DDDAWorkspaceProjectPath -WorkspaceRoot $WorkspaceRoot -ProjectId $ProjectId
$script:MiroPython = $null

try {
    $platformGitRoot = Invoke-DDDAGit -RepositoryPath $script:PlatformRoot -Arguments @("rev-parse", "--show-toplevel")
    if ([System.IO.Path]::GetFullPath($platformGitRoot).TrimEnd('\', '/') -ne [System.IO.Path]::GetFullPath($script:PlatformRoot).TrimEnd('\', '/')) {
        throw "PlatformPath není Git root DDDA: $($script:PlatformRoot)"
    }

    $projectGitRoot = Invoke-DDDAGit -RepositoryPath $script:ProjectRoot -Arguments @("rev-parse", "--show-toplevel")
    if ([System.IO.Path]::GetFullPath($projectGitRoot).TrimEnd('\', '/') -ne [System.IO.Path]::GetFullPath($script:ProjectRoot).TrimEnd('\', '/')) {
        throw "Projekt není samostatný Git root: $($script:ProjectRoot)"
    }

    Assert-DDDACleanGitRepository -RepositoryPath $script:PlatformRoot -Label "Platformní"

    $controlledMiroPrefixes = @("miro/", "reports/miro-sync/")
    $initialProjectChanges = Invoke-DDDAGit -RepositoryPath $script:ProjectRoot -Arguments @("status", "--porcelain")
    if ($Resume) {
        $null = Assert-DDDAGitChangesWithinPath -PorcelainText $initialProjectChanges -AllowedPrefix $controlledMiroPrefixes -Label "Projektový repozitář v resume režimu"
        if (-not [string]::IsNullOrWhiteSpace($initialProjectChanges)) {
            Write-Host "Resume: používají se existující necommitnuté změny omezené na miro/ a reports/miro-sync/."
        }
    }
    else {
        Assert-DDDACleanGitRepository -RepositoryPath $script:ProjectRoot -Label "Projektový"
    }

    $accessToken = Get-DDDAMiroAccessToken -ResetToken:$ResetToken -NonInteractive:$NonInteractive
    $env:MIRO_ACCESS_TOKEN = $accessToken
    $null = Assert-DDDAMiroTokenScopes -AccessToken $accessToken

    $pythonCommand = Resolve-DDDAPythonCommand
    $installArguments = @("-PlatformPath", $script:PlatformRoot, "-PythonCommand", $pythonCommand)
    if ($ForceRecreateRuntime) {
        $installArguments += "-ForceRecreate"
    }
    Invoke-DDDAChildPowerShell -ScriptPath (Join-Path $script:PlatformRoot "scripts/Install-DDDAMiroRuntime.ps1") -Arguments $installArguments

    $script:MiroPython = Join-Path $script:PlatformRoot ".ddda/runtime/miro-venv/Scripts/python.exe"
    if (-not (Test-Path $script:MiroPython)) {
        throw "DDDA Miro runtime nebyl vytvořen: $($script:MiroPython)"
    }

    $packageManifestPath = Join-Path $script:PlatformRoot "ddda-package.json"
    if (Test-Path -LiteralPath $packageManifestPath -PathType Leaf) {
        $packageManifest = Get-Content -LiteralPath $packageManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $sourceCommit = [string]$packageManifest.source_commit
        $renderPath = Join-Path $script:PlatformRoot "runtime/miro/ddda_miro/render.py"
        $renderText = Get-Content -LiteralPath $renderPath -Raw -Encoding UTF8
        if ($renderText -notmatch 'RENDER_CONTRACT_VERSION\s*=\s*"(?<version>[^"]+)"') {
            throw "Candidate package renderer neobsahuje RENDER_CONTRACT_VERSION."
        }
        $expectedContract = [string]$Matches["version"]
        $scaffoldPath = Join-Path $script:PlatformRoot "scaffolds/miro/strategic-ddd-method-board.yaml"
        $scaffoldHash = (Get-FileHash -LiteralPath $scaffoldPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $provenanceEvidencePath = Join-Path $script:ProjectRoot "reports/miro-sync/runtime-provenance.json"
        $provenanceText = & (Join-Path $script:PlatformRoot "scripts/platform/Assert-DDDAMiroRuntimeProvenance.ps1") `
            -PlatformPath $script:PlatformRoot `
            -ExpectedRenderContractVersion $expectedContract `
            -ExpectedSourceCommit $sourceCommit `
            -ExpectedScaffoldSha256 $scaffoldHash `
            -EvidencePath $provenanceEvidencePath `
            -Json | Out-String
        if ($LASTEXITCODE -ne 0) {
            throw "Miro runtime provenance guard selhal před prvním vzdáleným zápisem."
        }
        $provenance = $provenanceText.Trim() | ConvertFrom-Json
        if ([string]$provenance.status -ne "PASS" -or -not [bool]$provenance.checked_before_remote_write) {
            throw "Miro runtime provenance guard nevrátil PASS."
        }
    }

    Write-Host "=== Projektový Miro preflight ==="
    Write-Host "Workspace: $([System.IO.Path]::GetFullPath($WorkspaceRoot))"
    Write-Host "Projekt:   $($script:ProjectRoot)"

    $doctor = Invoke-ProjectMiroCli -CommandArguments @("doctor")
    if (-not (Get-DDDAObjectPropertyValue -InputObject $doctor -Name "scaffold_exists" -DefaultValue $false)) {
        throw "Projektový Miro scaffold nebyl nalezen."
    }

    $renderArguments = @("render")
    if ($CreateBoard) {
        $renderArguments += "--create-board"
    }

    Write-Host ""
    Write-Host "=== Povinný scaffold dry-run ==="
    $preview = Invoke-ProjectMiroCli -CommandArguments ($renderArguments + "--dry-run")
    $preview | ConvertTo-Json -Depth 20 | Write-Host

    if ($DryRun) {
        Assert-DDDACleanGitRepository -RepositoryPath $script:PlatformRoot -Label "Platformní"
        if ($Resume) {
            $dryRunProjectChanges = Invoke-DDDAGit -RepositoryPath $script:ProjectRoot -Arguments @("status", "--porcelain")
            $null = Assert-DDDAGitChangesWithinPath -PorcelainText $dryRunProjectChanges -AllowedPrefix $controlledMiroPrefixes -Label "Projektový repozitář po resume dry-run"
        }
        else {
            Assert-DDDACleanGitRepository -RepositoryPath $script:ProjectRoot -Label "Projektový"
        }
        Write-Host ""
        Write-Host "DDDA projektový Miro scaffold dry-run: PASS"
        Write-Host "Poznámka: managed artifact push vyžaduje existující board a probíhá až bez -DryRun."
        return
    }

    Write-Host ""
    Write-Host "=== Render cílového boardu ==="
    $firstRender = Invoke-ProjectMiroCli -CommandArguments $renderArguments
    foreach ($contract in @{ layout_contract_status = "PASS"; remote_layout_status = "PASS"; utf8_status = "PASS"; overall_status = "PENDING_HUMAN_REVIEW" }.GetEnumerator()) {
        $actual = [string](Get-DDDAObjectPropertyValue -InputObject $firstRender -Name $contract.Key)
        if ($actual -ne [string]$contract.Value) {
            throw "Miro render contract '$($contract.Key)' očekával '$($contract.Value)', získal '$actual'."
        }
    }
    $boardId = [string](Get-DDDAObjectPropertyValue -InputObject $firstRender -Name "board_id")
    if ([string]::IsNullOrWhiteSpace($boardId)) {
        throw "Renderer nevrátil board_id."
    }

    $onlineDoctor = Invoke-ProjectMiroCli -CommandArguments @("doctor", "--online")
    if (-not (Get-DDDAObjectPropertyValue -InputObject $onlineDoctor -Name "board")) {
        throw "Online doctor nevrátil board."
    }

    Write-Host ""
    Write-Host "=== Managed artifact push dry-run ==="
    $syncPreview = Invoke-ProjectMiroCli -CommandArguments @("sync", "--direction", "push", "--dry-run")
    Assert-NoMiroConflicts -Result $syncPreview -Label "Managed artifact push dry-run"
    $syncPreview | ConvertTo-Json -Depth 20 | Write-Host

    Write-Host ""
    Write-Host "=== Managed artifact push ==="
    $firstSync = Invoke-ProjectMiroCli -CommandArguments @("sync", "--direction", "push")
    Assert-NoMiroConflicts -Result $firstSync -Label "Managed artifact push"
    foreach ($contract in @{ technical_sync_status = "PASS"; layout_contract_status = "PASS"; remote_layout_status = "PASS"; utf8_status = "PASS"; overall_status = "PENDING_HUMAN_REVIEW" }.GetEnumerator()) {
        $actual = [string](Get-DDDAObjectPropertyValue -InputObject $firstSync -Name $contract.Key)
        if ($actual -ne [string]$contract.Value) {
            throw "Miro sync contract '$($contract.Key)' očekával '$($contract.Value)', získal '$actual'."
        }
    }

    $firstSnapshot = Get-DDDAMiroMapSnapshot -ProjectPath $script:ProjectRoot
    if ($firstSnapshot.BoardId -ne $boardId) {
        throw "Board ID v miro-map.yaml neodpovídá rendereru. Renderer: $boardId; mapping: $($firstSnapshot.BoardId)"
    }
    if (@($firstSnapshot.ItemIds).Count -eq 0) {
        throw "miro-map.yaml neobsahuje žádné Miro item ID."
    }

    Write-Host ""
    Write-Host "=== Idempotentní kontrolní render ==="
    $secondRender = Invoke-ProjectMiroCli -CommandArguments @("render")
    $secondBoardId = [string](Get-DDDAObjectPropertyValue -InputObject $secondRender -Name "board_id")
    if ($secondBoardId -ne $boardId) {
        throw "Kontrolní render změnil board ID. Původní: $boardId; nové: $secondBoardId"
    }

    $createBoardOperations = @(
        (Get-DDDAObjectPropertyValue -InputObject $secondRender -Name "operations" -DefaultValue @()) |
            Where-Object { (Get-DDDAObjectPropertyValue -InputObject $_ -Name "action") -eq "create_board" }
    ).Count
    if ($createBoardOperations -ne 0) {
        throw "Kontrolní render se pokusil vytvořit další board."
    }

    Write-Host ""
    Write-Host "=== Idempotentní managed artifact push dry-run ==="
    $secondSync = Invoke-ProjectMiroCli -CommandArguments @("sync", "--direction", "push", "--dry-run")
    Assert-NoMiroConflicts -Result $secondSync -Label "Idempotentní managed artifact push"
    $mutatingOperations = @(
        (Get-DDDAObjectPropertyValue -InputObject $secondSync -Name "operations" -DefaultValue @()) |
            Where-Object {
                (Get-DDDAObjectPropertyValue -InputObject $_ -Name "action") -in @("push_create_miro", "push_update_miro")
            }
    ).Count
    if ($mutatingOperations -ne 0) {
        throw "Kontrolní managed artifact push není idempotentní; plánuje $mutatingOperations create/update operací."
    }

    $secondSnapshot = Get-DDDAMiroMapSnapshot -ProjectPath $script:ProjectRoot
    $mappingDifference = Compare-Object -ReferenceObject @($firstSnapshot.ItemIds) -DifferenceObject @($secondSnapshot.ItemIds)
    if ($mappingDifference) {
        throw "Kontrolní render nebo sync změnil množinu Miro item ID; hrozí duplikace."
    }

    Assert-DDDACleanGitRepository -RepositoryPath $script:PlatformRoot -Label "Platformní"

    $projectChanges = Invoke-DDDAGit -RepositoryPath $script:ProjectRoot -Arguments @("status", "--porcelain")
    $projectEntries = @(ConvertFrom-DDDAGitPorcelain -PorcelainText $projectChanges)
    $unexpectedChanges = @(
        $projectEntries |
            Where-Object {
                -not $_.Path.StartsWith("miro/", [System.StringComparison]::OrdinalIgnoreCase) -and
                -not $_.Path.StartsWith("reports/miro-sync/", [System.StringComparison]::OrdinalIgnoreCase)
            }
    )
    if ($unexpectedChanges.Count -gt 0) {
        throw "Inicializace změnila neočekávané projektové soubory:`n$($unexpectedChanges.Line -join "`n")"
    }

    Write-Host ""
    Write-Host "DDDA projektový Miro technical validation: PASS"
    Write-Host "Layout contract: PASS"
    Write-Host "UTF-8: PASS"
    Write-Host "Human visual acceptance: PENDING"
    Write-Host "Overall: PENDING_HUMAN_REVIEW"
    Write-Host "Board ID: $boardId"
    Write-Host "Board URL: https://miro.com/app/board/$boardId/"
    Write-Host ""
    Write-Host "Projektové změny k review:"
    if ([string]::IsNullOrWhiteSpace($projectChanges)) {
        Write-Host "  žádné"
    }
    else {
        Write-Host $projectChanges
        Write-Host ""
        if ($SuppressCommitInstructions) {
            Write-Host "Projektové změny jsou diagnostický výstup acceptance běhu."
            Write-Host "Necommituj je, dokud nadřazený acceptance report není technicky PASS."
        }
        else {
            Write-Host "Zkontroluj diff a commitni Miro mapping, sync state a sync report v projektovém repozitáři:"
            Write-Host "  git -C `"$($script:ProjectRoot)`" diff -- miro/ reports/miro-sync/"
            Write-Host "  git -C `"$($script:ProjectRoot)`" add miro/miro-map.yaml miro/sync-state.yaml reports/miro-sync/"
            Write-Host "  git -C `"$($script:ProjectRoot)`" commit -m `"chore: initialize project Miro board and managed artifacts`""
        }
    }
}
finally {
    if ($originalTokenExists) {
        $env:MIRO_ACCESS_TOKEN = $originalToken
    }
    else {
        Remove-Item Env:\MIRO_ACCESS_TOKEN -ErrorAction SilentlyContinue
    }
}
