# ADR 0017: Planning lifecycle uses active delivery evidence

Status: Accepted for implementation; Human Review remains required.
Change: #94. Foundation: #173 authority/projection taxonomy.

## Context

The canonical reconciler accepted an open planning Issue in Backlog while its
primary Draft PR was In progress (#88/#92). Project Status became stale because
planning derivation considered blockers and closure but omitted implementation entry.

## Decision

Extend the existing reconciliation entrypoint, not a second lifecycle authority.
One planning projection function consumes canonical Issue state, unresolved
dependency projection and active primary PR relationships. Closure wins, then
blockers, then implementation entry. Draft and Ready both imply planning In progress;
Ready delivery remains In review. Closed historical release-source evidence cannot
reopen completed planning. Existing early statuses are preserved without active PRs.

The stable entrypoint has explicit reconcile and read-only verify modes. Both
consume the same derivation and emit lifecycle evidence and S3 projection mismatch
categories. Verify cannot mutate Project or dependencies. Authority drift blocks
PASS. Reports retain schema v6 and remaining_count, and add mode, status,
remaining_mismatches and problems. Existing no-argument use remains reconcile.

## Consequences and compatibility

This is a prospective projection correction. No Issues, branches or PRs are
created by derivation. No priority, release scope, human review, merge or release
authorization is inferred. Historical 0.1.1 release-source PRs and frozen matrix
v1 are preserved. Privileged live reconciliation stays manual on trusted source;
standard PR CI tests the contract with isolated fixtures and no Project credentials.
