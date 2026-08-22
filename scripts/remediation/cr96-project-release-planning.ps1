[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = [System.IO.Path]::GetFullPath($RepositoryRoot)
$configPath = Join-Path $root 'config/governance/github-bootstrap.json'
$selfPath = $MyInvocation.MyCommand.Path

if (-not $NoPush) {
    throw 'This remediation is authorized only with -NoPush; broker owns the validated push.'
}
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Missing governance contract: $configPath"
}

$text = [System.IO.File]::ReadAllText($configPath, [System.Text.Encoding]::UTF8)

function Replace-ExactlyOnce {
    param(
        [Parameter(Mandatory = $true)][string]$InputText,
        [Parameter(Mandatory = $true)][string]$Old,
        [Parameter(Mandatory = $true)][string]$New,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $first = $InputText.IndexOf($Old, [System.StringComparison]::Ordinal)
    if ($first -lt 0) { throw "Expected governance fragment not found: $Label" }
    $second = $InputText.IndexOf($Old, $first + $Old.Length, [System.StringComparison]::Ordinal)
    if ($second -ge 0) { throw "Governance fragment is ambiguous: $Label" }
    return $InputText.Substring(0, $first) + $New + $InputText.Substring($first + $Old.Length)
}

$dependencyOld = @'
    {
      "blocked": 62,
      "blocked_by": [
        34,
        35,
        47,
        48,
        52
      ]
    }
  ],
'@
$dependencyNew = @'
    {
      "blocked": 62,
      "blocked_by": [
        34,
        35,
        47,
        48,
        52
      ]
    },
    {
      "blocked": 75,
      "blocked_by": [
        96
      ]
    }
  ],
'@
$text = Replace-ExactlyOnce -InputText $text -Old $dependencyOld -New $dependencyNew -Label 'release plan #75 blocked by #96'

$item88 = @'
    {
      "kind": "issue",
      "numbers": [
        88
      ],
      "metadata": {
        "Status": "Backlog",
        "Work Package": "Other",
        "Item Type": "Enabler",
        "Target Release": "TBD",
        "Blocked": "No",
        "Human Review": "Pending"
      }
    }
'@
$item96And88 = @'
    {
      "kind": "issue",
      "numbers": [
        96
      ],
      "metadata": {
        "Status": "Ready",
        "Priority": "P0",
        "Work Package": "Other",
        "Item Type": "Defect",
        "Platform Area": "RELEASE",
        "Impact": "HIGH",
        "Target Release": "0.1.1",
        "Blocked": "No",
        "Human Review": "Pending",
        "Outcome summary": "Enforce declared release scope equals physical release-source scope and block DDDA 0.1.1 release readiness until current-source recovery is explicitly decided."
      }
    },
    {
      "kind": "issue",
      "numbers": [
        88
      ],
      "metadata": {
        "Status": "Backlog",
        "Work Package": "Other",
        "Item Type": "Enabler",
        "Target Release": "TBD",
        "Blocked": "No",
        "Human Review": "Pending"
      }
    }
'@
$text = Replace-ExactlyOnce -InputText $text -Old $item88 -New $item96And88 -Label 'planning item #96'

$descriptionOld = '      "description": "Approved stabilization release scope from #75. Milestone membership is release scope, not release approval.",'
$descriptionNew = '      "description": "Approved stabilization release scope from #75 plus P0 release-readiness blocker #96. Milestone membership is release scope, not release approval.",'
$text = Replace-ExactlyOnce -InputText $text -Old $descriptionOld -New $descriptionNew -Label 'DDDA 0.1.1 milestone description'

$scopeOld = @'
      "issues": [
        9,
        12,
        67,
        68,
        70
      ],
'@
$scopeNew = @'
      "issues": [
        9,
        12,
        67,
        68,
        70,
        96
      ],
'@
$text = Replace-ExactlyOnce -InputText $text -Old $scopeOld -New $scopeNew -Label 'DDDA 0.1.1 milestone membership'

# Parse the exact result before committing; semantic authority must remain valid JSON.
$parsed = $text | ConvertFrom-Json
$release = @($parsed.milestones | Where-Object { $_.title -eq 'DDDA 0.1.1' })
if ($release.Count -ne 1) { throw 'Expected exactly one DDDA 0.1.1 milestone contract.' }
if (96 -notin @($release[0].issues | ForEach-Object { [int]$_ })) { throw '#96 is absent from DDDA 0.1.1 milestone contract.' }
$group96 = @($parsed.item_groups | Where-Object { $_.kind -eq 'issue' -and 96 -in @($_.numbers | ForEach-Object { [int]$_ }) })
if ($group96.Count -ne 1) { throw 'Expected exactly one planning item group for #96.' }
$meta = $group96[0].metadata
$expected = @{
    'Status' = 'Ready'; 'Priority' = 'P0'; 'Work Package' = 'Other'; 'Item Type' = 'Defect';
    'Platform Area' = 'RELEASE'; 'Impact' = 'HIGH'; 'Target Release' = '0.1.1';
    'Blocked' = 'No'; 'Human Review' = 'Pending'
}
foreach ($key in $expected.Keys) {
    if ([string]$meta.$key -ne [string]$expected[$key]) {
        throw "#96 metadata mismatch for '$key': '$($meta.$key)'"
    }
}
$dep96 = @($parsed.dependencies | Where-Object { [int]$_.blocked -eq 75 -and 96 -in @($_.blocked_by | ForEach-Object { [int]$_ }) })
if ($dep96.Count -ne 1) { throw '#75 release-readiness dependency on #96 is absent or ambiguous.' }

[System.IO.File]::WriteAllText($configPath, $text, (New-Object System.Text.UTF8Encoding($false)))

Push-Location $root
try {
    git diff --check -- config/governance/github-bootstrap.json
    if ($LASTEXITCODE -ne 0) { throw 'git diff --check failed for governance contract.' }

    git add -- config/governance/github-bootstrap.json
    git rm --quiet -- $selfPath
    if ($LASTEXITCODE -ne 0) { throw 'Failed to stage remediation script removal.' }

    git diff --cached --check
    if ($LASTEXITCODE -ne 0) { throw 'git diff --cached --check failed.' }

    $changed = @(git diff --cached --name-only)
    if ($changed.Count -ne 2 -or 'config/governance/github-bootstrap.json' -notin $changed -or 'scripts/remediation/cr96-project-release-planning.ps1' -notin $changed) {
        throw "Unexpected staged remediation scope: $($changed -join ', ')"
    }

    git commit -m 'chore(governance): project defect 96 into release planning'
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create CR96 governance projection commit.' }
}
finally {
    Pop-Location
}
