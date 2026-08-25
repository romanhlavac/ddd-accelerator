# Controlled release-source recovery

## Purpose

When `main` already contains work outside the declared release scope, DDDA may
use a separately reconstructed release source only after an explicit human
recovery decision. This is not a scope expansion and does not rewrite `main`
or any historical tag.

The recovery source contains

```text
previous canonical tag
→ recovered commits for approved shipping PRs only
→ one metadata-only recovery ledger commit
```

## Ledger

The candidate source contains exactly one versioned file:

```text
config/governance/release-source-recovery-ledger.json
```

Its schema is `schemas/release-source-recovery-ledger.schema.json`. Each entry
binds one reconstructed commit to the immutable original authority:

```json
{
  "recovered_commit_sha": "<new recovery commit SHA>",
  "source_pr": 74,
  "source_merge_commit_sha": "<merged source PR SHA>",
  "primary_cr": 9
}
```

The ledger has exactly one metadata-only commit. That commit may change only
the ledger file; every other physical commit since the previous tag must have
one and only one ledger entry. The Release Scope Gate freshly reads back the
original PR, its single primary CR, merged SHA and changed-path result hashes.
Any stale SHA, non-merged source PR, altered path result, incomplete coverage,
duplicate mapping or out-of-scope CR is a failure.

## Authority boundary

The ledger is evidence, not authorization. It cannot add an Issue to a
milestone, defer a scope item, accept a risk, create a Human Release Decision,
or authorize promotion, tag creation or publication. The candidate remains
Draft until standard CI, a Human Release Decision Record and the normal release
governance boundaries are satisfied.

## Recovery procedure

1. Freeze the intended candidate source SHA and read the live milestone/Project authority.
2. Create the reconstruction branch from the previous canonical SemVer tag.
3. Reapply only the selected original shipping changes, preserving their exact
   changed-path results.
4. Add the ledger as its only metadata-only commit.
5. Open a Draft recovery candidate PR and run exact-SHA standard CI.
6. Run the read-only Release Scope Gate inventory. A PASS proves the physical
   source equals the declared scope; it is not a release authorization.

No automatic revert, scope expansion, tag movement, force-push or history
rewrite is permitted.
