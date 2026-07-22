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

## Rychlý start

Před spuštěním se přesuň do **parent adresáře**, ve kterém má vzniknout `DDDA-Workspace`.

```powershell
New-Item -ItemType Directory -Force .\DDDA-Workspace\platform | Out-Null

git clone `
  https://github.com/romanhlavac/ddd-accelerator.git `
  .\DDDA-Workspace\platform\ddd-accelerator

$WorkspaceRoot = (Resolve-Path .\DDDA-Workspace).Path
$PlatformRoot = (Resolve-Path .\DDDA-Workspace\platform\ddd-accelerator).Path

& (Join-Path $PlatformRoot 'scripts\Test-DDDAInstallation.ps1') `
  -PlatformPath $PlatformRoot

& (Join-Path $PlatformRoot 'scripts\Initialize-DDDAWorkspace.ps1') `
  -WorkspaceRoot $WorkspaceRoot

& (Join-Path $PlatformRoot 'scripts\New-DDDAProject.ps1') `
  -WorkspaceRoot $WorkspaceRoot `
  -ProjectId life-insurance-greenfield `
  -Name 'Nová životní pojišťovna' `
  -Type portfolio-program `
  -TypeAlias greenfield-portfolio
```

## Zapojení Miro

Miro app musí mít scope `boards:read` a `boards:write`. Token se neukládá do Gitu.

```powershell
$env:MIRO_ACCESS_TOKEN = '<token>'
$env:LIFE_INSURANCE_GREENFIELD_MIRO_BOARD_ID = '<board-id>'

& (Join-Path $PlatformRoot 'scripts\Install-DDDAMiroRuntime.ps1')

$ProjectRoot = Join-Path $WorkspaceRoot 'projects\life-insurance-greenfield'

& (Join-Path $PlatformRoot 'scripts\Test-DDDAMiroConfiguration.ps1') `
  -ProjectPath $ProjectRoot `
  -Online

& (Join-Path $PlatformRoot 'scripts\Initialize-DDDAMiroBoard.ps1') `
  -ProjectPath $ProjectRoot `
  -DryRun

& (Join-Path $PlatformRoot 'scripts\Initialize-DDDAMiroBoard.ps1') `
  -ProjectPath $ProjectRoot
```

## Řízený synchronizační worker

Pro průběžnou spolupráci lze spustit polling worker. Worker nejméně jednou za 30 sekund provede kontrolovaný režim `Both`, zapisuje auditní report a při prvním konfliktu se ukončí s exit code `2`, aby se konflikt nešířil dál.

```powershell
& (Join-Path $PlatformRoot 'scripts\Start-DDDAMiroSyncWorker.ps1') `
  -ProjectPath $ProjectRoot `
  -IntervalSeconds 60
```

Worker neprovádí Git commit, push ani merge a neobnovuje OAuth token. Rotaci nebo refresh tokenu musí zajistit provozní prostředí; pro lokální práci lze token před spuštěním znovu nastavit v environment variable.

## Ovládání přes chat

Typický prompt:

> Scope: project. Aktivní projekt: `life-insurance-greenfield`. Nejprve načti `project.yaml`, `ddda.lock.yaml`, `docs/README.md` a relevantní cookbook. Proveď dry-run Miro synchronizace. Vypiš plánované create/update/delete operace, konflikty a dotčené YAML soubory. Nic nezapisuj, dokud plán nepotvrdím.

## Dokumentace

Začni v [indexu dokumentace](docs/README.md), pokračuj [hlavním návodem](USAGE.md) a referenčním [greenfield příkladem životní pojišťovny](examples/life-insurance-greenfield/README.md).
