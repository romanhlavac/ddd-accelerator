# Controlled release-source promotion from GitHub Actions

## Purpose

This runbook is the production execution path for a frozen DDDA controlled release-source candidate after exact-SHA validation, Human Release Decision, Release Scope Gate, promotion dry-run and explicit human promotion/release authorization have all passed.

It does **not** merge the controlled candidate PR. The release source remains the exact PR head SHA and the workflow fails closed if that identity changes.

## Preconditions

Before production promotion:

- the controlled candidate PR is open and Ready for review;
- its branch matches `release/<version>-controlled-recovery-source` or a canonical numbered successor `-vN`, `N >= 2`;
- the PR explicitly states that it must not be merged into `main`;
- one authoritative Human Release Decision Record exists for the exact PR/SHA/package/version and has `decision=go`;
- the HRDR-bound candidate package and validation report are still available and their SHA-256 identity matches;
- a governed `promotion_dry_run` has passed with `release_scope_gate_status=PASS`, `promotion_preflight_status=PASS`, `side_effect_assertions_status=PASS` and `wrapper_status=PASS`;
- one explicit human promotion/release authorization is materialized on the controlled PR as `ddda:promotion-release-authorization:v1`.

The authorization record must bind repository, PR, exact source SHA, candidate package SHA-256, version and the exact command `promote-pr -Pr <PR> -Version <VERSION> -ConfirmPromotion`. It must explicitly prohibit candidate merge and enumerate the release package, release validation, canonical tag and GitHub Release as the only authorized release side effects after canonical PASS.

## Production command comment

After the authorization record exists, the human authorizer requests the production run with one exact PR comment:

```text
/ddda promote-controlled --source-sha <40-char-SHA> --version <X.Y.Z> --package-sha256 <64-char-SHA256>
```

The `Controlled release-candidate promotion` GitHub Actions workflow is defined on the default branch and is triggered only by that command on a pull request conversation. The command actor must be the same human GitHub identity that authored the single authoritative promotion/release authorization record.

## Fail-closed execution sequence

The workflow:

1. checks out the current default-branch control plane and binds the run to its exact SHA;
2. validates the human authorization marker and command identity;
3. validates the frozen Ready controlled candidate identity;
4. restores only the candidate validation artifact named by the HRDR `validation_workflow_run`;
5. recalculates the physical candidate-package SHA-256 and compares it with the HRDR and promotion authorization;
6. executes `promote-pr -DryRun` again immediately before release and requires exact zero-side-effect PASS evidence;
7. performs a fresh read-back of the default branch, candidate PR and authorization record;
8. executes the canonical `promote-pr -Pr <PR> -Version <VERSION> -ConfirmPromotion` path;
9. runs release validation before any canonical tag is created;
10. after PASS, materializes the canonical release package, annotated tag and GitHub Release using the existing release publication contract;
11. performs fresh server-side read-back proving the default branch is unchanged, the controlled PR remains open and unmerged, the tag resolves to the frozen source SHA and the GitHub Release contains the canonical package plus `result.json` and `result.md`;
12. uploads an audit artifact containing authorization, exact evidence, dry-run evidence, release report, package and final read-back.

## Permissions and secrets

The workflow runs in environment `ddda-backlog-governance`.

- `GITHUB_TOKEN` is scoped to the workflow and needs `contents: write` only because canonical promotion creates the tag and GitHub Release.
- `DDDA_GITHUB_PROJECT_TOKEN` remains an environment secret used only for the authoritative Release Scope Gate read-back.
- no secret value is written to Git, Chat, workflow artifacts or release assets.

## Recovery boundary

A failed release validation must not create a canonical tag or GitHub Release. If an irreversible side effect fails after release validation, preserve all workflow evidence and follow the bounded release-recovery procedure; do not rebuild or mutate the frozen controlled candidate to manufacture replacement evidence.
