[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = [System.IO.Path]::GetFullPath($RepositoryRoot).TrimEnd('\','/')
$expectedMain = '2646bf28918dfbb98fb8980f2be07428dc1ebbb1'
$selfRelative = 'scripts/remediation/REM-12-miro-board-identity-handoff.ps1'
$selfPath = Join-Path $root $selfRelative
$cliRelative = 'runtime/miro/ddda_miro/cli.py'
$supportRelative = 'scripts/platform/DDDAMiroEvidenceSupport.ps1'
$wrapperRelative = 'scripts/platform/Invoke-DDDAMiroAcceptanceEvidence.ps1'
$psTestRelative = 'tests/powershell/Test-DDDAMiroEvidence.ps1'
$pyTestRelative = 'runtime/miro/tests/test_cli_board_identity_handoff.py'
$remoteBrokerRelative = 'docs/developer-guide/remote-validation-broker.md'
$changelogRelative = 'CHANGELOG.md'
$finalPaths = @($cliRelative,$supportRelative,$wrapperRelative,$psTestRelative,$pyTestRelative,$remoteBrokerRelative,$changelogRelative) | Sort-Object

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $output = @(& git -C $root @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed:`n$($output -join [Environment]::NewLine)"
    }
    return (($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine).Trim()
}

function Write-Text {
    param([string]$Path,[string]$Text,[switch]$Bom)
    $encoding = New-Object System.Text.UTF8Encoding([bool]$Bom)
    [System.IO.File]::WriteAllText($Path,$Text,$encoding)
}

function Replace-ExactOnce {
    param([string]$Text,[string]$Old,[string]$New,[string]$Label)
    $first = $Text.IndexOf($Old,[System.StringComparison]::Ordinal)
    if ($first -lt 0) { throw "$Label: expected source text not found." }
    $second = $Text.IndexOf($Old,$first + $Old.Length,[System.StringComparison]::Ordinal)
    if ($second -ge 0) { throw "$Label: expected source text is not unique." }
    return $Text.Substring(0,$first) + $New + $Text.Substring($first + $Old.Length)
}

$current = Invoke-Git @('rev-parse','HEAD')
$parent = Invoke-Git @('rev-parse','HEAD^')
if ($parent -ne $expectedMain) {
    throw "Staging commit parent '$parent' does not match exact main '$expectedMain'."
}
$statusBefore = Invoke-Git @('status','--porcelain')
if (-not [string]::IsNullOrWhiteSpace($statusBefore)) { throw "Working tree is not clean before remediation:`n$statusBefore" }
$stagingPaths = @(Invoke-Git @('diff','--name-only',$expectedMain,$current) -split "`r?`n" | Where-Object { $_ })
if ($stagingPaths.Count -ne 1 -or $stagingPaths[0] -ne $selfRelative) {
    throw "Staging commit must contain only $selfRelative. Observed: $($stagingPaths -join ', ')"
}

# 1) Miro CLI emits an explicit non-secret board identity marker immediately after POST /boards succeeds.
$cliPath = Join-Path $root $cliRelative
$cli = Get-Content -LiteralPath $cliPath -Raw -Encoding UTF8
$oldCliHeader = @'
from .sync import sync_project


def _parser() -> argparse.ArgumentParser:
'@
$newCliHeader = @'
from .sync import sync_project


BOARD_IDENTITY_HANDOFF_PREFIX = "DDDA_MIRO_BOARD_ID_HANDOFF:"


class _BoardIdentityHandoffClient:
    """Proxy that emits board identity immediately after successful board creation."""

    def __init__(self, inner):
        self._inner = inner

    def create_board(self, *args, **kwargs):
        board = self._inner.create_board(*args, **kwargs)
        board_id = str((board or {}).get("id") or "").strip()
        if not board_id:
            raise ValueError("Miro create_board succeeded without a usable board id")
        print(f"{BOARD_IDENTITY_HANDOFF_PREFIX}{board_id}", file=sys.stderr, flush=True)
        return board

    def __getattr__(self, name):
        return getattr(self._inner, name)


def _parser() -> argparse.ArgumentParser:
'@
$cli = Replace-ExactOnce -Text $cli -Old $oldCliHeader -New $newCliHeader -Label 'Miro CLI handoff proxy'
$oldCliRender = @'
        elif args.command == "render":
            client = None if args.dry_run and not os.environ.get(config.token_env) else MiroClient(config.access_token())
            result = render_board(config, client, create_board=args.create_board, dry_run=args.dry_run)
'@
$newCliRender = @'
        elif args.command == "render":
            raw_client = None if args.dry_run and not os.environ.get(config.token_env) else MiroClient(config.access_token())
            client = None if raw_client is None else _BoardIdentityHandoffClient(raw_client)
            result = render_board(config, client, create_board=args.create_board, dry_run=args.dry_run)
'@
$cli = Replace-ExactOnce -Text $cli -Old $oldCliRender -New $newCliRender -Label 'Miro CLI render client wiring'
Write-Text -Path $cliPath -Text $cli

# 2) Shared evidence helper parses exactly one handoff identity and fails closed on conflicting markers.
$supportPath = Join-Path $root $supportRelative
$support = Get-Content -LiteralPath $supportPath -Raw -Encoding UTF8
$oldSupportAnchor = 'function New-DDDANotRunMiroEvidence {'
$newSupportBlock = @'
function Get-DDDAMiroBoardIdentityHandoff {
    param([object[]]$ChildOutput = @())

    $text = (($ChildOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine)
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $null
    }

    $matches = [regex]::Matches($text, '(?m)^DDDA_MIRO_BOARD_ID_HANDOFF:(?<id>[^\r\n]+?)\s*$')
    if ($matches.Count -eq 0) {
        return $null
    }

    $ids = @(
        $matches |
            ForEach-Object { [string]$_.Groups['id'].Value.Trim() } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            Select-Object -Unique
    )
    if ($ids.Count -ne 1) {
        throw "Miro board identity handoff je nejednoznačný. Nalezené identity: $($ids -join ', ')"
    }

    return [pscustomobject][ordered]@{
        board_id = [string]$ids[0]
        board_url = "https://miro.com/app/board/$($ids[0])/"
        source = "create_board_stderr_handoff"
    }
}

function New-DDDANotRunMiroEvidence {
'@
$support = Replace-ExactOnce -Text $support -Old $oldSupportAnchor -New $newSupportBlock -Label 'Miro evidence handoff helper'
Write-Text -Path $supportPath -Text $support -Bom

# 3) Evidence wrapper recovers board identity before requiring a child report and reconciles it with report identity.
$wrapperPath = Join-Path $root $wrapperRelative
$wrapper = Get-Content -LiteralPath $wrapperPath -Raw -Encoding UTF8
$oldChildOutputBlock = @'
        $childOutput | ForEach-Object { Write-Host $_ }
        foreach ($line in $childOutput) {
            $text = [string]$line
            if ($text -match '^Report:\s*(?<path>.+?)\s*$') {
                $reportPath = [string]$Matches["path"]
            }
        }
'@
$newChildOutputBlock = @'
        $handoff = Get-DDDAMiroBoardIdentityHandoff -ChildOutput $childOutput
        if ($null -ne $handoff) {
            $boardId = [string]$handoff.board_id
            $boardUrl = [string]$handoff.board_url
        }

        $childOutput | ForEach-Object { Write-Host $_ }
        foreach ($line in $childOutput) {
            $text = [string]$line
            if ($text -match '^Report:\s*(?<path>.+?)\s*$') {
                $reportPath = [string]$Matches["path"]
            }
        }
'@
$wrapper = Replace-ExactOnce -Text $wrapper -Old $oldChildOutputBlock -New $newChildOutputBlock -Label 'wrapper child handoff recovery'
$oldReportIdentity = @'
        $report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $workspace = [string]$report.workspace
        $projectPath = [string]$report.project
        $boardId = [string]$report.miro_board_id
        if (-not [string]::IsNullOrWhiteSpace($boardId)) {
            $boardUrl = "https://miro.com/app/board/$boardId/"
        }
'@
$newReportIdentity = @'
        $report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $workspace = [string]$report.workspace
        $projectPath = [string]$report.project
        $reportBoardId = [string]$report.miro_board_id
        if (-not [string]::IsNullOrWhiteSpace($reportBoardId)) {
            if (-not [string]::IsNullOrWhiteSpace($boardId) -and $boardId -ne $reportBoardId) {
                throw "Miro board identity handoff '$boardId' neodpovídá child reportu '$reportBoardId'."
            }
            $boardId = $reportBoardId
            $boardUrl = "https://miro.com/app/board/$boardId/"
        }
'@
$wrapper = Replace-ExactOnce -Text $wrapper -Old $oldReportIdentity -New $newReportIdentity -Label 'wrapper report identity reconciliation'
Write-Text -Path $wrapperPath -Text $wrapper -Bom

# 4) PowerShell regression proves recovery from failure output and fail-closed conflicting identity behavior.
$psTestPath = Join-Path $root $psTestRelative
$psTest = Get-Content -LiteralPath $psTestPath -Raw -Encoding UTF8
$oldPsAnchor = @'
$wrapperCommand = Get-Command (Join-Path $PlatformPath "scripts/platform/Invoke-DDDAMiroAcceptanceEvidence.ps1")
foreach ($parameterName in @("KeepReviewBoard", "MiroTeamId", "EvidenceOutputPath", "CleanupOnFailure")) {
    Assert-True -Condition $wrapperCommand.Parameters.ContainsKey($parameterName) -Message "Miro evidence wrapper nemá parametr $parameterName."
}

$tempRoot = Join-Path $env:TEMP ("ddda-miro-evidence-test-" + [Guid]::NewGuid().ToString("N"))
'@
$newPsAnchor = @'
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
'@
$psTest = Replace-ExactOnce -Text $psTest -Old $oldPsAnchor -New $newPsAnchor -Label 'PowerShell failure-path regression'
Write-Text -Path $psTestPath -Text $psTest -Bom

# 5) Python regression proves the marker is emitted immediately by the create-board proxy before later render work can fail.
$pyTestPath = Join-Path $root $pyTestRelative
$pyTest = @'
from __future__ import annotations

from ddda_miro.cli import BOARD_IDENTITY_HANDOFF_PREFIX, _BoardIdentityHandoffClient


class _FakeClient:
    def __init__(self):
        self.calls = []

    def create_board(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return {"id": "uXjV-ImmediateHandoff="}

    def get_board(self, board_id):
        return {"id": board_id}


def test_create_board_proxy_emits_identity_immediately(capsys):
    inner = _FakeClient()
    client = _BoardIdentityHandoffClient(inner)

    board = client.create_board("name", "description", team_id="team")

    assert board["id"] == "uXjV-ImmediateHandoff="
    assert len(inner.calls) == 1
    assert capsys.readouterr().err.strip() == (
        f"{BOARD_IDENTITY_HANDOFF_PREFIX}uXjV-ImmediateHandoff="
    )


def test_proxy_delegates_non_create_calls():
    client = _BoardIdentityHandoffClient(_FakeClient())
    assert client.get_board("uXjV-Existing=") == {"id": "uXjV-Existing="}
'@
Write-Text -Path $pyTestPath -Text $pyTest

# 6) Document the explicit handoff protocol and its security/fail-closed semantics.
$brokerPath = Join-Path $root $remoteBrokerRelative
$broker = Get-Content -LiteralPath $brokerPath -Raw -Encoding UTF8
$oldBrokerAnchor = @'
```text
REST API = deterministic automation/data plane
MCP      = optional interactive AI control plane
```

GitHub Actions nesmí používat MCP pro online acceptance, reconcile nebo HVR materialization. MCP quota ani nedostupnost Miro connectoru není technical-gate dependency.
'@
$newBrokerAnchor = @'
```text
REST API = deterministic automation/data plane
MCP      = optional interactive AI control plane
```

Při board-lifecycle acceptance je board identity auditní identifikátor, nikoli secret. Jakmile `POST /boards` úspěšně vrátí board ID, Miro CLI okamžitě emituje explicitní stderr marker `DDDA_MIRO_BOARD_ID_HANDOFF:<board-id>`. Evidence wrapper tento marker zachytí nezávisle na child reportu, takže board ID/URL a cleanup audit přežijí i failure po vytvoření boardu, ale před vytvořením child reportu. Více různých handoff identit nebo rozpor handoff vs. child report znamená fail-closed. Token ani authorization metadata se do handoffu nezapisují.

GitHub Actions nesmí používat MCP pro online acceptance, reconcile nebo HVR materialization. MCP quota ani nedostupnost Miro connectoru není technical-gate dependency.
'@
$broker = Replace-ExactOnce -Text $broker -Old $oldBrokerAnchor -New $newBrokerAnchor -Label 'remote broker handoff documentation'
Write-Text -Path $brokerPath -Text $broker

# 7) Changelog records the #12 stabilization delta.
$changelogPath = Join-Path $root $changelogRelative
$changelog = Get-Content -LiteralPath $changelogPath -Raw -Encoding UTF8
$oldChangelog = '- annotated release tag nyní používá deterministic non-secret Git identity pouze v izolovaném release-source clone; clean runner proto nezávisí na ambientním `user.name`/`user.email` a bounded recovery po post-validation tag failure je explicitně zdokumentována.'
$newChangelog = $oldChangelog + "`r`n- Miro acceptance failure-path nyní předává board identity explicitním non-secret handoff markerem ihned po úspěšném vytvoření boardu; evidence wrapper zachová board ID/URL a cleanup audit i při child failure před child reportem a konfliktní identity failují closed."
$changelog = Replace-ExactOnce -Text $changelog -Old $oldChangelog -New $newChangelog -Label 'CHANGELOG #12 entry'
Write-Text -Path $changelogPath -Text $changelog

# Targeted deterministic validation before committing.
$python = Get-Command python -ErrorAction Stop
& $python.Source -m pytest (Join-Path $root $pyTestRelative) -q
if ($LASTEXITCODE -ne 0) { throw "Python board identity handoff regression failed." }

& (Join-Path $root 'tests/powershell/Test-DDDAMiroEvidence.ps1') -PlatformPath $root
if ($LASTEXITCODE -ne 0) { throw "PowerShell Miro evidence regression failed." }

# Self-remove staging transport and verify exact final scope.
Remove-Item -LiteralPath $selfPath -Force
$observed = @(& git -C $root status --porcelain | ForEach-Object {
    $line = $_.ToString()
    if ($line.Length -ge 4) { $line.Substring(3) } else { $line }
} | ForEach-Object { $_.Trim('"') } | Sort-Object -Unique)
$expectedObserved = @($finalPaths + $selfRelative | Sort-Object)
if (($observed -join "`n") -ne ($expectedObserved -join "`n")) {
    throw "Unexpected remediation paths. Expected:`n$($expectedObserved -join "`n")`nObserved:`n$($observed -join "`n")"
}

$null = Invoke-Git @('add','-A')
$null = Invoke-Git @('commit','-m','fix(miro): preserve board identity across child failure')
$after = Invoke-Git @('rev-parse','HEAD')
$count = [int](Invoke-Git @('rev-list','--count',"$current..$after"))
if ($count -ne 1) { throw "Remediation must create exactly one corrective commit; created $count." }
$statusAfter = Invoke-Git @('status','--porcelain')
if (-not [string]::IsNullOrWhiteSpace($statusAfter)) { throw "Working tree is not clean after remediation:`n$statusAfter" }

Write-Host "REM-12 PASS"
Write-Host "base=$current"
Write-Host "validated_commit=$after"
Write-Host "paths=$($finalPaths -join ',')"

if (-not $NoPush) {
    $null = Invoke-Git @('push','origin',"HEAD:fix/12-miro-board-identity-handoff")
}
