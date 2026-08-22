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

```text
NO_MANUAL_GITHUB_GUI_FOR_MECHANICAL_OPERATIONS
```

Do not perform setup item-by-item in the GitHub UI merely because one connector does not expose the required mutation. Determine the required capability and use the canonical provider order:

```text
CONNECTOR
→ CANONICAL_BROKER_OR_DEDICATED_CREDENTIAL
→ HUMAN_BOOTSTRAP_ONLY
→ UNAVAILABLE
```

`HUMAN_BOOTSTRAP_ONLY` means the programmatic route exists and user OAuth consent/scope is the only missing prerequisite. The human authorizes only; automation performs the mutation and fresh read-back. `UNAVAILABLE` is used only after the approved programmatic routes are exhausted with a concrete capability diagnosis.

Canonical authorization contract:

```text
config/platform/github-capability-routing.json
docs/developer-guide/github-capability-authorization.md
```

Authoritative governance artifacts:

```text
scripts/platform/Bootstrap-DDDAGitHubGovernance.ps1
scripts/platform/Apply-DDDAGitHubGovernance.ps1
scripts/platform/Initialize-DDDAGitHubGovernance.ps1
config/governance/github-bootstrap.json
config/governance/backlog-policy.yaml
```

The automation is intended to be idempotent: it reads current GitHub state, adds missing relationships/items/fields/views and reconciles configured metadata. It never merges, rebases, promotes, releases or issues Human Review/GO decisions.

## Prerequisites by selected execution route

Do not require GitHub CLI merely because this runbook mentions it.

1. If the connected GitHub capability supports the required operation, use `CONNECTOR`.
2. Otherwise prefer the canonical DDDA broker or approved dedicated governance credential.
3. Only if the remaining gap is user OAuth consent/scope for an available CLI/API route, enter `HUMAN_BOOTSTRAP_ONLY`.
4. Use `UNAVAILABLE` only when no approved programmatic route can satisfy the capability.

For a selected local/CLI route, prerequisites are:

- current GitHub CLI `gh`;
- authenticated repository-owner access;
- the least-privilege scope required by the requested capability;
- PowerShell supported by the scripts.

Verify without exposing a token:

```powershell
gh --version
gh auth status
```

For a user-owned Project V2 mutation, `project` is a typical required scope when live GitHub semantics require it. Existing login:

```powershell
gh auth refresh -s project
```

Fresh browser/device login:

```powershell
gh auth login --hostname github.com --git-protocol https --web --scopes project
```

The human performs only the local GitHub authorization challenge. Do not ask for a PAT/token in Chat/Work and do not ask the human to edit Project fields or other deterministic GitHub state manually after consent.

A local `gh` credential is not automatically available to a separate ChatGPT connector or cloud runner. If the execution plane cannot reuse the authorized local session, diagnose that session-boundary gap and use the canonical broker/dedicated-credential route instead of pretending the credential was transferred.

## Recommended execution — no repository switch required

The canonical connector/broker route is preferred when it can perform the requested governance operation. The following local bootstrap is a supported CLI execution path when that route has been selected; it is not a reason to bypass capability routing.

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
    throw "GitHub CLI není autentizované. Použij canonical authorization route; pokud je zvolen HUMAN_BOOTSTRAP_ONLY, spusť jeden přesný gh auth login/refresh příkaz pro požadovanou capability."
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
- may open the Project as a convenience unless disabled by script parameters; opening the Project is not a substitute for programmatic mutation/read-back.

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
Project: DDDA Platform Backlog & Delivery
Visibility: PUBLIC
Repository: romanhlavac/ddd-accelerator
```

Items include:

- all governed Work Package and Change Request Issues required by the versioned mapping;
- every open implementation Pull Request as a delivery projection;
- PR #8 only through its explicit versioned WP-08 legacy exception until merge/close.

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

Create/verify exactly the canonical machine-managed views:

1. `Plánování a Backlog` — table, filter `is:issue`;
2. `Implementace a Delivery` — table, filter `is:pr is:open`.

The planning view contains WP/CR planning items. The delivery view contains all currently open implementation PRs. A PR Project item is a delivery projection, not backlog authority; its `Work Package` is derived from the primary CR and planning `Item Type` remains unset.

Optional analyst views may be created manually, but are not part of the versioned invariant and must not replace these two views.

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
- all governed planning items, all open delivery PR items, required fields and both canonical views exist;
- #10/#11/#13 are Done;
- #45 is outside Milestone 0.1.0;
- Milestone contains only PR #8 and Issues #9–#15;
- no dates, priority, release or human approval were invented;
- no merge/rebase/promotion occurred.

The selected execution route must also prove:

- authenticated actor/capability after any browser/device authorization;
- fresh Project/native GitHub read-back after mutation;
- no PAT/OAuth token in report, artifact, PR comment, Chat-facing evidence or Git history;
- authorization did not create Human Review/merge/release/tag approval.

## Evidence

The automation writes a setup report. Publish/attach the reviewed result to #42 with:

- current governance branch SHA;
- Project URL;
- hierarchy/dependency results;
- Milestone membership;
- selected GitHub capability provider and non-secret authorization state;
- actor/capability verification when `HUMAN_BOOTSTRAP_ONLY` was used;
- warnings/unsupported operations;
- any deliberate deviation from versioned configuration.

Do not commit local reports automatically and do not interpret technical PASS or authorization success as Human Review PASS.
