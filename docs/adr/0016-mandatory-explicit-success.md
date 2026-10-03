# ADR 0016: Singular mandatory-check explicit-success contract

Status: Proposed — #73

Date: 2026-10-03

## Context

The S1 shared check adapter still accepts NEUTRAL and SKIPPED for mandatory
checks and selects attempts by start time. This can accept a non-success gate
and mishandle a newer queued attempt with no start timestamp.

## Decision

Keep one decision owner in the existing Governance Kernel. Normalize response
shapes in the existing check adapter and collect all attempts in the existing
process entry point. Require exact names, explicit required sets, observed
candidate SHA, authoritative attempt identity and completed SUCCESS.

Rank attempts by GitHub's monotonically allocated check-run/status identity,
not start/completion time. Fail closed on multiple producers or contradictory
winning identities. Keep optional/non-applicable workflow outcomes non-gating.

## Alternatives

Wrapper-specific evaluators would reintroduce S1 duplication. Merely changing
an allowed-conclusion list would leave missing checks, SHA binding and rerun
ambiguity unresolved. Both alternatives are rejected.

## Consequences and compatibility

Live mandatory semantics become stricter. New readiness evidence needs explicit
required names and observed SHA provenance. Existing command PASS/FAIL exit
behavior remains; detailed evidence distinguishes NOT_READY. Historical 0.1.1
assets and the frozen v1 scenario baseline are preserved. Active v2 scenarios
record this prospective change. The controlled-recovery compatibility route
and all human decision/authorization boundaries remain authoritative.

## Validation

Use conclusion/status tables, missing/exact-SHA cases, rerun ordering,
identity ambiguity, optional skip isolation, paginated collection, process
exit evidence and lifecycle parity. Run standard exact-SHA CI and package-first
validate-pr before Human Review. No technical result authorizes a merge.
