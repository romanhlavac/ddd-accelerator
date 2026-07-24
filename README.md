# DDDA — Domain-Driven Design Accelerator

DDDA je chat-first, Miro-first a Git-verzované pracovní prostředí pro doménovou analýzu, socio-technickou architekturu, modernizaci a návrh bounded contexts. Jedna platformní instalace obsluhuje více nezávislých projektových repozitářů.

## Co je implementováno

- multi-project workspace a samostatný Git repozitář pro každý projekt,
- chatové pracovní postupy a projektové prompty,
- deklarativní Miro scaffold pro tok Align → Discover → Decompose → Strategize → Connect → Organize → Define → Code,
- živý renderer Miro boardu přes REST API v2,
- obousměrná synchronizace spravovaných artefaktů YAML ↔ Miro,
- dry-run, explicitní konflikty, tombstone delete, auditní sync reporty a idempotentní mapping,
- řízený polling worker pro průběžnou synchronizaci,
- automatizovaná inicializace po clone a opakovatelný online Miro smoke test,
- automatizované vytvoření workspace a materializace referenčního example projektu,
- idempotentní inicializace cílového Miro boardu pro konkrétní projekt,
- Mermaid jako odvozená textová projekce,
- česká metodika, kuchařky, typové workflow a referenční projekt životní pojišťovny.

## Základní ownership

| Reprezentace | Vlastní |
|---|---|
| YAML | identitu, význam, status, stage, vztahy a data ownership |
| Miro | workshopovou interakci, polohu, velikost a vizuální seskupení |
| Git | historii, review a schválení změn |
| Mermaid | generované pohledy pro chat a dokumentaci |

Sémantický konflikt se nikdy neřeší implicitním last-write-wins. Runtime vytvoří conflict record a vyžádá rozhodnutí.

## Kanonický první start

Toto je doporučený postup pro nového uživatele. Po `git clone` se workspace, referenční example projekt i oba Miro smoke testy spouštějí jedním orchestrátorem.

Z parent adresáře, ve kterém má vzniknout `DDDA-Workspace`:

```powershell
New-Item -ItemType Directory -Force .\DDDA-Workspace\platform | Out-Null

git clone `
  https://github.com/romanhlavac/ddd-accelerator.git `
  .\DDDA-Workspace\platform\ddd-accelerator

Set-Location .\DDDA-Workspace\platform\ddd-accelerator

.\scripts\Initialize-DDDAFirstRun.ps1 -WithMiro -Full
```

Jediný příkaz po clone automaticky provede:

1. kontrolu platformy, Pythonu a PowerShell skriptů;
2. instalaci Miro runtime;
3. izolovaný online platformní Miro smoke test;
4. vytvoření `DDDA-Workspace`;
5. materializaci skutečného referenčního projektu `life-insurance-greenfield` včetně artifacts, ingestion a workshop prompts;
6. kontrolu workspace a projektu;
7. vytvoření cílového Miro boardu example projektu;
8. online doctor a idempotentní kontrolní render projektového boardu.

První online běh si vyžádá Miro access token se scopes `boards:read` a `boards:write`. Na Windows jej uloží pomocí DPAPI mimo Git root. Skript neprovádí automatický push, merge ani commit projektového Miro mappingu.

Detailní iniciační postup a očekávané výstupy jsou v [kuchařce 15 — První spuštění a referenční example projekt](docs/cookbooks/15-prvni-spusteni-a-example-projekt.md).

## Offline první start

Bez Miro API:

```powershell
.\scripts\Initialize-DDDAFirstRun.ps1
```

Tím vznikne a projde kontrolou workspace i referenční example projekt. Projektový board lze doplnit později:

```powershell
.\scripts\Initialize-DDDAProjectMiro.ps1 `
  -WorkspaceRoot '..\..' `
  -ProjectId 'life-insurance-greenfield' `
  -CreateBoard
```

## Samostatné provozní příkazy

Pouze platformní inicializace po clone:

```powershell
.\scripts\Initialize-DDDAAfterClone.ps1 -WithMiro -Full
```

Pouze opakovaný online Miro smoke test platformy:

```powershell
.\scripts\Invoke-DDDAMiroSmokeTest.ps1 -Full
```

Pouze materializace referenčního example projektu v existujícím workspace:

```powershell
.\scripts\New-DDDAExampleProject.ps1 -WorkspaceRoot '..\..'
```

Pouze vytvoření nebo kontrolní render projektového boardu:

```powershell
.\scripts\Initialize-DDDAProjectMiro.ps1 `
  -WorkspaceRoot '..\..' `
  -ProjectId 'life-insurance-greenfield' `
  -CreateBoard
```

## Řízený synchronizační worker

Pro průběžnou spolupráci lze spustit polling worker. Worker nejméně jednou za 30 sekund provede kontrolovaný režim `Both`, zapisuje auditní report a při prvním konfliktu se ukončí s exit code `2`, aby se konflikt nešířil dál.

```powershell
$WorkspaceRoot = (Resolve-Path '..\..').Path
$PlatformRoot = (Resolve-Path '.').Path
$ProjectRoot = Join-Path $WorkspaceRoot 'projects\life-insurance-greenfield'

& (Join-Path $PlatformRoot 'scripts\Start-DDDAMiroSyncWorker.ps1') `
  -ProjectPath $ProjectRoot `
  -IntervalSeconds 60
```

Worker neprovádí Git commit, push ani merge a neobnovuje OAuth token. Rotaci nebo refresh tokenu musí zajistit provozní prostředí; pro lokální práci lze použít uložený token nebo `MIRO_ACCESS_TOKEN`.

## Ovládání přes chat

Typický prompt:

> Scope: project. Aktivní projekt: `life-insurance-greenfield`. Nejprve načti `project.yaml`, `ddda.lock.yaml`, `docs/README.md` a relevantní cookbook. Proveď dry-run Miro synchronizace. Vypiš plánované create/update/delete operace, konflikty a dotčené YAML soubory. Nic nezapisuj, dokud plán nepotvrdím.

## Dokumentace

Začni [kuchařkou prvního spuštění](docs/cookbooks/15-prvni-spusteni-a-example-projekt.md), pokračuj [indexem dokumentace](docs/README.md), [hlavním návodem](USAGE.md), [inicializací po clone](docs/cookbooks/13-inicializace-po-clone.md), [inicializací cílového Miro boardu](docs/cookbooks/14-inicializace-ciloveho-miro-boardu.md) a referenčním [greenfield příkladem životní pojišťovny](examples/life-insurance-greenfield/README.md).
