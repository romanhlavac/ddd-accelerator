# Backlog status and relationship model

## Relationship types

```text
GAP Issue
  discovered need; may be triaged into a Work Package or Change Request.

Work Package Parent Issue
  owns roadmap outcome and delivery-slice checklist.

Child Change Request
  owns concrete implementation scope and acceptance criteria.

Pull Request
  implements or closes a Child Change Request.

ADR
  records a long-lived decision required by one or more Change Requests.

Milestone
  groups approved release scope.

GitHub Project
  controls order, priority, status and operational views.
```

## Relationship notation

Use explicit references in Issue and PR bodies/comments:

```markdown
Parent Work Package: WP-09 — #<parent>
Child of: #<parent>
Implements: #<child>
Blocked by: #<issue-or-pr>
Blocks: #<issue-or-pr>
Related ADR: docs/adr/NNNN-....md
Target Milestone: DDDA X.Y.Z | TBD
```

If native GitHub sub-issues are available, use them in addition to the textual links. The Parent Issue checklist remains a readable roadmap summary.

## Status ownership

- Issue body: requested outcome, scope and acceptance.
- GitHub Project Status: current operational state.
- Issue comments: state transitions, blocker details and decisions.
- PR state: implementation/review state, not roadmap priority.
- Roadmap document: aggregated Work Package state.

## Required transition comment

When an item becomes Blocked, Ready, Cancelled or materially rescoped, add a short decision comment:

```markdown
Backlog transition

- Previous state: ...
- New state: ...
- Reason: ...
- Decision owner: ...
- Dependencies / evidence: ...
- Next review or unblock condition: ...
```

Routine automated transitions such as PR opened → In progress need not generate a verbose comment if Project automation is trustworthy and the branch/PR link is visible.
