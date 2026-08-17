# HVR reference-fidelity fast loop

## Purpose

Prevent repeated Human Visual Review failures caused by requirement drift, circular tests, stale candidates, or expensive full-pipeline feedback on trivial visual corrections.

## Mandatory flow for reference-derived artifacts

1. **Freeze reference first.** Read the actual reference and persist the mechanical oracle: identity, geometry, content, styles, topology, connector endpoints and immutable asset hashes where applicable.
2. **Classify exact-reference work as NO-DESIGN-ZONE.** “Same as reference” forbids redesign or implementation substitution unless the reviewer explicitly authorizes it.
3. **Run a red test before repair.** Prove the current defect is detected by the oracle.
4. **Use property-by-property diff.** Cardinality-only checks are insufficient. Compare visible content, relative geometry, styles, routing semantics, endpoint attachment and asset identity.
5. **Mutation-test the oracle.** Intentionally vary the properties that previously failed and require the test to turn red.
6. **Use an artifact-level fast loop first.** Do not spend full CI/package/HVR cycles until the artifact contract passes its deterministic tests.
7. **Perform independent live read-back.** Validate the target as returned by Miro, not the payload the writer intended to send.
8. **Require zero-mutation second reconcile.** Idempotence is a mechanical gate.
9. **Materialize the HVR candidate from the validated Platform Lab state.** Evidence identifies Git SHA, source board, HVR board/frame and frozen oracle. The current PR #8 path uses a server-side copy into the logical `DDDA_HVR` slot.
10. **Keep human review judgment-heavy.** Humans judge visual usability and acceptance; missing items, wrong fonts, wrong endpoints, layering prerequisites and stale topology are automated failures.
11. **Continue the FAST-LOOP automatically.** After a human `FAIL`, orchestration proceeds through remediation, deterministic tests, exact-SHA CI, online Platform Lab validation and HVR materialization without requesting intermediate user actions. The next user action is requested only when a fresh exact-SHA HVR candidate is ready.

## Fail-closed rules

- A technical limitation is a FAIL for the affected mechanical step, not permission to reinterpret an exact-reference requirement.
- A local tool limitation must not stop independent automated steps. In particular, MCP quota/unavailability is not a blocker for REST-based GitHub Actions validation or HVR materialization.
- Structural PASS cannot substitute for Human Visual Review.
- A test derived from the implementation rather than the external reference is not an acceptance oracle.
- Full CI is a downstream gate; it is not the first feedback mechanism for a local visual defect.
- Never mark `READY_FOR_HUMAN_REVIEW` when reference-vs-live mechanical diff is non-zero or a mandatory render-fidelity precondition is unproven.
- Do not ask the reviewer to validate moving intermediate corrective commits. Freeze and materialize one fresh candidate after automated gates are green.

## Evidence required before HVR

- exact Git SHA;
- reference identity and frozen property contract;
- target Platform Lab board/frame identity;
- reference-vs-target mechanical diff = zero for the declared visible contract;
- render-fidelity guards for previously observed defects;
- mutation-test PASS;
- live REST read-back PASS;
- second reconcile zero mutation;
- protected-frame regression PASS;
- standard exact-SHA CI PASS;
- `DDDA_HVR` server-side materialization from that same validated SHA;
- copied-board technical read-back PASS;
- `human_review_status=PENDING` until the reviewer returns a verdict.
