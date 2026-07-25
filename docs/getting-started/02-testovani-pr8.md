# Acceptance test řiditelnosti projektu

PR #8 přidává jednotný acceptance runner.

## Offline test

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering
```

Ověří instalaci, vytvoření dočasného workspace a projektu, intake, tailoring, current status, agent contract a posun G1 → G2. Dočasné prostředky po úspěchu odstraní.

## Online test proti Miro

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering -WithMiro -Full
```

Runner vytvoří izolovaný projektový board, vykreslí `current-status` a `next-actions`, provede kontrolní render a po úspěchu board odstraní. Report zůstane v lokálním DDDA state adresáři.

## Vizuální kontrola boardu

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering -WithMiro -Full -KeepReviewBoard
```

Tento režim board a dočasný workspace zachová. Po review je odstraň ručně; runner vypíše jejich identifikátory. Produkční projektový board se nikdy nepoužívá.
