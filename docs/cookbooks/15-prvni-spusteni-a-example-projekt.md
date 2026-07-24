# 15 První spuštění a referenční example projekt

## Účel

Toto je **kanonický iniciační postup pro nového uživatele DDDA**. Po `git clone` automatizuje celý řetězec:

1. kontrolu platformy a instalaci runtime;
2. izolovaný online smoke test proti Miro API;
3. vytvoření workspace;
4. materializaci referenčního projektu životní pojišťovny jako samostatného Git repozitáře;
5. kontrolu workspace a projektu;
6. vytvoření cílového Miro boardu example projektu;
7. online doctor a idempotentní kontrolní render projektového boardu.

Nižší úrovně postupu jsou popsány v kuchařkách [13 Inicializace po clone](13-inicializace-po-clone.md) a [14 Inicializace cílového Miro boardu](14-inicializace-ciloveho-miro-boardu.md). Pro první spuštění se jednotlivé příkazy ručně neskládají; používá se orchestrátor níže.

## Předpoklady

- Git;
- Windows PowerShell 5.1 nebo PowerShell 7;
- Python 3.11+ dostupný jako `python` nebo `py`;
- Miro Developer team a aplikace se scopes `boards:read` a `boards:write`;
- access token aplikace;
- nastavené `git config user.name` a `git config user.email`, protože example projekt dostane vlastní iniciační commit.

## Standardní clone

Z parent adresáře, ve kterém má vzniknout `DDDA-Workspace`:

```powershell
New-Item -ItemType Directory -Force .\DDDA-Workspace\platform | Out-Null

git clone `
  https://github.com/romanhlavac/ddd-accelerator.git `
  .\DDDA-Workspace\platform\ddd-accelerator

Set-Location .\DDDA-Workspace\platform\ddd-accelerator
```

## Jediný příkaz po clone

```powershell
.\scripts\Initialize-DDDAFirstRun.ps1 -WithMiro -Full
```

Při standardní topologii skript automaticky odvodí `WorkspaceRoot` jako adresář `DDDA-Workspace`. Při jiné topologii jej lze zadat explicitně:

```powershell
.\scripts\Initialize-DDDAFirstRun.ps1 `
  -WorkspaceRoot 'C:\path\to\DDDA-Workspace' `
  -WithMiro `
  -Full
```

## Co proběhne automaticky

### 1. Platforma po clone

Orchestrátor spustí `Initialize-DDDAAfterClone.ps1`:

- ověří čistý platformní Git root;
- zkontroluje povinné soubory a PowerShell syntaxi;
- nainstaluje Miro runtime do ignorovaného `.ddda/runtime/miro-venv`;
- spustí izolovaný online Miro smoke test;
- ověří YAML → Miro, Miro → YAML, `PromoteNew`, polling worker a idempotenci;
- po úspěchu odstraní dočasný testovací board a workspace.

Při prvním online běhu se token zadává skrytě. Na Windows se uloží pomocí DPAPI mimo Git root a další kroky jej znovu použijí.

### 2. Workspace

Vznikne:

```text
DDDA-Workspace/
├── platform/ddd-accelerator/
├── projects/
├── workspace.yaml
└── DDDA.code-workspace
```

Existující kompatibilní workspace se znovu použije.

### 3. Referenční example projekt

`New-DDDAExampleProject.ps1` vytvoří samostatný Git repozitář:

```text
DDDA-Workspace/projects/life-insurance-greenfield/
```

Do něj materializuje skutečný obsah z `examples/life-insurance-greenfield/`:

- bohatý `project.yaml`;
- ingestion katalog a interview placeholder;
- project charter;
- domain event `policy-issued`;
- context map;
- workshopové prompty;
- prázdný Miro mapping připravený pro první board;
- aktuální `ddda.lock.yaml` vůči klonované platformě.

Nejde tedy o prázdný projekt pouze pojmenovaný jako example.

### 4. Projektový Miro smoke test

`Initialize-DDDAProjectMiro.ps1 -CreateBoard`:

- provede povinný dry-run;
- vytvoří cílový board projektu;
- vyrenderuje metodický scaffold;
- spustí online doctor;
- provede druhý kontrolní render;
- ověří stejné `board_id` a stabilní množinu `miro_item_id`;
- nevytvoří druhý board ani duplicitní frames.

Toto je první smoke test proti Miro **pro skutečný example projekt**, nikoli pouze platformní dočasný test.

## Očekávaný konec

```text
DDDA první spuštění: PASS
Workspace: ...\DDDA-Workspace
Projekt:   ...\DDDA-Workspace\projects\life-insurance-greenfield
```

Workspace otevři:

```powershell
cursor .\DDDA-Workspace\DDDA.code-workspace
```

Při standardní topologii a práci z platformního rootu:

```powershell
cursor ..\..\DDDA.code-workspace
```

## Jediné ruční kroky

Po clone zůstávají záměrně ruční pouze:

1. první skryté zadání Miro access tokenu;
2. kontrola změny `projects/life-insurance-greenfield/miro/miro-map.yaml`;
3. projektový commit mappingu po review.

Skript neprovádí automatický push, merge ani commit Miro mappingu.

Kontrola mappingu:

```powershell
git -C '..\..\projects\life-insurance-greenfield' diff -- miro/miro-map.yaml
```

Commit po review:

```powershell
git -C '..\..\projects\life-insurance-greenfield' add miro/miro-map.yaml

git -C '..\..\projects\life-insurance-greenfield' commit -m 'chore: initialize example Miro board'
```

## Offline varianta

Bez Miro API:

```powershell
.\scripts\Initialize-DDDAFirstRun.ps1
```

Vytvoří a ověří workspace i referenční example projekt, ale nevytvoří projektový board. Online část lze doplnit později:

```powershell
.\scripts\Initialize-DDDAProjectMiro.ps1 `
  -WorkspaceRoot '..\..' `
  -ProjectId 'life-insurance-greenfield' `
  -CreateBoard
```

## Opakované spuštění a obnova

Orchestrátor je resumable:

- existující workspace znovu použije;
- existující validní example projekt znovu použije;
- existující `board_id` z `miro/miro-map.yaml` použije místo vytvoření dalšího boardu;
- po přerušeném projektovém Miro bootstrapu automaticky použije bezpečný `-Resume` režim;
- `-Resume` připustí pouze necommitnuté změny pod `miro/`; změny v `project.yaml`, artifacts, ingestion nebo jiných projektových souborech běh zastaví;
- druhý běh znovu provede dry-run, online doctor a idempotentní render bez vytvoření dalšího boardu.

Při selhání platformního smoke testu zůstává dočasný board a workspace pro diagnostiku. Detaily jsou v kuchařce 13. Při selhání po vytvoření projektového boardu neupravuj ani nemaž `miro/miro-map.yaml`; po opravě platformy spusť stejný first-run příkaz znovu.

## Definition of Done

- výstup končí `DDDA první spuštění: PASS`;
- platformní Git root je čistý;
- `workspace.yaml` registruje `life-insurance-greenfield`;
- example projekt je samostatný Git repozitář;
- example obsahuje referenční artifacts, ingestion a workshop prompts;
- projektový Miro board prošel online doctor a idempotentním druhým renderem;
- projektový diff po online inicializaci je omezen na `miro/`;
- token není v repozitáři ani reportu.
