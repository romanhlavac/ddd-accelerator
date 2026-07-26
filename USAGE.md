# DDDA — úplný chat-first provozní návod

Tento dokument je hlavní end-to-end uživatelská příručka. Pokrývá vývoj platformy, clone a smoke testy, candidate/release package, generovaný validation workspace, example projekt, vlastní řízený projekt, starter metodiku, status a gaty, Miro, Git, diagnostiku a bezpečnost.

## 1. Pracovní model

DDDA má čtyři explicitně oddělené oblasti:

```text
DDDA platform repository
  verzovaná metodika, knowledge, schémata, runtime, CLI, testy a release lifecycle

DDDA release package
  distribuovatelný ZIP vytvořený z přesného Git source state

DDDA workspace
  instance platformy obsahující registr a samostatné projektové repozitáře

DDDA project repository
  intake, evidence, modely, rozhodnutí, gaty, Miro mapping a reporty konkrétní iniciativy
```

Klientský workspace se nikdy nepoužívá jako platformní test fixture. Platformní testy používají syntetický minimal example.

Každá chatová relace začíná scope.

Projektová práce:

```text
Scope: project
Aktivní projekt: claims-modernization
Povoleno: project.yaml, project-intake.yaml, lifecycle-tailoring.yaml, ingestion/, artifacts/, decisions/, workshops/, miro/, reports/, .ddda/
Zakázáno: platformní repozitář, secrets, implicitní push/merge, automatické gate approval
```

Vývoj platformy:

```text
Scope: platform
Povoleno: CHANGELOG.md, docs/, knowledge/, config/, schemas/, scripts/, runtime/, templates/, scaffolds/, examples/, tests/
Zakázáno: klientská a projektová data, secrets, přímá změna main, implicitní promotion
```

Chat vysvětluje, navrhuje a reviewuje. Skripty provádějí potvrzené mechanické kroky. Člověk schvaluje scope, architektonická rozhodnutí, gaty, sémantické konflikty, commit, push, merge a release.

## 2. Vývoj DDDA platformy

### 2.1 Základní diagnostika

Z kořene platformního repozitáře:

```powershell
.\ddda.ps1 doctor
```

Příkaz ověří:

- Git nebo package distribuci;
- povinné soubory;
- PowerShell parser a UTF-8 BOM;
- JSON schemas;
- dokumentační strukturu;
- dostupnost stabilního CLI a platform lifecycle souborů.

### 2.2 Test suites

```powershell
.\ddda.ps1 test -Suite lint
.\ddda.ps1 test -Suite schema
.\ddda.ps1 test -Suite unit
.\ddda.ps1 test -Suite component
.\ddda.ps1 test -Suite regression
.\ddda.ps1 test -Suite security
```

Package-dependent suites vyžadují `-PackagePath`:

```powershell
.\ddda.ps1 test -Suite smoke -PackagePath $PackagePath
.\ddda.ps1 test -Suite integration -PackagePath $PackagePath
.\ddda.ps1 test -Suite e2e -PackagePath $PackagePath
```

Acceptance project steeringu:

```powershell
.\ddda.ps1 test -Suite acceptance
```

Online proti Miro:

```powershell
.\ddda.ps1 test -Suite acceptance -WithMiro -Full -CleanupOnFailure
```

### 2.3 Jednopříkazová validace PR

Offline:

```powershell
.\ddda.ps1 validate-pr -Pr 8
```

Včetně Miro:

```powershell
.\ddda.ps1 validate-pr -Pr 8 -WithMiro -Full -CleanupOnFailure
```

`validate-pr` automaticky:

1. ověří čistý aktivní platformní repozitář;
2. načte exact `refs/pull/<PR>/head` SHA;
3. vytvoří izolovaný checkout mimo aktivní repo;
4. vytvoří candidate package svázaný s SHA;
5. ověří package obsah, cesty a nepřítomnost secrets;
6. rozbalí package do čistého adresáře;
7. spustí lint, schema, unit, component, integration, smoke, regression a security;
8. vytvoří minimal example workspace z package;
9. provede manifest-driven ingestion syntetických vstupů;
10. ověří steering G1 → G2;
11. volitelně vytvoří izolovaný Miro board a ověří managed artifacts, mapping, sync state a idempotenci;
12. vytvoří JSON a Markdown validation report;
13. při PASS uklidí pracovní checkout a workspaces;
14. při FAIL zachová diagnostiku.

