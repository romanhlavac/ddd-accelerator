# DDDA platform Pull Request

## Backlog relationship

- Parent Work Package: `WP-XX — #<issue>`
- Change Request: `CR #<issue>`; relationship `Implements #<issue>` nebo `Closes #<issue>`
- Related GAP / defect / risk: `#...`
- Target Milestone: `DDDA X.Y.Z` nebo `TBD`

> PR je jednotkou skutečné implementační změny. Nezakládej PR pouze jako plán nebo vzdálený roadmap placeholder.

## Goal

Jaký konkrétní outcome tohoto PR realizuje?

## Actual change scope

### In scope implemented

- ...

### Explicitly not implemented

- ...

### Scope changes since Issue refinement

- none / popis schválené změny a odkaz na aktualizované Issue

## Classification

Platform areas:

- [ ] DOC
- [ ] METHODOLOGY
- [ ] TEMPLATE
- [ ] SCHEMA
- [ ] ORCHESTRATION
- [ ] INGESTION
- [ ] CLI
- [ ] WORKSPACE-GENERATOR
- [ ] EXAMPLE
- [ ] TESTING
- [ ] RELEASE
- [ ] SECURITY-GOVERNANCE

Impact:

- [ ] LOW
- [ ] MEDIUM
- [ ] HIGH
- [ ] BREAKING

Migration impact:

- [ ] None
- [ ] Non-breaking / additive
- [ ] Breaking — migration note included

## Repository changes

- implementation/configuration:
- schemas/contracts:
- tests/fixtures:
- documentation/examples:
- ADR:
- changelog:
- migration note:

## Acceptance coverage

| Acceptance requirement | Implementation evidence | Test evidence | Documentation evidence | Status |
|---|---|---|---|---|
| ... | ... | ... | ... | covered / partial / missing / scope creep |

## Test evidence

- CI run / exact SHA:
- local validation report:
- candidate package hash:
- suites executed:
- online external-system evidence:
- diagnostics retained:

## Human Review

Handoff: `CR #<cr> → PR #<pr> — READY FOR HUMAN REVIEW` (`R<n>` only for documented implementation revision lineage).
Verdict: `Human Review PR #<pr>: PASS|CHANGES_REQUIRED` (compact: `HR PR #<pr>`).
Human Visual Review, when required: `HVR PR #<pr> / <artifact>: PASS|CHANGES_REQUIRED`.
Machine marker remains `ddda:human-pr-review:v1`. See [canonical terminology](../docs/governance/review-terminology.md).

Judgment areas required:

- [ ] scope and product outcome
- [ ] methodology
- [ ] architecture and contracts
- [ ] security and isolation
- [ ] compatibility and migration
- [ ] usability / Miro visual acceptance
- [ ] release readiness and residual risks
- [ ] not required beyond normal code review

Implementation Human Review evidence:

- status: not started / in progress / PASS / CHANGES_REQUIRED
- exact reviewed SHA:
- evidence link:

For a release candidate, HRDR is separate: `PENDING_HUMAN_DECISION / GO / GO_WITH_ACCEPTED_RISKS / NO_GO`.

## Risks and residual risks

| Risk | Status | Owner | Mitigation / follow-up |
|---|---|---|---|
| ... | open / accepted / mitigated | ... | ... |

## Checklist

- [ ] PR odkazuje na konkrétní Change Request.
- [ ] Skutečný diff odpovídá Goal, In scope a Out of scope.
- [ ] Každá behaviorální změna má odpovídající testy.
- [ ] Contract change je dokumentována.
- [ ] Významné dlouhodobé rozhodnutí má ADR.
- [ ] Breaking změna má migration note a migration tests.
- [ ] CHANGELOG popisuje pouze skutečně dodanou změnu.
- [ ] Testy nepoužívají client workspace ani klientská data.
- [ ] Release/package neobsahuje secrets, `.git`, cache ani user-specific paths.
- [ ] Automatizace nevytváří lidské gate approval nebo GO/NO-GO.
- [ ] Validation evidence je navázána na current head SHA.
- [ ] Parent Work Package a roadmap budou po dokončení aktualizovány.
- [ ] Merge ani release nebude proveden bez explicitního lidského rozhodnutí.
