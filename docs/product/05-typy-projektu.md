# Typy projektu v manifestu

Kanonické typy jsou validovány `project.schema.json`. Alias zachovává původní nebo organizační pojmenování, ale runtime a metodika pracují s kanonickým typem.

Přehled workflow a use cases je v [metodickém katalogu](../methodology/02-typy-projektu-toky-use-cases.md).

## Manifest

```yaml
project:
  id: life-insurance-greenfield
  name: Greenfield životní pojišťovna
  type: portfolio-program
  type_alias: greenfield-portfolio
  schema_version: 1
```

## Miro konfigurace

```yaml
miro:
  board_id: null
  board_id_env: LIFE_INSURANCE_GREENFIELD_MIRO_BOARD_ID
  access_token_env: MIRO_ACCESS_TOKEN
  scaffold: scaffolds/miro/strategic-ddd-method-board.yaml
  synchronization: bidirectional
```
