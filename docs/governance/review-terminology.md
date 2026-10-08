# Review terminology

This vocabulary applies prospectively to DDDA platform implementation and visual artifact reviews. Historical audit comments and PR8 evidence remain intact.

| Term | Meaning | User-facing form |
|---|---|---|
| Human Review | Judgment review of an implementation PR, bound to an exact SHA and candidate package | `Human Review PR #84: PASS` or `CHANGES_REQUIRED` |
| HR | Compact form of Human Review | `HR PR #84: PASS` |
| Human Visual Review | Review of a rendered visual artifact such as a Miro frame | `Human Visual Review PR #84 / Frame 01: PASS` |
| HVR | Reserved compact form of Human Visual Review | `HVR PR #84 / Frame 01: PASS` |
| CR #n | Change Request Issue identifier | `CR #70` |
| PR #n | Pull Request identifier | `PR #84` |
| R<n> | Implementation revision or attempt within a change lineage | `CR #70 → PR #84 R5` |

A general implementation handoff says `CR #70 → PR #84 R5 — READY FOR HUMAN REVIEW`. The `R<n>` counter is optional and needs an explainable lineage; it is never a Human Review round, Human Visual Review round, PR number, or commit number. Omit it when it adds no useful information. Avoid bare `#70 / #84` or `HVR #84`, which obscure the identifier type or artifact.

An implementation verdict uses `Human Review PR #84: PASS` or `Human Review PR #84: CHANGES_REQUIRED` (compact `HR PR #84`). A visual verdict names both PR and artifact, for example `HVR PR #84 / Frame 01: PASS`. Visual review cannot substitute for the general implementation judgment review.

The authoritative machine marker remains `<!-- ddda:human-pr-review:v1 -->`; its schema and exact-SHA/package binding are unchanged. A Human Release Decision Record (HRDR) is a separate release decision, never a synonym for either review. Historical audit comments and evidence are not rewritten.
