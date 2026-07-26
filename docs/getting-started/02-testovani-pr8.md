# Acceptance test řiditelnosti projektu

PR #8 přidává jednotný acceptance runner.

## Offline test

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering
```

Ověří instalaci, vytvoření dočasného workspace a projektu, intake, tailoring, current status, agent contract a posun G1 → G2. Dočasné prostředky po úspěchu odstraní.

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
8. po úspěchu odstraní board i dočasný workspace.

`-CleanupOnFailure` odstraní i board neúspěšného aktuálního běhu, pokud už jeho ID bylo zapsáno do mappingu. Diagnostický workspace a report zůstanou zachovány.

## Vizuální kontrola boardu

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering -WithMiro -Full -KeepReviewBoard
```

Tento režim board a dočasný workspace zachová. Produkční projektový board se nikdy nepoužívá.
