[CmdletBinding()]
param(
    [string]$PlatformPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [Parameter(Mandatory = $true)][ValidateSet("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")][string]$Gate,
    [Parameter(Mandatory = $true)][ValidateSet("passed", "conditional", "rejected")][string]$Outcome,
    [Parameter(Mandatory = $true)][string]$Reviewer,
    [string]$Approver,
    [string]$DecisionOwner,
    [string]$Scope,
    [string]$Note,
    [string[]]$Condition = @(),
    [string]$ConditionOwner,
    [string]$ConditionDueAt,
    [switch]$HumanDecision,
    [switch]$TestSimulation,
    [switch]$Commit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "private/DDDASteeringSupport.ps1")

if ($HumanDecision -and $TestSimulation) {
    throw "Použij právě jeden režim: -HumanDecision nebo -TestSimulation."
}
if (-not $HumanDecision -and -not $TestSimulation) {
    throw "Gate outcome '$Outcome' vyžaduje explicitní -HumanDecision. Automatizace nesmí vytvářet produkční gate decision."
}
foreach ($required in @(
    @{ Name = "DecisionOwner"; Value = $DecisionOwner },
    @{ Name = "Approver"; Value = $Approver },
    @{ Name = "Scope"; Value = $Scope }
)) {
    if ([string]::IsNullOrWhiteSpace([string]$required.Value)) {
        throw "Gate decision vyžaduje -$($required.Name)."
    }
}
if ($Outcome -eq "conditional") {
    if (@($Condition).Count -eq 0) {
        throw "Outcome conditional vyžaduje alespoň jednu -Condition."
    }
    if ([string]::IsNullOrWhiteSpace($ConditionOwner)) {
        throw "Outcome conditional vyžaduje -ConditionOwner."
    }
    if ([string]::IsNullOrWhiteSpace($ConditionDueAt)) {
        throw "Outcome conditional vyžaduje -ConditionDueAt."
    }
}
if ($Outcome -eq "passed" -and @($Condition).Count -gt 0) {
    throw "Outcome passed nesmí obsahovat neuzavřené -Condition."
}

$platformRoot = (Resolve-Path $PlatformPath).Path
$projectRoot = (Resolve-Path $ProjectPath).Path
Assert-DDDAProjectGitRoot -ProjectRoot $projectRoot
$arguments = @(
    "review-gate",
    "--platform-root", $platformRoot,
    "--project-root", $projectRoot,
    "--gate", $Gate,
    "--outcome", $Outcome,
    "--reviewer", $Reviewer,
    "--approver", $Approver,
    "--decision-owner", $DecisionOwner,
    "--scope", $Scope
)
if ($HumanDecision) { $arguments += @("--provenance", "human") }
if ($TestSimulation) { $arguments += "--test-simulation" }
if (-not [string]::IsNullOrWhiteSpace($Note)) { $arguments += @("--note", $Note) }
foreach ($value in $Condition) { $arguments += @("--condition", $value) }
if (-not [string]::IsNullOrWhiteSpace($ConditionOwner)) { $arguments += @("--condition-owner", $ConditionOwner) }
if (-not [string]::IsNullOrWhiteSpace($ConditionDueAt)) { $arguments += @("--condition-due-at", $ConditionDueAt) }
$result = Invoke-DDDASteeringJson -PlatformRoot $platformRoot -Arguments $arguments

Write-Host "Gate ${Gate}: $Outcome"
Write-Host "Provenance: $(if ($HumanDecision) { 'human' } else { 'test_simulation' })"
Write-Host "Decision owner: $DecisionOwner"
Write-Host "Reviewer: $Reviewer"
Write-Host "Approver: $Approver"
Write-Host "Aktuální fáze: $($result.current_stage)"
Write-Host "Další gate: $($result.next_gate)"
Write-Host "Před commitem zkontroluj: git -C `"$projectRoot`" diff"

if ($Commit) {
    & git -C $projectRoot diff --check
    if ($LASTEXITCODE -ne 0) { throw "Git diff --check selhal." }
    & git -C $projectRoot add project.yaml decisions/gates artifacts/status reports/project-status.yaml
    if ($LASTEXITCODE -ne 0) { throw "Git add gate změn selhal." }
    & git -C $projectRoot commit -m "docs(gate): record $Gate $Outcome"
    if ($LASTEXITCODE -ne 0) { throw "Gate commit selhal." }
    Write-Host "Gate commit byl vytvořen. Push ani merge nebyl proveden."
}
