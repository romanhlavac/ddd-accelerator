---
name: ddda-github-project-v2-governance
description: Mandatory operating instructions for DDDA GitHub Project V2 backlog administration, CR/WP consistency, GitHub CLI/GraphQL execution and safe browser/device authorization.
---

# DDDA GitHub Project V2 Governance Skill

## 1. Activation and authority

Load this skill together with `ddda-platform-development-skill.md` whenever the task touches any of the following:

- GitHub Project `DDDA Platform Backlog`;
- Work Package / Change Request hierarchy;
- adding, removing or reconciling backlog items;
- Project V2 fields, views or item metadata;
- consistency between GitHub Issues and the Project backlog;
- GitHub Project automation or authorization.

Canonical supporting sources:

- `config/governance/backlog-policy.yaml`
- `config/governance/github-bootstrap.json`
- `docs/governance/native-github-setup-runbook.md`
- `docs/governance/project-administration-checklist.md`
- `scripts/platform/Initialize-DDDAGitHubGovernance.ps1`
- `scripts/platform/Apply-DDDAGitHubGovernance.ps1`

GitHub Issues and native relationships are authoritative for work-item identity and parent/child structure. GitHub Project V2 is the planning projection. Versioned governance files are the reproducible configuration contract. None of these layers may be silently treated as interchangeable.

## 2. Never confuse connector limits with GitHub capability

A connected GitHub App/connector that does not expose a direct `Projects V2 write` action is **not evidence that the Project cannot be changed**.

Before claiming that Project V2 administration is unavailable or asking the user to perform it manually, try the approved DDDA path:

```text
existing versioned DDDA governance automation
→ GitHub CLI (`gh`)
→ user authorization with `project` scope when required
→ `gh project ...` and/or `gh api graphql`
→ live Project V2 read-back
```

Only after this path has actually been attempted and has failed for a concrete reason may the task be reported as blocked.

Do not make the user repeatedly remind the runtime that this fallback exists.

## 3. Preferred execution order

For a Project/backlog mutation:

1. Read the current repository, Issue, WP and PR state through the connected GitHub source.
2. Load the exact current DDDA platform-development skill and this skill.
3. Check whether the repository already contains a supported governance script/workflow that performs the requested operation.
4. Prefer the stable versioned governance script over ad-hoc GraphQL.
5. If Project V2 write authorization is missing, obtain user `project` scope through GitHub CLI browser/device authorization.
6. Apply only the requested deterministic Project/relationship mutations.
7. Perform a live read-back from Project V2 and native Issue relationships.
8. Reconcile the versioned governance configuration/roadmap when the live governance model changed.
9. Validate the resulting Git commit when repository files changed.
10. Never merge/publish/promote merely because backlog administration succeeded.

## 4. GitHub Project V2 authorization

User-owned Project V2 operations normally require a user authorization that includes the `project` scope. Repository `GITHUB_TOKEN` permissions and a GitHub App installation token may be sufficient for repository Issues while still being insufficient for the user's Project V2.

Do not assume permission either way; probe the operation.

Approved GitHub CLI authorization paths are:

```powershell
gh auth refresh -s project
```

for an existing CLI login, or:

```text
gh auth login --hostname github.com --git-protocol https --web --scopes project
```

for a fresh browser/device flow.

Security rules:

- never ask the user to paste a GitHub token/PAT into Chat or Work;
- never print or publish the resulting OAuth token;
- only the short-lived verification URL and device code may be surfaced to the user;
- a device code is an authorization challenge, not a reusable credential;
- keep runner authorization ephemeral unless a separately approved secret-storage design exists;
- never commit `hosts.yml`, tokens, cookies or CLI credential stores;
- delete or expire any temporary device-code artifact as soon as practical.

If a remote GitHub Actions runner is used and the running job's log cannot be read interactively, a short-lived private Actions artifact may carry **only** the verification URL and device code. It must never carry the authenticated token.

## 5. Project V2 mutation mechanism

Use the highest-level `gh project` command that expresses the operation. Use `gh api graphql` when Project V2 functionality or field mutation is not adequately exposed by the CLI command.

Typical operations include:

```text
gh project list

gh project item-add

gh project item-edit

gh api graphql
```

For GraphQL writes, resolve stable node IDs immediately before mutation; do not hard-code transient Project item IDs into long-lived methodology unless they are explicitly versioned external identifiers.

Every mutation must be followed by a query/read-back that proves the expected Project item and field values actually exist.

A successful mutation response without read-back is not sufficient evidence.

## 6. DDDA backlog consistency contract

A DDDA Change Request is consistent only when all applicable layers agree:

```text
GitHub Issue
  ↓
native WP parent/sub-issue relationship
  ↓
DDDA Platform Backlog membership
  ↓
Project V2 fields
  ↓
versioned governance config / roadmap
```

For every CR, check at minimum:

