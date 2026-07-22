# Workspace a více projektů

## 1. Cíl

Jedna rozbalená instalace DDDA musí obsloužit více nezávislých iniciativ bez kopírování metodiky a nástrojů. Sdílí se produktové šablony, schémata a nástroje; nesdílí se projektová fakta, synchronizační stav ani rozhodnutí.

## 2. Doporučená struktura

```text
projects/
└── <project-slug>/
    ├── project.yaml
    ├── inputs/
    ├── artifacts/
    │   ├── align/
    │   ├── discover/
    │   ├── decompose/
    │   ├── strategize/
    │   ├── connect/
    │   ├── organize/
    │   ├── define/
    │   └── code/
    ├── diagrams/
    │   └── generated/
    ├── decisions/
    ├── workshops/
    ├── sync/
    │   ├── miro-map.yaml
    │   ├── sync-state.yaml
    │   └── conflicts/
    └── README.md
```

## 3. Project manifest

`project.yaml` je vstupním bodem projektu.

```yaml
schema_version: 1.0.0
project_id: life-insurance-greenfield
name: Greenfield životní pojišťovna
project_type: greenfield-portfolio
language: cs
status: active
miro:
  board_id_env: DDDA_LIFE_MIRO_BOARD_ID
  board_url: null
workflow:
  profile: greenfield-portfolio
  current_stage: discover
  completed_gates: [G1]
repositories:
  primary: .
classification:
  data_sensitivity: confidential
owners:
  business_sponsor: CEO
  architecture_owner: Chief Architect
```

Board ID se doporučuje načítat z prostředí; veřejný manifest nemá obsahovat token.

## 4. Identita a namespace

`project_id`:

- je stabilní a nemění se při přejmenování projektu,
- používá formát lowercase kebab-case,
- tvoří namespace všech `artifact_id`,
- nesmí být opakovaně použit pro jinou iniciativu.

`artifact_id` musí být unikátní alespoň v rámci projektu. Pro externí odkazy se používá plný tvar:

```text
ddda:<project_id>:<artifact_type>:<artifact_id>
```

## 5. Izolace

Zakázané implicitní vazby:

- jeden `sync-state.yaml` pro více projektů,
- jeden Miro frame spravovaný dvěma projekty,
- přímý relativní odkaz do `artifacts/` jiného projektu,
- sdílený artefakt bez explicitního ownera.

Sdílení se realizuje přes publikovaný kontrakt nebo referenci:

```yaml
external_reference:
  project_id: customer-identity-platform
  artifact_id: bc-customer-identity
  contract_version: 2.1.0
```

## 6. Životní cyklus projektu

| Stav | Význam |
|---|---|
| proposed | manifest existuje, scope není schválen |
| active | probíhá práce |
| paused | práce je dočasně zastavena |
| completed | cílové gates byly dosaženy |
| archived | artefakty jsou pouze pro čtení |

Archivace nezruší historii ani odkazy. Miro board může být uzamčen, ale YAML a Git historie zůstávají autoritativní.

## 7. Branching a review

Doporučení:

- menší změny: feature branch a pull request,
- workshopový import: samostatný commit se zdrojovým Miro revision,
- konflikty: samostatný commit s odkazem na conflict record,
- gate approval: tag nebo podepsaný ADR/checkpoint commit.

## 8. Bootstrap nového projektu

Bootstrap musí:

1. validovat unikátnost `project_id`,
2. vytvořit adresářovou strukturu,
3. zapsat manifest,
4. zvolit workflow profile,
5. připravit Miro mapping bez tokenu,
6. vytvořit počáteční README a backlog otázek,
7. spustit strukturální validaci.

Podrobný postup je v kuchařce `docs/cookbooks/01-zalozeni-projektu.md`.
