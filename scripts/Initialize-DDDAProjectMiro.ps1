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
    [switch]$Resume
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

    $raw = & $script:MiroPython -m ddda_miro --project $script:ProjectRoot --platform $script:PlatformRoot @CommandArguments 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($raw | Out-String).Trim()

    if ($exitCode -ne 0) {
        throw ("DDDA Miro CLI selhalo: {0}`n{1}" -f ($CommandArguments -join " "), $text)
    }

    try {
        return ($text | ConvertFrom-Json)
    }
    catch {
        throw ("DDDA Miro CLI nevrátilo platný JSON.`nPříkaz: {0}`nVýstup:`n{1}" -f ($CommandArguments -join " "), $text)
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

    $initialProjectChanges = Invoke-DDDAGit -RepositoryPath $script:ProjectRoot -Arguments @("status", "--porcelain")
    if ($Resume) {
        $null = Assert-DDDAGitChangesWithinPath -PorcelainText $initialProjectChanges -AllowedPrefix "miro/" -Label "Projektový repozitář v resume režimu"
        if (-not [string]::IsNullOrWhiteSpace($initialProjectChanges)) {
            Write-Host "Resume: používají se existující necommitnuté změny omezené na miro/."
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
    Write-Host "=== Povinný dry-run ==="
    $preview = Invoke-ProjectMiroCli -CommandArguments ($renderArguments + "--dry-run")
    $preview | ConvertTo-Json -Depth 20 | Write-Host

    if ($DryRun) {
        Assert-DDDACleanGitRepository -RepositoryPath $script:PlatformRoot -Label "Platformní"
        if ($Resume) {
            $dryRunProjectChanges = Invoke-DDDAGit -RepositoryPath $script:ProjectRoot -Arguments @("status", "--porcelain")
            $null = Assert-DDDAGitChangesWithinPath -PorcelainText $dryRunProjectChanges -AllowedPrefix "miro/" -Label "Projektový repozitář po resume dry-run"
        }
        else {
            Assert-DDDACleanGitRepository -RepositoryPath $script:ProjectRoot -Label "Projektový"
        }
        Write-Host ""
        Write-Host "DDDA projektový Miro dry-run: PASS"
        return
    }

    Write-Host ""
    Write-Host "=== Render cílového boardu ==="
    $firstRender = Invoke-ProjectMiroCli -CommandArguments $renderArguments
    $boardId = [string](Get-DDDAObjectPropertyValue -InputObject $firstRender -Name "board_id")
    if ([string]::IsNullOrWhiteSpace($boardId)) {
        throw "Renderer nevrátil board_id."
    }

    $onlineDoctor = Invoke-ProjectMiroCli -CommandArguments @("doctor", "--online")
    if (-not (Get-DDDAObjectPropertyValue -InputObject $onlineDoctor -Name "board")) {
        throw "Online doctor nevrátil board."
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

    $secondSnapshot = Get-DDDAMiroMapSnapshot -ProjectPath $script:ProjectRoot
    $mappingDifference = Compare-Object -ReferenceObject @($firstSnapshot.ItemIds) -DifferenceObject @($secondSnapshot.ItemIds)
    if ($mappingDifference) {
        throw "Kontrolní render změnil množinu Miro item ID; hrozí duplikace scaffoldu."
    }

    Assert-DDDACleanGitRepository -RepositoryPath $script:PlatformRoot -Label "Platformní"

    $projectChanges = Invoke-DDDAGit -RepositoryPath $script:ProjectRoot -Arguments @("status", "--porcelain")
    $projectEntries = @(ConvertFrom-DDDAGitPorcelain -PorcelainText $projectChanges)
    $unexpectedChanges = @(
        $projectEntries |
            Where-Object { -not $_.Path.StartsWith("miro/", [System.StringComparison]::OrdinalIgnoreCase) }
    )
    if ($unexpectedChanges.Count -gt 0) {
        throw "Inicializace změnila neočekávané projektové soubory:`n$($unexpectedChanges.Line -join "`n")"
    }

    Write-Host ""
    Write-Host "DDDA projektový Miro board: PASS"
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
        Write-Host "Zkontroluj diff a commitni změnu v projektovém repozitáři, typicky:"
        Write-Host "  git -C `"$($script:ProjectRoot)`" diff -- miro/miro-map.yaml"
        Write-Host "  git -C `"$($script:ProjectRoot)`" add miro/miro-map.yaml"
        Write-Host "  git -C `"$($script:ProjectRoot)`" commit -m `"chore: initialize project Miro board`""
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
