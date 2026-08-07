# Native GitHub setup runbook

## Purpose

This runbook materializes live GitHub structures that repository files alone cannot activate:

- native Parent/Sub-issue relationships;
- native `Blocked by` / `Blocking` dependencies;
- GitHub Project, fields, items and initial metadata;
- Project views;
- Milestone and release-scope assignments.

The authoritative administration/evidence Issue is #42.

## Automation-first rule

Do not perform setup item-by-item in the GitHub UI unless automation reports one specific unsupported/failed operation.

Authoritative artifacts:

```text
scripts/platform/Bootstrap-DDDAGitHubGovernance.ps1
scripts/platform/Apply-DDDAGitHubGovernance.ps1
scripts/platform/Initialize-DDDAGitHubGovernance.ps1
config/governance/github-bootstrap.json
config/governance/backlog-policy.yaml
```

The automation is intended to be idempotent: it reads current GitHub state, adds missing relationships/items/fields/views and reconciles configured metadata. It never merges, rebases, promotes, releases or issues Human Review/GO decisions.

## Prerequisites

- current GitHub CLI `gh`;
- authenticated repository-owner access;
- Project scope authorization;
- PowerShell supported by the scripts.

Verify:

```powershell
gh --version
gh auth status
```

Authorize Projects once where required:

```powershell
gh auth refresh -s project
```

## Recommended execution — no repository switch required

Do **not** switch the active PR #8 checkout or run the governance automation from a OneDrive-synchronized Git working tree. The safe bootstrap downloads the required governance files through the GitHub API into a new sibling workspace and leaves the current checkout untouched.

From any current directory inside or beside the repository, download and execute the bootstrap from the governance branch:

```powershell
$ErrorActionPreference = "Stop"

$repository = "romanhlavac/ddd-accelerator"
$ref = "feature/github-native-backlog-governance"
$repositoryPath = "scripts/platform/Bootstrap-DDDAGitHubGovernance.ps1"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI 'gh' není dostupné v PATH."
}

& gh auth status
if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI není autentizované. Spusť nejprve: gh auth login"
}

$currentPath = (Get-Location).Path
$parentPath = Split-Path -Parent $currentPath
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$bootstrapPath = Join-Path $parentPath "Bootstrap-DDDAGitHubGovernance-$timestamp.ps1"

$encodedRef = [Uri]::EscapeDataString($ref)
$endpoint = "repos/$repository/contents/$repositoryPath?ref=$encodedRef"
$response = & gh api $endpoint 2>&1

if ($LASTEXITCODE -ne 0) {
    throw "Stažení bootstrap skriptu selhalo:`n$($response -join "`n")"
}

$payload = ($response -join "`n") | ConvertFrom-Json
$fileBytes = [Convert]::FromBase64String(($payload.content -replace "\s", ""))
[System.IO.File]::WriteAllBytes($bootstrapPath, $fileBytes)
Unblock-File -LiteralPath $bootstrapPath -ErrorAction SilentlyContinue

& $bootstrapPath
if (-not $?) {
    throw "Governance automatizace skončila chybou."
}
```

The bootstrap:

- derives a sibling work directory from the current location;
- downloads only the required scripts/config via `gh api`;
- avoids `git switch`, `git clone`, reset and cleanup of the current repository;
- runs the Apply wrapper;
- preserves the generated work directory/report for diagnostics;
- opens the Project by default unless disabled by script parameters.

## Direct execution from a clean governance checkout

Only in a clean, non-synchronized checkout of Draft PR #43:

```powershell
.\scripts\platform\Initialize-DDDAGitHubGovernance.ps1
```

This produces the plan without mutations.

Apply:

```powershell
.\scripts\platform\Apply-DDDAGitHubGovernance.ps1
```

The wrapper invokes the initializer with `-Apply`, opens the Project, finds the latest setup report and publishes the evidence summary to #42 unless disabled.

## Target hierarchy

```text
WP-08 #17
  #9 #10 #11 #12 #13 #14 #15 #45

WP-09 #18
  #21 #22 #23 #24 #25 #50 #26 #51

WP-10 #19
  #27 #28 #29 #30 #31 #32 #33

WP-11 #20
  #34 #35 #36 #37 #38 #39 #40 #47 #41 #48 #46
