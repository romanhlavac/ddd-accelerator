# WP-10 — Enterprise ingestion

## Outcome

```text
source document/model
→ normalized evidence fragments
→ Markdown evidence projection
→ YAML evidence registration
→ downstream reviewed interpretation
```

Ingestion creates auditable evidence with provenance and limitations. It does not create an approved domain model, architecture decision or gate approval.

## Baseline compatibility

WP-08 / PR #8 already provides a minimal package-first ingestion manifest, example and validation flow. WP-10 must extend that versioned baseline or introduce an explicit compatible successor with tested migration. A parallel manifest/source catalog is forbidden.

## Capability ownership

| Issue | Owned capability |
|---|---|
| #27 | foundational manifest, source identity, normalized evidence, Markdown materialization and YAML registration |
| #31 | central security, privacy, classification, redaction and path-isolation policy |
| #28 | DOCX/XLSX/PPTX adapters |
| #29 | PDF extraction and explicit OCR fallback |
| #30 | ArchiMate supported-subset adapter and coverage report |
| #32 | incremental lifecycle, reconciliation, tombstones, resume and impact traceability |
| #33 | synthetic enterprise corpus and package-first E2E |

WP-10 owns evidence inception. Semantic interpretation, EventStorming and Miro workshop remain WP-11 responsibilities.

## Dependency order

```text
#27 → #31
#27 + #31 → #28, #29, #30, #32
#28 + #29 + #30 + #31 + #32 → #33
```

Meaning:

- #27 establishes common source/path/evidence abstractions;
- #31 establishes one central policy consumed by every adapter and lifecycle component;
- adapters and #32 do not create format-specific security or identity models;
- #27 is not blocked by completed #31/#32 implementations, but its final contract requires security review;
- no reverse dependency cycle exists.

## Authority boundary

```text
source
→ extracted evidence
→ Markdown evidence
→ YAML registration
→ reviewed interpretation
→ candidate/validated artifact
→ human decision
```

Markdown is a readable evidence projection. YAML registration is the machine-readable identity, hash binding, lifecycle and traceability record.

## In scope

- versioned enterprise manifest and source catalog;
- stable source/version/location/adapter provenance;
- path and workspace isolation;
- shared classification/redaction/parser-safety controls;
- Office, PDF/OCR and ArchiMate supported subsets;
- deterministic normalized evidence and Markdown materialization;
- YAML registration with Markdown SHA-256 binding;
- unsupported-content and coverage reports;
- idempotence, reconciliation, tombstones and resume;
- source-to-downstream impact queries;
- package-first synthetic acceptance.

## Out of scope

- document editing or ECM;
- guaranteed OCR/layout reconstruction;
- client documents in the platform repository;
- automatic DDD/architecture decisions;
- vector/search product;
- WP-09 program semantics;
- WP-11 interpretation, agents and workshop round-trip.

## Acceptance criteria

- [ ] PR #8 minimal manifest/example remains valid or has tested migration;
- [ ] every source and fragment retains stable identity and exact provenance;
- [ ] no read/write escapes configured workspace roots;
- [ ] every adapter consumes #31 central policy;
- [ ] active content, macros and external resources are deny-by-default;
- [ ] supported evidence units create Markdown and YAML registration;
- [ ] registration detects unmanaged Markdown drift;
- [ ] unsupported/skipped content is never silently lost;
- [ ] OCR is explicit, opt-in and distinguishable from native extraction;
- [ ] unchanged rerun is idempotent;
- [ ] changed/removed input uses reconciliation and tombstones;
- [ ] sensitive tombstones/reports remain redacted;
- [ ] partial failure/resume does not duplicate or corrupt evidence;
- [ ] evidence cannot automatically approve an artifact or gate;
- [ ] package and fixtures contain no client data, secrets or local paths.

## Quality attributes

- provenance and auditability;
- security and privacy;
- deterministic behavior and data integrity;
- idempotence and resumability;
- adapter extensibility;
- explainability of extraction limitations;
- observability and resource control.

## Dependencies and consumers

- WP-08 supplies package, workspace and validation boundaries;
- WP-11 #47 consumes registered evidence without implementing ingestion;
- WP-09 may consume evidence but is not a prerequisite.

## Exit criteria

- #27–#33 contracts are compatible and non-duplicative;
- security policy is shared by all components;
- materialization, hash binding, add/change/delete/failure/resume tests PASS;
- synthetic package-first E2E passes without client data;
- one registered evidence set is handed downstream without automatic approval;
- native hierarchy/dependencies and roadmap are current.