Aktivní větev ani aktivní working tree se nemění. Candidate package a validation report zůstávají pro promotion.

Pro zachování diagnostiky i po PASS:

```powershell
.\ddda.ps1 validate-pr -Pr 8 -KeepArtifacts
```

### 2.4 Candidate a release package

Package je jednotka distribuce a reprodukovatelné validace. Obsahuje `ddda-package.json` se source commit SHA, druhem package a verzí.

Interní tvorba candidate package:

```powershell
.\scripts\platform\New-DDDAPlatformPackage.ps1 -Kind candidate -Version 'pr.8.local' -OutputPath $PackagePath
```

Kontrola package:

```powershell
.\scripts\platform\Test-DDDAPlatformPackage.ps1 -PackagePath $PackagePath
```

Package nesmí obsahovat:

```text
.git/
.ddda/
.tmp/
.reports/
.releases/
dist/
Python caches
credentials
Miro token
client data
uživatelské absolutní cesty
```

### 2.5 Validation report

Report obsahuje:

- PR, branch a exact head SHA;
- package cestu a SHA-256;
- status a délku každé suite;
- diagnostické logy;
- workspace a Miro board ID, pokud byly použity.

Lokální platformní výstupy jsou mimo Git pod DDDA state rootem. Na Windows typicky:

```text
%LOCALAPPDATA%\DDDA\validation\
%LOCALAPPDATA%\DDDA\validation-reports\
%LOCALAPPDATA%\DDDA\packages\
%LOCALAPPDATA%\DDDA\promotion\
%LOCALAPPDATA%\DDDA\release-reports\
```

### 2.6 Promotion

Nejdřív spusť pouze preflight:

```powershell
.\ddda.ps1 promote-pr -Pr 8 -Version 0.8.0 -DryRun
```

Preflight kontroluje:

- PR je otevřený a není draft;
- target branch odpovídá policy;
- head SHA se od validace nezměnil;
- CI checks jsou PASS;
- existuje PASS validation report pro stejný PR a SHA;
- candidate package hash odpovídá reportu;
- review policy je splněna;
- changelog, ADR a migration note existují.

Dry-run neprovede merge, release ani tag.

Skutečný promotion vyžaduje samostatné explicitní potvrzení:

```powershell
.\ddda.ps1 promote-pr -Pr 8 -Version 0.8.0 -ConfirmMerge
```

S online Miro release acceptance:

```powershell
.\ddda.ps1 promote-pr -Pr 8 -Version 0.8.0 -ConfirmMerge -WithMiro -Full -CleanupOnFailure
```

Po merge promotion:

1. načte nový `main` a ověří merge commit;
2. vytvoří release package;
3. rozbalí package do izolovaného prostředí;
4. vytvoří generated release workspace;
5. provede manifest-driven ingestion;
6. spustí security, smoke, E2E a acceptance;
7. volitelně spustí Miro acceptance;
8. vytvoří release report;
9. vytvoří a pushne tag až po PASS.

Běžné testy nikdy nemergují ani netagují. `-ConfirmMerge` je explicitní lidská approval boundary.

Detail: `docs/user-guide/validate-and-promote-pr.md`.

## 3. Kanonický první clone a smoke testy

Z parent adresáře, ve kterém má vzniknout workspace:

