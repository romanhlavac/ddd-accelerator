# Periodic backlog and delivery review checklist

## New items

- [ ] Every new GAP has origin and evidence.
- [ ] No idea is represented only by an empty branch or planned PR.
- [ ] Duplicates and obsolete items are identified.

## Work Packages and planning projection

- [ ] Every active WP has a stable `WP-XX` ID.
- [ ] Outcome, boundaries and exit criteria remain valid.
- [ ] Child Issue checklist matches actual delivery slices.
- [ ] Native Parent/Sub-issue ownership agrees with Project `Work Package` for governed CRs.
- [ ] Every active WP and governed CR required by policy is present and correctly classified in `DDDA Platform Backlog & Delivery`.
- [ ] The canonical planning view is `Plánování a Backlog`, layout `Table`, filter `is:issue`.

## Ready queue

- [ ] Goal, scope and acceptance criteria are complete.
- [ ] Impact and migration impact are known.
- [ ] Dependencies are resolvable.
- [ ] Owner is known.
- [ ] Required ADR/discovery is complete or explicitly part of the item.
- [ ] Pre-change WP/backlog/delivery consistency read-back found no unexplained authority conflict.

## Active implementation and delivery projection

- [ ] Every active branch has an Issue and Draft/active PR.
- [ ] Every open platform PR has exactly one primary `Implements #<CR>` or `Closes #<CR>` relationship, unless it has an explicit versioned legacy exception.
- [ ] `Refs`, `Related`, title prefixes or stacked Git ancestry are not used as a substitute for primary implementation authority or WP ownership.
- [ ] Every open implementation PR is present in `DDDA Platform Backlog & Delivery` as a delivery Project item.
- [ ] PR Project `Work Package` is derived from the primary CR and equals its authoritative Work Package.
- [ ] PR Project `Item Type` is unset; a delivery PR is not a second Change Request or planning authority.
- [ ] PR Project `Status` is `Blocked` when `Blocked = Yes`; otherwise Draft PR is `In progress` and a non-draft open PR is `In review`.
- [ ] If Issue/PR title contains `[WP-XX]`, the prefix matches authoritative Work Package.
- [ ] Long-inactive Draft PRs are closed, resumed or re-triaged.
- [ ] PR scope remains aligned with its primary CR.
- [ ] The canonical delivery view is `Implementace a Delivery`, layout `Table`, filter `is:pr is:open`.

## Mandatory consistency read-back

- [ ] A repository-wide pre-read-back was performed before a backlog/WP/governance mutation.
- [ ] A repository-wide post-read-back was performed after the mutation.
- [ ] Read-back covered all active WPs, governed CRs, all open platform PRs, native hierarchy and both Project projections.
- [ ] Read-back checked PR → primary CR mapping and derived WP for every open PR.
- [ ] Read-back checked PR Project membership, `Work Package`, `Status` and absence of planning `Item Type`.
- [ ] Read-back checked Project title and both canonical view filters.
- [ ] Post-change mismatch count is exactly `0`.
- [ ] Any legacy exception is versioned, reasoned and has an expiry condition.
- [ ] Technical governance PASS/Ready/merge recommendation is blocked when any unexplained mismatch remains.
- [ ] Automation did not invent product ownership, primary CR, priority, Human Review result or any gate/release approval.

## Blocked work

- [ ] Blocker is specific.
- [ ] Unblock condition and owner are documented.
- [ ] Blocking relation is linked.
- [ ] Last review date is recent enough.

## Release planning

- [ ] Milestone scope is explicit.
- [ ] `Target Release` matches Milestone where applicable.
- [ ] P0/P1 and RED/AMBER findings are reviewed.
- [ ] CHANGELOG contains only delivered/release-candidate changes.
- [ ] Human Review requirements are visible.

## Completed work

- [ ] Merged PR and evidence exist.
- [ ] Issue closure reason is correct.
- [ ] Parent WP is updated.
- [ ] Roadmap is updated if outcome/state changed.
- [ ] Follow-up residual risks have Issues and owners.
