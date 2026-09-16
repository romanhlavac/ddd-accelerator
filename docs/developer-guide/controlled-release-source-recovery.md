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
→ exactly one deterministic release-cut commit changing only CHANGELOG.md
→ one metadata-only recovery ledger commit
```

## Ledger

The candidate source contains exactly one versioned file:

```text
config/governance/release-source-recovery-ledger.json
```

Its schema is `schemas/release-source-recovery-ledger.schema.json`. Schema v1
remains readable for historical pre-promotion candidates. Promotion of a
controlled recovery source requires schema v2. Each entry
binds one reconstructed commit to the immutable original authority:

```json
{
  "recovered_commit_sha": "<new recovery commit SHA>",
  "source_pr": 74,
  "source_merge_commit_sha": "<merged source PR SHA>",
  "primary_cr": 9
}
```

The Release Scope Gate derives exactly one metadata-only commit from the
physical inventory. That commit may change only the ledger file and is not
listed inside that file: a ledger cannot safely contain the SHA of the commit
that creates it. Every other physical commit since the previous tag must have
one and only one ledger entry. The Gate freshly reads back the original PR,
its single primary CR, merged SHA and changed-path result hashes.
Any stale SHA, non-merged source PR, altered path result, incomplete coverage,
duplicate mapping or out-of-scope CR is a failure.

Schema v2 adds exactly one `release_cut` record. It binds the release version,
the release-cut commit SHA, the fixed path `CHANGELOG.md`, and that path's
source/result blob SHAs. The Gate reads the commit and its single parent back
from GitHub, requires the complete changed-path set to equal
`{CHANGELOG.md}`, and verifies both blob identities. The final ledger-only
commit is derived from the candidate tip, so the ledger never self-references.

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
4. Create exactly one deterministic release-cut commit changing only
   `CHANGELOG.md` and record its commit/source/result blob identities in a
   schema-v2 ledger.
5. Add/update the ledger in one final ledger-only metadata commit.
6. Open a Draft recovery candidate PR and run exact-SHA standard CI.
7. Run the read-only Release Scope Gate inventory. A PASS proves the physical
   source equals the declared scope; it is not a release authorization.

After the candidate is Ready and HRDR, RTDR (when transformations exist), the
Release Scope Gate and exact-SHA validation are all PASS, governed promotion
uses the PR head itself as the release source. It never merges that PR into
`main` and never deletes its source branch. Dry-run records before/after
assertions for PR merged state, head SHA, base SHA, tag and GitHub Release.
Actual promotion validates an operation-local package first; only after the
release suites and report are PASS may it materialize the canonical package,
tag the exact candidate SHA and publish the GitHub Release.

No automatic revert, scope expansion, tag movement, force-push or history
rewrite is permitted.
