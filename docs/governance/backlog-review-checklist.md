# Periodic backlog review checklist

## New items

- [ ] Every new GAP has origin and evidence.
- [ ] No idea is represented only by an empty branch or planned PR.
- [ ] Duplicates and obsolete items are identified.

## Work Packages

- [ ] Every active WP has stable `WP-XX` ID.
- [ ] Outcome, boundaries and exit criteria remain valid.
- [ ] Child Issue checklist matches actual delivery slices.
- [ ] Native Parent/Sub-issue ownership agrees with Project `Work Package` for governed CRs.
- [ ] Every active WP and governed CR that policy requires in the Project is present and correctly classified in `DDDA Platform Backlog`.

## Ready queue

- [ ] Goal, scope and acceptance criteria are complete.
- [ ] Impact and migration impact are known.
- [ ] Dependencies are resolvable.
- [ ] Owner is known.
- [ ] Required ADR/discovery is complete or explicitly part of the item.
- [ ] Pre-change WP/backlog consistency read-back found no unexplained authority conflict.

## Active implementation

- [ ] Every active branch has an Issue and Draft/active PR.
- [ ] Every active PR has exactly one primary `Implements #<CR>` or `Closes #<CR>` relationship, unless it has an explicit versioned legacy exception.
- [ ] `Refs`, `Related`, title prefixes or stacked Git ancestry are not used as a substitute for primary implementation authority or WP ownership.
- [ ] Every governed CR is visible in `DDDA Platform Backlog` unless policy explicitly excludes it.
- [ ] CR Project `Work Package` equals authoritative native/versioned WP ownership.
- [ ] PR-declared Work Package equals the Work Package of its primary CR.
- [ ] If planning policy also represents PRs as Project items, their Project fields are consistent with the primary CR.
- [ ] Long-inactive Draft PRs are closed, resumed or re-triaged.
- [ ] PR scope remains aligned with Issue scope.

## Mandatory consistency read-back

- [ ] A repository-wide pre-read-back was performed before a backlog/WP/governance mutation.
- [ ] A repository-wide post-read-back was performed after the mutation.
- [ ] Read-back covered all active WPs, governed CRs, all open platform PRs, native hierarchy and CR Project membership/fields.
- [ ] Read-back checked PR → primary CR mapping and derived WP for every open PR.
- [ ] If planning policy uses PR Project items, those fields were also checked.
- [ ] Post-change mismatch count is exactly `0`.
- [ ] Any legacy exception is versioned, reasoned and has an expiry condition.
- [ ] Technical governance PASS/Ready/merge recommendation is blocked when any unexplained mismatch remains.
- [ ] Automation did not invent product ownership, primary CR, priority or any human approval.

## Blocked work

- [ ] Blocker is specific.
- [ ] Unblock condition and owner are documented.
- [ ] Blocking relation is linked.
- [ ] Last review date is recent enough.

## Release planning

- [ ] Milestone scope is explicit.
- [ ] `Target Release` matches Milestone.
- [ ] P0/P1 and RED/AMBER findings are reviewed.
- [ ] CHANGELOG contains only delivered/release-candidate changes.
- [ ] Human Review requirements are visible.

## Completed work

- [ ] Merged PR and evidence exist.
- [ ] Issue closure reason is correct.
- [ ] Parent WP is updated.
- [ ] Roadmap is updated if outcome/state changed.
- [ ] Follow-up residual risks have Issues and owners.
