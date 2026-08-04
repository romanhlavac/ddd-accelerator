# DDDA Artifact Registry

> **Authority:** Git/YAML is source of truth. This Markdown document is a read-only projection for navigation and review; it cannot approve a gate or change artifact lifecycle.

## Registry identity

- Registry contract: `REM-PR8-HVA-CC-012.2-gh-md-v1`
- Projection: GitHub-rendered Markdown
- Scope: managed steering artifacts shown in Miro Control Center frame `00`
- Product source: bound to the exact candidate SHA in the REM-012.2 `result.json`
- GitHub Pages evolution: backlog issue `#45`; not part of the current remediation

## Artifact health

| Measure | Value |
|---|---:|
| Managed artifacts | 3 |
| Scaffold | 1 |
| Working | 2 |
| Candidate | 0 |
| Validated | 0 |
| Accepted | 0 |
| Superseded | 0 |
| Attention items | 1 |

## Attention required

1. Human visual review of Miro frames `00`, `01`, and `10` remains pending. Technical completion must not be interpreted as gate approval.

## Managed artifacts

| Artifact | Type | Stage | Lifecycle | Provenance | Owner | Revision | Last sync | Detail |
|---|---|---|---|---|---|---|---|---|
| `project-charter` | `project-charter` | Align | `scaffold` | `generated` | Project decision owner from workspace | Exact candidate source | On demand | [`project-intake.template.yaml`](../../templates/project/project-intake.template.yaml) |
| `ddda.current-status` | `project-status` | Control | `working` | `generated` | DDDA steering runtime | Exact candidate source | On demand | [`Get-DDDAProjectStatus.ps1`](../../scripts/Get-DDDAProjectStatus.ps1) |
| `ddda.next-actions` | `next-actions` | Control | `working` | `generated` | DDDA steering runtime | Exact candidate source | On demand | [`Get-DDDAProjectStatus.ps1`](../../scripts/Get-DDDAProjectStatus.ps1) |

## Projection rules

- The registry may grow to hundreds of rows without expanding the Miro frame.
- Miro displays only aggregate health, up to five attention items, the registry contract, and a link to this document.
- Lifecycle and provenance are separate dimensions.
- `accepted` and gate `passed` require explicit human decisions outside this projection.
- A changed registry file changes its SHA-256 and invalidates prior REM-012.2 technical evidence.
