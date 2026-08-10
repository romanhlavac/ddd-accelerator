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
- if the previous oversized card-only companion is present, remove its children/connectors first, restore the empty frame to reference geometry/placement, then reconcile the source image/items/connectors. This ordering avoids an invalid parent shrink with out-of-bounds children;
- reconcile idempotently and prove a zero-mutation second run;
- keep `human_review_status=PENDING` after technical PASS.

The main Frame 01 journey, methodology block and eight DDD Starter phase companions remain unchanged by this correction.

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
