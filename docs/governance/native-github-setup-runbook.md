# Native GitHub setup runbook

## Purpose

This runbook creates the live GitHub structures that cannot be produced by repository files alone:

- native Parent/Sub-issue relationships;
- native issue dependencies;
- GitHub Project fields and views;
- Project item metadata;
- Milestone and release-scope assignments.

The authoritative execution/evidence Issue is #42. The machine-readable target state is `config/governance/backlog-policy.yaml`.

## 1. Native Sub-issues

Create these parent/child relationships:

```text
#17 → #9,#10,#11,#12,#13,#14,#15
#18 → #21,#22,#23,#24,#25,#26
#19 → #27,#28,#29,#30,#31,#32,#33
#20 → #34,#35,#36,#37,#38,#39,#40,#41
```

GitHub CLI:

```powershell
gh issue edit 17 -R romanhlavac/ddd-accelerator --add-sub-issue 9,10,11,12,13,14,15
gh issue edit 18 -R romanhlavac/ddd-accelerator --add-sub-issue 21,22,23,24,25,26
gh issue edit 19 -R romanhlavac/ddd-accelerator --add-sub-issue 27,28,29,30,31,32,33
gh issue edit 20 -R romanhlavac/ddd-accelerator --add-sub-issue 34,35,36,37,38,39,40,41
```

PR #8 and Draft PR #43 are linked implementations, not Sub-issues.

## 2. Native dependencies

### WP-08

```powershell
gh issue edit 14 -R romanhlavac/ddd-accelerator --add-blocked-by 13
gh issue edit 12 -R romanhlavac/ddd-accelerator --add-blocked-by 14
gh issue edit 11 -R romanhlavac/ddd-accelerator --add-blocked-by 12
gh issue edit 10 -R romanhlavac/ddd-accelerator --add-blocked-by 11
gh issue edit 9  -R romanhlavac/ddd-accelerator --add-blocked-by 10
```

### WP-09

```powershell
gh issue edit 23 -R romanhlavac/ddd-accelerator --add-blocked-by 21,22
gh issue edit 24 -R romanhlavac/ddd-accelerator --add-blocked-by 22,23
gh issue edit 25 -R romanhlavac/ddd-accelerator --add-blocked-by 21,24
gh issue edit 26 -R romanhlavac/ddd-accelerator --add-blocked-by 25
```

### WP-10

```powershell
gh issue edit 28 -R romanhlavac/ddd-accelerator --add-blocked-by 27,31
gh issue edit 29 -R romanhlavac/ddd-accelerator --add-blocked-by 27,31
gh issue edit 30 -R romanhlavac/ddd-accelerator --add-blocked-by 27,31
gh issue edit 32 -R romanhlavac/ddd-accelerator --add-blocked-by 27
gh issue edit 33 -R romanhlavac/ddd-accelerator --add-blocked-by 28,29,30,31,32
```

### WP-11

```powershell
gh issue edit 35 -R romanhlavac/ddd-accelerator --add-blocked-by 34
gh issue edit 37 -R romanhlavac/ddd-accelerator --add-blocked-by 36
gh issue edit 38 -R romanhlavac/ddd-accelerator --add-blocked-by 37
gh issue edit 39 -R romanhlavac/ddd-accelerator --add-blocked-by 36,37,38
gh issue edit 40 -R romanhlavac/ddd-accelerator --add-blocked-by 37,38,39
gh issue edit 41 -R romanhlavac/ddd-accelerator --add-blocked-by 35,40
```

Dependencies express logical prerequisites. They do not assign dates, priorities or approvals.

## 3. GitHub Project

Create a user Project:

```text
Name: DDDA Platform Backlog
Layout: Table
Owner: romanhlavac
```

Add:

- PR #8;
- Issues #9–#42;
- Draft PR #43;
- Issue #44.

Do not bulk-import unrelated historical items.

## 4. Fields

Custom fields:

- Status: Backlog, Discovery, Triaged, Ready, In progress, In review, Blocked, Done, Cancelled;
- Priority: P0, P1, P2, P3;
- Work Package: WP-08, WP-09, WP-10, WP-11, Other;
- Item Type: GAP, Work Package, Change Request, Defect, Risk, Enabler;
- Platform Area: DDDA platform taxonomy;
- Impact: LOW, MEDIUM, HIGH, BREAKING;
- Target Release: text;
- Start date: date;
- Target date: date;
- Outcome summary: text;
- Owner: person;
- Blocked: boolean;
- Human Review: Not required, Pending, PASS, FAIL, Accepted risks;
- Dependency: text projection/rationale.

Enable system fields:

- Parent issue;
- Sub-issue progress;
- Milestone;
- Linked pull requests;
- Assignees.

Do not invent dates or future target releases.

## 5. Views

Create and save:

1. `Work Packages` — Table, filter `Item Type = Work Package`, show outcome and Sub-issue progress.
2. `WP hierarchy` — Table grouped by Parent issue.
3. `Delivery board` — Board by Status.
4. `Roadmap by Work Package` — Roadmap using Start date and Target date, grouped by WP, milestone markers enabled.
5. `Release scope` — Table grouped by Milestone.
6. `Blocked and P0` — filter Blocked/P0.
7. `Human review queue` — filter In review or Human Review Pending.
8. `Ready without owner` — filter Ready and empty Owner.
9. `Recently completed` — filter Done.

Unscheduled roadmap items remain visible. Dates remain blank until explicitly decided.

## 6. Initial metadata

Parent Work Packages:

```text
#17 WP-08: Blocked, Target Release 0.1.0, Human Review Pending
#18 WP-09: Backlog, Target Release TBD
#19 WP-10: Backlog, Target Release TBD
#20 WP-11: Backlog, Target Release TBD
```

Children inherit the matching Work Package field. WP-09 through WP-11 priorities remain unset until prioritization.

PR #8: WP-08, Blocked, Target Release 0.1.0, Human Review Pending.

Draft PR #43: blocked by PR #8 resolution; target release remains undecided.

## 7. Milestone

Create:

```text
DDDA 0.1.0
```

Assign:

- PR #8;
- Issues #9–#15.

Do not assign Parent WP #17 because it would duplicate release-progress counting. Do not assign WP-09 through WP-11 or Draft PR #43 without a separate release decision.

Leave the due date empty until an approved date exists.

## 8. Safe workflows

Allowed examples:

- item added → Backlog;
- closed Issue → Done;
- reopened Issue → Triaged;
- merged PR → PR item Done.

Never automate:

- Priority;
- Target Release or Milestone;
- dates;
- Human Review PASS;
- gate `passed`;
- HRDR or GO/NO-GO;
- closing a Parent WP after one PR merge.

## 9. Verification

Before closing #42 verify:

- every child has the expected native parent;
- every specified dependency is visible;
- Project fields and all nine views exist;
- parent progress is visible;
- roadmap does not contain fabricated dates;
- Milestone contains only PR #8 and #9–#15;
- no human approval is automated;
- evidence/screenshots and deviations are recorded in #42.
