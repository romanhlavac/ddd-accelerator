# ADR 0010: GitHub capability routing and browser/device authorization

Status: Proposed — pending Human Review

Date: 2026-08-21

## Context

DDDA platform development uses Chat/Work for orchestration and GitHub Actions for authoritative execution. In practice, the connected GitHub surface, repository `GITHUB_TOKEN`, the canonical DDDA broker, dedicated governance credentials, GitHub CLI and GitHub REST/GraphQL expose different capability sets.

A recurring failure mode was to treat a missing connector mutation as if GitHub itself could not perform the operation. That pushed deterministic administration work — especially GitHub Project V2 changes — back to the human through the GitHub GUI even when an approved programmatic route existed after one-time OAuth consent.

For repository-wide Project governance, an additional gap exists: the repository already has a canonical secret-bearing workflow `.github/workflows/reconcile-ddda-project-backlog.yml` using the approved `ddda-backlog-governance` environment and persistent Project credential, but Chat/Work has no direct Project V2 or workflow-dispatch surface. Requiring a person to click Run workflow for each reconciliation would violate the operating model, while exposing the Project credential to Chat/Work or duplicating reconciliation logic in the broker would weaken the security boundary.

The desired quality attributes are:

- autonomous mechanical orchestration;
- least privilege;
- auditability;
- explicit trust and authorization boundaries;
- fail-closed behavior;
- no credential disclosure;
- exact-SHA and source identity;
- serialization of privileged Project mutation;
- clear separation of authorization from judgment-heavy governance decisions.

## Decision

DDDA adopts capability-first routing for deterministic GitHub operations.

```text
CONNECTOR
→ CANONICAL_BROKER_OR_DEDICATED_CREDENTIAL
→ HUMAN_BOOTSTRAP_ONLY
→ UNAVAILABLE
```

The operation is classified by the capability it needs before scopes or credentials are selected.

### Connector first

When the approved GitHub connector exposes the required capability and permission, use it directly.

### Canonical broker or dedicated credential second

When the connector surface lacks the operation, use the canonical DDDA broker or an approved dedicated credential route if it exposes the capability. A connector limitation is not evidence that the GitHub capability is unavailable.

### Browser/device authorization only for missing user consent

`HUMAN_BOOTSTRAP_ONLY` is used only when a programmatic CLI/API route exists and the sole missing prerequisite is user OAuth consent or an additional least-privilege scope.

The orchestration initiates the browser/device flow when possible. The human performs only the GitHub consent challenge. After consent, the execution plane verifies actor and capability and continues programmatically.

### Fail closed only after route exhaustion

`UNAVAILABLE` is used only when connector, canonical broker/dedicated credential and an authorizable CLI/API route cannot satisfy the capability. The failure includes a concrete non-secret capability diagnosis.

## Mechanical GUI invariant

```text
NO_MANUAL_GITHUB_GUI_FOR_MECHANICAL_OPERATIONS
```

A human must not be instructed to mechanically edit Issues, Pull Requests, Project fields or workflows through GitHub GUI merely because the current connector does not expose the mutation.

This does not prohibit GitHub web pages as the human surface for OAuth consent, Human Review, merge authorization or another explicit governance decision.

## Permanent Project V2 reconciliation transport

For repository-wide `DDDA Platform Backlog & Delivery` reconciliation, DDDA standardizes the following permanent route:

```text
Chat / Work
→ GitHub connector
→ exact allowlisted PR comment
→ trusted default-branch DDDA broker
→ canonical reconciliation workflow dispatch
→ GitHub Actions environment ddda-backlog-governance
→ existing persistent Project credential
→ reconcile + fresh live read-back
→ zero remaining mismatches
→ audit artifact + broker evidence
```

The command is exactly:

```text
/ddda reconcile-project --expected-sha <40-char-current-pr-head-sha>
```

The broker validates allowed actor, same-repository PR and live PR head. `--expected-sha` must equal the live PR head before dispatch. Extra arguments, shell fragments, workflow names and alternate refs are rejected.

