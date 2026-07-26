# Kontrakty DDDA

## Project intake

Schéma: `schemas/project-intake.schema.json`. Šablona: `templates/project/project-intake.template.yaml`.

Povinné jsou project ID, název, typ, business problém, rozhodnutí, goal, scope-in, aktéři a quality attributes.

## Lifecycle tailoring

Schéma: `schemas/lifecycle-tailoring.schema.json`. Vždy odkazuje na starter metodu `align-discover-decompose-strategize-connect-organize-define-code`.

## Gate record

Schéma: `schemas/gate-status.schema.json`. Evidence část je automatizovatelná; outcome je explicitní lidské rozhodnutí.

## Project status

Schéma: `schemas/project-status.schema.json`. Report uvádí current stage, next gate, gate evidence, next actions a doporučený prompt.

## Agent contract

Schéma: `schemas/agent-contract.schema.json`. Vymezuje allowed write paths, forbidden actions, validační pravidla a handoff. Je host-neutral a neobsahuje provider-specific runtime.

## Capability catalog

Schéma: `schemas/capability-catalog.schema.json`. Katalog je v `docs/reference/capability-catalog.yaml`. CI kontroluje syntaxi, odkazy a dokumentační coverage.

## Ingestion manifest

Schéma: `schemas/ingestion-manifest.schema.json`.

Manifest určuje:

- ID syntetického example;
- project intake;
- seznam source souborů;
- cílové cesty uvnitř workspace;
- roli vstupu;
- povinnost vstupu.

Reference: `examples/minimal/manifest.yaml`.

Source i target jsou validovány proti povoleným rootům. Manifest není licence ke čtení nebo zápisu mimo example a workspace.

## Package manifest

Schéma: `schemas/package-manifest.schema.json`. Soubor v distribuovaném ZIP: `ddda-package.json`.

Obsahuje:

- `package_id`;
- druh `candidate` nebo `release`;
- verzi;
- exact `source_commit`;
- source ref, pokud je znám;
- UTC čas vytvoření.

Package SHA-256 je uložen ve validation nebo release reportu, nikoli uvnitř samotného ZIP před jeho dokončením.

## Validation report

Schéma: `schemas/validation-report.schema.json`.

Report obsahuje:

- validation ID a celkový status;
- source kind, repository, PR, branch a exact commit;
- package path a SHA-256;
- generated workspace;
- Miro board ID, pokud bylo použito;
- stav, délku a detail jednotlivých suites;
- diagnostické cesty.

JSON je machine-readable source pro `promote-pr`. Markdown je review projekce. Promotion akceptuje pouze PASS report pro aktuální PR head SHA a odpovídající package hash.

## Platform development policy

Soubor: `config/platform/development-policy.yaml`.

Určuje:

- cílovou base branch;
- merge method;
- minimální počet approvals;
- požadavek explicitního confirmation;
- povinné governance dokumenty.

Policy nesmí obcházet branch protection nebo GitHub oprávnění. Je další fail-closed guardrail platformního CLI.
