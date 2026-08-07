# REM-PR8-HVA-CC-012.5 — Frame 01 redline adoption and review-board recovery

Status: corrective recovery authorized; Human Visual Review pending

Date: 2026-08-07

## Human direction

Frame `01 – DDD Starter journey, gates a iterace` must be taken from the explicitly selected human-review redline board before HVR-2 continues. The redline is authoritative for this adoption step; semantic corrections discovered during the subsequent HVR must not be silently folded into the copy operation.

Source board: `uXjVH2vcvRI=`

Source Frame 01: `3458764679494310883`

## Failed first target and diagnosis

The first REM-012.5 exact-SHA run targeted the previously reviewed board `uXjVH1phki0=`. Before the first target mutation, the secret-bearing Miro API returned HTTP 404 for target Frame 01. The approved Miro connector independently reported board access denied, while the source redline remained readable. Therefore no partial Frame-01 copy occurred; the old physical review board is no longer a usable HVR target.

The ordinary Platform CI online acceptance did not delete that board: it creates its own isolated smoke/review boards. A previously preserved validation review board remains available and is used as the recovery target.

## Recovery target

Target board: `uXjVH0doLYY=`

Recovered Frame 00: `3458764680243144441`

Target Frame 01: `3458764680243144449`

The preserved board initially contains a generic generated Control Center rather than the Human-accepted REM-012.4 cockpit. Recovery therefore performs two bounded operations in one exact-SHA transaction:

1. reconstruct Frame 00 from the versioned Human-accepted `rem-012-4-frame-00.yaml` contract, using the accepted frame geometry and sticky role palette and retargeting only the Frame-01 navigation URL;
2. resize target Frame 01 to the source redline geometry and reconcile all supported Frame-01 children and connectors from the selected redline.

All other 16 method frames are protected by a canonical before/after snapshot digest.

## Frame 00 acceptance boundary

HVR-1 / Frame 00 was Human ACCEPTED on exact SHA `ddc8e68bbab1bf64c680050347d881d5b485f225`. Recovery does not reopen the methodological decision. Because the physical Miro board changes, a short Human visual-equivalence spot check is required after technical recovery PASS before the prior acceptance is treated as operational on the recovered board.

## Frame 01 source-copy contract

The platform scaffold already declares `uXjVH2vcvRI=` as the read-only Frame-01 review redline. Source content, layout, style and connector semantics are copied as-is. The transport intentionally preserves any semantic inconsistency present in the redline; for example, cross-frame G1 readiness is a new HVR-2 question rather than something the copy operation may silently correct.

The source-driven reconcile preserves target IDs where semantic identity permits, creates missing source items, removes target Frame-01 children/connectors absent from the redline, remaps connectors, and requires a zero-mutation second run.

## Acceptance contract

Technical PASS requires:

- exact-SHA repository CI and candidate package provenance;
- targeted source/recovery regression tests;
- successful reconstruction and read-back of the eight-item accepted Frame 00;
- successful source-to-target Frame 01 reconcile;
- zero-mutation second Frame-00 and Frame-01 runs;
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

HVR-2 must then assess Frame 01 first-viewer clarity, fidelity to the selected redline, gate semantics, iteration semantics, terminology, readability and cross-frame consistency. Technical PASS does not imply HVR acceptance.

## Governance

This remediation must not merge PR #8, write to `main`, approve G1, promote or release the platform, create a tag, or mutate Frame 10/20+.
