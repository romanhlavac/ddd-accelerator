# Release candidate identity v1 (#131)

The S1 Governance Kernel in `runtime/platform/governance_kernel.py` is the machine decision owner. This guide defines its human-facing projection for new release-candidate PRs. Implementation PRs, including `fix(release): ...`, are not release candidates. A title or label alone never grants a release decision.

| Surface | Normal release candidate | Controlled recovery candidate |
|---|---|---|
| PR title | `[RELEASE][X.Y.Z] Release candidate` | `[RELEASE][X.Y.Z][RECOVERY] Controlled release candidate` |
| Source branch | `release/X.Y.Z` | `release/X.Y.Z-controlled-recovery-source` or numbered successor `-vN`, N ≥ 2 |
| Labels | `release-candidate` | `release-candidate`, `controlled-recovery` |
| Body record kind | `normal` | `controlled_recovery` |
| Lifecycle | Normal source after intended work is integrated; governed release path | Exceptional human-authorized reconstructed source with recovery ledger; dedicated validation lane, never an ordinary implementation merge |

Both kinds require exactly one body record, with the marker immediately followed by a fenced JSON object:

````text
<!-- ddda:release-candidate:v1 -->
```json
{"schema_version":1,"kind":"normal","version":"X.Y.Z"}
```
````

For recovery use `"kind":"controlled_recovery"`. JSON keys are exactly `schema_version`, `kind`, `version`; duplicate keys, duplicate marker, missing label, branch/title/body/version disagreement, and an unexpected recovery label fail closed. A PR must be open, on `main`, and its head SHA and repository must match the exact candidate context. HRDR scaffolding and promotion consume this check; a technical PASS never implies a Human Release Decision or permission to merge, promote, tag or publish.

Existing historical candidate PRs retain their title, body, labels and refs as audit identity. They are not silently converted into v1 candidates. A new operation on an old candidate needs a separately reviewed exact-SHA compatibility decision or a new, fully conforming candidate; historical decisions and releases remain unchanged. General branch lifecycle is owned by [branch lifecycle](branch-lifecycle.md), while controlled recovery scope and no-merge rules remain in [controlled recovery](../developer-guide/controlled-release-source-recovery.md).
