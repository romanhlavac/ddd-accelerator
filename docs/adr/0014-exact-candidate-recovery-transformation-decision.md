# ADR-0014: Exact-candidate human authorization for transformed recovery

## Status

Accepted for the DDDA release-governance control plane.

## Context

A controlled release source can be reconstructed from previously reviewed and merged implementation PRs. The default recovery invariant is intentionally strict: for every recovered shipping commit, the changed-path → result-blob map must be exactly equal to the original source merge commit. This protects physical release scope from silent omission or adaptation.

A legitimate recovery can nevertheless be an intentional, human-approved subset or adaptation. Treating that transformation as ordinary exact recovery produces false evidence; globally weakening path/hash equality would make the Release Scope Gate unsafe.

## Decision

Exact changed-path → result-blob equality remains the default and needs no exception record.

A non-equal recovered commit may be accepted only when the Release Scope Gate reads exactly one live GitHub comment marked `<!-- ddda:recovery-transformation-decision:v1 -->` and its JSON record satisfies the `recovery-transformation-decision` contract.

The decision is fail-closed and is bound to:

- repository, controlled candidate PR, exact candidate source SHA, candidate package SHA-256 and version;
- a non-bot GitHub comment author equal to the declared reviewer and to the authoritative HRDR decision owner;
- each transformed source PR, primary CR, source merge SHA and recovered commit SHA;
- the complete actual set of differing changed paths;
- for every differing path, source/recovered membership and exact result-blob SHA values.

The set of authorized transformations must equal the set of observed recovery-ledger path-hash mismatches. Extra, missing, stale, duplicate or malformed authorization is blocking. Any path not explicitly present in the complete difference set remains protected by exact equality.

The record authorizes only the physical recovery transformation. It does not close a scope Issue, change Milestone or Project state, authorize implementation merge, approve promotion, create a tag or publish a GitHub Release.

## Compatibility

This is an additive governance contract. Existing exact recoveries continue to pass without a decision record. Existing mismatching recoveries continue to fail unless an exact human decision exists. A candidate SHA/package change, source/recovered commit change, author/authority drift or any path/hash drift invalidates the authorization.

## Consequences

The recovery ledger cannot authorize its own deviation. Human judgment is recorded separately from machine provenance, while GitHub commit identities and live path/hash evidence keep the exception reproducible and auditable.