```powershell
New-Item -ItemType Directory -Force '.\DDDA-Workspace\platform' | Out-Null
git clone 'https://github.com/romanhlavac/ddd-accelerator.git' '.\DDDA-Workspace\platform\ddd-accelerator'
Set-Location '.\DDDA-Workspace\platform\ddd-accelerator'
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
10. ověří idempotentní render a managed artifact push.

První online běh si vyžádá token se scopes `boards:read` a `boards:write`. Na Windows se uloží pomocí DPAPI mimo Git.

Offline varianta:

```powershell
.\scripts\Initialize-DDDAFirstRun.ps1
```

Detail: `docs/getting-started/01-clone-smoke-example.md`.

## 4. Example projekt a další krok

Standardní referenční projekt:

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

Po schválení diffu:

```powershell
git -C $ProjectRoot add miro/miro-map.yaml miro/sync-state.yaml reports/miro-sync/
git -C $ProjectRoot commit -m 'chore: initialize example Miro board and managed artifacts'
```

Doporučený chat:

> Scope: project. Aktivní projekt: `life-insurance-greenfield`. Načti `project.yaml`, relevantní artefakty, current status a knowledge index. Shrň stav, nejistoty a nejmenší další krok. Nic nezapisuj bez potvrzení.

## 5. Generovaný minimal validation workspace

Minimal example je syntetická platformní fixture:

```text
examples/minimal/
├── manifest.yaml
├── input/project-intake.yaml
├── input/domain-notes.md
└── expected-invariants.yaml
```

Manifest-driven ingestion:

```powershell
.\scripts\platform\Invoke-DDDAExampleIngestion.ps1 -WorkspaceRoot $ValidationWorkspace
```

Generated workspace z rozbaleného package:

```powershell
.\scripts\platform\New-DDDAValidationWorkspace.ps1 -PlatformPath $ExtractedPackage -WorkspaceRoot $ValidationWorkspace
```

Výstup obsahuje ingestion report, samostatný projektový Git repozitář, steering metadata a počáteční stav `align/G1`.

Tento mechanismus je určen pro vývoj a release validaci platformy, nikoli jako náhrada enterprise ingestionu plánovaného v PR #10.

## 6. Založení vlastního řízeného projektu

### 6.1 Intake přes chat

Použij prompt:

> Pomoz mi připravit DDDA project intake. Nezačínej technologií. Ptej se na business problém, rozhodnutí, goal, scope/out-of-scope, aktéry, ownery, omezení, předpoklady, quality attributes, existující systémy a týmy. Doporuč nejmenší vhodný kanonický typ projektu. Výstup připrav podle `templates/project/project-intake.template.yaml`. Nic nevytvářej, dokud intake nepotvrdím.

Povinné části:

- project ID, name a type;
- business problem;
- decision to enable;
- goal;
- scope-in a explicitní out-of-scope;
- actors;
- quality attributes;
- ownery, pokud jsou známí.

### 6.2 Jeden execution příkaz

```powershell
$WorkspaceRoot = (Resolve-Path '..\..').Path
.\scripts\Initialize-DDDAProjectFirstRun.ps1 -WorkspaceRoot $WorkspaceRoot -IntakeFile '..\claims-modernization.intake.yaml' -WithMiro -Full
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

Skript vytvoří iniciační commit. Miro mapping, sync state a sync report zůstanou k samostatnému review a commitu.

Offline:

```powershell
.\scripts\Initialize-DDDAProjectFirstRun.ps1 -WorkspaceRoot $WorkspaceRoot -IntakeFile '..\claims-modernization.intake.yaml'
```

Po přerušeném běhu:

```powershell
.\scripts\Initialize-DDDAProjectFirstRun.ps1 -WorkspaceRoot $WorkspaceRoot -IntakeFile '..\claims-modernization.intake.yaml' -WithMiro -Resume
```

Resume odmítne necommitnuté změny mimo řízené DDDA cesty.

## 7. Kanonické typy projektů

| Typ | Doporučený tok |
|---|---|
| `portfolio-program` | portfolio → domény → investice → ownership → roadmap |
| `greenfield-product` | product vision → user needs → EventStorming → BC → první slice |
| `legacy-modernization` | pain → as-is evidence → hidden rules → seams/ACL → migrační slice |
| `legacy-transformation` | business model + operating model + core IT + transition states |
| `integration-landscape` | scénáře → context map → source of truth → kontrakty → failure modes |
| `purchased-product-adoption` | responsibility → vendor model → fit-gap → ACL → exit plan |
| `domain-discovery` | intake → evidence → glossary → events → hotspots → kandidátní BC |
| `architecture-review` | scope → evidence → QA → boundaries → findings → ADR backlog |
| `operating-model-and-teams` | flow → ownership → cognitive load → Team Topologies |
| `bounded-context-design` | purpose → language → lifecycle → aggregates → ports |

Programová rozšíření nad starter metodikou přidává PR #9. Enterprise ingestion přidává PR #10. EventStorming session runtime a multi-agent orchestrace přidává PR #11.

## 8. Starter metodika a tailoring

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

## 9. Current status a konverzační menu

Read-only dotaz:

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot
```

Strojově čitelný read-only výstup:

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot -Json
```

