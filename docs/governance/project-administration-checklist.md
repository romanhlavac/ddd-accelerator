# GitHub administration checklist

This checklist tracks repository-administration actions that cannot be guaranteed by committed files alone.

## GitHub Project

- [ ] Create `DDDA Platform Backlog`.
- [ ] Add fields and values from `config/governance/backlog-policy.yaml`.
- [ ] Create all views from `docs/governance/github-project-setup.md`.
- [ ] Configure safe status automations.
- [ ] Do not automate Priority, Target Release, Human Review PASS or release decisions.
- [ ] Add PR #8, Issues #9–#15 and all new WP/child issues.

## Milestones

- [ ] Create `DDDA 0.1.0`.
- [ ] Assign PR #8 and only approved release blockers.
- [ ] Leave WP-09, WP-10 and WP-11 without milestone until target releases are decided.

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
- [ ] Review who can administer Project fields, Milestones and repository rules.
