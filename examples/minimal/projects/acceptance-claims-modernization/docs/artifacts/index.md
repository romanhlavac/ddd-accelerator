# Artifact Registry — acceptance-claims-modernization

> **Project-owned source of truth:** `artifacts/registry.yaml` in this project workspace. This Markdown document is a read-only projection. It does not approve a gate, change lifecycle, or replace an authorized human decision.

## How to read the registry

- **Lifecycle** describes maturity of an artifact, not approval of a project gate.
- **Provenance** describes how the artifact originated; it is not a quality rating.
- **ATTENTION** means that a person must review or complete the artifact. An attention item is not automatically blocking.
- **Blocking** is explicit. Only an item marked `blocking: true` prevents the current review from completing.

## Lifecycle states

| State | Meaning |
|---|---|
| `scaffold` | A generated starting structure that still requires project-specific content. |
| `working` | Actively edited and not yet proposed as a review candidate. |
| `candidate` | Submitted for a defined review against explicit acceptance criteria. |
| `validated` | Mechanically or professionally checked, but not yet accepted by the authorized decision owner. |
| `accepted` | Explicitly accepted by an authorized human decision recorded outside this projection. |
| `superseded` | Replaced by a newer artifact or decision and retained for traceability. |

## Current health

| Measure | Value |
|---|---:|
| Managed artifacts | 3 |
| Scaffold | 1 |
| Working | 2 |
| Candidate | 0 |
| Validated | 0 |
| Accepted | 0 |
| Superseded | 0 |
| ATTENTION items | 1 |
| Blocking items | 0 |

## Attention required

1. `project-charter` is still a scaffold and requires human review. This does not approve G1 and is not currently marked as blocking.

## Managed artifacts

| Artifact | Type | Stage | Lifecycle | Provenance | Owner | Attention | Blocking | Detail |
|---|---|---|---|---|---|---|---|---|
| `project-charter` | `project-charter` | Align | `scaffold` | `generated` | Acceptance Business Owner | yes | no | [`project-intake.template.yaml`](../../../../../templates/project/project-intake.template.yaml) |
| `ddda.current-status` | `project-status` | Control | `working` | `generated` | DDDA steering runtime | no | no | [`Get-DDDAProjectStatus.ps1`](../../../../../scripts/Get-DDDAProjectStatus.ps1) |
| `ddda.next-actions` | `next-actions` | Control | `working` | `generated` | DDDA steering runtime | no | no | [`Get-DDDAProjectStatus.ps1`](../../../../../scripts/Get-DDDAProjectStatus.ps1) |

## Projection rule

The Miro Control Center shows only current health, the attention definition, the next decision, and a link to this project-specific registry. Platform schemas and generators remain in the DDDA platform repository; project data do not share a global platform registry.

GitHub Pages remains deferred to backlog issue `#45`.
