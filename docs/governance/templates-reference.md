# Governance templates reference

## Issue forms

Repository provides:

- `.github/ISSUE_TEMPLATE/gap.yml` — new idea or discovered GAP;
- `.github/ISSUE_TEMPLATE/work-package.yml` — parent roadmap Work Package;
- `.github/ISSUE_TEMPLATE/change-request.yml` — concrete child implementation requirement.

## Pull request template

`.github/PULL_REQUEST_TEMPLATE.md` requires:

- parent Work Package and Change Request links;
- actual implemented and explicitly excluded scope;
- platform classification and impact;
- acceptance coverage matrix;
- exact-SHA validation evidence;
- human review and HRDR status;
- residual risks;
- confirmation that the PR is an implementation unit, not a roadmap placeholder.

## Text fallback — Work Package

```markdown
# Work Package: WP-XX — [title]

## Desired outcome
...

## Problem / GAP
...

## Business and platform value
...

## In scope
- ...

## Out of scope
- ...

## Boundaries
...

## Quality attributes and constraints
- ...

## Delivery slices / Child Issues
- [ ] ...

## Acceptance criteria
- [ ] ...

## Dependencies
...

## Risks and mitigations
...

## Target release
TBD

## Exit criteria
...
```

## Text fallback — Change Request

```markdown
# Change Request: [title]

## Parent Work Package
WP-XX — #...

## Goal
...

## Problem
...

## In scope
- ...

## Out of scope
- ...

## Classification
Platform areas: ...
Impact: LOW | MEDIUM | HIGH | BREAKING
Migration impact: None | Non-breaking | Breaking

## Acceptance criteria
- [ ] ...

## Required repository changes
- ...

## Required tests
- [ ] lint
- [ ] schema
- [ ] unit
- [ ] component
- [ ] integration
- [ ] smoke
- [ ] regression
- [ ] security/isolation
- [ ] acceptance
- [ ] E2E
- [ ] migration/compatibility
- [ ] manual review

## Expected evidence
...

## Dependencies
...

## Risks and mitigations
...

## Definition of Done
...
```

## HRDR boundary

HRDR template/schema is governed by the Human Review capability tracked under WP-08. This governance package defines its authoritative role but does not create a competing HRDR contract while PR #8 Human Review remediation is active.
