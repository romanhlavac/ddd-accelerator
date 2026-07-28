# 14 Inicializace cílového Miro boardu

## Účel a rozhodnutí

Tato aktivita vytvoří nebo idempotentně aktualizuje Miro board konkrétního DDDA projektu a následně na něj odešle aktuální managed YAML artefakty. Workspace pouze vyhledá projekt; board, mapping, sync state a změnová historie patří projektovému repozitáři.

Doporučená topologie:

```text
DDDA-Workspace/
├── platform/ddd-accelerator/
└── projects/
    ├── project-a/ ── Miro board A
    └── project-b/ ── Miro board B
```

Společný workspace board není náhradou projektových boardů. Pokud vznikne, má být samostatnou portfolio projekcí bez sdíleného `miro-map.yaml` s projektovými artefakty.

## Entry criteria

- inicializace po clone prošla;
- `workspace.yaml` registruje cílový projekt;
- projekt je samostatný čistý Git repozitář;
- platformní repozitář je čistý;
- projekt má `project.yaml`, `miro/miro-map.yaml` a scaffold konfiguraci;
- managed artefakty určené k publikaci jsou uloženy pod nakonfigurovaným `artifacts.root`;
- Miro token má scopes `boards:read` a `boards:write`.

## Vytvoření nového boardu

```powershell
.\scripts\Initialize-DDDAProjectMiro.ps1 `
  -WorkspaceRoot 'C:\path\to\DDDA-Workspace' `
  -ProjectId 'life-insurance-greenfield' `
  -CreateBoard
```

Skript:

1. načte projekt z `workspace.yaml`;
2. ověří samostatný Git root projektu;
3. ověří čistotu platformy a projektu;
4. načte token ze secret store nebo environment variable;
5. ověří token context;
6. nainstaluje Miro runtime;
7. provede povinný scaffold dry-run;
8. vytvoří nebo aktualizuje board a scaffold frames;
9. provede online doctor;
10. provede managed artifact push dry-run;
11. odešle managed YAML artefakty na board;
12. zapíše stabilní vazby do `miro/miro-map.yaml` a common-base hashe do `miro/sync-state.yaml`;
13. provede druhý kontrolní render;
14. provede idempotentní kontrolní artifact push dry-run;
15. ověří stejné board ID, stejnou množinu mapped item ID a nulový počet dalších create/update operací;
16. vypíše projektový Git diff k review.

`-CreateBoard` je bezpečné použít opakovaně. Pokud už `miro-map.yaml` obsahuje `board_id`, renderer použije stávající board a nevytvoří další.

## Pouze dry-run

```powershell
.\scripts\Initialize-DDDAProjectMiro.ps1 `
  -WorkspaceRoot 'C:\path\to\DDDA-Workspace' `
  -ProjectId 'life-insurance-greenfield' `
  -CreateBoard `
  -DryRun
```

Při vytváření nového boardu dry-run ověří scaffold bez volání write endpointů a bez změny projektového repozitáře. Managed artifact push vyžaduje existující board a provede se až při běhu bez `-DryRun`.

## Aktualizace existujícího boardu

Po změně scaffoldu, managed artefaktů nebo upgradu platformy:

```powershell
.\scripts\Initialize-DDDAProjectMiro.ps1 `
  -WorkspaceRoot 'C:\path\to\DDDA-Workspace' `
  -ProjectId 'life-insurance-greenfield'
```

Bez `-CreateBoard` musí být board ID dostupné z `project.yaml`, environment variable nebo `miro/miro-map.yaml`.

Po přerušeném Miro bootstrapu lze pokračovat pouze s řízenými změnami v `miro/` a `reports/miro-sync/`:

```powershell
.\scripts\Initialize-DDDAProjectMiro.ps1 `
  -WorkspaceRoot 'C:\path\to\DDDA-Workspace' `
  -ProjectId 'life-insurance-greenfield' `
  -Resume
```

## Vlastnictví dat

| Prvek | Vlastník |
|---|---|
| Miro board | konkrétní DDDA projekt |
| `miro/miro-map.yaml` | projektový Git repozitář |
| `miro/sync-state.yaml` | projektový Git repozitář |
| `reports/miro-sync/` | projektový Git repozitář |
| access token | lokální secret store nebo runtime prostředí |
| scaffold | platformní repozitář |
| význam artefaktů | projektové YAML |
| workshopová poloha a seskupení | Miro |

`board_id` není secret a může být verzováno v projektovém mappingu. Access token secret je a do Gitu nepatří.

## Git review a commit

Po úspěšném vytvoření boardu zkontroluj:

```powershell
git -C 'C:\path\to\project' diff -- miro/ reports/miro-sync/
```

Potom v projektovém repozitáři:

```powershell
git add miro/miro-map.yaml miro/sync-state.yaml reports/miro-sync/
git commit -m 'chore: initialize project Miro board and managed artifacts'
```

Platformní repozitář musí zůstat čistý.

## Kontroly

Definition of Done:

- online doctor vrátí cílový board;
- první a kontrolní render používají stejné `board_id`;
- všechny aktuální managed YAML artefakty mají stabilní Miro mapping;
- `miro/sync-state.yaml` obsahuje common-base hashe synchronizovaných artefaktů;
- množina `miro_item_id` se při kontrolním renderu nezmění;
- druhý render neobsahuje `create_board`;
- kontrolní artifact push dry-run neplánuje další create/update operace;
- změny projektu jsou omezené na `miro/` a `reports/miro-sync/`;
- platformní `git status --short` je prázdný;
- projektový diff byl zkontrolován před commitem.

## Anti-patterny

- jeden bidirekcionálně synchronizovaný board pro více nezávislých projektových repozitářů;
- ruční kopírování board ID mezi projekty;
- vytvoření nového boardu při každém spuštění;
- commit tokenu společně s mappingem;
- render do špinavého projektu, kde nelze oddělit předchozí změny;
- samostatný scaffold render bez počátečního managed artifact push, pokud má board reprezentovat aktuální stav projektu;
- automatický commit nebo push bez review mappingu.

## Navazující krok

Po inicializaci spusť první projektový workshop a používej dry-run synchronizace podle kuchařky [07 Miro ↔ YAML ↔ Git](07-synchronizace-miro-yaml-git.md).

## Human visual acceptance boundary

Úspěšný online initializer hlásí pouze:

```text
DDDA projektový Miro technical validation: PASS
Layout contract: PASS
UTF-8: PASS
Human visual acceptance: PENDING
Overall: PENDING_HUMAN_REVIEW
```

To není release approval. Pro zachování boardu k jednorázovému finálnímu review použij acceptance runner:

```powershell
.\scripts\Test-DDDAAcceptance.ps1 `
  -Suite project-steering `
  -WithMiro `
  -Full `
  -KeepReviewBoard `
  -MiroTeamId <STANDARD_TEAM_ID>
```

Runner vypíše:

- board ID;
- board URL;
- review workspace;
- acceptance report.

Finální lidský reviewer ověřuje `00 – Navigace, legenda a stav artefaktů`, `01 – DDD Starter journey, gates a iterace`, aktuální gate, čitelnost fontů, status legendu, mini-vzory, metodické odkazy, nepřekrývání, UTF-8 a zachování ruční workshopové práce. Human review se neopakuje po každé automatické opravě; proběhne jednou po zmrazení všech relevantních online změn.

Traceability je popsána v [Miro DDD Starter traceability](../reference/miro-ddd-starter-traceability.md).
