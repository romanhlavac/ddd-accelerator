# PR8 HVR-2 — Miro Tips exact-reference contract

Status: corrective contract for the next HVR-2 candidate

## Human requirement

`Miro Tips` is a **reference-derived artifact**. The target must reproduce the approved reference frame from board `uXjVH2vcvRI=`, frame `3458764679531043366`. This is a no-design zone: no redesign, reinterpretation, composite replacement, alternative onboarding layout, endpoint anchors, or readability optimization may replace the reference unless a human explicitly changes the requirement.

## Frozen mechanical oracle

The technical gate pins and verifies before any target reconciliation:

- frame geometry: `1919.433 × 1079.681`;
- one reference background image, id `3458764679531043367`, SHA-256 `04b83ec7d9bc07ae31c7c11c03ec974ff4bde00d7773d7f9e55036e877f6fffd`;
- 17 child items: image `1`, sticky notes `13`, text `3`;
- all three reference text items use font size `20`;
- eight tutorial connectors;
- connector shape `curved`, black normal stroke, stealth arrowhead;
- every connector terminates on the reference background image and retains its authored arrowhead endpoint position;
- required reference text markers remain present.

The target read-back must match the same native topology and property contract after source-to-target ID mapping. A second reconcile must be zero-mutation.

## Regression policy

Tests must fail when any of these mutations are introduced: `20 → 24` font drift, missing child item, missing connector, changed connector endpoint, changed background bytes, or reintroduction of the retired `reference_composite_image / 1 image / 0 connectors` target contract.

## HVR boundary

Technical PASS means only that the exact-reference mechanical contract is satisfied for the exact Git SHA and live read-back. Human Visual Review remains the authority for visual acceptance. A target mutation after candidate materialization invalidates the previous HVR evidence.

No merge, promotion, release, tag or gate approval is authorized by this corrective change.
