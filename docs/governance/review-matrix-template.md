# Scope review matrix template

Use this template before a platform PR is approved for promotion.

## Reviewed state

```text
PR: #<number>
Head SHA: <exact-sha>
Parent Work Package: WP-XX — #<issue>
Change Request: #<issue>
Candidate package hash: <sha256>
Validation report: <path-or-link>
```

## Evidence matrix

| Requirement | Implementation evidence | Test evidence | Documentation evidence | Status | Finding / action |
|---|---|---|---|---|---|
| Goal ... | file/function/diff | suite/report | doc/ADR | covered | — |
| In scope ... | ... | ... | ... | partial | ... |
| Out of scope ... | unexpected diff | ... | ... | scope creep | split/remove/update scope |

Allowed statuses:

- `covered` — requirement is fully implemented and evidenced;
- `partial` — meaningful part exists but acceptance is not complete;
- `missing` — required capability/evidence is absent;
- `scope creep` — change exists outside approved scope.

## Review decisions

### GREEN

All required items are covered; no unresolved safety or functional defect.

### AMBER

No blocking RED finding; each residual risk has:

- explicit description;
- owner;
- mitigation or monitoring;
- follow-up Issue;
- acceptance by authorized human reviewer.

### RED

At least one of:

- safety/security/data-integrity defect;
- automatic human approval or spoofed provenance;
- required acceptance criterion missing;
- release evidence invalid for current SHA;
- breaking impact without migration path;
- human usability or methodology acceptance failed;
- uncontrolled scope creep affecting release decision.

RED blocks promotion.

## Final recommendation

```text
GO | GO_WITH_ACCEPTED_RISKS | NO_GO
```

This recommendation is input to HRDR. The matrix itself is not an automated release approval.
