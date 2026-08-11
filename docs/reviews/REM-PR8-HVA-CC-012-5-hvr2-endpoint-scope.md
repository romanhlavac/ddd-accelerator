# REM-PR8-HVA-CC-012.5 — HVR-2 endpoint-scope corrective

Status: **CHANGES_REQUIRED → corrective implementation pending exact-SHA validation**

Human review finding: 2026-08-11

## Scope

This corrective increment is limited to the `Miro Tips` companion of:

`01 – DDD Starter journey, gates a iterace`

HVR-3 remains blocked. No merge, promotion, release, tag, gate approval or write to `main` is authorized.

## Latest human finding

Side-by-side review of the required reference screenshot and generated target identified two blockers:

1. **Callout endpoint fidelity:** black tutorial arrows must terminate at the Miro UI controls shown in the reference, not at generic image-border attachment points.
2. **Vertical spacing:** the whole Miro Tips companion must move lower to create a visibly larger gap below `METODIKA A ZDROJE`.

## Failed corrective attempt `3d31b0e...`

The first endpoint-fidelity corrective correctly preserved source endpoint `position` ahead of `snapTo` and made fresh read-back location-aware. Targeted tests passed, but the online Miro replacement failed on main Frame 01 connector `3458764680260503826` (`G1 · lidské rozhodnutí`).

The failure revealed an over-broad regression guard: endpoint-position equality had been applied to every Frame 01 connector, although the HVR-2 visual requirement concerns only the **black, captionless Miro Tips callouts**. Miro normalizes unrelated main-frame connector endpoints differently, so the broad comparator rejected a non-HVR connector before the Miro Tips transaction could complete.

## Corrective contract

### Endpoint semantics are scoped to Miro Tips

Only black (`#000000` / `#000`), captionless callout connectors carry the HVR-2 precise-endpoint contract.

For those connectors:

- when the source endpoint has a normalized `position`, that position is authoritative;
- `position` and `snapTo` MUST NOT be submitted together for the same endpoint;
- fresh read-back MUST compare the authored normalized endpoint coordinates;
- visible endpoint drift remains a technical failure.

For all other Frame 01 connectors:

- endpoint item identity, shape, style and captions remain validated;
- endpoint-position normalization is **not** treated as an HVR-2 visual contract;
- this prevents unrelated G1–G8 and methodology connectors from blocking Miro Tips remediation.

### Vertical placement

The target-only Miro Tips Y offset is increased from `+240` to **`+600` Miro units**.

Expected target center:

- x ≈ `-19834.447`
- y ≈ `-11727.533`

The reference geometry remains approximately:

- width `1919.43`
- height `1079.68`

At this placement Miro Tips remains separated from the `Align` companion while creating a materially larger visual gap below `METODIKA A ZDROJE`.

### Existing contracts retained

- reference Miro UI screenshot remains the background;
- native callout items remain above the screenshot;
- connectors remain above the callouts;
- at least eight black Miro Tips callouts remain present;
- current rejected target frame `3458764680392874705` is transactionally replaced;
- second reconcile is zero mutation;
- protected frames remain unchanged;
- technical PASS leaves `human_review_status=PENDING`.

## Human acceptance boundary

After exact-SHA technical PASS, the actual generated target must return to HVR-2.

Human review must confirm:

- every black arrow visibly lands on the intended Miro UI control;
- a first-time Miro user can associate each tip with its control without explanation;
- the larger vertical gap below `METODIKA A ZDROJE` is visually appropriate;
- no overlap or collateral Frame 01 degradation was introduced.

Only explicit `PASS` or accepted `PASS_WITH_NOTES` unblocks HVR-3.
