# 17 Current status, gaty a další krok

## Zobrazení stavu

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot
```

Výchozí režim je read-only. Načte již vytvořený `reports/project-status.yaml` a nemění projektový Git working tree.

Výstup ukazuje aktuální fázi, další gate, chybějící evidence a doporučený chatový prompt.

Strojově čitelný read-only výstup:

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot -Json
```

## Explicitní přepočet stavu

Po ruční změně evidence lze status výslovně přepočítat:

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot -Refresh
```

Přepočet aktualizuje:

- `artifacts/status/current-status.yaml`;
- `artifacts/status/next-actions.yaml`;
- `reports/project-status.yaml`.

Jde o write operaci. Před navazující Miro inicializací nebo synchronizací musí být změny zkontrolované a commitnuté.

## Kontrola gatů

```powershell
.\scripts\Test-DDDAGates.ps1 -ProjectPath $ProjectRoot
```

Konkrétní gate:

```powershell
.\scripts\Test-DDDAGates.ps1 -ProjectPath $ProjectRoot -Gate G3
```

`ready_for_review` neznamená schváleno. Znamená pouze, že konfigurace našla požadované evidence paths.

## Explicitní gate review

```powershell
.\scripts\Complete-DDDALifecycleStep.ps1 `
  -ProjectPath $ProjectRoot `
  -Gate G1 `
  -Outcome passed `
  -Reviewer 'Business owner' `
  -Note 'Scope a decision owner potvrzeny'
```

Skript aktualizuje gate record, `project.yaml`, current status a next actions. Commit standardně nevytvoří.

## Kontrolovaný commit

Nejprve:

```powershell
git -C $ProjectRoot diff
git -C $ProjectRoot diff --check
```

Potom lze stejný příkaz spustit s `-Commit`. Vytvoří lokální commit, nikoli push nebo merge.

Po commitu lze stav bezpečně číst bez dalších změn:

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot
```

## Conditional gate

```powershell
.\scripts\Complete-DDDALifecycleStep.ps1 `
  -ProjectPath $ProjectRoot `
  -Gate G5 `
  -Outcome conditional `
  -Reviewer 'Architecture owner' `
  -Condition 'Potvrdit source of truth pro party identity'
```

Conditional gate neposune workflow jako `passed`.
