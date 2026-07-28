# Acceptance test řiditelnosti projektu

PR #8 přidává jednotný acceptance runner.

## Offline test

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering
```

Ověří instalaci, vytvoření dočasného workspace a projektu, intake, tailoring, current status a agent contract.

Automatizace připraví G1 pouze jako `ready_for_review`. Nevytvoří `passed`, nezapíše G1 do `completed_gates` a nevydává se za lidského reviewera. Přechod G1 → G2 je výhradně výsledkem explicitního lidského gate decision a není součástí automatického acceptance běhu.

Dočasné prostředky po úspěchu odstraní.

## Online test proti Miro

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering -WithMiro -Full -CleanupOnFailure
```

Runner automaticky:

1. provede plný platformní Miro smoke test;
2. vytvoří izolovaný projektový board;
3. vykreslí metodický scaffold;
4. provede managed artifact push dry-run;
5. odešle `ddda.current-status` a `ddda.next-actions` spolu s ostatními managed artefakty;
6. ověří jejich záznam v `miro/miro-map.yaml` a `miro/sync-state.yaml`;
7. provede kontrolní render a idempotentní kontrolní push dry-run;
8. ověří, že Miro operace nevytvořila ani nepřepsala lidské gate decision;
9. po úspěchu odstraní board i dočasný workspace.

`-CleanupOnFailure` odstraní i board neúspěšného aktuálního běhu, pokud už jeho ID bylo zapsáno do mappingu. Diagnostický workspace a report zůstanou zachovány.

## Vizuální kontrola boardu

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering -WithMiro -Full -KeepReviewBoard
```

Tento režim board a dočasný workspace zachová a vypíše board ID, URL a workspace cestu. Produkční projektový board se nikdy nepoužívá.

Technický PASS acceptance neznamená lidské schválení gate ani human visual acceptance boardu.


## Význam online Miro výsledku

Online runner po technickém PASS zapisuje oddělené výsledky:

```text
technical_sync_status: PASS
layout_contract_status: PASS
utf8_status: PASS
human_visual_acceptance_status: PENDING
overall_status: PENDING_HUMAN_REVIEW
```

Board lze použít jako finální release evidence až po jednorázovém human visual review. Automatizace nikdy nesmí převést `PENDING` na lidský `PASS`.

## Auditní Miro evidence

Acceptance report, `validate-pr` report i release report používají stejný strukturovaný objekt `miro`. Zachovává `board_id` i po automatickém DELETE a obsahuje:

- ověřené managed artifact ID;
- výsledek mappingu a sync state;
- idempotence invarianty a počty druhého běhu;
- cleanup state `preserved`, `deleted`, `cleanup_failed` nebo `not_created`;
- cleanup timestamp, redigovanou chybu a diagnostické cesty;
- workspace a board URL pro režim `-KeepReviewBoard`.

Finální review board se vytváří pouze jednou nad zmrazeným SHA:

```powershell
.\ddda.ps1 validate-pr -Pr 8 -WithMiro -Full -KeepReviewBoard
```

Token ani jiné credentials nejsou součástí evidence. `miro_board_id` zůstává pouze compatibility aliasem; autoritativní je objekt `miro`.
