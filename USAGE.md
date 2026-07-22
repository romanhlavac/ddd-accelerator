# DDDA — chat-first provozní návod

Tento dokument je hlavní provozní příručka. Popisuje instalaci, role jednotlivých repozitářů, práci přes chat, projektové typy, Miro renderer, obousměrnou synchronizaci, Git/PR workflow a upgrade.

## 1. Pracovní model

DDDA má dvě oddělené změnové oblasti:

1. **platforma** — metodika, schémata, runtime, scaffoldy a obecná dokumentace,
2. **projekt** — vstupy, doménové modely, ADR, Miro mapping, reporty a rozhodnutí konkrétní iniciativy.

Každá chatová relace má začít uvedením scope:

```text
Scope: project
Aktivní projekt: life-insurance-greenfield
Povoleno: project.yaml, ingestion/, artifacts/, decisions/, workshops/, miro/, reports/
Zakázáno: platformní repozitář
```

nebo:

```text
Scope: platform
Povoleno: docs/, schemas/, scripts/, runtime/, templates/, scaffolds/
Zakázáno: klientská a projektová data
```

## 2. Instalace z parent adresáře

Přesuň se do parent adresáře, ve kterém má vzniknout `DDDA-Workspace`. `.` v následujících příkazech označuje právě tento adresář.

```powershell
New-Item -ItemType Directory -Force .\DDDA-Workspace\platform | Out-Null

git clone `
  https://github.com/romanhlavac/ddd-accelerator.git `
  .\DDDA-Workspace\platform\ddd-accelerator

$WorkspaceRoot = (Resolve-Path .\DDDA-Workspace).Path
$PlatformRoot = (Resolve-Path .\DDDA-Workspace\platform\ddd-accelerator).Path

& (Join-Path $PlatformRoot 'scripts\Test-DDDAInstallation.ps1') -PlatformPath $PlatformRoot
& (Join-Path $PlatformRoot 'scripts\Initialize-DDDAWorkspace.ps1') -WorkspaceRoot $WorkspaceRoot
```

Výsledek:

```text
DDDA-Workspace/
├── platform/ddd-accelerator/.git
├── projects/
├── workspace.yaml
└── DDDA.code-workspace
```

## 3. Založení projektu přes chat

Doporučený prompt:

> Pomoz mi založit DDDA projekt. Nejprve se ptej na business problém, očekávané rozhodnutí, scope, out-of-scope, aktéry, regulaci, dominantní quality attributes, existující systémy a týmy. Potom doporuč nejmenší vhodný kanonický typ projektu a vypiš přesný `New-DDDAProject.ps1` příkaz. Nic nevytvářej, dokud nepotvrdím project ID, název a typ.

Příklad:

```powershell
& (Join-Path $PlatformRoot 'scripts\New-DDDAProject.ps1') `
  -WorkspaceRoot $WorkspaceRoot `
  -ProjectId life-insurance-greenfield `
  -Name 'Nová životní pojišťovna' `
  -Type portfolio-program `
  -TypeAlias greenfield-portfolio
```

Skript vytvoří samostatný Git repozitář, manifest, lock, Miro mapping, sync state, adresář konfliktů a auditních reportů.

## 4. Typy projektů, use cases a tok

### 4.1 `portfolio-program`

Použití: nová společnost, transformační program, více produktů/domén/týmů.

```text
Strategický záměr → capability landscape → portfolio subdomén → kandidátní BC
→ context map → team topology → guardrails → inkrementy → delivery streams
```

Use cases: greenfield pojišťovna nebo banka; transformace core systému napříč value streams; build/buy/partner/retire portfolio.

Prompt:

> Proveď portfolio intake. Odděl business capabilities, domény, subdomény, systémy a organizační útvary. Nevytvářej bounded contexts z org chartu. Navrhni gaty a pořadí workshopů.

### 4.2 `greenfield-product`

```text
Product vision → potřeby uživatelů → Big Picture ES → subdomény a BC
→ quality attributes → první end-to-end slice → Design-Level ES → tactical design
```

Use cases: nový underwriting portal, digitální claim intake, nový marketplace.

Prompt:

> Najdi nejmenší hodnotný end-to-end slice. Nezačínej mikroservisami. Ukaž business události, rozhodnutí, invarianty a externí závislosti.

### 4.3 `legacy-modernization`

```text
Business pain → as-is evidence → skrytá pravidla → target boundaries
→ seams/ACL → migrační slice → reconciliation → decommission
```

Use cases: rozdělení monolitu, náhrada COTS, odstranění vendor lock-in.

Prompt:

> Odděl business realitu od současné implementace. Zmapuj system-of-record, runtime coupling, change coupling, rollback a decommission kritéria.

### 4.4 `legacy-transformation`

```text
As-is business + target capabilities + transition states
→ dočasné BC → změna ownershipu → migrační vlny → nový operating model
```

