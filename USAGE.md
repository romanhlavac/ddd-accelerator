# DDDA — chat-first provozní návod

Tento dokument je hlavní end-to-end uživatelská příručka. Popisuje první clone, smoke testy, workspace, example projekt, vlastní řízený projekt, starter metodiku, status a gaty, Miro, Git, diagnostiku a bezpečnost.

## 1. Pracovní model

DDDA má dvě oddělené změnové oblasti:

1. **platforma** — metodika, knowledge pack, schémata, runtime, scaffoldy, skripty a obecná dokumentace;
2. **projekt** — intake, evidence, doménové modely, gate records, ADR, Miro mapping, reporty a rozhodnutí konkrétní iniciativy.

Každá chatová relace začíná scope:

```text
Scope: project
Aktivní projekt: claims-modernization
Povoleno: project.yaml, project-intake.yaml, lifecycle-tailoring.yaml, ingestion/, artifacts/, decisions/, workshops/, miro/, reports/, .ddda/
Zakázáno: platformní repozitář, secrets, implicitní push/merge, automatické gate approval
```

nebo:

```text
Scope: platform
Povoleno: docs/, knowledge/, config/, schemas/, scripts/, runtime/, templates/, scaffolds/
Zakázáno: klientská a projektová data
```

Chat vysvětluje, navrhuje a reviewuje. Skripty provádějí potvrzené změny. Člověk schvaluje scope, gaty, sémantické konflikty, commit, push a merge.

## 2. Kanonický první clone a smoke testy

Z parent adresáře:

```powershell
New-Item -ItemType Directory -Force .\DDDA-Workspace\platform | Out-Null

git clone `
  https://github.com/romanhlavac/ddd-accelerator.git `
  .\DDDA-Workspace\platform\ddd-accelerator

Set-Location .\DDDA-Workspace\platform\ddd-accelerator

.\scripts\Initialize-DDDAFirstRun.ps1 -WithMiro -Full
```

Tento příkaz automaticky:

1. ověří platformní Git root a čistý stav;
2. ověří PowerShell a Python;
3. nainstaluje steering a Miro runtime;
4. spustí izolovaný platformní Miro smoke test;
5. vytvoří workspace;
6. materializuje referenční example projekt;
7. provede workspace a project doctor;
8. vytvoří projektový Miro board;
9. odešle aktuální managed YAML artefakty na board;
10. ověří idempotentní render i managed artifact push.

První online běh si vyžádá token se scopes `boards:read` a `boards:write`. Na Windows se uloží pomocí DPAPI mimo Git.

Offline varianta:

```powershell
.\scripts\Initialize-DDDAFirstRun.ps1
```

Detail: `docs/getting-started/01-clone-smoke-example.md`.

## 3. Example projekt a další krok

Standardní example je:

```text
DDDA-Workspace/projects/life-insurance-greenfield
```

Po online inicializaci zkontroluj projektový mapping, sync state a sync report:

```powershell
$WorkspaceRoot = (Resolve-Path '..\..').Path
$ProjectRoot = Join-Path $WorkspaceRoot 'projects\life-insurance-greenfield'

git -C $ProjectRoot status --short
git -C $ProjectRoot diff -- miro/ reports/miro-sync/
```

Je-li diff správný:

```powershell
git -C $ProjectRoot add miro/miro-map.yaml miro/sync-state.yaml reports/miro-sync/
git -C $ProjectRoot commit -m 'chore: initialize example Miro board and managed artifacts'
```

Doporučený chat:

> Scope: project. Aktivní projekt: `life-insurance-greenfield`. Načti `project.yaml`, relevantní artefakty, `artifacts/status/current-status.yaml`, pokud existuje, a knowledge index. Shrň stav, nejistoty a nejmenší další krok. Nic nezapisuj bez potvrzení.

## 4. Založení vlastního řízeného projektu

### 4.1 Intake přes chat

Použij prompt:

> Pomoz mi připravit DDDA project intake. Nezačínej technologií. Ptej se na business problém, rozhodnutí, goal, scope/out-of-scope, aktéry, ownery, omezení, předpoklady, quality attributes, existující systémy a týmy. Doporuč nejmenší vhodný kanonický typ projektu. Výstup připrav podle `templates/project/project-intake.template.yaml`. Nic nevytvářej, dokud intake nepotvrdím.

Povinné intake části:

- project ID, name a type;
- business problem;
- decision to enable;
- goal;
- scope-in a explicitní out-of-scope;
- actors;
- quality attributes;
- ownery, pokud jsou známí.

### 4.2 Jeden execution příkaz

```powershell
$WorkspaceRoot = (Resolve-Path '..\..').Path

