# GitHub administration checklist

This checklist tracks repository-administration actions that cannot be guaranteed by committed files alone.

## GitHub Project

- [ ] Create `DDDA Platform Backlog & Delivery`.
- [ ] Add all custom fields and exact values from `config/governance/backlog-policy.yaml`.
- [ ] Add `Start date`, `Target date` and `Outcome summary`.
- [ ] Enable/show system fields `Parent issue`, `Sub-issue progress`, `Milestone` and `Linked pull requests` in relevant views.
- [ ] Create/verify `Plánování a Backlog` as Table with filter `is:issue`.
- [ ] Create/verify `Implementace a Delivery` as Table with filter `is:pr is:open`.
- [ ] Keep any additional analytical views optional and non-authoritative.
- [ ] Keep items with unknown dates unscheduled; do not invent dates for visualization.
- [ ] Configure safe status automations.
- [ ] Do not automate Priority, Target Release, dates, Human Review PASS, dependencies or release decisions.
- [ ] Ensure all governed WP/CR Issues are planning items and every open implementation PR is a delivery item; apply only the explicit PR #8 legacy exception for primary-CR mapping.

## Native hierarchy

- [ ] #17 is the native parent of #9–#15.
- [ ] #18 is the native parent of #21–#26.
- [ ] #19 is the native parent of #27–#33.
- [ ] #20 is the native parent of #34–#41.
- [ ] Prefixes such as `[WP-09]` remain navigation aids, not the only hierarchy representation.
- [ ] Parent Issues display native Sub-issue progress.
- [ ] Implementation PRs are not Sub-issues; every open implementation PR is a Project delivery projection linked to exactly one primary CR, except the versioned PR #8 legacy exception.

## Native dependencies

- [ ] Configure `Blocked by` / `Blocking` edges according to `config/governance/backlog-policy.yaml`.
- [ ] Record rationale in Issue body/comment or Project Dependency field.
- [ ] Verify WP-08 critical path remains consistent with Issue #15.
- [ ] Verify WP-09 sequencing: #21/#22 → #23/#24 → #25 → #26.
- [ ] Verify WP-10 sequencing: #27 and #31 enable adapters/incremental work; #28–#33 enable #33.
- [ ] Verify WP-11 sequencing: #34→#35, #36→#37→#38, #36/#37/#38→#39, #37/#38/#39→#40, #35/#40→#41.
- [ ] Dependencies do not automatically set Priority, dates or human decisions.

## Initial Work Package metadata

- [ ] WP-08: Status `Blocked`, Target Release `0.1.0`, current Human Review state reflected without changing its authority.
- [ ] WP-09: Status `Backlog`, Target Release `TBD`, no dates until decided.
- [ ] WP-10: Status `Backlog`, Target Release `TBD`, no dates until decided.
- [ ] WP-11: Status `Backlog`, Target Release `TBD`, no dates until decided.
- [ ] Outcome summary values match the machine-readable backlog policy.
- [ ] Priority is assigned through explicit triage, not inferred from WP number.

## Milestones

- [ ] Create `DDDA 0.1.0`.
- [ ] Assign PR #8 and only explicitly approved release blockers.
- [ ] Do not add Parent WP #17 if it would double-count release progress.
- [ ] Leave WP-09, WP-10 and WP-11 without milestone until target releases are decided.
- [ ] Keep Project `Target Release` consistent with actual Milestone assignment.
- [ ] Record milestone scope evidence in Issue #42.

## Evidence

- [ ] Capture screenshots or review notes for Project fields.
- [ ] Capture screenshots or review notes for all views.
- [ ] Capture native parent/sub-issue hierarchy evidence.
- [ ] Capture dependency relationship evidence.
- [ ] Capture Milestone scope and progress evidence.
- [ ] Record any deviation from the versioned contract and update docs/policy before closing #42.

## Optional labels

Recommended labels:

```text
kind:gap
kind:work-package
kind:change-request
kind:defect
kind:risk
kind:enabler
priority:P0
priority:P1
priority:P2
priority:P3
impact:low
impact:medium
impact:high
impact:breaking
status:blocked
human-review:pending
human-review:red
human-review:amber
human-review:green
area:methodology
area:orchestration
area:ingestion
area:testing
area:release
area:security-governance
```

Project fields remain the authority for priority and status. Labels are search/navigation aids and must not become a conflicting parallel state model.

## Repository settings

- [ ] Keep squash merge as the standard promotion policy.
- [ ] Prevent direct main changes through branch protection/ruleset where available.
- [ ] Require relevant CI checks before merge.
- [ ] Ensure PR template and Issue Forms are enabled after governance PR merge.
- [ ] Review who can administer Project fields, native hierarchy, dependencies, Milestones and repository rules.
