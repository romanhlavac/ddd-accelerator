# Branch inventory after 0.1.1 — 2026-10-03

Source main: `f44fe66a118fa54b58d8c8bac97b4136f8c5c795`. This is a repository-wide read-back of 118 branches and 113 PRs. Unique commits are GitHub ahead_by relative to main, not a deletion authorization. Last activity records branch HEAD commit and associated PR update; no independent branch-usage telemetry is available. Published v0.1.1 targets V4 source SHA `4415c17fcba98298c40b25555a9a0bf5f550f13e`.

| Classification | Count | Decision |
| --- | ---: | --- |
| AMBIGUOUS | 111 | Preserve |
| ACTIVE | 3 | Preserve |
| REQUIRED_FOR_AUDIT_OR_RELEASE | 4 | Preserve |
| SAFE_TO_DELETE | 0 | No deletion |

Release-source PR #146 and branches V1–V4 are preserved as historical release/audit evidence. Current open PRs #95 and #106 and protected `main` are active. The old `automation/pr86-governance-normalization` retains two commits unique to its branch; the historical `gov/` read-back branches lack provable safe cleanup ownership. All uncertain branches remain AMBIGUOUS. No branch deletion, force push or history rewrite was performed. The full per-branch SHA, PR association, merge status, unique commits, activity, references and rationale are in [branch-inventory-2026-10-03.json](branch-inventory-2026-10-03.json).

Reclassification requires a fresh main/branch/PR/reference read-back and deterministic proof. A historical name or merged PR alone is insufficient for automatic deletion.