```

Cross-cutting #16, #42, Draft PR #43, #44 and #49 remain under `Work Package: Other`; #49 is intentionally not a WP-11 child.

PR #8 and Draft PR #43 remain linked implementation items, not Sub-issues.

Parent membership is capability ownership, not release scope.

## Target dependencies

The complete graph is read from `config/governance/github-bootstrap.json`.

### WP-08

```text
#13 → #14 → #12 → #11 → #10 → #9
```

Closed #10/#11/#13 project to `Done`; historical edges remain auditable. Operational critical path is documented in #17/#15.

### WP-09

```text
#21 + #22 → #23
#22 + #23 → #24
#21 + #24 → #25 → #50 → #26 → #51
```

### WP-10

```text
#27 → #31
#27 + #31 → #28, #29, #30, #32
#28 + #29 + #30 + #31 + #32 → #33
```

This direction avoids the former textual cycle. #31 owns central security policy; adapters/#32 consume it.

### WP-11

```text
#34 → #35
#36 → #37 → #38
#36 + #37 + #38 → #39
#37 + #38 + #39 → #40
#27 + #31 + #32 + #34–#40 → #47
#35 + #40 + #47 → #41
#47 + #41 + #48 → #46
```

### Cross-cutting documentation

```text
#16 + #46 + #48 → #49
```

PR #8 stable resolution is an explicit entry condition for broad documentation path moves, not an automatically materialized Issue dependency.

## GitHub Project

Create or reuse:

```text
Owner: romanhlavac
Project: DDDA Platform Backlog
Visibility: PUBLIC
Repository: romanhlavac/ddd-accelerator
```

Items include:

- PR #8;
- Issues #9–#42;
- Draft PR #43;
- Issues #44–#51.

## Fields

- `Status`;
- `Priority`;
- `Work Package`;
- `Item Type`;
- `Platform Area`;
- `Impact`;
- `Target Release`;
- `Start date`;
- `Target date`;
- `Outcome summary`;
- `Blocked` (`No`/`Yes`);
- `Human Review`;
- `Dependency`.

Ownership uses native `Assignees`.

Priority, dates, target release and human review are never inferred automatically.

## Initial metadata rules

- WP-08: Blocked, Target Release `0.1.0`, Human Review Pending;
- WP-09–WP-11: Backlog, Target Release `TBD`;
- #10/#11/#13: Done and `Blocked = No`;
- #45: WP-08/Backlog/TBD, not Milestone 0.1.0;
- #48: WP-11 child;
- #50/#51: WP-09 children;
- #49: Other/Backlog/Blocked;
- closed/merged items: `Done` based on live GitHub state.

Configured values are bootstrap defaults/projections. Safe Project workflows should keep closed/reopened status synchronized.

## Views

Create/verify:

1. `Work Packages`;
2. `WP hierarchy`;
3. `Delivery board`;
4. `Roadmap by Work Package`;
5. `Release scope`;
6. `Blocked and P0`;
7. `Human review queue`;
8. `Ready without owner`;
9. `Recently completed`.

Advanced grouping/visible fields may require UI finalization.

## Milestone

Create/reuse `DDDA 0.1.0` and assign exactly:

- PR #8;
- Issues #9–#15.

Do not assign:

- Parent #17;
- #45;
- WP-09–WP-11;
- Draft PR #43;
- #49–#51.

Milestone membership is release scope, not GO/approval.

## Safe built-in workflows only

Allowed mechanical examples:

- item added → Backlog;
- closed Issue → Done;
- reopened Issue → Triaged;
- merged PR → Done.

Never automate:

- Priority;
- Target Release/Milestone;
- Start/Target dates;
- dependencies based on inference;
- Human Review PASS;
- gate `passed`;
- HRDR or GO/NO-GO;
- closing Parent WP after one PR.

## Verification

After Apply, verify at least:

```powershell
gh issue view 17 -R romanhlavac/ddd-accelerator --json subIssues,subIssuesSummary
gh issue view 18 -R romanhlavac/ddd-accelerator --json subIssues,subIssuesSummary
gh issue view 19 -R romanhlavac/ddd-accelerator --json subIssues,subIssuesSummary
gh issue view 20 -R romanhlavac/ddd-accelerator --json subIssues,subIssuesSummary

gh issue view 31 -R romanhlavac/ddd-accelerator --json parent,blockedBy,blocking
gh issue view 50 -R romanhlavac/ddd-accelerator --json parent,blockedBy,blocking
gh issue view 51 -R romanhlavac/ddd-accelerator --json parent,blockedBy,blocking
gh issue view 46 -R romanhlavac/ddd-accelerator --json parent,blockedBy,blocking
gh issue view 49 -R romanhlavac/ddd-accelerator --json parent,blockedBy,blocking

gh project list --owner romanhlavac
gh project field-list <PROJECT_NUMBER> --owner romanhlavac
gh project item-list <PROJECT_NUMBER> --owner romanhlavac --limit 100
```

Confirm:

- every configured child has the expected native parent;
- every direct dependency is visible and graph is acyclic;
- all Project items/fields/nine views exist;
- #10/#11/#13 are Done;
- #45 is outside Milestone 0.1.0;
- Milestone contains only PR #8 and Issues #9–#15;
- no dates, priority, release or human approval were invented;
- no merge/rebase/promotion occurred.

## Evidence

The automation writes a setup report. Publish/attach the reviewed result to #42 with:

- current governance branch SHA;
- Project URL;
- hierarchy/dependency results;
- Milestone membership;
- warnings/unsupported operations;
- any deliberate deviation from versioned configuration.

Do not commit local reports automatically and do not interpret technical PASS as Human Review PASS.
