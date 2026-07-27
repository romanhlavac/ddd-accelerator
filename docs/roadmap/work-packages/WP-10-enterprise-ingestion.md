# WP-10 — Enterprise ingestion

## Outcome

DDDA získá bezpečnou, manifest-driven a auditovatelnou ingestion pipeline pro enterprise zdroje, která převádí dokumenty a modely do normalizované evidence s jednoznačnou provenance, aniž by zaměňovala extrahovaný obsah za schválené doménové nebo architektonické rozhodnutí.

## State

```text
State: backlog
Target release: TBD
Depends on: WP-08 package-first validation and security boundaries
```

## Problem / GAP

Aktuální platforma má pouze minimální example ingestion pro validační workspace. Chybí produkčně použitelná pipeline pro:

- Office dokumenty;
- PDF;
- ArchiMate modely;
- větší sady Markdown/YAML/JSON/XML;
- source provenance a immutable source identity;
- normalizaci, deduplikaci a aktualizaci zdrojů;
- bezpečnou práci s citlivými vstupy;
- reporting chyb, warningů, unsupported elementů a coverage;
- opakovatelné incremental ingestion;
- vazbu evidence na downstream artifacts a decisions.

## In scope

- enterprise ingestion manifest a source catalog;
- source identity, checksum, version, timestamp a provenance;
- allowed paths, workspace boundary a no-path-escape checks;
- source adapters pro Office, PDF a ArchiMate;
- extraction bez OCR jako default; OCR pouze explicitní fallback capability;
- text, metadata, tables, images/figures references a structural hierarchy podle podporovaného formátu;
- ArchiMate elements, relationships, views a properties v explicitně podporovaném rozsahu;
- normalizovaný evidence model;
- chunking, deduplication, update detection a tombstone semantics;
- unsupported-content reporting;
- security classification, redaction hooks a secret/PII controls;
- ingestion report a machine-readable diagnostics;
- deterministic test fixtures bez klientských dat;
- incremental/resumable processing;
- traceability source → extracted evidence → generated artifact;
- CLI/orchestration integration;
- release package a example workspace acceptance.

## Out of scope

- obecný enterprise content management systém;
- plnohodnotný document editor;
- automatické schválení pravdivosti extrahovaného obsahu;
- automatické doménové rozhodnutí pouze z dokumentů;
- garantované OCR všech jazyků a layoutů;
- parsing proprietárních formátů bez jasného kontraktu;
- ukládání klientských dokumentů do platform repository;
- program portfolio lifecycle — WP-09;
- multi-agent reasoning runtime — WP-11.

## Core contracts

### Source manifest

Každý source entry musí obsahovat minimálně:

```yaml
source_id: stable-id
path: relative/path
media_type: application/pdf
classification: internal
expected_adapter: pdf
checksum: optional-on-first-run
include:
  - text
  - metadata
exclude:
  - embedded-attachments
```

### Provenance

Každý evidence fragment musí zachovat:

- source ID;
- source hash/version;
- location: page/sheet/slide/view/element/path;
- extraction adapter and version;
- extraction timestamp;
- confidence/limitations, pokud relevantní;
- transformation history;
- downstream references.

### Authority boundary

```text
source document
→ extracted evidence
→ reviewed interpretation
→ approved artifact/decision
```

Ingestion vytváří evidence, ne approval.

## Proposed delivery slices

1. **Enterprise manifest and provenance model**
   - schemas, source catalog, hashes, update/tombstone rules.
2. **Normalized evidence model and pipeline core**
   - adapter interface, diagnostics, resumability, deduplication.
3. **Office ingestion**
   - DOCX, XLSX, PPTX v explicitně podporovaném rozsahu.
4. **PDF ingestion**
   - text/layout metadata, tables and figure references; explicit OCR fallback policy.
5. **ArchiMate ingestion**
   - XML/model parsing, elements, relations, views, properties and coverage report.
6. **Security, privacy and isolation**
   - path rules, classification, redaction, secret and client-data guards.
7. **Traceability and downstream consumption**
   - evidence links for discovery, decisions and artifacts.
8. **Incremental operation and change detection**
   - add/update/delete, idempotence, resume and conflict behavior.
9. **Example corpus and acceptance**
   - synthetic Office/PDF/ArchiMate fixture, package-first E2E and reports.

## Acceptance criteria at WP level

- [ ] all inputs are declared in a manifest or explicitly registered source catalog;
- [ ] no adapter reads or writes outside allowed workspace boundaries;
- [ ] every extracted fragment has stable source provenance;
- [ ] unchanged sources are processed idempotently;
- [ ] changed sources produce explicit update evidence;
- [ ] deleted sources use controlled tombstone semantics;
- [ ] unsupported content is reported, not silently ignored;
- [ ] Office adapters preserve relevant document hierarchy and metadata;
- [ ] PDF adapter reports extraction limitations and does not silently use OCR;
- [ ] ArchiMate adapter documents supported elements, relationships, views and properties;
- [ ] extraction does not create approved DDD/architecture artifacts automatically;
- [ ] client data and secrets are absent from platform examples and release package;
- [ ] ingestion reports are machine-readable and human-readable;
- [ ] pipeline can resume after failure without duplicating evidence;
- [ ] source → evidence → artifact traceability is queryable;
- [ ] package-first E2E passes on synthetic enterprise corpus;
- [ ] performance boundaries and maximum supported fixture sizes are documented.

## Quality attributes

- provenance and auditability;
- security and privacy;
- interoperability;
- extensibility of adapters;
- deterministic behavior;
- resumability;
- observability;
- data integrity;
- explainability of extraction limitations;
- cost control.

## Risks

| Risk | Impact | Mitigation |
|---|---:|---|
| Extraction appears more authoritative than source supports | High | evidence/interpretation/decision separation |
| Client data leaks into examples or reports | High | synthetic fixtures, classification and package guards |
| PDF/OCR quality is inconsistent | High | explicit adapter limitations, confidence and opt-in OCR |
| ArchiMate support is claimed too broadly | High | supported-subset contract and coverage report |
| Incremental updates corrupt traceability | High | stable IDs, hashes, tombstones and regression fixtures |
| Adapter scope becomes unbounded | Medium | adapter contracts and separate Change Requests |
| Large documents cause uncontrolled cost/time | Medium | size limits, metrics, batching and cancellation |

## Dependencies

- WP-08 package, validation report, security/isolation and release lifecycle;
- WP-09 can consume ingestion evidence but is not prerequisite;
- WP-11 can orchestrate assisted interpretation later but must preserve provenance and human approval.

## Exit criteria

- core manifest, provenance and evidence contracts are stable;
- agreed adapters pass component, integration, security and E2E tests;
- synthetic corpus contains no client data;
- incremental add/update/delete and resume scenarios pass;
- extraction limitations are documented and visible in reports;
- one end-to-end example demonstrates evidence use without automatic approval;
- release package validation and roadmap status are updated.
