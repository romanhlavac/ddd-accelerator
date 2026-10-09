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


## Default Human Review presentation

For a normal implementation PR, present exactly these three semantic blocks:

1. **Co se mění** — one plain-language statement of the intended behavior or outcome.
2. **Co se nesmí změnit** — the safety, governance and business boundaries that must remain intact.
3. **Jaký dluh, riziko nebo výjimku přijímáš** — only when applicable; otherwise explicitly state that none is requested.

Keep the review to at most three concise decision points by default. Questions must require human judgment and be understandable to the decision owner. Complex or high-risk changes may add only genuinely judgment-heavy questions.

CI, exact SHA, candidate-package hash, schemas, path checks and other automated controls are validated evidence, not tasks for the human to independently verify. Human Review PASS remains bound to the exact SHA and package, and remains separate from merge authorization.