Po ruční změně evidence lze status explicitně přepočítat:

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot -Refresh
```

`-Refresh` je write operace. Aktualizuje current status, next actions a project status report. Změny zkontroluj a commitni před navazující Miro operací.

Doporučený chat:

> Načti current status a next actions. Vysvětli, proč je další gate právě tato. Ukaž chybějící evidence, nejistoty a maximálně tři další kroky. Neprováděj zápis bez potvrzení.

## 10. Gate engine

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
.\scripts\Complete-DDDALifecycleStep.ps1 -ProjectPath $ProjectRoot -Gate G1 -Outcome passed -Reviewer 'Business owner' -Note 'Scope a decision owner potvrzeny'
```

Conditional:

```powershell
.\scripts\Complete-DDDALifecycleStep.ps1 -ProjectPath $ProjectRoot -Gate G5 -Outcome conditional -Reviewer 'Architecture owner' -Condition 'Potvrdit source of truth pro party identity'
```

Lokální commit pouze explicitně:

```powershell
.\scripts\Complete-DDDALifecycleStep.ps1 -ProjectPath $ProjectRoot -Gate G1 -Outcome passed -Reviewer 'Business owner' -Commit
```

Push ani merge se neprovádí.

## 11. Knowledge pack a práce s kontextem

Začni `knowledge/00-knowledge-index.md`. Načítej pouze relevantní playbook.

Před složitější projektovou úlohou načti:

```text
project.yaml
project-intake.yaml
lifecycle-tailoring.yaml
artifacts/status/current-status.yaml
knowledge/00-knowledge-index.md
```

Facts musí zachovat source path. Hypotézy zůstávají candidate. Rozhodnutí mají ownera a Git review boundary.

Mode policy:

- Ask/Plan — porozumění, review, varianty a decision framing;
- Agent — potvrzené souborové změny a execution skripty;
- Debug — reprodukce a izolace technické chyby;
- explicitní reasoning — gates, BC boundaries, ADR a investiční rozhodnutí;
- Auto — jen nízkorizikový drafting, ne finální rozhodnutí.

## 12. Projektový ingestion řízený chatem

Současný projektový tok:

1. vlož zdroje do `ingestion/`;
2. vytvoř `ingestion/catalog.yaml` s provenance, ownerem, důvěryhodností a citlivostí;
3. nech chat oddělit fakta, tvrzení, hypotézy a otázky;
4. zapiš rozpory jako hotspoty.

Automatizované enterprise extraktory, archive recursion, OCR a input-fit assessment jsou plánované v PR #10.

## 13. Miro app a runtime

Miro runtime očekává scopes `boards:read` a `boards:write`. Pro běžnou práci používej secret store vytvořený first-runem; token nevkládej do příkazové historie.

Offline doctor:

```powershell
.\scripts\Test-DDDAMiroConfiguration.ps1 -ProjectPath $ProjectRoot
```

Online doctor:

```powershell
.\scripts\Test-DDDAMiroConfiguration.ps1 -ProjectPath $ProjectRoot -Online
```

## 14. Inicializace projektového boardu a managed artefaktů

Dry-run:

```powershell
.\scripts\Initialize-DDDAMiroBoard.ps1 -ProjectPath $ProjectRoot -DryRun
```

Vytvoření boardu:

```powershell
.\scripts\Initialize-DDDAProjectMiro.ps1 -WorkspaceRoot $WorkspaceRoot -ProjectId 'claims-modernization' -CreateBoard
```

Inicializátor:

1. provede scaffold dry-run;
2. vykreslí board;
3. provede online doctor;
4. provede managed artifact push dry-run;
5. odešle managed YAML artefakty;
6. zapíše `miro/miro-map.yaml`, `miro/sync-state.yaml` a sync report;
7. provede kontrolní render;
8. ověří idempotentní push bez dalších create/update operací.

Status a next-actions jsou standardní managed artifacts.

## 15. Obousměrná synchronizace

Pull dry-run:

```powershell
.\scripts\Invoke-DDDAMiroSync.ps1 -ProjectPath $ProjectRoot -Direction Pull -DryRun
```

Push dry-run:

```powershell
.\scripts\Invoke-DDDAMiroSync.ps1 -ProjectPath $ProjectRoot -Direction Push -DryRun
```

Oba směry:

```powershell
.\scripts\Invoke-DDDAMiroSync.ps1 -ProjectPath $ProjectRoot -Direction Both
```

Synchronizují se pouze položky s markerem `DDDA:<project>:<artifact>`. Unmanaged workshopový obsah se zachová.

## 16. Polling worker

```powershell
.\scripts\Start-DDDAMiroSyncWorker.ps1 -ProjectPath $ProjectRoot -IntervalSeconds 60
```

