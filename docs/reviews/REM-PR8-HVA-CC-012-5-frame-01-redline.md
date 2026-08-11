# REM-PR8-HVA-CC-012.5 — Frame 01 redline adoption and review-board recovery

Status: corrective recovery authorized; HVR-2 CHANGES_REQUIRED

Date: 2026-08-10

## Human direction

Frame `01 – DDD Starter journey, gates a iterace` must be taken from the explicitly selected human-review redline board before HVR-2 continues. The redline is authoritative for the journey, phase companions and the visual composition unless a later explicit Human Review finding overrides a specific part.

Source board: `uXjVH2vcvRI=`

Source Frame 01: `3458764679494310883`

Recovery target board: `uXjVH0doLYY=`

Legacy Frame 00 container: `3458764680243144441`

The preserved target board is the active HVR board. All 16 method frames outside Frame 00/01 recovery scope remain protected by before/after canonical snapshots.

## Frame 00 recovery boundary

HVR-1 / Frame 00 was Human ACCEPTED on exact SHA `ddc8e68bbab1bf64c680050347d881d5b485f225`. The legacy Frame 00 container later proved irreducible through Miro API `PATCH` with deterministic `3.0204`.

Recovery therefore treats the legacy ID as a migration anchor. It uses the verified two-copy swap and no Frame-00 geometry or position PATCH is used. The accepted `7000 × 4914.42` geometry and accepted top-left are preserved. A Human visual-equivalence spot check remains pending on the recovered physical board; this does not reopen the accepted methodological decision.

## Frame 01 source-copy contract

The platform scaffold declares `uXjVH2vcvRI=` as the read-only Frame-01 review redline. The main Frame 01 journey and the eight DDD Starter phase companions remain source-driven.

The source-driven reconcile:

- preserves target IDs where semantic identity permits;
- creates missing source items;
- removes target Frame-01 children/connectors absent from the redline;
- remaps connectors;
- preserves companion-frame geometry by translating it with the Frame-01 center delta;
- requires a zero-mutation second run.

Semantic inconsistencies discovered during HVR are not silently corrected unless the Human Review explicitly authorizes that correction.

## Acceptance contract

Technical PASS requires:

- exact-SHA repository CI and candidate-package provenance;
- targeted source/recovery regression tests;
- verified Frame 00 recovery and eight accepted children;
- successful source-to-target Frame 01 reconcile;
- successful companion-frame reconcile;
- zero-mutation second Frame-00 and Frame-01/companion runs;
- unchanged digest for all 16 protected frames;
- machine-readable evidence.

Successful technical execution yields:

```text
technical_status: PASS
human_review_status: PENDING
overall_status: READY_FOR_HUMAN_REVIEW
frame00_hvr_original_decision: ACCEPTED
frame00_visual_equivalence_spot_check: PENDING
```

Technical PASS does not imply HVR acceptance.

## HVR-2 finding — Miro Tips

HVR-2 verdict: `CHANGES_REQUIRED` on 2026-08-10.

### Rejected corrective interpretation

An earlier corrective interpretation replaced the reference visual tutorial with a DDDA-authored `4600 × 2600` card-only guide and explicitly removed the Miro UI screenshot. That implementation was technically testable but failed Human Review.

The reviewer clarified that, for a first-time Miro user, the screenshot/template and callout arrows are not incidental decoration. They are the essential explanatory mechanism: each tip must be visually tied to the actual Miro control it describes. The card-only substitute is therefore rejected.

This latest Human Review supersedes the earlier requirement to avoid screenshot dependency.

### Authoritative reference UI tutorial contract

`Miro Tips` must now preserve the reference-board tutorial concept and relative layout:

- use the reference companion frame geometry and relative placement, approximately `1919.43 × 1079.68`, translated with Frame 01 rather than expanded to `4600 × 2600`;
- contain at least one full Miro UI screenshot/template image;
- retain the reference tutorial stickies/text, including navigation/edit mode, sticky creation, connection lines, Tab, Alt+drag, Shift+drag, right-click drag, undo, frames overview, other-user cursors, facilitator following, map and 100% zoom;
- retain the green `add your own tips here` sticky;
- contain at least eight black callout connectors whose endpoint is anchored to the Miro UI image, preserving the source endpoint position/snap semantics so the arrows point at the actual controls;
- not replace the visual tutorial with generic colored text cards;
- treat the current oversized `Miro Tips` container as irreducible for in-place shrink. Exact-SHA online remediation on `fe6e5f0ad7aade600e988c11d961a2f7141da691` removed its visible children and still received deterministic Miro `HTTP 400 / 3.0204` (`Child item cannot be placed outside the bounds of its parent`) when PATCHing the frame to reference size;
- recover it transactionally: create a new companion at the reference geometry/placement, populate and verify the full UI image/items/connectors, and only then delete the legacy oversized companion. No geometry PATCH of the irreducible legacy frame is allowed;
- permit the physical Miro item ID of the `Miro Tips` companion to change as part of this bounded container migration; the replacement ID becomes the active review object while Frame 01 and all other companion IDs remain outside this correction;
- reconcile idempotently and prove a zero-mutation second run against the replacement frame;
- keep `human_review_status=PENDING` after technical PASS.

The main Frame 01 journey, methodology block and eight DDD Starter phase companions remain unchanged by this correction.


### HVR-2 follow-up finding — callouts hidden behind screenshot

Human Review again returned `CHANGES_REQUIRED` after exact SHA `7082b6724c99349d7466083c0ab8360959e6c98e`. The generated target contained the Miro UI screnshot and black connectors, but the explanatory yellow/green stickies and text were visually obscured. The resulting arrows therefore appeared detached from any explanation.

Gap analysis identified a rendering-order defect in the companion copier: native callout items were created first and the full-frame Miro screenshot image was created afterwards. Because overlapping Miro items are stacked by creation order, the screenshot covered the callout stickies/text while connectors remained visible above it. Structural checks for image count, marker text and connector count therefore passed even though first-viewer usability failed.

The corrective contract is now explicit:

- the Miro UI screenshot is the background layer and MUST be created/reconciled before native stickies/text;
- native callout items MUST be visually above the screenshot;
- connectors are created only after both layers exist;
- the currently generated but visually invalid target Miro Tips frame `3458764680388504033` is a bounded legacy migration anchor and MUST be transactionally replaced even though its geometry already matches the reference;
- the replacement is populated in image → native callouts → connectors order;
- the second run MUST be zero mutation;
- technical validation still leaves HVR-2 pending for an explicit human verdict.

## HVR-2 review boundary

After exact-SHA technical PASS, Human Review must inspect the actual target Frame 01 and specifically verify:

- Miro Tips is at the same relative position and scale as the reference;
- the full Miro UI template is visible;
- yellow/green tips are legible at practical review zoom;
- black arrows visibly point to the intended UI controls;
- the tutorial is understandable to a first-time Miro user;
- the rest of Frame 01 remains visually and semantically consistent.

HVR-3 remains blocked until HVR-2 is explicitly accepted by the human reviewer.

## Governance

This remediation must not merge PR #8, write to `main`, approve G1, promote or release the platform, create a tag, or mutate Frame 10/20+.

## HVR-2 follow-up — endpoint fidelity and spacing

Latest human verdict remains `CHANGES_REQUIRED@. The reference screenshot and target screenshot show two blocking visual gaps:

1. callout arrow terminal points are normalized to the tutorial image border instead of the intended Miro UI controls;
2. the Miro Tips companion sits too close to the enlarged `METODIKA A ZDROJE` section.

Corrective contract for the next exact-SHA