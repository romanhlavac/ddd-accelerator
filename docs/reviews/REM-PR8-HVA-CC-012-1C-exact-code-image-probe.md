# REM-PR8-HVA-CC-012.1C — Exact-code online Miro image probe

## Status

IMPLEMENTED, PENDING EXACT-SHA CI

## Goal

Execute the managed Miro image transport from the exact candidate package and publish machine-readable online evidence for all three declared source assets.

## Acceptance

- the candidate package is built from and proves the exact PR head SHA;
- the probe runs from the expanded candidate package, not the source checkout;
- all three declared source items are resolved under their declared source frames;
- every created target item is remotely re-read and verified as Miro type `image`;
- source board, frame and item provenance and SHA-256 semantic identity are recorded;
- the second reconcile performs zero create/update operations and preserves target IDs;
- the diagnostic board is deleted and the deletion is remotely verified;
- a standalone JSON evidence artifact is uploaded for the exact SHA.

## Boundary

This remediation validates transport mechanics only. It does not modify the preserved human-review board or frames `00`, `01`, `10`, or `20+`; the existing visual-review finding remains unresolved.
