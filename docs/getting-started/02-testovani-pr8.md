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