.\scripts\Initialize-DDDAProjectFirstRun.ps1 `
  -WorkspaceRoot $WorkspaceRoot `
  -IntakeFile '..\claims-modernization.intake.yaml' `
  -WithMiro `
  -Full
```

Vznikne:

```text
projects/claims-modernization/
├── project.yaml
├── project-intake.yaml
├── project-profile.yaml
├── lifecycle-tailoring.yaml
├── artifacts/align/project-charter.yaml
├── artifacts/status/current-status.yaml
├── artifacts/status/next-actions.yaml
├── decisions/gates/G1.yaml ... G8.yaml
├── .ddda/session-context.yaml
├── .ddda/agent-contract.yaml
├── miro/
└── reports/project-status.yaml
```

Skript vytvoří iniciační commit. Miro mapping, sync state a sync report po online bootstrapu zůstanou k samostatnému review a commitu.

Offline:

```powershell
.\scripts\Initialize-DDDAProjectFirstRun.ps1 `
  -WorkspaceRoot $WorkspaceRoot `
  -IntakeFile '..\claims-modernization.intake.yaml'
```

Po přerušeném běhu:

```powershell
.\scripts\Initialize-DDDAProjectFirstRun.ps1 `
  -WorkspaceRoot $WorkspaceRoot `
  -IntakeFile '..\claims-modernization.intake.yaml' `
  -WithMiro `
  -Resume
```

Resume odmítne necommitnuté změny mimo řízené DDDA cesty.

## 5. Typy projektů

### 5.1 `portfolio-program`

Více domén, produktů a týmů. Starter tok zůstává zachován; programová rozšíření přijdou v PR #9.

### 5.2 `greenfield-product`

Product vision → potřeby uživatelů → Big Picture EventStorming → subdomény a BC → první hodnotný slice → tactical design.

### 5.3 `legacy-modernization`

Business pain → as-is evidence → skrytá pravidla → seams/ACL → migrační slice → reconciliation → decommission.

### 5.4 `legacy-transformation`

Současná změna business modelu, operating modelu a core IT včetně transition states.

### 5.5 `integration-landscape`

Business scénáře → context map → source of truth → kontrakty → konzistence, latency, failure modes a observability.

### 5.6 `purchased-product-adoption`

Business odpovědnost → vendor model → fit-gap → data ownership → ACL → exit a continuity plan.

### 5.7 `domain-discovery`

Intake → evidence → glossary → commands/events/actors → hotspots → subdomény → kandidátní BC → validation backlog.

### 5.8 `architecture-review`

Scope → evidence → business/domain alignment → quality attributes → boundaries/data ownership → findings → ADR backlog.

### 5.9 `operating-model-and-teams`

Doménové hypotézy → flow of change → ownership → cognitive load → Team Topologies → interaction modes.

### 5.10 `bounded-context-design`

Purpose a ubiquitous language → Design-Level EventStorming → lifecycle → aggregates/invariants → ports → persistence/integration.

## 6. Starter metodika a tailoring

Kanonické jádro:

```text
Align → Discover → Decompose → Strategize → Connect → Organize → Define → Code
   G1       G2          G3            G4          G5         G6        G7      G8
```

Tailoring určuje hloubku, rozšíření a případně odložené fáze. Neodstraňuje význam starter metodiky a nesmí automaticky označit odloženou gate za splněnou.

Automatizace rozlišuje:

- **evidence status** — zda existují očekávané podklady;
- **artifact status** — observed, candidate, validated, accepted, superseded, deleted_pending;
- **gate decision** — passed, conditional nebo rejected po explicitním review.

## 7. Current status a konverzační menu

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot
```

Výchozí režim je read-only. Načte `reports/project-status.yaml` a nemění projektový Git working tree.

Strojově čitelný read-only výstup:

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot -Json
```

Po ruční změně evidence lze status explicitně přepočítat:

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot -Refresh
```

`-Refresh` je write operace: aktualizuje `current-status.yaml`, `next-actions.yaml` a `reports/project-status.yaml`. Změny zkontroluj a commitni před navazující Miro operací.

Doporučený chat:

> Načti current status a next actions. Vysvětli, proč je další gate právě tato. Ukaž chybějící evidence, nejistoty a maximálně tři další kroky. Neprováděj zápis bez potvrzení.

## 8. Gate engine

Všechny gaty:

```powershell
.\scripts\Test-DDDAGates.ps1 -ProjectPath $ProjectRoot
```

Jedna gate:

```powershell
.\scripts\Test-DDDAGates.ps1 -ProjectPath $ProjectRoot -Gate G3
```

`ready_for_review` není approval. Je to technická informace, že byly nalezeny požadované evidence paths.

Explicitní review:

```powershell
.\scripts\Complete-DDDALifecycleStep.ps1 `
  -ProjectPath $ProjectRoot `
  -Gate G1 `
  -Outcome passed `
  -Reviewer 'Business owner' `
  -Note 'Scope a decision owner potvrzeny'
```

Conditional:

```powershell
.\scripts\Complete-DDDALifecycleStep.ps1 `
  -ProjectPath $ProjectRoot `
  -Gate G5 `
  -Outcome conditional `
  -Reviewer 'Architecture owner' `
  -Condition 'Potvrdit source of truth pro party identity'
```

Lokální commit pouze explicitně:

```powershell
.\scripts\Complete-DDDALifecycleStep.ps1 `
  -ProjectPath $ProjectRoot `
  -Gate G1 `
  -Outcome passed `
  -Reviewer 'Business owner' `
  -Commit
```

Push ani merge se neprovádí.

## 9. Knowledge pack a práce s kontextem

Začni `knowledge/00-knowledge-index.md`. Načítej pouze relevantní playbook. Před složitější projektovou úlohou vždy načti:

```text
project.yaml
project-intake.yaml
lifecycle-tailoring.yaml
artifacts/status/current-status.yaml
knowledge/00-knowledge-index.md
```

Facts musí zachovat source path. Hypotézy zůstávají candidate. Rozhodnutí mají ownera a Git review boundary.

Mode policy:

- Ask/Plan — porozumění, review, varianty, facilitační a rozhodovací framing;
- Agent — potvrzené souborové změny a execution skripty;
- Debug — reprodukce a izolace technické chyby;
- explicitní reasoning — gates, BC boundaries, ADR a investiční rozhodnutí;
- Auto — jen nízkorizikový drafting, ne finální rozhodnutí.

## 10. Ingestion řízený chatem

Současný PR #8 zachovává manuálně řízený ingestion:

1. vlož zdroje do `ingestion/`;
2. vytvoř `ingestion/catalog.yaml` s provenance, ownerem, důvěryhodností a citlivostí;
3. nech chat oddělit fakta, tvrzení, hypotézy a otázky;
4. zapiš rozpory jako hotspoty.

Automatizované extraktory a input-fit assessment jsou plánované v PR #10.

## 11. Miro app a runtime

Miro runtime očekává scopes `boards:read` a `boards:write`. Pro běžnou práci používej secret store vytvořený first-runem; token nevkládej do příkazové historie.

Offline doctor:

```powershell
.\scripts\Test-DDDAMiroConfiguration.ps1 -ProjectPath $ProjectRoot
```

Online doctor:

```powershell
.\scripts\Test-DDDAMiroConfiguration.ps1 -ProjectPath $ProjectRoot -Online
```

## 12. Inicializace projektového boardu a managed artefaktů

Dry-run:

```powershell
.\scripts\Initialize-DDDAMiroBoard.ps1 -ProjectPath $ProjectRoot -DryRun
```

Vytvoření boardu:

```powershell
.\scripts\Initialize-DDDAProjectMiro.ps1 `
  -WorkspaceRoot $WorkspaceRoot `
  -ProjectId 'claims-modernization' `
  -CreateBoard
```

Inicializátor nejprve vykreslí scaffold a potom automaticky provede managed artifact push. Stabilní vazby zapisuje do `miro/miro-map.yaml`, common-base hashe do `miro/sync-state.yaml` a auditní výsledek do `reports/miro-sync/`. Status a next-actions jsou standardní managed artifacts a po úspěšném běhu jsou na projektovém boardu i v mappingu.

## 13. Obousměrná synchronizace

Pull:

```powershell
.\scripts\Invoke-DDDAMiroSync.ps1 -ProjectPath $ProjectRoot -Direction Pull -DryRun
```

Push:

```powershell
.\scripts\Invoke-DDDAMiroSync.ps1 -ProjectPath $ProjectRoot -Direction Push -DryRun
```