Použití: současně se mění produkty, procesy, operating model i core IT.

### 4.5 `integration-landscape`

```text
Business scénáře → context map → source of truth → kontrakty
→ konzistence/latence → failure modes → ACL → observabilita
```

Použití: nejasné vlastnictví dat, point-to-point integrace, konfliktní API/eventy.

### 4.6 `purchased-product-adoption`

```text
Business odpovědnost → vendor model → fit-gap → data ownership
→ konfigurační hranice → ACL → exit/continuity plan
```

Taktické DDD uvnitř vendor produktu se bez přístupu a důvodu nemodeluje.

### 4.7 `domain-discovery`

```text
Intake → ingestion → glossary → commands/events/actors → hotspots
→ lifecycles → subdomény → kandidátní BC → validační backlog
```

Použití: časově omezené poznání domény, typicky do G3.

### 4.8 `architecture-review`

```text
Review scope → evidence → business/domain alignment → quality attributes
→ boundaries/data ownership → integration/security/operations → findings → ADR backlog
```

Prompt:

> Každý finding strukturovat jako evidence → symptom → root cause → dopad → riziko → doporučení → ověřovací krok.

### 4.9 `operating-model-and-teams`

```text
Doménové hypotézy → tok změn → ownership → cognitive load
→ stream-aligned/platform/enabling/complicated-subsystem → interaction modes
```

Použití: ownership, cognitive load, fronty mezi týmy, Team Topologies.

### 4.10 `bounded-context-design`

```text
Purpose/UL/contracts → Design-Level ES → lifecycle → aggregates/invariants
→ domain events → application ports → persistence/integration → code views
```

Použití: detail jednoho již vymezeného bounded contextu.

## 5. Ingestion řízený chatem

1. Vlož zdroje do `ingestion/`.
2. Vytvoř `ingestion/catalog.yaml` s původem, datem, ownerem, důvěryhodností a citlivostí.
3. Nech chat rozdělit fakta, tvrzení, hypotézy a otevřené otázky.
4. Nech vygenerovat glossary a seznam workshopových hotspotů.

Prompt:

> Analyzuj pouze soubory v `ingestion/`. Zachovej terminologii zdrojů. U každého závěru uveď source path. Nevysvětlené rozpory zapiš jako hotspot, ne jako sjednocený fakt.

## 6. Miro app a runtime

Miro REST API používá OAuth bearer token. Runtime očekává scopes `boards:read` a `boards:write`.

```powershell
$env:MIRO_ACCESS_TOKEN = '<token>'
$env:LIFE_INSURANCE_GREENFIELD_MIRO_BOARD_ID = '<board-id>'

& (Join-Path $PlatformRoot 'scripts\Install-DDDAMiroRuntime.ps1')
$ProjectRoot = Join-Path $WorkspaceRoot 'projects\life-insurance-greenfield'

& (Join-Path $PlatformRoot 'scripts\Test-DDDAMiroConfiguration.ps1') `
  -ProjectPath $ProjectRoot
```

Online kontrola:

```powershell
& (Join-Path $PlatformRoot 'scripts\Test-DDDAMiroConfiguration.ps1') `
  -ProjectPath $ProjectRoot `
  -Online
```

## 7. Render Miro boardu

Vždy začni dry-runem:

```powershell
& (Join-Path $PlatformRoot 'scripts\Initialize-DDDAMiroBoard.ps1') `
  -ProjectPath $ProjectRoot `
  -DryRun
```

Pokud board ID není nastavené, lze vytvořit privátní board:

```powershell
& (Join-Path $PlatformRoot 'scripts\Initialize-DDDAMiroBoard.ps1') `
  -ProjectPath $ProjectRoot `
  -CreateBoard
```

Renderer vytváří nebo aktualizuje frames podle scaffoldu a zapisuje stabilní vazby do `miro/miro-map.yaml`.

Prompt:

> Proveď dry-run renderu Miro boardu. Shrň počet framů, create/update operace a chybějící konfiguraci. Po mém potvrzení spusť skutečný render. Nezapisuj token ani board ID do Gitu.

## 8. Obousměrná synchronizace

### Pull

```powershell
& (Join-Path $PlatformRoot 'scripts\Invoke-DDDAMiroSync.ps1') `
  -ProjectPath $ProjectRoot `
  -Direction Pull `
  -DryRun
```

### Push

```powershell
& (Join-Path $PlatformRoot 'scripts\Invoke-DDDAMiroSync.ps1') `
  -ProjectPath $ProjectRoot `
  -Direction Push `
  -DryRun
```

### Both

```powershell
& (Join-Path $PlatformRoot 'scripts\Invoke-DDDAMiroSync.ps1') `
  -ProjectPath $ProjectRoot `
  -Direction Both
