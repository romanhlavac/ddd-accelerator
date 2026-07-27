# Issue and PR linking examples

## Work Package parent

```markdown
## Delivery slices

- [ ] #201 P0–P10 lifecycle contract
- [ ] #202 Wardley Mapping artifact
- [ ] #203 Portfolio prioritization
```

## Child Change Request

```markdown
Parent Work Package: WP-09 — #200
Blocked by: WP-08 / PR #8 release-grade lifecycle
Related ADR: docs/adr/0003-github-native-backlog-governance.md
Target release: TBD
```

## Draft PR

```markdown
Parent Work Package: WP-09 — #200
Implements #201
```

Use `Closes #201` only when the PR fully satisfies the Child Issue Definition of Done. Use `Implements #201` when the Issue requires additional PRs or post-merge evidence.

## Residual risk

```markdown
AMBER residual risk

- Risk: ...
- Owner: ...
- Follow-up: #...
- Accepted by: <human identity>
- Applies to reviewed SHA: <sha>
```

## Blocker

```markdown
Backlog transition

- Previous state: In progress
- New state: Blocked
- Reason: ...
- Blocked by: #...
- Owner: ...
- Unblock condition: ...
- Next review: YYYY-MM-DD
```
