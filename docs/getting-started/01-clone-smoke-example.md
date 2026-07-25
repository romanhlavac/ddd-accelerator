# Clone, smoke testy, workspace a example projekt

Toto je kanonický postup pro nového uživatele. Ruční práce je omezena na clone a první bezpečné zadání Miro tokenu.

## 1. Clone

Z parent adresáře:

```powershell
New-Item -ItemType Directory -Force .\DDDA-Workspace\platform | Out-Null

git clone `
  https://github.com/romanhlavac/ddd-accelerator.git `
  .\DDDA-Workspace\platform\ddd-accelerator

Set-Location .\DDDA-Workspace\platform\ddd-accelerator
```

## 2. Jeden automatizovaný first-run

```powershell
.\scripts\Initialize-DDDAFirstRun.ps1 -WithMiro -Full
```

Orchestrátor ověří platformu, nainstaluje Miro i steering runtime, spustí izolovaný Miro smoke test, vytvoří workspace, materializuje example projekt a inicializuje jeho projektový board. Token se na Windows uloží přes DPAPI mimo Git.

Očekávaný konec:

```text
DDDA první spuštění: PASS
```

## 3. Offline varianta

```powershell
.\scripts\Initialize-DDDAFirstRun.ps1
```

Board lze doplnit později přes `Initialize-DDDAProjectMiro.ps1`.

## 4. Kontrola example projektu

```powershell
$WorkspaceRoot = (Resolve-Path '..\..').Path
$ProjectRoot = Join-Path $WorkspaceRoot 'projects\life-insurance-greenfield'

git -C $ProjectRoot status --short
```

Po online inicializaci je očekávána změna `miro/miro-map.yaml`. Zkontroluj diff a commitni pouze mapping:

```powershell
git -C $ProjectRoot diff -- miro/miro-map.yaml
git -C $ProjectRoot add miro/miro-map.yaml
git -C $ProjectRoot commit -m 'chore: initialize example Miro board'
```

## 5. Další krok v chatu

> Scope: project. Aktivní projekt: `life-insurance-greenfield`. Načti `project.yaml`, relevantní artefakty, `artifacts/status/current-status.yaml` a knowledge index. Shrň aktuální stav, chybějící evidence a navrhni nejmenší další krok. Nic nezapisuj bez potvrzení.

Pro založení vlastního řízeného projektu pokračuj kuchařkou 16.
