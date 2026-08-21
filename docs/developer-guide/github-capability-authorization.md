# GitHub capability routing and browser/device authorization

## Purpose and authority

This runbook defines the canonical DDDA routing contract for deterministic GitHub operations when Chat/Work needs a capability that may or may not be exposed by the connected GitHub surface.

Machine-readable authority:

```text
config/platform/github-capability-routing.json
```

Decision record:

```text
docs/adr/0010-github-capability-authorization-routing.md
```

This runbook refines the platform-development operating model; it does not create a second development skill and does not authorize merge, promotion, release or tag operations.

## Core invariant

```text
NO_MANUAL_GITHUB_GUI_FOR_MECHANICAL_OPERATIONS
```

If a GitHub operation is deterministic and programmatically available through an approved route, the orchestration performs it programmatically. A missing connector mutation is not by itself a human blocker and is not a reason to tell the human to edit Issues, Pull Requests, Project fields, workflows or other GitHub state through the web UI.

The human is asked to perform a mechanical GitHub GUI mutation only if a separate governance contract explicitly makes that GUI action the actual human decision surface. Lack of an API/connector button is not such a decision.

## Capability-first routing

Determine the required GitHub capability before deciding which credential or scope is needed.

Canonical provider order:

```text
A. CONNECTOR
   capability is exposed by the approved connected GitHub surface
   → use connector

B. CANONICAL_BROKER_OR_DEDICATED_CREDENTIAL
   connector surface lacks the capability
   → use the canonical DDDA broker or an approved dedicated credential route

C. HUMAN_BOOTSTRAP_ONLY
   a programmatic CLI/API route exists and the only missing prerequisite is user OAuth consent/scope
   → initiate browser/device authorization
   → human performs consent only
   → verify actor + capability
   → continue programmatically

D. UNAVAILABLE
   connector, canonical broker/dedicated credential and an authorizable CLI/API route cannot satisfy the capability
   → fail closed with concrete capability diagnosis
```

`HUMAN_BOOTSTRAP_ONLY` is an explicit non-terminal orchestration state. It is not a generic blocker. `UNAVAILABLE` is the terminal capability blocker.

## Connector versus GitHub capability

The connected ChatGPT GitHub surface and GitHub itself are different capability sets.

Examples:

- connector can expose repository Issues/PR/Git operations directly;
- connector may not expose a Project V2 mutation even though `gh project` or GitHub GraphQL can perform it;
- a workflow operation may be available through the canonical broker while not being exposed as a connector action;
- a dedicated governance credential can have a privileged capability that the regular connector or repository `GITHUB_TOKEN` intentionally lacks.

Therefore:

```text
connector operation missing
≠ GitHub capability unavailable
≠ human must use GitHub GUI
```

## Scope derivation

Do not hard-code a broad scope set before knowing the required capability.

Process:

```text
required operation
→ required GitHub capability
→ selected provider
→ least-privilege authorization needed by that provider
```

For a user-owned GitHub Project V2 mutation, `project` is a typical GitHub CLI OAuth scope, but request it only when live GitHub semantics and the selected route actually require it.

Similarly, do not request workflow or repository scopes merely because they are commonly useful. Derive them from the operation being executed.

## Browser/device authorization

Browser/device authorization is used only for `HUMAN_BOOTSTRAP_ONLY`.

Existing authenticated CLI login missing one scope:

```powershell
gh auth refresh -s <required-scope>
```

Fresh login:

```powershell
gh auth login --hostname github.com --git-protocol https --web --scopes <required-scopes>
```

The orchestration initiates the flow when its execution environment supports it. The human receives only the verification URL/device code and the GitHub consent challenge necessary to authorize the requested least-privilege capability.

Allowed human actions are limited to:

1. open the verification URL;
2. enter a device code if GitHub requests it;
3. approve the OAuth consent;
4. confirm that authorization completed.

The human is not asked in the same bootstrap to:

