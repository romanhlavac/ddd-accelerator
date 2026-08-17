# REM-PR8-HVA-CC-012.1B — Managed Miro image transport

## Status

IMPLEMENTED, PENDING EXACT-SHA CI

## Goal

Prove a reproducible vertical slice from exact source-board image identity to a managed Miro `image` item, including source provenance, SHA-256 evidence, semantic identity, zero-duplicate reconciliation and automatic diagnostic-board cleanup.

## Scope

This increment is diagnostic infrastructure only. It does not modify the preserved human-review board or propagate images into frames `00`, `01`, `10` or `20+`. Those visual changes remain follow-up remediation work after this transport is accepted.

## Source assets

- HUMAN REVIEW REDLINE frame `3458764679531716415`: process image `3458764679531716416` and Align marker `3458764679531716417`.
- Restored Strategic DDD frame `3458764567890733009`: Business Model Canvas image `3458764567890733049`.

## Acceptance

- all source items are verified as images under the declared source frames;
- downloaded bytes are hashed and transported as Miro data URLs;
- target items use stable semantic titles with the observed digest;
- the second reconcile preserves item IDs and performs zero create/update operations;
- the isolated diagnostic board is deleted;
- standard source, package-first and online Miro CI must pass for the resulting exact SHA.
