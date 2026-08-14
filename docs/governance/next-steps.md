# Governance rollout next steps

1. Commit the Backlog + Delivery projection contracts to PR #63 on an exact-SHA-bound atomic commit.
2. Validate that exact PR #63 SHA through `Validate DDDA` and the governance contract regression tests.
3. Run privileged Project reconciliation from the committed exact SHA; rename/reuse the Project as `DDDA Platform Backlog & Delivery`.
4. Verify `Plánování a Backlog` (`is:issue`) and `Implementace a Delivery` (`is:pr is:open`).
5. Read back all governed WP/CR planning items and every open implementation PR delivery item; require `remaining_mismatches = 0`.
6. Keep PR #8 source branch/head untouched; its only exception is the versioned WP-08 legacy mapping until merge/close.
7. Update PR #63 evidence and request Human Review. Technical PASS does not imply Human Review, merge, promotion or release approval.
