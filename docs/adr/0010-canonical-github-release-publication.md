# ADR 0010: Canonical GitHub Release publication

- Status: Proposed
- Date: 2026-08-25
- Related: #68, #96, #98

## Context

The canonical promotion path validates a release package and emits a release report and annotated Git tag. A tag alone exposes GitHub-generated source archives but does not publish the validated DDDA product package or durable release evidence.

The required invariant is:

```text
validated release version + source SHA + package SHA-256 + report + tag
= one immutable GitHub Release publication
```

## Decision

After all release gates and release validation PASS, promotion creates or read-backs exactly one final GitHub Release named `DDDA X.Y.Z` for tag `vX.Y.Z`. It publishes these deterministic assets:

- `ddda-X.Y.Z.zip` — canonical validated DDDA package;
- `ddda-X.Y.Z-release-report.json`;
- `ddda-X.Y.Z-release-report.md`.

Publication verifies the annotated tag dereferences to the exact validated release source SHA, then verifies each physical asset SHA-256 by GitHub digest or authenticated download/read-back. Existing tag, Release or assets are never overwritten. Partial failure is not PASS; recovery requires a separate explicit authorization and fresh identity/hash read-back.

GitHub source archives remain convenience source archives, not the DDDA product package.

## Consequences

- Release distribution and evidence become directly discoverable in GitHub Releases.
- Release publication adds a post-validation side-effect boundary and recovery state.
- #96 remains responsible for proving that the release source itself is physically in scope before publication may begin.
- #68 remains responsible for tag identity/recovery; this decision only extends recovery with Release and asset identity.

## Validation

- deterministic asset-name and hash checks;
- release API orchestration and server read-back;
- missing/wrong/duplicate asset and partial-publication regressions;
- dry-run proves no tag, Release or asset side effect;
- authorization and secret-isolation tests.
