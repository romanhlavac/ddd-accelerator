# Kuchařka 01 — Založení projektu

## Výsledek

Vznikne izolovaný projektový Git repozitář s manifestem, DDDA lockem, ingestion, artefakty, prompt library, Miro mappingem, sync state, konflikty a auditními reporty.

## Předpoklady

- platforma prošla `Test-DDDAInstallation.ps1`,
- uživatel stojí v parent adresáři workspace,
- je znám business problém a očekávané rozhodnutí,
- Git identity je nakonfigurována.

## Chat intake prompt

> Pomoz mi vybrat typ projektu. Ptej se na business outcome, rozhodnutí, scope, provozní kontinuitu, systémy, data ownership, regulaci, týmy a quality attributes. Na konci navrhni project ID, kanonický typ, alias, první gaty a přesný bootstrap příkaz.

## Technický krok

```powershell
$WorkspaceRoot = (Resolve-Path .\DDDA-Workspace).Path
$PlatformRoot = (Resolve-Path .\DDDA-Workspace\platform\ddd-accelerator).Path

& (Join-Path $PlatformRoot 'scripts\New-DDDAProject.ps1') `
  -WorkspaceRoot $WorkspaceRoot `
  -ProjectId claims-modernization `
  -Name 'Modernizace likvidace pojistných událostí' `
  -Type legacy-modernization
```

## Co skript dělá

1. kontroluje unikátní ID,
2. vytvoří sibling Git repo,
3. vygeneruje manifest a lock,
4. vytvoří `workshops/prompts`, `miro/conflicts` a `reports/miro-sync`,
5. připraví Miro mapping a sync state,
6. provede initial commit,
7. registruje projekt ve workspace.

## Validace

```powershell
$ProjectRoot = Join-Path $WorkspaceRoot 'projects\claims-modernization'
& (Join-Path $PlatformRoot 'scripts\Test-DDDAInstallation.ps1') `
  -PlatformPath $PlatformRoot -WorkspaceRoot $WorkspaceRoot -ProjectPath $ProjectRoot
```

## Typické chyby

- project ID podle technologie,
- projekt uvnitř platformního repo,
- nejasný decision owner,
- board token v manifestu,
- použití portfolio profilu jen proto, že projekt je velký.

## Navazující krok

Katalogizuj ingestion a připrav Miro board podle kuchařky 02.