The only dispatch target is:

```text
.github/workflows/reconcile-ddda-project-backlog.yml
```

and its canonical source ref is `main`. Workflow identity is policy-controlled, never user-controlled.

### Credential boundary

The Project credential remains solely in the existing GitHub Actions environment `ddda-backlog-governance` and is consumed by the canonical workflow. It is not made available to Chat, Work or the broker job, and it must not appear in logs, artifacts, comments or Git history.

The broker receives only repository-level permission needed to dispatch/read the allowlisted Actions workflow. `actions: write` is isolated to the dedicated `reconcile-project` job. The broker does not receive a generic remote shell and does not implement Project GraphQL reconciliation itself.

No second Project credential is introduced unless a future separate ADR demonstrates a concrete need.

### Source identity and serialization

Before dispatch the broker:

1. reconfirms the exact PR head against `--expected-sha`;
2. waits for any existing queued/in-progress canonical reconciliation run to finish;
3. resolves current `main` to an exact source SHA;
4. dispatches exactly one canonical workflow;
5. binds the discovered run to that source SHA.

Broker-triggered Project reconciliation jobs also share a non-cancelling concurrency group. If the source SHA changes before evidence is accepted, the old run is not presented as current; after serialization, a bounded retry resolves and executes against the new source identity.

### Evidence contract

A successful broker result is accepted only if:

- the child workflow conclusion is `success`;
- its `head_sha` equals the resolved reconciliation source SHA;
- current `main` still equals that source when evidence is accepted;
- exactly one non-expired canonical audit artifact exists for that source SHA;
- `audit.json`, `presentation.json` and `release-planning.json` all carry that source SHA;
- every `remaining_count` is zero.

Evidence identifies at minimum repository, PR, requested actor, authorized PR head, explicit expected SHA, canonical workflow, source SHA, child run ID/conclusion, audit artifact ID/name and remaining mismatch count.

Authorization or reconciliation technical PASS does not create Human Review, merge, release/promotion or tag authorization.

## Authorization commands

For an existing GitHub CLI login missing a required scope:

```powershell
gh auth refresh -s <required-scope>
```

For a fresh browser/device login:

```powershell
gh auth login --hostname github.com --git-protocol https --web --scopes <required-scopes>
```

Scopes are derived from the requested capability. For a user-owned Project V2 mutation, `project` is a typical scope only when the selected live route actually requires it.

For normal DDDA Project reconciliation this local OAuth path is not the operating mechanism once the approved persistent workflow credential is healthy. Browser/device authorization is a one-time bootstrap/recovery mechanism only; it is never repeated per reconciliation.

## Runtime/session boundary

A local GitHub CLI credential is local state. DDDA must never pretend that a credential created in the human's local browser/CLI session is automatically available to a separate ChatGPT connector or cloud runner.

If direct same-runtime browser/device authorization is unavailable, the human receives at most one exact local bootstrap command. If no approved session bridge exists, the orchestration diagnoses that gap and prefers the permanent canonical broker/dedicated-credential solution rather than manual GitHub GUI mutation.

For a persistent workflow credential, provisioning or rotation must end in the approved GitHub secret store without exposing the value to Chat/Work. If the existing workflow proves the credential is healthy, no bootstrap is requested.

## Security

- no PAT/token is requested in Chat/Work;
- OAuth tokens are never printed into evidence;
- `gh auth token` is not used as a token-disclosure/evidence mechanism;
- device code/verification URL are authorization challenges only;
- least privilege and ephemeral authorization are preferred for human bootstrap;
- persistent credentials exist only in an approved secret store;
- no generic remote shell is introduced;
- the broker cannot dispatch arbitrary workflow identity or user-selected ref;
- Project reconciliation logic and Project credential remain in the canonical workflow/environment;
- fresh actor/capability verification and live mutation read-back are mandatory.

## Governance separation

Authorization success does not imply:

- Human Review PASS;
- merge authorization;
- Human Release Decision;
- release/promotion authorization;
- tag authorization.

