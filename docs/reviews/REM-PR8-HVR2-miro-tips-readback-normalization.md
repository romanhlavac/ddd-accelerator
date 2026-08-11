# REM-PR8-HVR2 — Miro Tips connector read-back normalization

Status: corrective clarification; HVR-2 remains `CHANGES_REQUIRED`

Date: 2026-08-11

This note supersedes only the endpoint-read-back and spacing details in `REM-PR8-HVA-CC-012-5-frame-01-redline.md`. All other recovery and governance constraints remain unchanged.

## Evidence from exact SHA 13b9f7f5486803856d3190988db273e7bdd2d766

The specialized remediation successfully created the active replacement Miro Tips frame `3458764680476608045` at the enlarged spacing (`vertical_offset_y: 600`, target center y approximately `-11727.533`) and removed the prior known-bad frame `3458764680392874705`. The run then failed closed on `companion connector 3458764680476608257 read-back mismatch`.

The failure is caused by Miro REST connector endpoint normalization: fresh read-back can normalize attachment coordinates even when the authored create/update payload contains the intended custom endpoint `position`. Exact read-back coordinate equality is therefore not a reliable mechanical proof of visible arrow-terminal placement.

## Superseding contract

- Black captionless Miro Tips callouts MUST still transport exactly one endpoint-location representation: authored custom `position` when present, otherwise `snapTo`.
- `position` and `snapTo` MUST NOT be submitted together for the same endpoint.
- The reconcile comparator validates stable connector semantics: endpoint item IDs, shape, style and captions. It tolerates Miro endpoint-coordinate normalization on read-back.
- A zero-mutation subsequent reconcile is the mechanical idempotence gate.
- Exact terminal placement on the visible Miro controls is an explicit HVR-2 Human Review criterion because REST read-back cannot reliably prove the visual geometry.
- The active replacement frame `3458764680476608045` MUST NOT be force-replaced solely because of normalized connector read-back.
- The 600 px vertical offset supersedes the earlier 240 px proposal and remains subject to Human Review.
- Technical PASS leaves `human_review_status=PENDING`; HVR-3 remains blocked until explicit human acceptance.

No merge, promotion, release, tag or gate approval is authorized by this clarification.
