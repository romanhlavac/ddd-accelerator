[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$gitRoot = (& git -C $root rev-parse --show-toplevel).Trim()
if ([System.IO.Path]::GetFullPath($gitRoot) -ne [System.IO.Path]::GetFullPath($root)) {
    throw "RepositoryRoot does not match the Git repository root."
}

Push-Location $root
try {
    if (@(& git status --porcelain).Count -ne 0) {
        throw "Broker remediation wrapper requires a clean working tree."
    }

    $python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } elseif (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { throw "Python is required." }
    & $python -m pytest --version *> $null
    if ($LASTEXITCODE -ne 0) {
        & $python -m pip install --disable-pip-version-check "pytest>=8,<9"
        if ($LASTEXITCODE -ne 0) { throw "Cannot install the focused test dependency." }
    }

    $childRelative = "scripts/remediation/Fix-DDDA-ProjectFieldOptionReconcile.ps1"
    $child = Join-Path $root $childRelative
    if (-not (Test-Path -LiteralPath $child -PathType Leaf)) {
        throw "Staged remediation script is missing: $childRelative"
    }

    # The staged child predates the broker parameter contract and has one
    # PowerShell StrictMode null-output edge in its clean-tree guard. Execute a
    # temporary, byte-equivalent copy with only that guard made array-safe; the
    # governed implementation diff remains unchanged and both staging scripts
    # are removed before the validated commit.
    $childText = Get-Content -LiteralPath $child -Raw -Encoding UTF8
    $oldGuard = 'if ((& git status --porcelain).Count -ne 0) {'
    $newGuard = 'if (@(& git status --porcelain).Count -ne 0) {'
    if (($childText.Split($oldGuard).Count - 1) -ne 1) {
        throw "Expected exactly one child clean-tree guard to adapt."
    }
    $tempChild = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-project-field-option-" + [Guid]::NewGuid().ToString("N") + ".ps1")
    [System.IO.File]::WriteAllText($tempChild, $childText.Replace($oldGuard, $newGuard), (New-Object System.Text.UTF8Encoding($false)))
    try {
        & $tempChild
        if (-not $?) {
            throw "Project field-option remediation failed."
        }
    }
    finally {
        Remove-Item -LiteralPath $tempChild -Force -ErrorAction SilentlyContinue
    }

    Remove-Item -LiteralPath $child -Force

    $wrapperRelative = "scripts/remediation/Invoke-DDDA-ProjectFieldOptionReconcileBroker.ps1"
    $expected = @(
        "CHANGELOG.md",
        "docs/governance/wp-backlog-consistency.md",
        "runtime/platform/tests/test_project_backlog_delivery_governance.py",
        "scripts/platform/Reconcile-DDDAProjectBacklogCore.py",
        $childRelative,
        $wrapperRelative
    ) | Sort-Object

    Remove-Item -LiteralPath $PSCommandPath -Force

    $observed = @(& git status --porcelain=v1 | ForEach-Object { $_.Substring(3).Trim() } | Sort-Object)
    $unexpected = @($observed | Where-Object { $_ -notin $expected })
    $missing = @($expected | Where-Object { $_ -notin $observed })
    if ($unexpected.Count -gt 0 -or $missing.Count -gt 0) {
        throw "Remediation path contract mismatch. Unexpected=[$($unexpected -join ', ')] Missing=[$($missing -join ', ')]"
    }

    & git add -- @expected
    if ($LASTEXITCODE -ne 0) { throw "git add failed." }

    $staged = @(& git diff --cached --name-only | Sort-Object)
    $unexpectedStaged = @($staged | Where-Object { $_ -notin $expected })
    $missingStaged = @($expected | Where-Object { $_ -notin $staged })
    if ($unexpectedStaged.Count -gt 0 -or $missingStaged.Count -gt 0) {
        throw "Staged path contract mismatch. Unexpected=[$($unexpectedStaged -join ', ')] Missing=[$($missingStaged -join ', ')]"
    }

    & git commit -m "fix(governance): reconcile Project field options"
    if ($LASTEXITCODE -ne 0) { throw "Validated remediation commit failed." }

    if (@(& git status --porcelain).Count -ne 0) {
        throw "Validated remediation commit left a dirty working tree."
    }

    if (-not $NoPush) {
        Write-Host "Commit created. Push is intentionally owned by the governed broker." -ForegroundColor Yellow
    }
}
finally {
    Pop-Location
}
