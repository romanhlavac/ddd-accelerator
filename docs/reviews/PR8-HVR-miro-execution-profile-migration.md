# PR #8 HVR environment migration — three private Miro execution profiles

Date: 2026-08-14

PR: #8

Base before this migration: `705cbec7a5d00682656487201263d6226b2a61bf`

## Decision

PR #8 FAST-LOOP používá během současného platform-development období tři striktně oddělené Miro REST profily v privátním Developer Teamu:

```text
platform_lab → MIRO_PLATFORM_LAB_ACCESS_TOKEN → DDDA_PLATFORM_LAB
github_ci    → MIRO_GH_CI_ACCESS_TOKEN       → DDDA_GH_CI
hvr          → MIRO_HVR_ACCESS_TOKEN          → DDDA_HVR
```

Cross-profile credential fallback ani legacy `MIRO_ACCESS_TOKEN` nejsou povoleny. MCP zůstává pouze volitelný interaktivní kanál a není součástí technical gate.

`example_project` a `project_runtime` jsou v této fázi deferred. Jejich boardy a credentials se neprovisionují v PR #8 development wiring.

## HVR status transition

Technická HVR-2 evidence pro SHA `705cbec7a5d00682656487201263d6226b2a61bf` prokázala předchozí execution-profile contract, ale po zavedení tří fyzicky oddělených boardů není final acceptance evidence pro nový HVR target.

Status:

```text
HVR-2 previous technical evidence: SUPERSEDED_BY_THREE_PROFILE_BINDING
HVR-2 human decision: PENDING_REVALIDATION
HVR-3: BLOCKED_BY_HVR-2
```

Nejde o zpětný FAIL. Jde o nový acceptance boundary pro změněný exact SHA a nový HVR board.

## New HVR-2 technical prerequisites

Nový exact-SHA run musí prokázat:

1. všechny tři secrets jsou přítomné a nejsou nahrazeny jiným profile credentialem;
2. token context každého profilu odpovídá očekávanému privátnímu Developer Teamu a obsahuje `boards:read` + `boards:write`;
3. `platform_lab` resolveuje `DDDA_PLATFORM_LAB` a PR8 Frame 01 remediation probíhá REST API výhradně přes `MIRO_PLATFORM_LAB_ACCESS_TOKEN`;
4. fresh Platform Lab read-back je PASS;
5. second Platform Lab reconcile má zero create/update/delete mutation;
6. protected frames zůstávají unchanged;
7. Miro Tips ověří zmrazený nativní zdroj reference `uXjVH2vcvRI=` / frame `3458764679531043366` (17 child items: 1 image, 13 sticky notes, 3 texts, 8 šipek a SHA-256 backgroundu), ale cílový výstup je právě **jeden** bitově ověřený PNG kompozit schváleného pohledu; cílové native cards, texty, sticky notes a konektory jsou zakázány;
8. `github_ci` používá pouze `MIRO_GH_CI_ACCESS_TOKEN` a online acceptance běží na dedicated `DDDA_GH_CI` boardu po jeho machine-only resetu;
9. po technickém Platform Lab PASS je `DDDA_HVR` materializován výhradně přes `MIRO_HVR_ACCESS_TOKEN` jako server-side copy validovaného Platform Lab boardu;
10. HVR copy read-back potvrzuje očekávaný obsah a poskytne exact-SHA review URL;
11. technical status je `PASS` a human review zůstává `PENDING`;
12. MCP availability ani MCP quota není součástí technical PASS.

## Human review

HVR-2 se provádí nad **dedikovaným `DDDA_HVR` targetem zachyceným v exact-SHA evidence**, nikoli nad Platform Labem. Protože HVR logical slot je materializován server-side kopií, jeho fyzické board ID se může mezi HVR runy změnit.

Reviewer může použít Miro GUI a vrátit screenshot/findings. MCP je volitelný pomocný kanál.

## Miro Tips visual-delivery decision

Nativní REST replay byl odmítnut jako vizuálně nepravdivý: REST normalizuje zdrojový text `20` na `24` a předchozí reconcile vytvořil obraz až po anotacích, takže obraz je zakryl. Pro tento jediný reference-derived frame je proto schválený delivery contract:

```text
frozen native source evidence
→ one approved composite image
→ SHA-256 and fresh REST image read-back
→ human visual review
```

Kompozit není editovatelná sada jednotlivých šipek nebo sticky notes. Je to vědomý trade-off pro přesnou vizuální shodu. Technical PASS stále neznamená human visual acceptance; aktuální HVR zůstává `CHANGES_REQUIRED`, dokud reviewer neověří výsledný frame.

HVR-1 se automaticky neruší. Pokud exact-SHA run prokáže zachování protected content a spot-check neukáže collateral regression, dřívější HVR-1 decision se zachová.

## Governance

Tato migrace neautorizuje merge, promotion, release ani gate approval. Po HVR-2 PASS pokračuje HVR-3 a standardní PR #8 release decision.
