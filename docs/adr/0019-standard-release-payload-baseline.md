# ADR 0019: STANDARD payload baseline and scope dispositions

Status: Accepted design; implementation pending exact-SHA Human Review and merge

Date: 2026-10-14

## Context and authority

The decision owner approved the three baseline/content/cancellation principles
on 2026-10-14 and assigned their bounded implementation to CR #171 at 14:51:40
Europe/Budapest. This is a prospective change to standard scope semantics, not
merely kernel refactoring. CR #96 and ADR 0011 preserve historical 0.1.1
authority. Milestone membership, historical tags, Git history and published
assets remain unchanged. Controlled recovery is not authorized.

## Decision

From 0.1.2, STANDARD uses physical-scope contract v2 in the existing Governance
Kernel. Candidate Context v1 gains a versioned, SHA/package-bound content scope
reference; schema v1 and historical 0.1.1 scope remain readable.

The previous canonical SemVer tag still selects the baseline. Its published
canonical ZIP must be fetched read-only, SHA-256/size verified against the
GitHub asset, and bound to the annotated tag, peeled source and complete Git
tree. Missing, conflicting, truncated or unsupported evidence fails closed.
The exact candidate ZIP is reused, never rebuilt by the collector.

The collector provides the complete first-parent source chain from a unique
common ancestor and the complete before/after tree entries. The kernel replays
every transition and requires the final tree to equal the entire candidate
payload. For each physical payload delta, the last source state exactly equal
to the baseline is the anchor. Every subsequent contribution needs the exact
merged PR identity, unique primary CR and current Milestone authority. A shared
path's out-of-scope contribution stays blocking until a proven return to its
baseline state removes it. The latest PR or file author never overrides scope.

Inherited equal payload and completely reverted changes are not new delivery.
Raw payload hashes remain significant even when Windows CRLF export binds to
the same canonical Git blob. A formatting-only payload drift without a source
contribution fails; documentation, configuration, workflows and tests receive
the same coverage as runtime. Source modes and symlinks remain in the proof.
Package inclusion rules are not changed.

Declared scope is fully accounted by delivered CRs and explicit
cancelled-no-delivery dispositions. These sets must be disjoint. Cancellation
requires a current closed/not_planned Issue and one explicit repository-owner
User record in its conversation with marker `ddda:cancelled-no-delivery:v1`;
closure alone cannot authorize it. The record carries schema_version=1,
repository, issue, decision=CANCELLED_NO_DELIVERY and decision_owner equal to
the comment author. Existing human decisions can be materialized with their
original evidence reference; automation cannot derive a decision from tests.
For organization-owned repositories this narrow actor contract fails closed
until a separately reviewed decision-owner policy exists.

## Consequences and limits

- Diverged lineage may pass only with complete verified payload/provenance;
  no tag movement, baseline replacement or recovery transformation is used.
- A cancelled CR remains in the Milestone and is never reported as shipped.
- Legacy scope cannot satisfy STANDARD 0.1.2; a coarse PASS reference without
  contract version, source SHA and package hash cannot satisfy release context.
- Unknown contribution, unsupported submodule, missing historical ZIP,
  missing baseline anchor and non-merged candidate source contribution fail.
- This implementation deliberately does not invent exemptions for a release
  cut, baseline-only recovery metadata removal or CR #88/#155. Those cases stay
  blocked until their exact authority/content proof exists. No source cleanup
  or new release candidate is performed by this PR.
- Source inventory acquisition PASS is distinct from a kernel preview PASS and
  from the actual HRDR-bound Release Scope Gate. The optional CI diagnostic job
  creates read-only evidence and no human decision or release authorization.

## Alternatives

Merging old lineage alone does not remove out-of-scope payload. Replacing the
baseline with a newer main hides unshipped content. Reconstructing a selective
source from the old tag is recovery. None is selected.

## Validation

Production-kernel scenarios cover cross-lineage proof, shared-path extra scope,
forged/incomplete replay, exact net-zero revert, raw payload drift, cancellation
without authority, cancellation with delivery, package/tree mismatch and token
removal across asset redirects. Frozen scenario matrix v1 is not changed; the
active v2 matrix includes #171 payload cases. Exact-SHA CI and package-first
validation are required before Human Review; merge needs separate authorization.
