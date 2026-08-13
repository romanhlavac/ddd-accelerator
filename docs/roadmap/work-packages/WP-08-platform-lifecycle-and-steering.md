# WP-08 — Platform lifecycle & project steering

## Outcome

DDDA platforma má reprodukovatelný, auditovatelný a bezpečný produktový lifecycle a současně poskytuje chat-first project steering nad zachovanou DDD Starter metodikou G1–G8. Mechanické kontroly jsou automatizované; gate, HRDR, GO/NO-GO, merge a release zůstávají explicitními lidskými rozhodnutími.

## Current state

```text
State: active / blocked
Target release: 0.1.0
Implementation: PR #8
Human Review: IN PROGRESS
Release readiness: NO_GO
```

PR #8 obsahuje podstatnou část lifecycle a steering foundation. Uzavřené remediation položky #10, #11 a #13 jsou dokončené. Zbývající kritická cesta vede přes Miro redesign/evidence, final deterministic validation, frozen SHA a HRDR.

## Scope for DDDA 0.1.0

- `ddda.ps1`, `validate-pr` a `promote-pr`;
- exact-SHA CI/local validation;
- candidate/release package a package hash;
- isolated example workspace generated from package;
- minimal manifest-driven ingestion baseline;
- machine-readable a human-readable validation evidence;
- path isolation, package-content a secret-leak controls;
- chat-first intake, tailoring, status a next actions;
- evidence-driven G1–G8;
- generic project-owned Miro runtime, mapping, sync state a idempotence;
- human-only gate decisions;
- online Miro evidence a human visual acceptance;
- legacy workspace compatibility;
- release docs, changelog, ADR, migration note a HRDR.

## Out of scope for DDDA 0.1.0

- P0–P10, Wardley, portfolio, roadmap a benefits — WP-09;
- enterprise Office/PDF/ArchiMate ingestion — WP-10;
- multi-agent/EventStorming runtime — WP-11;
- external package registry;
- canonical G1–G8 journey change;
- GitHub Pages Artifact Registry dashboard — #45.
- persistent DDDA Platform Lab / board taxonomy / reference-adoption lifecycle — #53.
- persistent DDDA Example Project board lifecycle — #54.
- per-project Miro identity/team/Space/token UX — #55.
- corporate Miro execution-profile rebinding — #56.
- explicit profile credentials and legacy generic-token fallback removal — #57.

## Baselines for future Work Packages

PR #8 delivers foundation/preliminary contracts that later WPs must explicitly extend or version:

- minimal ingestion manifest/example → WP-10 #27;
- preliminary agent/capability schemas → WP-11 #36;
- generic Miro runtime/mapping/sync state → EventStorming extension #35;
- G1–G8 methodology/cookbooks → methodology gap remediation #48.

Parallel source-of-truth implementations are forbidden; compatibility or migration must be explicit and tested.

## Child issues

### Release 0.1.0 remediation

- #9 — Human Review and HRDR; open, mandatory promotion criterion;
- #10 — release docs/auth/changelog; **Done**;
- #11 — legacy compatibility regression; **Done**;
- #12 — online Miro acceptance traceability; open;
- #13 — human-only gate decisions; **Done**;
- #14 — Miro steering board redesign; open;
- #15 — remediation execution plan; active.

### Future WP-08 evolution

- #45 — GitHub Pages Artifact Registry dashboard; `Target Release: TBD` and explicitly outside Milestone `DDDA 0.1.0`.
- #53 — persistent Platform Lab, board taxonomy and reference/adoption lifecycle; `Target Release: TBD`, partial docs slice in Draft PR #58, explicitly outside Milestone `DDDA 0.1.0`.
- #54 — persistent Example Project board lifecycle; `Target Release: TBD`, outside Milestone `DDDA 0.1.0`.
- #55 — per-project Miro identity/team/Space/token UX; `Target Release: TBD`, outside Milestone `DDDA 0.1.0`.
- #56 — corporate Miro execution-profile rebinding; `Target Release: TBD`, outside Milestone `DDDA 0.1.0`.
- #57 — explicit profile credentials and legacy generic-token fallback removal; `Target Release: TBD`, blocked by #53/#54/#55, outside Milestone `DDDA 0.1.0`.

Parent membership under WP-08 does not imply release scope, priority or approval.

## Critical path

```text
#13 DONE
→ #14 Miro board redesign
→ #12 Miro evidence contract
→ remaining deterministic suites
→ freeze PR #8 SHA
→ one final Miro human visual acceptance
→ promotion dry-run
→ HRDR finalization in #9
→ explicit GO / GO_WITH_ACCEPTED_RISKS / NO_GO
→ merge and release only after separate explicit instruction
```

#9 is not by itself an implementation-remediation blocker. A finalized HRDR bound to the exact frozen SHA and candidate package hash is nevertheless mandatory for promotion/release.

#15 coordinates execution; it does not replace direct dependency relationships.

## Acceptance criteria

- [ ] production `passed` originates only from auditable human provenance;
- [ ] automation may prepare `ready_for_review`, never approve gate/release;
- [ ] Miro Control Center, G1–G8 journey and gate states are usable and traceable;
- [ ] technical Miro PASS remains separate from human visual acceptance;
- [ ] reports retain board ID, mapping, sync state, idempotence and cleanup evidence;
- [ ] legacy workspace remains usable without mandatory migration;
- [ ] validation is bound to exact PR SHA and package hash;
- [ ] promotion dry-run performs no merge, release or tag;
- [ ] HRDR is final for exact frozen evidence;
- [ ] no unresolved RED remains;
- [ ] #45 and #53–#57 do not enter release 0.1.0 implicitly.

## Exit criteria

- release-scope remediation issues are closed with evidence;
- deterministic tests PASS for frozen SHA;
- final Miro human visual acceptance PASS;
- promotion dry-run PASS;
- HRDR records explicit human decision;
- PR #8 merge/release occurs only after explicit instruction;
- package, validation report and `v0.1.0` identify the validated state;
- WP/roadmap are updated to Done;
- future #45/#53–#57 remain independently planned.
