# Kuchařka 01 — Založení projektu

## Výsledek

Vznikne izolovaný DDDA projekt s vlastním Git repozitářem, manifestem `project.yaml`, lock souborem `ddda.lock.yaml`, standardní adresářovou strukturou a registrací v lokálním `workspace.yaml`.

## Předpoklady

- platforma DDDA je naklonována a prošla `Test-DDDAInstallation.ps1`,
- workspace byl vytvořen pomocí `Initialize-DDDAWorkspace.ps1`,
- příkaz `git` je dostupný v PowerShellu,
- je znám stabilní `project_id`, pracovní název a dominantní typ projektu,
- žádný Miro token nebude uložen do Gitu.

## Pravidlo pro cesty

Následující příklady spusť z **parent adresáře**, ve kterém existuje nebo má vzniknout `DDDA-Workspace`. Relativní cesta `.` označuje tento aktuální parent adresář.

```powershell
$ParentRoot = (Get-Location).Path
$WorkspaceRoot = Join-Path $ParentRoot 'DDDA-Workspace'
$PlatformRoot = Join-Path $WorkspaceRoot 'platform\ddd-accelerator'
```

## Doporučený postup

```powershell
& (Join-Path $PlatformRoot 'scripts\New-DDDAProject.ps1') `
  -WorkspaceRoot $WorkspaceRoot `
  -ProjectId life-insurance-greenfield `
  -Name "Nová životní pojišťovna" `
  -Type portfolio-program `
  -TypeAlias greenfield-portfolio
```

Skript:

1. ověří, že `project_id` ještě není registrován,
2. vytvoří `projects/<project_id>/`,
3. vygeneruje `project.yaml` a `ddda.lock.yaml`,
4. vytvoří adresáře `ingestion`, `artifacts`, `decisions`, `workshops`, `miro`, `reports` a `exports`,
5. inicializuje samostatný Git repozitář projektu,
6. vytvoří počáteční commit,
7. přidá projekt do `workspace.yaml` a `DDDA.code-workspace`.

## Volitelný vzdálený repozitář

Existující prázdný GitHub repozitář lze připojit při bootstrapu:

```powershell
& (Join-Path $PlatformRoot 'scripts\New-DDDAProject.ps1') `
  -WorkspaceRoot $WorkspaceRoot `
  -ProjectId claims-modernization `
  -Name "Modernizace likvidace pojistných událostí" `
  -Type legacy-modernization `
  -RemoteUrl https://github.com/example/claims-modernization.git

$ProjectRoot = Join-Path $WorkspaceRoot 'projects\claims-modernization'
git -C $ProjectRoot push -u origin main
```

## Kanonický manifest

```yaml
project:
  id: claims-modernization
  name: "Modernizace likvidace pojistných událostí"
  type: legacy-modernization
  type_alias: null
  schema_version: 1
  language: cs
  status: active

ddda:
  repository: romanhlavac/ddd-accelerator
  required_ref: main
  lock_file: ddda.lock.yaml
miro:
  board_id: null
  workspace_area: claims-modernization
  synchronization: disabled
artifacts:
  canonical_source: yaml
  root: artifacts
  mermaid_projection: true
  conflict_policy: manual-review
```

## Kontroly

```powershell
$ProjectRoot = Join-Path $WorkspaceRoot 'projects\claims-modernization'

git -C $ProjectRoot status
Get-Content (Join-Path $ProjectRoot 'project.yaml')
Get-Content (Join-Path $ProjectRoot 'ddda.lock.yaml')

& (Join-Path $PlatformRoot 'scripts\Test-DDDAInstallation.ps1') `
  -PlatformPath $PlatformRoot `
  -WorkspaceRoot $WorkspaceRoot `
  -ProjectPath $ProjectRoot
```

## Typické chyby

- příkazy jsou spuštěny z jiného adresáře než z parent adresáře deklarovaného v postupu,
- projekt je založen uvnitř platformního Git repozitáře,
- projekt je pojmenován podle technického řešení místo business scope,
- platformní a projektové změny jsou připraveny v jednom commitu,
- kopie jiného projektu obsahuje staré `artifact_id` nebo Miro mapping,
- `ddda.lock.yaml` je ručně přepsán bez řízeného upgradu.

## Navazující krok

Pokračujte kuchařkou `02-priprava-miro-boardu.md` a poté gate G1.
