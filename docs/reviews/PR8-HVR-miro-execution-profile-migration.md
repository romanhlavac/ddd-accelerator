# PR #8 HVR environment migration — Miro execution profiles

Date: 2026-08-12

PR: #8

Base before migration: `c555abc2a015f85e5fbf4f6403ce5f8c0a44e4b3`

## Decision

PR #8 FAST-LOOP se převádí na explicitní Miro execution profiles podle ADR 0007. Dosavadní review target `uXjVH0doLYY=` se během bootstrapu používá jako `platform_lab` binding, aby nebylo nutné před dokončením PR zakládat nový board a znovu migrovat board-specific frame identity.

## HVR status transition

Dosavadní technická HVR-2 evidence pro SHA `c555abc2a015f85e5fbf4f6403ce5f8c0a44e4b3` prokázala tehdejší Miro contract, ale po změně execution/credential contractu již není final acceptance evidence.

Status:

```text
HVR-2 previous technical evidence: SUPERSEDED_BY_EXECUTION_PROFILE_MIGRATION
HVR-2 human decision: PENDING_REVALIDATION
HVR-3: BLOCKED_BY_HVR-2
```

To není zpětný FAIL původní evidence. Je to nový acceptance boundary pro změněný exact SHA.

## New HVR-2 technical prerequisites

Nový exact-SHA run musí prokázat:

1. target board je resolved profile `platform_lab`;
2. secret-bearing write probíhá přes REST API, nikoli MCP;
3. preferred HVR credential chain je `MIRO_HVR_ACCESS_TOKEN → MIRO_PLATFORM_LAB_ACCESS_TOKEN → MIRO_ACCESS_TOKEN`;
4. remote replacement/reconcile proběhne na configured Platform Lab boardu;
5. fresh read-back je PASS;
6. second reconcile má zero create/update/delete mutation;
7. protected frames zůstávají unchanged;
8. Miro Tips control anchors a +600 spacing zůstávají v accepted contractu;
9. technical status je `PASS` a human review zůstává `PENDING`;
10. MCP availability ani MCP quota není součástí technical PASS.

## Human review

Po technickém PASS bude HVR-2 znovu předán člověku se stabilní URL na Frame 01/Miro Tips. Reviewer může použít Miro GUI a vrátit screenshot/findings. MCP je volitelný pomocný kanál.

HVR-1 se automaticky neruší. Pokud exact-SHA run prokáže unchanged protected content a závěrečný spot-check neukáže collateral regression, dřívější HVR-1 decision se zachová.

## Governance

Tato migrace neautorizuje merge, promotion, release ani gate approval. Po HVR-2 PASS pokračuje HVR-3 a standardní PR #8 release decision.
