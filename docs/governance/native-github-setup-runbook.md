# Native GitHub setup runbook

## Purpose

This runbook creates the live GitHub structures that repository files alone cannot activate:

- native Parent/Sub-issue relationships;
- native `Blocked by` / `Blocking` dependencies;
- GitHub Project, custom fields, items and initial metadata;
- Project views;
- Milestone and release-scope assignments.

The authoritative execution/evidence Issue is #42.

## Automation-first rule

Do not perform the setup item-by-item in the GitHub UI unless the automation reports a specific unsupported or failed operation.

Authoritative automation:

```text
scripts/platform/Initialize-DDDAGitHubGovernance.ps1
config/governance/github-bootstrap.json
```

The script is idempotent: it reads the current GitHub state and adds only missing relationships, fields, items, views and milestone assignments.

## Prerequisites

Use a current GitHub CLI version that supports:

- `gh issue edit --add-sub-issue`;
- `gh issue edit --add-blocked-by`;
- `gh project` commands.

Verify authentication:

```powershell
gh --version
gh auth status
```

If Project access is missing, authorize it once:

```powershell
gh auth refresh -s project
```

This browser authorization is the only potentially unavoidable pre-run interaction.

## Recommended execution

Run from the repository root after checking out Draft PR #43 or its branch:

```powershell
git fetch origin
git switch feature/github-native-backlog-governance
git pull --ff-only
```

First inspect the plan:

```powershell
.\scripts\platform\Initialize-DDDAGitHubGovernance.ps1
```

Apply the setup and open the resulting Project:

```powershell
.\scripts\platform\Initialize-DDDAGitHubGovernance.ps1 -Apply -OpenProject
```

The script writes a local evidence report:

```text
ddda-github-governance-setup-YYYYMMDD-HHMMSS.md
```

Do not commit this local report automatically. Attach or summarize it in Issue #42 after review.

## What the script performs

### Native hierarchy

```text
WP-08 #17 → #9–#15
WP-09 #18 → #21–#26
WP-10 #19 → #27–#33
WP-11 #20 → #34–#41
```

PR #8 and Draft PR #43 remain implementation links, not Sub-issues.

### Native dependencies

The complete dependency graph is read from:

```text
config/governance/github-bootstrap.json
```

It includes the WP-08 remediation critical path and the planned dependency graphs for WP-09 through WP-11.

### GitHub Project

The script creates or reuses:

```text
Owner: romanhlavac
Project: DDDA Platform Backlog
Visibility: PUBLIC
Repository link: romanhlavac/ddd-accelerator
```

It adds:

- PR #8;
- Issues #9–#42;
- Draft PR #43;
- Issue #44.

### Fields

The script creates or normalizes:

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
- `Blocked`;
- `Human Review`;
- `Dependency`.

GitHub Projects does not provide a custom Boolean field in the required CLI/API contract, so `Blocked` is a single-select field with `No` and `Yes`.

Ownership uses the native `Assignees` system field rather than a duplicate custom Person field.

The script intentionally leaves Priority, Start date and Target date empty unless explicitly configured later.

### Initial metadata

The script sets:

- WP-08 as Blocked with Target Release `0.1.0` and Human Review Pending;
- WP-09 through WP-11 as Backlog with Target Release `TBD`;
- children under the matching Work Package;
- PR #8 under WP-08;
- Draft PR #43 and governance items under `Other`;
- completed/closed items to `Done` when their current GitHub state is closed or merged.

### Views

The script attempts to create:

1. `Work Packages`;
2. `WP hierarchy`;
3. `Delivery board`;
4. `Roadmap by Work Package`;
5. `Release scope`;
6. `Blocked and P0`;
7. `Human review queue`;
8. `Ready without owner`;
9. `Recently completed`.

The current GitHub API can create views and basic filters. Some advanced UI settings still require a short manual finalization; see below.

### Milestone

The script creates or reuses:

```text
DDDA 0.1.0
```

and assigns:

- PR #8;
- Issues #9–#15.

It deliberately does not assign Parent WP #17, WP-09 through WP-11 or Draft PR #43.

## Remaining manual steps after a successful run

These are the only expected manual Project actions.

### 1. Finish view configuration

Open `DDDA Platform Backlog` and configure the created views:

#### Work Packages

```text
Layout: Table
Filter: Item Type = Work Package
Visible fields:
  Title
  Outcome summary
  Status
  Priority
  Sub-issue progress
  Start date
  Target date
  Target Release
  Human Review
```

#### WP hierarchy

```text
Layout: Table
Group by: Parent issue
Visible fields:
  Title
  Parent issue
  Status
  Priority
  Blocked
  Dependency
  Target Release
  Linked pull requests
```

#### Delivery board

```text
Layout: Board
Column field: Status
Visible fields:
  Priority
  Work Package
  Assignees
  Target Release
  Blocked
```

#### Roadmap by Work Package

```text
Layout: Roadmap
Start field: Start date
Target field: Target date
Group by: Work Package
Milestone markers: enabled
Unscheduled items: visible
```

#### Release scope

```text
Layout: Table
Group by: Milestone
Visible fields:
  Title
  Milestone
  Status
  Priority
  Work Package
  Human Review
  Blocked
  Linked pull requests
```

For the remaining views, verify the generated filter and select useful visible fields. Save every changed view.

### 2. Configure safe built-in workflows

In Project settings, enable only mechanical workflows such as:

- item added → Backlog;
- closed Issue → Done;
- reopened Issue → Triaged;
- merged PR → Done.

Never automate:

- Priority;
- Target Release or Milestone;
- Start/Target dates;
- Human Review PASS;
- gate `passed`;
- HRDR or GO/NO-GO;
- closing a Parent WP after one PR merge.

### 3. Verify release scope

Confirm that Milestone `DDDA 0.1.0` contains exactly the intended release candidates:

- PR #8;
- Issues #9–#15.

It must not contain Parent WP #17, WP-09 through WP-11 or PR #43 unless a later explicit release decision changes the scope.

### 4. Record evidence

Attach or summarize the generated setup report in Issue #42 and record:

- Project URL;
- any warnings or failed automated actions;
- confirmation of hierarchy and dependencies;
- confirmation of Milestone scope;
- screenshots only where they add useful evidence;
- any deliberate deviation from the versioned configuration.

## Verification commands

```powershell
gh issue view 17 -R romanhlavac/ddd-accelerator --json subIssues,subIssuesSummary
gh issue view 18 -R romanhlavac/ddd-accelerator --json subIssues,subIssuesSummary
gh issue view 23 -R romanhlavac/ddd-accelerator --json parent,blockedBy,blocking
gh issue view 33 -R romanhlavac/ddd-accelerator --json parent,blockedBy,blocking
gh issue view 41 -R romanhlavac/ddd-accelerator --json parent,blockedBy,blocking
gh project list --owner romanhlavac
gh project field-list <PROJECT_NUMBER> --owner romanhlavac
gh project item-list <PROJECT_NUMBER> --owner romanhlavac --limit 100
```

Before closing #42, verify that:

- every child has the expected native parent;
- every configured dependency is visible;
- all fields and nine views exist;
- Parent WP progress is visible;
- the Roadmap contains no fabricated dates;
- the Milestone scope is correct;
- no human approval is automated.
