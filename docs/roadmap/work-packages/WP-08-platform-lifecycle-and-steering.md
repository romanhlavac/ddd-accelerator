# WP-08 — Platform lifecycle & project steering

## Outcome

DDDA platforma má reprodukovatelný, auditovatelný a bezpečný produktový lifecycle a současně poskytuje chat-first project steering nad zachovanou DDD Starter metodikou G1–G8.

## Current state

```text
State: active / blocked
Target release: 0.1.0
Implementation: PR #8
Human Review: IN PROGRESS
Release readiness: NO_GO
```

Technická implementace PR #8 obsahuje podstatnou část lifecycle a steering foundation, ale release je blokován Human Review remediation.

## Goal

- jednotný platformní entry point;
- exact-SHA CI a local validation;
- candidate/release package jako distribuovatelná jednotka;
- isolated example workspace vytvořený z package;
- manifest-driven minimal ingestion;
- machine-readable a čitelný validation report;
- explicitní promotion gate;
- chat-first intake, tailoring, current status a next actions;
- evidence-driven gaty G1–G8;
- project-owned Miro projection;
- automatické mechanické kontroly a explicitní human judgment.

## In scope

- `ddda.ps1`;
- `validate-pr` a `promote-pr`;
- packaging, package-content a hash checks;
- release validation workspace;
- example ingestion a report;
- path isolation a secret leakage kontroly;
- GitHub CI taxonomy;
- project steering runtime;
- intake a lifecycle tailoring;
- current status a next actions;
- gate status a evidence contracts;
- Miro bootstrap, mapping, sync state a idempotence;
- Human Review a HRDR foundation;
- ADR, changelog, migration a release documentation;
- compatibility evidence pro pre-steering workspace.

## Out of scope

- program lifecycle P0–P10;
- Wardley Mapping a portfolio prioritizace;
- plná enterprise ingestion Office/PDF/ArchiMate;
- multi-agent fan-out/fan-in runtime;
- externí package registry;
- změna kanonické DDD Starter journey.

## Existing implementation evidence

- PR #8 — platform lifecycle and project steering;
- Issues #9–#15 — Human Review, blockers a remediation plan;
- prior merged PR #3–#7 — alpha foundation, path portability, Miro runtime, post-clone automation a first-run example.

## Active child issues / remediation

- #9 — Standardizovat Human Review a HRDR;
- #10 — Sjednotit release dokumentaci, autentizaci a changelog;
- #11 — Doplnit explicitní legacy workspace compatibility regression;
- #12 — Zlepšit traceability online Miro acceptance;
- #13 — Vynutit human-only gate decisions;
- #14 — Redesignovat Miro steering board;
- #15 — Uzavřít Human Review remediation před promotion.

## Critical path

```text
#13 human-only decisions
→ #14 Miro board redesign
→ #12 Miro evidence contract
→ #11 legacy compatibility
→ #10 release hygiene
→ all deterministic suites
→ freeze PR #8 SHA
→ one final Miro human visual acceptance
→ promotion dry-run
→ HRDR finalization in #9
→ explicit GO/NO-GO
→ merge and release 0.1.0
```

## Acceptance criteria at WP level

- [ ] production gate `passed` can originate only from auditable human provenance;
- [ ] automation can prepare evidence and `ready_for_review`, but cannot approve gate or release;
- [ ] Miro steering board is usable, deterministic and methodologically faithful;
- [ ] G1–G8 journey, Control Center and all gate states are visible and traceable;
- [ ] online Miro acceptance separates technical status from human visual acceptance;
- [ ] validation report retains board identity, mapping, sync state, idempotence and cleanup evidence;
- [ ] legacy pre-steering workspace can be used without mandatory migration;
- [ ] explicit adoption does not auto-pass any gate;
- [ ] release docs, authentication contract, changelog version and tag are consistent;
- [ ] `validate-pr` PASS is bound to exact PR head SHA and package hash;
- [ ] `promote-pr -DryRun` passes without merge, release or tag;
- [ ] HRDR is final for exact frozen SHA and candidate hash;
- [ ] no unresolved RED finding remains;
- [ ] release 0.1.0 is produced only after explicit human GO.

## Quality attributes

- auditability;
- reproducibility;
- process safety;
- security and secret isolation;
- compatibility;
- usability of steering;
- testability;
- modifiability;
- deterministic release behavior.

## Risks

| Risk | Impact | Mitigation |
|---|---:|---|
| Automation masquerades as human approver | High | provenance contract, spoofing tests, promotion preflight |
| Technical Miro PASS hides unusable board | High | explicit human visual status, final review board |
| Validation evidence becomes stale after SHA change | High | exact-SHA binding and invalidation |
| Release docs drift from implementation | Medium | repository contract tests and promotion consistency check |
| Governance change disturbs active PR #8 review | High | relationships/comments only; no PR #8 source change |

## Exit criteria

- all child blocker/remediation issues are closed with evidence;
- all deterministic tests pass for frozen SHA;
- final Miro human visual acceptance passes;
- promotion dry-run passes;
- HRDR issues GO or GO_WITH_ACCEPTED_RISKS;
- PR #8 is merged through controlled promotion;
- release package and release validation report exist;
- tag `v0.1.0` exists for validated state;
- roadmap and parent WP issue are updated to `done`.
