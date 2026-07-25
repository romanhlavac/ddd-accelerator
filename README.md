# DDDA — Domain-Driven Design Accelerator

DDDA je chat-first, Miro-first a Git-verzované pracovní prostředí pro doménovou analýzu, socio-technickou architekturu, modernizaci a návrh bounded contexts. Jedna platformní instalace obsluhuje více nezávislých projektových repozitářů.

## Co je implementováno

- multi-project workspace a samostatný Git repozitář pro každý projekt;
- kanonická starter metodika `Align → Discover → Decompose → Strategize → Connect → Organize → Define → Code` s gatami G1–G8;
- chatové pracovní postupy, projektové prompty a přenosný knowledge pack;
- řízený project intake, lifecycle tailoring, current status, next actions a evidence-driven gate records;
- agentní scope a handoff kontrakt, mode/model policy a explicitní Git approval boundary;
- deklarativní Miro scaffold a živý REST API v2 renderer;
- obousměrná synchronizace spravovaných artefaktů YAML ↔ Miro;
- dry-run, explicitní konflikty, tombstone delete, auditní reporty a idempotentní mapping;
- řízený polling worker;
- automatizovaná inicializace po clone a online Miro smoke test;
- automatizované vytvoření workspace a referenčního example projektu;
- automatizovaný one-command bootstrap libovolného řízeného projektu;
- česká metodika, capability katalog, kuchařky, CLI reference a referenční projekt životní pojišťovny.

## Základní ownership

| Reprezentace | Vlastní |
|---|---|
| YAML | identitu, význam, status, stage, vztahy a data ownership |
| Miro | workshopovou interakci, polohu, velikost a vizuální seskupení |
| Git | historii, review a schválení změn |
| Mermaid | generované pohledy pro chat a dokumentaci |
| Chat | porozumění, otázky, varianty, review a potvrzení execution kroku |

Sémantický konflikt se nikdy neřeší implicitním last-write-wins. Gate se nikdy neschválí pouze proto, že automatizace našla požadované soubory.

## Kanonický první start

Z parent adresáře, ve kterém má vzniknout `DDDA-Workspace`:

```powershell
New-Item -ItemType Directory -Force .\DDDA-Workspace\platform | Out-Null

git clone `
  https://github.com/romanhlavac/ddd-accelerator.git `
  .\DDDA-Workspace\platform\ddd-accelerator

Set-Location .\DDDA-Workspace\platform\ddd-accelerator

.\scripts\Initialize-DDDAFirstRun.ps1 -WithMiro -Full
```

Jediný příkaz po clone:

1. zkontroluje Git, PowerShell, Python a povinné soubory;
2. nainstaluje steering a Miro runtime;
3. spustí izolovaný online platformní Miro smoke test;
4. vytvoří workspace;
5. materializuje `life-insurance-greenfield` jako samostatný Git repozitář;
6. provede kontroly workspace a projektu;
7. vytvoří cílový Miro board example projektu;
8. provede online doctor a idempotentní render.

První online běh si vyžádá Miro access token se scopes `boards:read` a `boards:write`. Na Windows jej uloží přes DPAPI mimo Git root. Skript neprovádí push ani merge a necommituje Miro mapping.

Detail: [Clone, smoke testy, workspace a example projekt](docs/getting-started/01-clone-smoke-example.md).

## Offline první start

```powershell
.\scripts\Initialize-DDDAFirstRun.ps1
```

## Řízený vlastní projekt

Nejprve připrav potvrzený intake podle `templates/project/project-intake.template.yaml`. Potom:

```powershell
$WorkspaceRoot = (Resolve-Path '..\..').Path

.\scripts\Initialize-DDDAProjectFirstRun.ps1 `
  -WorkspaceRoot $WorkspaceRoot `
  -IntakeFile '..\claims-modernization.intake.yaml' `
  -WithMiro `
  -Full
```

Skript vytvoří projekt, project profile, tailoring, project charter, G1–G8 records, agent contract, current status, next actions, iniciační commit a volitelně projektový Miro board.

Detail: [Kuchařka 16](docs/cookbooks/16-zalozeni-rizeneho-projektu.md).

## Current status a gate review

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot

.\scripts\Test-DDDAGates.ps1 -ProjectPath $ProjectRoot

.\scripts\Complete-DDDALifecycleStep.ps1 `
  -ProjectPath $ProjectRoot `
  -Gate G1 `
  -Outcome passed `
  -Reviewer 'Business owner'
```

`Complete-DDDALifecycleStep.ps1` standardně pouze aktualizuje projektové soubory. Push ani merge neprovádí. Lokální commit vytvoří jen s explicitním `-Commit`.

## Acceptance test PR #8

Offline:

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering
```

Online proti Miro:

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering -WithMiro -Full
```

Runner používá izolovaný workspace a board. Po úspěchu je odstraní a zachová report. Vizuální review lze vynutit přes `-KeepReviewBoard`.

## Řízený synchronizační worker

```powershell
$WorkspaceRoot = (Resolve-Path '..\..').Path
$PlatformRoot = (Resolve-Path '.').Path
$ProjectRoot = Join-Path $WorkspaceRoot 'projects\life-insurance-greenfield'

& (Join-Path $PlatformRoot 'scripts\Start-DDDAMiroSyncWorker.ps1') `
  -ProjectPath $ProjectRoot `
  -IntervalSeconds 60
```

Worker neprovádí Git commit, push ani merge a při sémantickém konfliktu se zastaví.

## Ovládání přes chat

Typický prompt:

> Scope: project. Aktivní projekt: `claims-modernization`. Načti `project.yaml`, `project-intake.yaml`, `lifecycle-tailoring.yaml`, `artifacts/status/current-status.yaml` a `knowledge/00-knowledge-index.md`. Shrň aktuální fázi, další gate, chybějící evidence a navrhni nejmenší další krok. Nic nezapisuj bez potvrzení.

## Dokumentace

Začni zde:

1. [Getting started](docs/getting-started/01-clone-smoke-example.md)
2. [USAGE — úplný provozní návod](USAGE.md)
3. [Capability katalog](docs/capabilities/README.md)
4. [Index dokumentace](docs/README.md)
5. [Kuchařka řízeného projektu](docs/cookbooks/16-zalozeni-rizeneho-projektu.md)
6. [Status a gaty](docs/cookbooks/17-status-gates-a-dalsi-krok.md)
7. [Referenční greenfield example](examples/life-insurance-greenfield/README.md)
