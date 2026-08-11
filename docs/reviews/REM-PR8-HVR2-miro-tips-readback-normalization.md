# REM-PR8-HVR2 — Miro Tips arrowhead fidelity and spacing

Status: corrective implementation pending exact-SHA validation; HVR-2 remains `CHANGES_REQUIRED`

Date: 2026-08-11

This note supersedes only the endpoint-read-back and spacing details in `REM-PR8-HVA-CC-012-5-frame-01-redline.md`. All other recovery and governance constraints remain unchanged.

## Evidence and diagnosis

Exact SHA `13b9f7f5486803856d3190988db273e7bdd2d766` successfully created the active replacement Miro Tips frame `3458764680476608045` at the enlarged spacing (`vertical_offset_y: 600`, target center y approximately `-11727.533`) and removed the prior known-bad frame `3458764680392874705`. The run then failed closed on a Miro Tips connector read-back mismatch.

The previous comparison was too broad in two different ways across successive attempts: first it applied precise endpoint coordinates to unrelated Frame 01 connectors; then it required both ends of a curved tutorial connector to preserve source coordinates. The human finding concerns the visible **arrowhead landing point on the Miro UI screenshot**, not the sticky-side routing attachment.

A later workaround that tolerated all endpoint-coordinate normalization is also insufficient: it can return technical PASS while an arrowhead is visibly attached to the wrong place, which contradicts the HVR-2 acceptance criterion.

## Superseding contract

- Only black, captionless Miro Tips tutorial connectors carry precise HVR-2 endpoint semantics.
- For these connectors the screenshot-side `endItem` is the visual contract. Its authored source `position` is preserved when available; `position` and `snapTo` are never submitted together.
- The sticky-side `startItem` is a routing attachment, not a precise visual contract. When the source provides `snapTo`, the target uses that stable attachment and Miro may normalize its resulting route.
- Fresh read-back validates endpoint item IDs for every connector and additionally validates the screenshot-side arrowhead position for black captionless Miro Tips callouts.
- Main Frame 01 connectors remain outside this endpoint-position gate.
- The active replacement frame `3458764680476608045` is retained; it is not force-replaced solely to change connector semantics.
- The target-only vertical offset remains **+600 Miro units**, producing target center y approximately `-11727.533` and a materially larger gap below `METODIKA A ZDROJE`.
- A second reconcile must be zero mutation.
- Technical PASS still leaves `human_review_status=PENDING`; HVR-3 remains blocked until explicit Human Review acceptance.

## Human Review criterion

After exact-SHA technical PASS, HVR-2 must inspect the actual target Frame 01 and specifically confirm:

1. each black arrowhead visibly lands on the intended Miro UI control rather than a generic screenshot border or unrelated location;
2. each explanatory tip is unambiguously associated with the relevant control;
3. the increased gap below `METODIKA A ZDROJE` is visually appropriate;
4. no overlap or collateral Frame 01 degradation was introduced.

No merge, promotion, release, tag or gate approval is authorized by this correction.