- it is a GitHub **Issue**, not a placeholder Pull Request;
- it has exactly one intended WP parent when the CR belongs to a WP;
- it is present in `DDDA Platform Backlog` unless explicitly excluded by governance policy;
- `Item Type = Change Request`;
- `Work Package` matches the native parent WP;
- a closed CR has Project `Status = Done`;
- an open CR has a valid non-Done status;
- configured deterministic fields match `github-bootstrap.json` when the CR is present there;
- title prefix, native parent and versioned WP mapping do not contradict each other;
- milestone/Target Release follows explicit release planning and is not inferred merely from issue age or implementation activity.

Precedence for resolving an unambiguous WP conflict:

```text
1. native parent/sub-issue relationship
2. explicit versioned governance mapping
3. title prefix / prose reference
```

If the native parent and versioned mapping disagree and intent cannot be established mechanically, fail closed rather than moving the CR to a guessed WP.

## 7. Safe automatic reconciliation

The runtime may automatically repair mechanical inconsistencies when intent is deterministic, including:

- add a missing CR to the configured Project;
- set `Item Type = Change Request`;
- set `Work Package` to the already-established native WP parent;
- set `Status = Done` for a closed Issue;
- add a missing native parent relationship when the versioned policy and Issue semantics establish one unambiguously;
- update versioned hierarchy/item groups after the live model is intentionally changed;
- normalize a title prefix when native parent + versioned mapping already establish the WP and the title alone is stale.

Do **not** automatically invent or change judgment-heavy planning values such as:

- Priority;
- Start date / Target date;
- release Milestone or `Target Release`, unless explicitly configured/authorized;
- Human Review PASS;
- gate approval;
- HRDR;
- GO/NO-GO;
- strategic sequencing.

Those require an explicit decision or an already-versioned deterministic policy.

## 8. Meaning of “add this to the backlog”

For DDDA, creating an Issue alone does not complete a request to add something to the project backlog.

Unless the user explicitly asks only for an Issue, complete the full applicable projection:

```text
create/update CR Issue
→ attach native WP parent
→ add to DDDA Platform Backlog
→ set deterministic Project metadata
→ update versioned governance mapping/roadmap as required
→ read back all layers
```

Do not state “added to backlog” before Project membership has been verified.

A Pull Request that implements a CR is not a second backlog CR unless the planning model explicitly requires PR items in the Project. Keep `CR Issue` and `implementation PR` conceptually separate.

## 9. Active PR isolation

Backlog administration must not invalidate an unrelated active platform FAST-LOOP or exact-SHA review.

If the active PR is undergoing exact-SHA CI/HVR/remediation:

- do not move that PR's source branch merely to change Project/backlog governance;
- apply Project V2/native Issue administration directly outside the PR source tree when possible;
- put versioned governance/skill changes on the dedicated governance branch or a separate stacked Draft PR;
- rebase/retarget after the active PR is stable or merged;
- never present evidence from the old SHA as valid for a newly moved active PR head.

## 10. One-shot GitHub Actions control-plane fallback

A one-shot workflow is a fallback for Chat/Work when no existing supported self-service workflow can perform a required GitHub control-plane operation.

It requires explicit human authorization and must be narrowly scoped.

Required controls:

- run only on a dedicated governance/staging branch, never `main` and never an unrelated active FAST-LOOP branch;
- declare minimum repository permissions;
- use browser/device authorization for user `project` scope instead of embedding a PAT;
- mutate only explicitly targeted Issues/Project items/fields;
- read back the live result before reporting PASS;
- preserve no reusable OAuth credential in Git or artifacts;
- remove the staging workflow after successful completion;
- commit any intended versioned governance updates in a normal reviewable commit;
- failure before read-back is overall failure and must leave enough diagnostics to retry safely.

Do not create a new one-shot workflow when an existing DDDA governance script/workflow can be safely extended or invoked.

## 11. CR ↔ Project audit procedure

When asked to check all CRs against the project backlog, perform a repository-wide audit rather than checking only recently discussed Issues.

Discovery should include open and closed repository Issues whose role is Change Request, using title/template/body metadata and versioned governance mappings. Exclude Pull Requests from the CR set.

For each CR produce/check:

```text
issue number + state
expected WP
native parent
Project membership
Item Type
Work Package field
Project Status
configured deterministic metadata
versioned hierarchy/item-group presence
inconsistency classification
repair action / no action
```

Classify findings at least as:

```text
PASS
MISSING_PROJECT_ITEM
MISSING_PARENT
WP_MISMATCH
ITEM_TYPE_MISMATCH
STATUS_MISMATCH
VERSIONED_CONFIG_MISSING
VERSIONED_CONFIG_CONFLICT
AMBIGUOUS_REQUIRES_DECISION
```

Repair all deterministic findings in the same governed operation and rerun the audit. Final evidence must distinguish `found`, `repaired`, and `remaining ambiguous` counts.

## 12. Evidence and completion

Project/backlog work is complete only when evidence identifies:

- repository;
- Project title/number;
- affected Issue/CR numbers;
- native parent state;
- Project item membership;
- relevant field read-back;
- versioned governance commit SHA when Git files changed;
- temporary authorization/control-plane cleanup state;
- any intentionally unresolved judgment-heavy fields.

Never report a Project V2 write as complete based only on an Issue update, an assumed automation trigger or a workflow step that did not perform final read-back.
