# REM-PR8-HVA-CC-011 — content coherence and traceability hardening

Status: IMPLEMENTED, PENDING_CI_AND_HUMAN_REVIEW

Date: 2026-08-02

Scope: PR #8, branch `feat/project-steering-and-documentation`

## Důvod změny

REM-010 opravil parent ownership frame `01` a prokázal technickou reprodukovatelnost. Následný pre-review ale našel čtyři zbývající vady: syntetický claims projekt používal obecný vendor-lock problém, Align a Organize odkazovaly pouze na root DDD Starter boardu, overview G7 duplikoval invariantní roli a některé odkazy označené jako kuchařka mířily na metodickou nebo produktovou dokumentaci.

## Implementovaný kontrakt

1. Acceptance Claims Modernization používá claims-specific business problém a jednotný ubiquitous language.
2. Všechny stage, traceability řádky a povinné DDD Starter templates míří na konkrétní `moveToWidget` source frame.
3. G7 overview používá role `PURPOSE`, `BUSINESS DECISIONS`, `UBIQUITOUS LANGUAGE` a `INBOUND / OUTBOUND`.
4. Každý `cookbook_url` míří pod `docs/cookbooks/`; metodika zůstává v `method_url`.
5. Layout validator fail-closed ověřuje exact source frame, klasifikaci cookbook odkazů a neduplicitní stage role.
6. Acceptance test ověřuje doménovou koherenci syntetického claims scénáře.
7. Render contract je `REM-PR8-HVA-CC-011`.

## Exact source frames doplněné v REM-011

- Align — `Business model canvas - exercise`: `3458764567890733010`.
- Organize — `Starter Modelling Process - Organize`: `3458764567797253955`.
- Lifecycle template — `Starter Modelling Process - Decompose`: `3458764567797029926`.

Ostatní stage odkazy zůstávají vázané na již existující exact source frames z REM-010.

## Stav akceptace

Automatizace může potvrdit layout, zdroje, odkazy, UTF-8, idempotenci a obsahovou konzistenci fixture. Nemůže vydat lidské vizuální nebo metodické schválení. Výsledek proto zůstává `PENDING_HUMAN_REVIEW`.

## Zakázané operace

REM-011 neautorizuje merge, promotion, release, tag ani force-push.
