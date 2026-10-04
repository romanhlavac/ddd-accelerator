# Branch lifecycle and cleanup (#65)

The implementation PR is the unit of change. Start new work from `main` on
`feature/<change-id>-<short-name>`, `fix/<change-id>-<short-name>`,
`docs/<change-id>-<short-name>` or `release/<version>`. CI runs
`Check-DDDABranchPolicy.py` against the actual PR branch and SHA, using the
exception registry from trusted `main`. `feat/`, `chore/`, `gov/`,
`governance/` and `agent/` are legacy-only. The registry currently binds the
already open PR #95 and controlled release-source PR #146 to exact heads;
their exception expires on PR closure or head change.

Only a GitHub Actions control-plane owner may create
`automation/<purpose>-<run-id>`. The helper
`scripts/platform/Manage-DDDAAutomationBranches.py` creates one manifest-only
commit on an exact source SHA, with owner, purpose and run identity. A producer
uses `managed_branch(...)` around its staging operation so `finally` evaluates
cleanup on success and failure. It records the source, resulting HEAD and
cleanup decision. Only `.ddda/automation-provenance.json` and
`.ddda/automation-staging/` may differ from the declared source. Such a branch
cannot be an ordinary implementation PR or confer release authority.

Cleanup is an ordinary, non-force deletion only after fresh branch HEAD,
manifest, source ancestry, changed paths, run identity, associated PRs and
release/tag references are checked. A moving HEAD, unknown owner, unverified
unique history, open PR or audit/release reference keeps the branch.
The canonical Project reconciliation workflow reports stale branches through
its audit artifact and does not delete them. Re-run the read-back before any
later cleanup decision.

The initial [inventory](branch-inventory-2026-10-03.md) preserves every
historical branch. `SAFE_TO_DELETE` is empty and deleted branches are empty.
PR #146 and all controlled 0.1.1 V1–V4 recovery generations remain protected
as release evidence; `gov/` residues and the older `automation/` branch are
AMBIGUOUS, not cleanup authorization.