- open a Project and edit fields;
- find an Issue and change metadata;
- click a workflow Run button;
- manually create a Project item;
- perform another deterministic GitHub mutation that the authorized CLI/API route can execute.

## Runtime/session boundary

If Chat/Work can initiate a `gh` browser/device flow in the same execution environment that will subsequently use the authenticated session:

```text
initiate authorization
→ show only verification URL/device code
→ wait for consent confirmation
→ verify actor/capability
→ continue automatically
```

If the current runtime cannot initiate the flow, provide at most one exact local bootstrap command for the required capability.

That local command is useful only when the resulting authenticated session is available to the execution plane that will perform the operation. A credential created in the human's local `gh` credential store must never be represented as automatically available to a separate cloud runner, ChatGPT connector or GitHub Actions runner.

If no approved session bridge exists, report that exact capability gap and use or design the canonical broker/dedicated-credential route instead of sending the human into GitHub GUI administration.

## Post-authorization verification

A successful OAuth page is not operational evidence by itself.

Before the first privileged operation, verify at minimum:

```text
authenticated actor
required capability / effective scope
repository or Project target identity
```

Use `gh auth status` or an equivalent non-secret API probe. Never use `gh auth token` in a way that prints a token into logs or evidence.

After the mechanical mutation, perform a fresh live read-back from GitHub. A successful mutation response without read-back is incomplete.

For Project V2 this means reading the Project item and the relevant field value after the mutation. Repository-wide governance reconciliation retains its stricter `remaining_mismatches = 0` requirement where applicable.

## Security contract

Mandatory rules:

- never ask the human to paste a PAT or OAuth token into Chat/Work;
- never print or persist the OAuth token in Chat, prompts, logs, artifacts, `result.json`, PR comments or Git history;
- verification URL and device code are authorization challenges, not reusable credentials;
- prefer least privilege and ephemeral authorization;
- persist a credential only in an explicitly approved secret store;
- make credential lifetime/cleanup explicit;
- do not introduce a generic remote shell as an authorization workaround;
- secret-bearing operations remain in their approved secret-bearing execution plane.

## Governance boundaries

Authorization establishes only that an actor may perform the requested GitHub capability.

It never implies:

```text
Human Review PASS
merge authorization
Human Release Decision
release/promotion authorization
tag authorization
```

Those remain separate human governance boundaries defined by the platform lifecycle.

## Project V2 regression case

Known failure class:

```text
ChatGPT connector does not expose Project V2 mutation
but canonical broker or authorized gh/GraphQL can perform it
```

Required behavior:

```text
connector capability missing
→ try canonical broker/dedicated credential
→ if only OAuth consent is missing, HUMAN_BOOTSTRAP_ONLY
→ human authorizes only
→ perform Project V2 mutation programmatically
→ fresh Project V2 read-back
```

Forbidden behavior:

```text
connector capability missing
→ ask human to open Project
→ ask human to locate item
→ ask human to edit Status/field manually
```

## Failure diagnosis

Use `UNAVAILABLE` only after the approved route set has been exhausted. Diagnostic evidence must state:

- requested capability;
- attempted/considered providers;
- selected/failed provider;
- authenticated actor if known;
- target repository/Project identity;
- whether user consent could solve the gap;
- whether a runtime/session boundary prevents reuse of local authorization;
- the precise non-secret reason execution cannot continue.

Do not collapse a connector limitation, missing OAuth scope, broker defect, GitHub permission failure and network failure into one generic "GitHub unavailable" status.

## Completion checklist

A mechanical GitHub operation using this contract is complete only when:

- the capability and selected provider are explicit;
- any human interaction was authorization-only unless a separate human governance decision was required;
- actor/capability were verified after browser/device authorization;
- no token/PAT entered evidence channels;
- the operation was performed programmatically;
- fresh live read-back confirms the expected state;
- applicable repository-wide reconciliation is zero-mismatch;
- no Human Review, merge, release or tag authorization was inferred.