Technický test dvou cyklů:

```powershell
.\scripts\Start-DDDAMiroSyncWorker.ps1 -ProjectPath $ProjectRoot -IntervalSeconds 30 -MaxCycles 2
```

Worker zapisuje report, při konfliktu končí exit code 2 a nikdy neprovádí commit, push nebo merge.

## 17. Konflikty a mazání

Při souběžné změně stejné sémantiky vznikne explicitní conflict record v `miro/conflicts/`. Nic se nepřepisuje last-write-wins.

Obnova chybějící mapped položky:

```powershell
.\scripts\Invoke-DDDAMiroSync.ps1 -ProjectPath $ProjectRoot -Direction Push -RecreateMissing -DryRun
```

Mazání je tombstone-first přes `artifact.status: deleted_pending`. Skutečné odstranění vyžaduje `-ConfirmDelete`.

## 18. Git workflow projektového repozitáře

Před commitem:

```powershell
.\scripts\Test-DDDARepositoryScope.ps1 -PlatformPath $PlatformRoot -ProjectPath $ProjectRoot -Scope project -RequireChanges
git -C $ProjectRoot diff
git -C $ProjectRoot diff --check
```

Doporučený chat:

> Připrav projektový commit. Odděl generované reporty od sémantických změn, ukaž diff, navrhni commit message a ověř čistý platformní repozitář. Nepushuj bez potvrzení.

## 19. Acceptance testy project steeringu

Offline:

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering
```

Online proti Miro:

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering -WithMiro -Full -CleanupOnFailure
```

Vizuální review boardu:

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering -WithMiro -Full -KeepReviewBoard
```

Po PASS se standardně odstraní dočasný workspace i board; report zůstane v lokálním DDDA state adresáři.

## 20. Upgrade projektu

```powershell
.\scripts\Update-DDDAProject.ps1 -PlatformPath $PlatformRoot -ProjectPath $ProjectRoot -TargetRef main
```

Upgrade je samostatná projektová změna a nemá automaticky měnit přijatá doménová rozhodnutí.

## 21. Diagnostika

```powershell
.\scripts\Test-DDDAInstallation.ps1 -PlatformPath $PlatformRoot -WorkspaceRoot $WorkspaceRoot -ProjectPath $ProjectRoot
git -C $PlatformRoot status
git -C $ProjectRoot status
Get-Content (Join-Path $ProjectRoot 'artifacts\status\current-status.yaml')
Get-Content (Join-Path $ProjectRoot 'miro\miro-map.yaml')
Get-Content (Join-Path $ProjectRoot 'miro\sync-state.yaml')
```

Při platformním validation FAIL nejdřív otevři `result.md`, potom pouze log selhané suite. Diagnostický workspace nemaž před přečtením reportu.

## 22. Bezpečnostní pravidla

- tokeny a client secrets pouze v environment variables nebo secret store;
- token se nesmí objevit v intake, reportu, package, Gitu nebo shell history;
- žádný automatický push nebo merge mimo explicitní `promote-pr -ConfirmMerge`;
- žádný last-write-wins pro sémantické konflikty;
- žádné automatické gate approval;
- klientská data nikdy do platformního repozitáře, examples nebo package;
- workspace, package a ingestion cesty musí zůstat pod povoleným rootem;
- před citlivým exportem ověř `classification.data_sensitivity`;
- Miro acceptance test nepoužívá produkční projektový board;
- release tag vzniká až po úspěšné release validation.

## 23. Kde hledat detail

- platform lifecycle: `docs/developer-guide/platform-development-lifecycle.md`;
- testovací strategie: `docs/developer-guide/testing-strategy.md`;
- validate a promote PR: `docs/user-guide/validate-and-promote-pr.md`;
- capability katalog: `docs/capabilities/README.md`;
- schemas a kontrakty: `docs/reference/contracts.md`;
- CLI reference: `docs/reference/cli.md`;
- řízený project bootstrap: `docs/cookbooks/16-zalozeni-rizeneho-projektu.md`;
- status a gate review: `docs/cookbooks/17-status-gates-a-dalsi-krok.md`;
- Miro troubleshooting: `docs/cookbooks/12-miro-troubleshooting.md`;
- knowledge index: `knowledge/00-knowledge-index.md`;
- changelog: `CHANGELOG.md`;
- ADR: `docs/adr/`;
- migration notes: `docs/migration/`.