```

Runtime synchronizuje pouze spravované artefakty s markerem `DDDA:<project>:<artifact>`. Nespravované workshopové poznámky zachová.

## 9. Průběžný synchronizační worker

Worker je řízené polling spuštění stejného synchronizačního algoritmu; nejde o nekontrolovaný background merge. Minimální interval je 30 sekund. Každý cyklus:

1. načte aktuální YAML, mapping, common-base state a Miro items,
2. provede režim `Both`,
3. zapíše auditní report,
4. při konfliktu se ukončí s exit code `2`,
5. neprovádí Git commit, push ani merge.

```powershell
& (Join-Path $PlatformRoot 'scripts\Start-DDDAMiroSyncWorker.ps1') `
  -ProjectPath $ProjectRoot `
  -IntervalSeconds 60
```

Pro technický test dvou cyklů:

```powershell
& (Join-Path $PlatformRoot 'scripts\Start-DDDAMiroSyncWorker.ps1') `
  -ProjectPath $ProjectRoot `
  -IntervalSeconds 30 `
  -MaxCycles 2
```

Worker používá bearer token dostupný při startu. Automatický OAuth refresh není součástí lokálního runtime; token rotation/refresh musí zajistit secret manager nebo hostující služba. Po změně tokenu lokální worker restartuj.

### Obnova chybějící spravované položky

Pokud mapping odkazuje na Miro item, který byl ručně odstraněn, runtime záměrně vytvoří konflikt `mapped_remote_item_missing`. Po ověření, že položka má být obnovena, použij explicitní přepínač:

```powershell
& (Join-Path $PlatformRoot 'scripts\Invoke-DDDAMiroSync.ps1') `
  -ProjectPath $ProjectRoot `
  -Direction Push `
  -RecreateMissing `
  -DryRun
```

Po kontrole odstraň `-DryRun`. Tím se zabrání tichému znovuvytváření položek, které někdo záměrně odstranil.

## 10. Konflikty

Konflikt vzniká, pokud se od poslední společné base změnila stejná sémantika v YAML i Miru. Runtime vytvoří `miro/conflicts/<timestamp>-<artifact>.yaml` a vrátí exit code 2.

Prompt:

> Otevři všechny pending conflict records. Pro každý ukaž base, YAML a Miro variantu, business dopad a doporučené řešení. Nic nepřepisuj automaticky. Po rozhodnutí aktualizuj YAML, proveď dry-run push a připrav projektový commit.

## 11. Mazání

Mazání je tombstone-first:

```yaml
artifact:
  status: deleted_pending
```

První sync pouze oznámí pending delete. Skutečné odstranění z Mira vyžaduje:

```powershell
& (Join-Path $PlatformRoot 'scripts\Invoke-DDDAMiroSync.ps1') `
  -ProjectPath $ProjectRoot `
  -Direction Push `
  -ConfirmDelete
```

## 12. Gate review přes chat

Prompt:

> Proveď review gate G3. Načti povinnou evidence z metodiky. U každého kritéria uveď konkrétní artefakt a source path. Výsledek klasifikuj pass / conditional / fail. Neoznač gate jako completed bez explicitního potvrzení business a architecture ownera.

## 13. Git a PR

Před projektovým commitem:

```powershell
& (Join-Path $PlatformRoot 'scripts\Test-DDDARepositoryScope.ps1') `
  -PlatformPath $PlatformRoot `
  -ProjectPath $ProjectRoot `
  -Scope project `
  -RequireChanges
```

Prompt:

> Připrav projektový commit. Nejprve ukaž `git diff`, odděl generované reporty od sémantických změn, navrhni commit message a zkontroluj, že platformní repo je čisté. Nepushuj bez potvrzení.

## 14. Upgrade

Projekt se neupgraduje automaticky. Upgrade má vlastní projektový PR:

```powershell
& (Join-Path $PlatformRoot 'scripts\Update-DDDAProject.ps1') `
  -PlatformPath $PlatformRoot `
  -ProjectPath $ProjectRoot `
  -TargetRef main
```

## 15. Diagnostika

```powershell
& (Join-Path $PlatformRoot 'scripts\Test-DDDAInstallation.ps1') `
  -PlatformPath $PlatformRoot `
  -WorkspaceRoot $WorkspaceRoot `
  -ProjectPath $ProjectRoot

git -C $PlatformRoot status
git -C $ProjectRoot status
Get-Content (Join-Path $ProjectRoot 'miro\miro-map.yaml')
Get-Content (Join-Path $ProjectRoot 'miro\sync-state.yaml')
```

## 16. Bezpečnostní pravidla

- tokeny a client secrets pouze v environment variables nebo secret store,
- board ID lze držet v environment variable,
- žádný automatický push/merge,
- žádný last-write-wins pro sémantické konflikty,
- klientská data nikdy do platformního repozitáře,
- před citlivým exportem ověř `classification.data_sensitivity`.
