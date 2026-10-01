# Governance mismatch taxonomy v1

`config/governance/mismatch-taxonomy-v1.json` is the versioned owner of the
three primary mismatch categories. Every emitted mismatch receives exactly one
category. A code with no explicit projection or presentation mapping defaults
to `SAFETY_BLOCKING`.

| Category | Authority and response |
|---|---|
| `SAFETY_BLOCKING` | Candidate Git/SHA/package, canonical Issue/PR/Milestone/dependency, required CI, human decision, or explicit authorization is invalid or missing. Stop the relevant side effect and repair the authoritative evidence. |
| `GOVERNANCE_PROJECTION` | Canonical backlog/release records and Project/delivery projections disagree, or a projection cannot be read. This never grants or blocks release readiness. A backlog/Project mutation remains incomplete until fresh repository-wide read-back reports `remaining_mismatches = 0`. |
| `PRESENTATION` | A display-only value such as an optional Work Package title prefix is stale or ambiguous. It does not change backlog truth or release readiness; repair presentation without changing authority. |

Release safety is evaluated from the exact candidate identity, Git history and
package hash, primary Issue/PR relationships, native Milestone and unresolved
dependencies, human decision records, explicit authorization, and canonical CI.
GitHub Project fields and views are projections. Its release-history view is
read-only evidence; canonical Git tags, GitHub Releases, and assets remain the
release record.

Release-scope evidence reports projection mismatches in a separate
`projection_mismatches` collection. The gate result only contains safety
failures. Backlog reconciliation still fails closed on any remaining Project
or presentation mismatch after its mutations.
