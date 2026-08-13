# Roadmap Work Package and GitHub backlog index

Parent/sub-issue represents capability ownership. Native `blocked by` represents direct completion dependency. Priority/order is authoritative in GitHub Project.

## Recommended implementation order

1. **WP-08 / #17 — P0**: close current PR #8 / DDDA 0.1.0 foundation.
2. **WP-11 / #20 — P1**: EventStorming methodology & workshop runtime.
3. **WP-12 / #60 — P2**: Miro platform environments & lifecycle; may overlap WP-11 after stable PR8 Miro baseline.
4. **WP-13 / #61 — P3**: multi-agent orchestration & evidence synthesis.

## WP-08 — #17

Children: #9–#15 only. PR #8 remains the implementation under closure. No new feature scope.

#45 is now cross-cutting `Work Package: Other`.

## WP-09 — #18

Children: #21, #22, #23, #24, #25, #50, #26, #51.

## WP-10 — #19

Children: #27–#33.

## WP-11 — #20 EventStorming

Children: #34, #52, #35, #47, #48, #46, #62.

Dependency model:

```text
#34 + #52 → #35
#27 + #31 + #32 + #34 + #35 → #47
#34 + #35 + #47 + #48 + #52 → #62
#47 + #62 + #48 + #52 → #46
```

## WP-12 — #60 Miro platform environments

Children: #53, #54, #55, #56, #57.

```text
#53 → #57
#54 → #57
#55 → #57
```

## WP-13 — #61 Multi-agent

Children: #36, #37, #38, #39, #40, #41.

```text
#36 → #37 → #38
#36 + #37 + #38 → #39
#37 + #38 + #39 → #40
#36 + #37 + #38 + #39 + #40 → #41
```

## Cross-cutting

- #16 — GitHub-native backlog governance;
- #45 — GitHub Pages Artifact Registry dashboard (`Other`);
- #49 — role-based documentation IA (`Other`), blocked by #16, #46, #48 and #53.

## Boundary invariant

WP-11 base EventStorming does not have a mandatory dependency on WP-13. WP-13 output can be an optional analytical input only.
