# Mandatory GitHub checks: explicit success (#73)

The production decision owner is
`runtime.platform.governance_kernel.evaluate_check_summary`.
`runtime/platform/check_evidence.py` normalizes GitHub response shapes;
`Evaluate-DDDACheckRuns.py` collects and exposes the decision to PowerShell
and workflow consumers. There is no wrapper-specific success policy.

A mandatory PASS requires the exact check name in the declared required set,
the exact candidate SHA on the summary and selected attempt, a valid unique
attempt identity, `status=completed` and `conclusion=success`.
Failure, skipped, neutral, cancelled, timed_out, action_required, stale,
startup_failure, unknown and null conclusions never pass. Missing, queued,
in_progress, waiting, pending and requested are non-PASS; pending or missing
evidence is reported as NOT_READY. A new unknown status fails closed.

## Required sets and consumers

`config/governance/mandatory-checks-v1.json` declares the default implementation
set used by governed merge and standard promotion: the six protected-main
checks plus One-command PR validation. The set is explicit: a missing check
cannot disappear merely because the collector did not observe it.

The validate-pr CI entry uses the same process adapter for its Platform
validation prerequisite; it cannot require its own in-progress job. The remote
broker uses Platform validation and One-command PR validation before its
secret-bearing operation. Miro materialization declares its existing exact
required names and consumes the same adapter. Additional operation-specific
sets are explicit `--required-check` arguments, never fuzzy name matches.

Other workflows are OPTIONAL (or explicitly NOT_APPLICABLE); their skip or
failure does not satisfy or invalidate this mandatory set. Ignore options
cannot remove a required name. The Human Review coordinator and its gated
merge dry-run do not create a circular prerequisite. Their outcomes remain
separate from the technical required set and human authorization.

## Authoritative attempts

Collect all check-run pages with `filter=all`. Within an exact check name and
one producer, the highest GitHub-allocated numeric check-run ID is the newest
created attempt. An Actions rerun creates new check-run identities. Start and
completion timestamps do not rank attempts: a queued newer attempt with no
start timestamp must supersede an older success.

Identical duplicate API rows are idempotent. Different producers, invalid IDs
or contradictory evidence for the same winning ID are ambiguous and non-PASS.
A newer failure cannot be overridden by an old success; a newer successful
authoritative rerun replaces an old failure. Commit status contexts use their
status ID and `commit-status:<exact context>` identity; the collector binds them
to the observed combined-status response SHA.

## Evidence and compatibility

The process adapter emits source_sha, required_check_set and, for every selected
check, name, run_id, app_id, observed source SHA, status, conclusion,
classification, gate_result and failure_reason. Overall status remains PASS
or FAIL for existing lifecycle exit-code consumers; gate_result distinguishes
NOT_READY. PowerShell preserves the summary and prints it to workflow logs.
The validate-pr prerequisite evidence is also uploaded as an exact-SHA artifact.

Candidate Context v1 is hardened with observed SHA provenance on check summaries
and results. Missing provenance on newly evaluated readiness is non-PASS.
The accepted_conclusions transport option remains compatible only with SUCCESS;
it cannot expand the kernel policy. Historical 0.1.1 packages, tags, release
evidence and the frozen scenario matrix v1 remain unchanged. The explicit S2
controlled-recovery evidence route remains separate; this check contract does
not invent check-runs on its frozen release source.

Active #73 scenarios are in scenario-matrix-v2.json and exercise the production
kernel through the shared normalizer. Technical PASS never grants Human Review,
merge, promotion, release or tag authorization.
