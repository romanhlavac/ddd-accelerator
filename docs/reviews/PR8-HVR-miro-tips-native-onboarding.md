# HVR-2 remediation: Miro Tips native onboarding

Status: IMPLEMENTED_PENDING_EXACT_SHA_VALIDATION

## Rozhodnutí

Rámec **Miro Tips** na DDDA Platform Lab již nepoužívá screenshot ani šipky
ukotvené na jeho UI. Zachovává se existující kontejner a jeho poloha, ale jeho
děti se jednorázově nahradí sedmi DDDA-owned native shape prvky: nadpisem a
šesti čitelnými onboarding kartami.

## Technický kontrakt

- minimální velikost těla je 36 px, nadpisu 64 px;
- šest povinných sekcí kryje navigaci po plátně/rámcích, sticky notes,
  výběr/undo/duplikaci, spojování významů, spolupráci/facilitaci a
  vlastnictví + legendu DDDA;
- cílový rámec obsahuje 0 screenshotů a 0 callout connectorů;
- první reconcile smí odstranit dosavadní screenshotovou topologii;
  druhý reconcile musí mít zero create/update/delete mutation;
- zásah je omezen na děti Miro Tips; Frame 01 a všech 16 protected frames
  zůstávají nedotčené.

## HVR hranice

Automatizace dokládá exact-SHA technické invarianty a materializuje DDDA_HVR
pro lidské posouzení. Neznamená to vizuální approval: HVR-2 je připraveno k
novému lidskému review a HVR-3 zůstává blokované, dokud člověk nepotvrdí
čitelnost prvního pohledu, úplnost obsahu a praktickou použitelnost. Žádný
merge, promotion ani release tento corrective run neprovádí.
