# ADR 0010: GitHub capability routing and browser/device authorization

Status: Proposed — pending Human Review

Date: 2026-08-21

## Context

DDDA platform development uses Chat/Work for orchestration and GitHub Actions for authoritative execution. In practice, the connected GitHub surface, repository `GITHUB_TOKEN`, the canonical DDDA broker, dedicated governance credentials, GitHub CLI and GitHub REST/GraphQL expose different capability sets.

A recurring failure mode was to treat a missing connector mutation as if GitHub itself could not perform the operation. That pushed deterministic administration work — especially GitHub Project V2 changes — back to the human through the GitHub GUI even when an approved programmatic route existed after one-time OAuth consent.

The desired quality attributes are:

- autonomous mechanical orchestration;
- least privilege;
- auditability;
- explicit trust and authorization boundaries;
- fail-closed behavior;
- no credential disclosure;
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

## Runtime/session boundary

A local GitHub CLI credential is local state. DDDA must never pretend that a credential created in the human's local browser/CLI session is automatically available to a separate ChatGPT connector or cloud runner.

If direct same-runtime browser/device authorization is unavailable, the human receives at most one exact local bootstrap command. If no approved session bridge exists, the orchestration diagnoses that gap and prefers a canonical broker/dedicated-credential solution rather than manual GitHub GUI mutation.

## Security

- no PAT/token is requested in Chat/Work;
- OAuth tokens are never printed into evidence;
- `gh auth token` is not used as a token-disclosure/evidence mechanism;
- device code/verification URL are authorization challenges only;
- least privilege and ephemeral authorization are preferred;
- persistent credentials exist only in an approved secret store;
- no generic remote shell is introduced;
- fresh actor/capability verification and live mutation read-back are mandatory.

## Governance separation

Authorization success does not imply:

- Human Review PASS;
- merge authorization;
- Human Release Decision;
- release/promotion authorization;
- tag authorization.

## Options considered

### A. Connector-only execution

Rejected. It makes connector product-surface gaps indistinguishable from GitHub capability gaps and creates unnecessary manual work.

### B. Manual GitHub GUI fallback

Rejected for deterministic operations. It is difficult to reproduce, weakens auditability and makes the human a mechanical workflow engine.

### C. Persistent broad PAT available to Chat/Work

Rejected. It violates the existing secret boundary and least-privilege model.

### D. Capability-first routing with authorization-only human bootstrap

Accepted as the proposed direction. It preserves connector-first operation, reuses the canonical broker, uses browser/device consent only when needed and fails closed only after all approved programmatic routes are exhausted.

## Consequences

Positive:

- fewer false human blockers;
- Project V2 and similar connector gaps can use approved alternate programmatic routes;
- OAuth consent is separated from the actual mechanical mutation;
- scope requests become capability-driven and least-privilege;
- actor/read-back evidence becomes explicit;
- human governance boundaries remain intact.

Negative:

- the orchestration must model multiple GitHub providers;
- runtime/session separation can still prevent reuse of a locally bootstrapped credential;
- broker and dedicated-credential routes require ongoing capability governance;
- GitHub scope/API semantics can drift and require integration validation.

## Compatibility

The change is additive governance hardening. It does not change DDDA project workspaces, release artifacts or the canonical merge/release authorization boundaries.

## Validation

Automated contract/regression coverage must prove at minimum:

- connector support bypasses browser authorization;
- broker support bypasses browser authorization;
- missing user OAuth consent yields `HUMAN_BOOTSTRAP_ONLY`, not a generic blocker;
- human interaction is consent-only;
- actor/capability verification follows authorization;
- Project V2 mutation requires live read-back;
- token/PAT leakage channels are forbidden;
- authorization does not imply Human Review/merge/release/tag authorization;
- route exhaustion yields `UNAVAILABLE` with capability diagnosis;
- the connector-missing / authorized `gh` or GraphQL Project V2 failure mode does not result in manual Project GUI instructions.

## Decision ownership

Technical validation of this ADR does not accept it. The operating-model and security trade-off must be explicitly judged in Human Review of the implementing PR. Merge authorization remains a later and separate decision.
