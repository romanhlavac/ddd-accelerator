# Kontrakty řiditelnosti DDDA

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

Schéma: `schemas/agent-contract.schema.json`. Vymezuje allowed write paths, forbidden actions, validační pravidla a handoff. Neobsahuje model-provider specifický runtime; je host-neutral.

## Capability catalog

Schéma: `schemas/capability-catalog.schema.json`. Katalog je v `docs/reference/capability-catalog.yaml` a CI kontroluje jeho syntaxi, odkazy a dokumentační coverage.