Both:

```powershell
.\scripts\Invoke-DDDAMiroSync.ps1 -ProjectPath $ProjectRoot -Direction Both
```

Synchronizují se pouze položky s markerem `DDDA:<project>:<artifact>`. Unmanaged workshopový obsah se zachová.

## 14. Polling worker

```powershell
.\scripts\Start-DDDAMiroSyncWorker.ps1 `
  -ProjectPath $ProjectRoot `
  -IntervalSeconds 60
```

Worker provádí stejný řízený sync, zapisuje report, při konfliktu končí exit code 2 a nikdy neprovádí commit, push nebo merge.

Technický test dvou cyklů:

```powershell
.\scripts\Start-DDDAMiroSyncWorker.ps1 `
  -ProjectPath $ProjectRoot `
  -IntervalSeconds 30 `
  -MaxCycles 2
```

## 15. Konflikty a mazání

Při souběžné změně stejné sémantiky vznikne explicitní conflict record v `miro/conflicts/`. Nic se nepřepisuje last-write-wins.

Obnova chybějící mapped položky:

```powershell
.\scripts\Invoke-DDDAMiroSync.ps1 `
  -ProjectPath $ProjectRoot `
  -Direction Push `
  -RecreateMissing `
  -DryRun
```

Mazání je tombstone-first přes `artifact.status: deleted_pending`. Skutečné odstranění vyžaduje `-ConfirmDelete`.

## 16. Git a PR workflow

Před commitem:

```powershell
.\scripts\Test-DDDARepositoryScope.ps1 `
  -PlatformPath $PlatformRoot `
  -ProjectPath $ProjectRoot `
  -Scope project `
  -RequireChanges

git -C $ProjectRoot diff
git -C $ProjectRoot diff --check
```

Prompt:

> Připrav projektový commit. Odděl generované reporty od sémantických změn, ukaž diff, navrhni commit message a ověř čistý platformní repozitář. Nepushuj bez potvrzení.

## 17. Acceptance testy

Offline PR #8 suite:

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering
```

Online proti Miro:

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering -WithMiro -Full -CleanupOnFailure
```

Vizuální review:

```powershell
.\scripts\Test-DDDAAcceptance.ps1 `
  -Suite project-steering `
  -WithMiro `
  -Full `
  -KeepReviewBoard
```

Po PASS se standardně odstraní dočasný workspace i board; report zůstane v lokálním DDDA state adresáři.

## 18. Upgrade projektu

```powershell
.\scripts\Update-DDDAProject.ps1 `
  -PlatformPath $PlatformRoot `
  -ProjectPath $ProjectRoot `
  -TargetRef main
```

Upgrade je samostatná projektová změna a nemá automaticky měnit přijaté doménové rozhodnutí.

## 19. Diagnostika

```powershell
.\scripts\Test-DDDAInstallation.ps1 `
  -PlatformPath $PlatformRoot `
  -WorkspaceRoot $WorkspaceRoot `
  -ProjectPath $ProjectRoot

git -C $PlatformRoot status
git -C $ProjectRoot status
Get-Content (Join-Path $ProjectRoot 'artifacts\status\current-status.yaml')
Get-Content (Join-Path $ProjectRoot 'miro\miro-map.yaml')
Get-Content (Join-Path $ProjectRoot 'miro\sync-state.yaml')
```

## 20. Bezpečnostní pravidla

- tokeny a client secrets pouze v environment variables nebo secret store;
- token se nesmí objevit v intake, reportu, Gitu nebo shell history;
- žádný automatický push nebo merge;
- žádný last-write-wins pro sémantické konflikty;
- žádné automatické gate approval;
- klientská data nikdy do platformního repozitáře;
- před citlivým exportem ověř `classification.data_sensitivity`;
- Miro acceptance test nepoužívá produkční projektový board.

## 21. Kde hledat detail

- capability katalog: `docs/capabilities/README.md`;
- schemas a kontrakty: `docs/reference/contracts.md`;
- CLI reference: `docs/reference/cli.md`;
- řízený project bootstrap: `docs/cookbooks/16-zalozeni-rizeneho-projektu.md`;
- status a gate review: `docs/cookbooks/17-status-gates-a-dalsi-krok.md`;
- Miro troubleshooting: `docs/cookbooks/12-miro-troubleshooting.md`;
- knowledge index: `knowledge/00-knowledge-index.md`.
