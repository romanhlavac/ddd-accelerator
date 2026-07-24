# 14 Inicializace cílového Miro boardu

## Účel a rozhodnutí

Tato aktivita vytvoří nebo idempotentně aktualizuje Miro board konkrétního DDDA projektu. Workspace pouze vyhledá projekt; board, mapping a změnová historie patří projektovému repozitáři.

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
7. provede povinný dry-run;
8. vytvoří nebo aktualizuje board;
9. provede online doctor;
10. provede druhý kontrolní render;
11. ověří stejné board ID a stejnou množinu mapped item ID;
12. vypíše projektový Git diff k review.

`-CreateBoard` je bezpečné použít opakovaně. Pokud už `miro-map.yaml` obsahuje `board_id`, renderer použije stávající board a nevytvoří další.

## Pouze dry-run

```powershell
.\scripts\Initialize-DDDAProjectMiro.ps1 `
  -WorkspaceRoot 'C:\path\to\DDDA-Workspace' `
  -ProjectId 'life-insurance-greenfield' `
  -CreateBoard `
  -DryRun
```

Dry-run nevolá write endpointy a nesmí změnit projektový repozitář.

## Aktualizace existujícího boardu

Po změně scaffoldu nebo upgradu platformy:

```powershell
.\scripts\Initialize-DDDAProjectMiro.ps1 `
  -WorkspaceRoot 'C:\path\to\DDDA-Workspace' `
  -ProjectId 'life-insurance-greenfield'
```

Bez `-CreateBoard` musí být board ID dostupné z `project.yaml`, environment variable nebo `miro/miro-map.yaml`.

## Vlastnictví dat

| Prvek | Vlastník |
|---|---|
| Miro board | konkrétní DDDA projekt |
| `miro/miro-map.yaml` | projektový Git repozitář |
| access token | lokální secret store nebo runtime prostředí |
| scaffold | platformní repozitář |
| význam artefaktů | projektové YAML |
| workshopová poloha a seskupení | Miro |

`board_id` není secret a může být verzováno v projektovém mappingu. Access token secret je a do Gitu nepatří.

## Git review a commit

Po úspěšném vytvoření boardu zkontroluj:

```powershell
git -C 'C:\path\to\project' diff -- miro/miro-map.yaml
```

Potom v projektovém repozitáři:

```powershell
git add miro/miro-map.yaml
git commit -m 'chore: initialize project Miro board'
```

Platformní repozitář musí zůstat čistý.

## Kontroly

Definition of Done:

- online doctor vrátí cílový board;
- první a kontrolní render používají stejné `board_id`;
- množina `miro_item_id` se při kontrolním renderu nezmění;
- druhý render neobsahuje `create_board`;
- změny projektu jsou omezené na `miro/`;
- platformní `git status --short` je prázdný;
- projektový diff byl zkontrolován před commitem.

## Anti-patterny

- jeden bidirekcionálně synchronizovaný board pro více nezávislých projektových repozitářů;
- ruční kopírování board ID mezi projekty;
- vytvoření nového boardu při každém spuštění;
- commit tokenu společně s mappingem;
- render do špinavého projektu, kde nelze oddělit předchozí změny;
- automatický commit nebo push bez review mappingu.

## Navazující krok

Po inicializaci spusť první projektový workshop a používej dry-run synchronizace podle kuchařky [07 Miro ↔ YAML ↔ Git](07-synchronizace-miro-yaml-git.md).