A zero-mismatch Project reconciliation also does not imply any of these decisions.

## Default-branch activation constraint

GitHub `issue_comment` execution uses the workflow definition on the default branch. Therefore a new broker command implemented only in an unmerged PR cannot be demonstrated through the production connector-comment path until that reviewed broker definition is activated on default branch, unless a separately authorized platform bootstrap mechanism exists.

This is a deployment/control-plane constraint, not a reason to bypass governance by direct-main write, manual Project mutation or arbitrary workflow dispatch. Pre-merge exact-SHA CI must validate the implementation contract; live production broker E2E occurs only after an approved activation boundary.

## Options considered

### A. Connector-only execution

Rejected. It makes connector product-surface gaps indistinguishable from GitHub capability gaps and creates unnecessary manual work.

### B. Manual GitHub GUI fallback

Rejected for deterministic operations. It is difficult to reproduce, weakens auditability and makes the human a mechanical workflow engine.

### C. Persistent broad PAT available to Chat/Work

Rejected. It violates the existing secret boundary and least-privilege model.

### D. Broker receives Project token and performs reconciliation itself

Rejected. It duplicates canonical reconciliation logic, expands the credential trust boundary and makes the broker a privileged Project executor.

### E. Generic workflow-dispatch broker

Rejected. User-controlled workflow identity would create a broad execution primitive and unnecessary command-injection surface.

### F. Capability-first routing plus fixed canonical Project workflow broker

Accepted as the proposed direction. It preserves connector-first operation, reuses the existing approved secret-bearing workflow, confines `actions: write`, provides exact identity/evidence and keeps human browser consent as bootstrap/recovery only.

## Consequences

Positive:

- fewer false human blockers;
- Project V2 and similar connector gaps can use approved alternate programmatic routes;
- repeated Project reconciliation no longer requires mechanical GitHub GUI actions;
- Chat/Work never needs the Project credential;
- OAuth consent is separated from the actual mechanical mutation;
- scope requests become capability-driven and least-privilege;
- actor, exact PR SHA, source SHA, child run and audit evidence are explicit;
- human governance boundaries remain intact.

Negative:

- the orchestration must model multiple GitHub providers;
- repository `actions: write` is required on one dedicated broker job;
- runtime/session separation can still prevent reuse of a locally bootstrapped credential;
- default-branch activation prevents a new `issue_comment` command from proving itself through production comment E2E before approved activation;
- broker and dedicated-credential routes require ongoing capability governance;
- GitHub scope/API semantics can drift and require integration validation.

## Compatibility

The change is additive governance hardening. It does not change DDDA project workspaces, release artifacts or the canonical merge/release authorization boundaries. The existing Project reconciliation workflow remains the sole reconciliation implementation and keeps its existing Project credential/environment boundary.

## Validation

Automated contract/regression coverage must prove at minimum:

- valid allowed actor + exact SHA + canonical command authorizes reconciliation;
- SHA mismatch fails before dispatch;
- unauthorized actor fails;
- fork/wrong repository fails;
- unsupported command fails;
- arbitrary workflow identity cannot be supplied;
- extra args/command injection fail;
- Project credential is unavailable to Chat/Work and broker evidence;
- broker dispatches only the canonical Project reconciliation workflow;
- child workflow failure cannot produce broker PASS;
- child run/source SHA mismatch is rejected;
- accepted success exposes child run ID and audit artifact identity;
- audit evidence requires zero remaining mismatches;
- authorization/reconciliation PASS does not create Human Review, merge, release or tag approval;
- browser authorization is documented and modeled as one-time bootstrap/recovery, not a recurring operating step;
- route exhaustion yields `UNAVAILABLE` with capability diagnosis;
- the connector-missing Project V2 failure mode does not result in manual Project GUI instructions.

## Decision ownership

Technical validation of this ADR does not accept it. The operating-model and security trade-off must be explicitly judged in Human Review of the implementing PR. Merge authorization remains a later and separate decision.
