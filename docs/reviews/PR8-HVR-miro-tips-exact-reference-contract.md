# PR8 HVR-2 — Miro Tips exact-reference contract

Status: corrective contract for the next HVR candidate after human rejection

## Human requirement

`Miro Tips` is a **reference-derived artifact**. The visible target must reproduce the approved reference frame from board `uXjVH2vcvRI=`, frame `3458764679531043366`. This is a no-design zone: no redesign, reinterpretation, composite replacement, alternative onboarding layout, or readability optimization may replace the visible reference unless a human explicitly changes the requirement.

The latest HVR changed one implementation constraint without changing the visible reference: direct connector attachment to the screenshot is not acceptable when Miro normalizes the rendered endpoint. Invisible technical control anchors are therefore permitted only as transport mechanics required to reproduce the authored reference arrowhead landing points. They must not add visible content or alter the approved layout.

## Frozen mechanical oracle

The exact-reference contract was frozen by commit `67805d87b4195379af5524494c4941926c9a1565` at `2026-08-14T14:05:26Z`. The source oracle remains:

- frame geometry: `1919.433 × 1079.681`;
- one reference background image, id `3458764679531043367`;
- historical raw rendition SHA-256 observed at freeze: `04b83ec7d9bc07ae31c7c11c03ec974ff4bde00d7773d7f9e55036e877f6fffd`;
- the reference image item must report `modifiedAt <= 2026-08-14T14:05:26Z`; a later item mutation invalidates the frozen reference even when the Miro item ID is unchanged;
- 17 **visible** child items: image `1`, sticky notes `13`, text `3`;
- all three reference text items use font size `20`;
- eight tutorial connectors;
- connector shape `curved`, black normal stroke, stealth arrowhead;
- every source connector terminates on the reference background image and retains its authored arrowhead endpoint position;
- required reference text markers remain present.

Miro `imageUrl` is a rendition transport and may re-encode an unchanged image. Therefore the historical raw SHA is forensic evidence of the rendition observed at freeze, not a requirement that every later CDN response contain identical bytes. Current rendition bytes must remain readable; mutation protection is provided by the pinned image identity plus the frozen `modifiedAt` boundary. During HVR materialization, the live Platform Lab and copied HVR renditions are also compared to prove copy fidelity.

## Target render-fidelity contract

The target is allowed to differ physically only by eight invisible technical control anchors. The visible reference topology remains exactly 17 items.

Required target behavior:

1. retain/create the screenshot background before the visible sticky/text overlays;
2. place the 13 sticky notes and 3 text items above that screenshot background;
3. derive each control anchor from the corresponding frozen source connector `endItem.position` and the target screenshot geometry;
4. use one transparent `8 × 8` child anchor per tutorial callout;
5. terminate each generated tutorial connector on its control anchor, not directly on the screenshot image;
6. require zero direct-image tutorial connectors in the target;
7. preserve the source connector shape/style/caps and any authored start-side attachment semantics exposed by the API;
8. require a zero-mutation second reconcile for visible items, anchors and connectors.

The technical anchor policy is:

```text
layer:    background_image_before_native_callouts_v2
anchor:   transparent_control_anchor_from_reference_arrowhead_v2
endpoint: reference_arrowhead_position_to_control_anchor_v2
```

This policy exists solely because a previous HVR proved that direct screenshot-image attachment can pass structural read-back while rendering the arrowhead at the wrong UI control.

## Evidence semantics

Automated evidence may prove **reference structure match** and **render-fidelity preconditions**. It must not call those checks human visual equivalence.

```text
technical_status = PASS
human_review_status = PENDING
```

means only `READY_FOR_HUMAN_REVIEW`. Human Visual Review remains the sole authority for visual acceptance.

## Regression policy

Tests must fail for at least these regressions:

- `20 → 24` font drift;
- missing visible child item;
- missing tutorial connector;
- changed source arrowhead endpoint;
- missing/drifted transparent target control anchor;
- any target tutorial connector terminating directly on the screenshot image;
- a layer repair that deletes/recreates the background after native overlays;
- non-zero second reconcile;
- reference image `modifiedAt` later than the freeze boundary;
- unreadable image rendition;
- reintroduction of the retired `reference_composite_image / 1 image / 0 connectors` target contract.

A transport-only byte change of an otherwise unchanged pinned source image must not fail the frozen source oracle.

## HVR boundary

The FAST-LOOP must continue automatically through corrective implementation, deterministic tests, exact-SHA GitHub Actions, online `DDDA_PLATFORM_LAB` reconcile/read-back/idempotence and server-side `DDDA_HVR` materialization. The reviewer is requested only when the fresh exact-SHA HVR candidate is ready.

MCP availability or quota is not a technical gate because the authoritative online execution plane is profile-isolated REST in GitHub Actions.

Any source/doc/test change after the candidate SHA is frozen invalidates final HVR evidence and requires a new candidate/materialization.

No merge, promotion, release, tag or gate approval is authorized by this corrective change.
