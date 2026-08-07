# Implementation notes for backlog governance rollout

## Rollout strategy

Governance foundation is implemented in a separate branch and Draft PR based on `main` so that the frozen or reviewed source state of PR #8 is not modified.

Safe PR #8 migration consists only of:

- creating parent Work Package `WP-08`;
- linking PR #8 and Issues #9–#15 through GitHub comments/relationships;
- preserving current issue bodies and review evidence;
- leaving PR #8 source branch and head SHA unchanged.

After PR #8 is merged or otherwise resolved, this governance PR must be rebased onto the current `main`. Any overlapping documentation index, changelog or repository contract changes must then be reconciled and revalidated.

## Administration not stored by Git

The following GitHub objects cannot be represented solely by repository files:

- GitHub Project and its custom fields/views;
- Milestones and their issue assignments;
- Project item ordering;
- issue parent/sub-issue relationships when native sub-issues are unavailable;
- labels and repository rulesets.

Their desired configuration is versioned in:

- `config/governance/backlog-policy.yaml`;
- `docs/governance/github-project-setup.md`.

Actual GitHub configuration remains an administrative action and must be checked against these contracts.

## Deferred integration points

Until PR #8 is resolved, this Draft PR intentionally avoids editing files heavily changed by PR #8, especially:

- root `README.md`;
- `USAGE.md`;
- `docs/README.md`;
- `CHANGELOG.md`;
- PR #8 source files and validation contracts.

Before this governance PR becomes Ready for review:

1. rebase onto current `main`;
2. link governance docs from `docs/README.md`;
3. add the delivered governance change to `CHANGELOG.md`;
4. run repository contracts and documentation validation;
5. update roadmap issue links with final GitHub issue numbers;
6. perform scope review and validation for the rebased exact SHA.
