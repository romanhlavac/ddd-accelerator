# WP-10 — Enterprise ingestion

## Outcome

```text
source document/model
→ normalized evidence fragments
→ Markdown evidence projection
→ YAML evidence/artifact registration
→ downstream reviewed interpretation
```

Ingestion creates evidence, not an approved domain model, architecture decision or gate approval.

## Ownership

- #27 — manifest, source catalog, normalized evidence, Markdown materialization, YAML registration and common core
- #28 — Office adapters
- #29 — PDF and explicit OCR fallback
- #30 — ArchiMate
- #31 — security, privacy, classification and isolation
- #32 — incremental lifecycle, reconciliation, tombstones, resume and traceability
- #33 — synthetic corpus and package-first acceptance

## Authority boundary

Source, extracted evidence, Markdown evidence, YAML registration, reviewed interpretation, project artifact and human decision are separate authority levels. Markdown is a human-readable evidence projection; YAML registration is the machine-readable catalog, hash binding and traceability record.

## Acceptance

Every evidence fragment retains source/version/location/adapter provenance. Supported evidence units produce Markdown evidence and YAML registration. Registration binds to the Markdown SHA-256 and detects drift. Reruns are idempotent; changed/deleted sources use reconciliation and tombstones. Unsupported content and extraction limitations are explicit. No adapter reads/writes outside allowed boundaries. Evidence never creates automatic DDD or architecture approval. Package-first E2E covers add/change/delete/failure/resume and materialization with synthetic data.

## Dependencies and exit

WP-08 provides validation, packaging and security boundaries. WP-11 #47 consumes registered evidence but does not implement ingestion. Exit requires compatible #27–#33 contracts, passing materialization/idempotence/security/reconciliation tests and current native backlog governance.
