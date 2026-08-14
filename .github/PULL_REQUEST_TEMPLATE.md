# DDDA platform Pull Request

## Backlog relationship

- Parent Work Package: `WP-XX — #<issue>`
- Change Request: `Implements #<issue>` nebo `Closes #<issue>`
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

## Human review

Judgment areas required:

- [ ] scope and product outcome
- [ ] methodology
- [ ] architecture and contracts
- [ ] security and isolation
- [ ] compatibility and migration
- [ ] usability / Miro visual acceptance
- [ ] release readiness and residual risks
- [ ] not required beyond normal code review

HRDR / review evidence:

- status: not started / in progress / GO / GO_WITH_ACCEPTED_RISKS / NO_GO
- exact reviewed SHA:
- evidence link:

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
