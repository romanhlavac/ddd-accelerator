[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Replace-ExactlyOnce {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Old,
        [Parameter(Mandatory = $true)][string]$New,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $count = [regex]::Matches($Text, [regex]::Escape($Old)).Count
    if ($count -ne 1) {
        throw "Expected exactly one '$Label' replacement, found $count."
    }
    return $Text.Replace($Old, $New)
}

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

    $childText = Get-Content -LiteralPath $child -Raw -Encoding UTF8

    $childText = Replace-ExactlyOnce -Text $childText `
        -Old 'if ((& git status --porcelain).Count -ne 0) {' `
        -New 'if (@(& git status --porcelain).Count -ne 0) {' `
        -Label 'array-safe clean-tree guard'

    $oldCore = @'
        existing = list(field.get("options") or [])
        existing_names = {x.get("name") for x in existing}
        missing = [
            option
            for option in definition.get("options", [])
            if option.get("name") not in existing_names
        ]
        if not missing:
            continue
        options = [project_option_input(option) for option in existing]
        options.extend(project_option_input(option) for option in missing)
        gql(q, {"fieldId": field["id"], "options": options})
'@
    $newCore = @'
        existing = {
            option.get("name"): option.get("id")
            for option in field.get("options") or []
        }
        missing = [
            option
            for option in definition.get("options", [])
            if option.get("name") not in existing
        ]
        if not missing:
            continue
        options = []
        for option in definition.get("options", []):
            item = project_option_input(option)
            existing_id = existing.get(option.get("name"))
            if existing_id:
                item["id"] = existing_id
            options.append(item)
        gql(q, {"fieldId": field["id"], "options": options})
'@
    $childText = Replace-ExactlyOnce -Text $childText -Old $oldCore -New $newCore -Label 'canonical option normalization'

    $childText = Replace-ExactlyOnce -Text $childText `
        -Old 'def test_reconciler_materializes_missing_configured_project_options_without_dropping_existing_options():' `
        -New 'def test_reconciler_materializes_missing_configured_project_options_and_normalizes_to_versioned_contract():' `
        -Label 'test name'

    $childText = Replace-ExactlyOnce -Text $childText `
        -Old '    ns["gql"] = fake_gql' `
        -New '    ns["reconcile_configured_project_options"].__globals__["gql"] = fake_gql' `
        -Label 'first gql monkeypatch'

    $childText = Replace-ExactlyOnce -Text $childText `
        -Old '    ns["gql"] = lambda *args, **kwargs: calls.append((args, kwargs))' `
        -New '    ns["reconcile_configured_project_options"].__globals__["gql"] = lambda *args, **kwargs: calls.append((args, kwargs))' `
        -Label 'second gql monkeypatch'

    $oldAssertions = @'
    assert [option["name"] for option in variables["options"]] == ["WP-08", "Legacy", "WP-14"]
    assert variables["options"][0]["id"] == "OPT-08"
    assert variables["options"][1]["id"] == "OPT-LEGACY"
    assert "id" not in variables["options"][2]
'@
    $newAssertions = @'
    assert [option["name"] for option in variables["options"]] == ["WP-08", "WP-14"]
    assert variables["options"][0]["id"] == "OPT-08"
    assert "id" not in variables["options"][1]
'@
    $childText = Replace-ExactlyOnce -Text $childText -Old $oldAssertions -New $newAssertions -Label 'canonical option test assertions'

    $oldDoc = '- Privileged reconciler před item projection mechanicky doplní chybějící canonical `SINGLE_SELECT` options z verzovaného `github-bootstrap.json`, zachová existující live option IDs i případné další live options a fresh read-back musí prokázat přítomnost všech canonical options.'
    $newDoc = '- Privileged reconciler před item projection mechanicky normalizuje canonical `SINGLE_SELECT` options podle verzovaného `github-bootstrap.json`, zachová live option IDs pro shodné canonical hodnoty a fresh read-back musí prokázat přesnou dostupnost všech canonical options.'
    $childText = Replace-ExactlyOnce -Text $childText -Old $oldDoc -New $newDoc -Label 'governance documentation semantics'

    $tempChild = Join-Path ([System.IO.Path]::GetTempPath()) ("ddda-project-field-option-" + [Guid]::NewGuid().ToString("N") + ".ps1")
    [System.IO.File]::WriteAllText($tempChild, $childText, (New-Object System.Text.UTF8Encoding($false)))
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
