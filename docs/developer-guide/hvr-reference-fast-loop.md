# HVR reference-fidelity fast loop

## Purpose

Prevent repeated Human Visual Review failures caused by requirement drift, circular tests, stale candidates, or expensive full-pipeline feedback on trivial visual corrections.

## Mandatory flow for reference-derived artifacts

1. **Freeze reference first.** Read the actual reference and persist the mechanical oracle: identity, geometry, content, styles, topology, connector endpoints and immutable asset hashes where applicable.
2. **Classify exact-reference work as NO-DESIGN-ZONE.** “Same as reference” forbids redesign or implementation substitution unless the reviewer explicitly authorizes it.
3. **Run a red test before repair.** Prove the current defect is detected by the oracle.
4. **Use property-by-property diff.** Cardinality-only checks are insufficient. Compare visible content, relative geometry, styles, routing semantics, endpoint attachment and asset identity.
5. **Mutation-test the oracle.** Intentionally vary the properties that previously failed and require the test to turn red.
6. **Use an artifact-level fast loop first.** Do not spend full CI/package/HVR cycles until the local artifact contract passes.
7. **Perform independent live read-back.** Validate the target as returned by Miro, not the payload the writer intended to send.
8. **Require zero-mutation second reconcile.** Idempotence is a mechanical gate.
9. **Materialize an immutable HVR candidate.** Evidence identifies Git SHA, board, frame and frozen oracle. Any later target mutation invalidates that candidate.
10. **Keep human review judgment-heavy.** Humans judge visual usability and acceptance; missing items, wrong fonts, wrong endpoints and stale topology are automated failures.

## Fail-closed rules

- A technical limitation is a FAIL, not permission to reinterpret an exact-reference requirement.
- Structural PASS cannot substitute for Human Visual Review.
- A test derived from the implementation rather than the external reference is not an acceptance oracle.
- Full CI is a downstream gate; it is not the first feedback mechanism for a local visual defect.
- Never mark `READY_FOR_HUMAN_REVIEW` when reference-vs-live diff is non-zero.

## Evidence required before HVR

- exact Git SHA;
- reference identity and frozen property contract;
- target board/frame identity;
- reference-vs-target mechanical diff = zero;
- mutation-test PASS;
- live read-back PASS;
- second reconcile zero mutation;
- protected-frame regression PASS;
- standard exact-SHA CI PASS.
