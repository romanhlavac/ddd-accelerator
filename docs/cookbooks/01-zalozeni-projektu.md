# Kuchařka 01 — Založení projektu

## Výsledek

Vznikne izolovaný projekt s manifestem, adresářovou strukturou, workflow profilem, prázdným Miro mappingem a počátečním backlogem otázek.

## Předpoklady

- existuje klon repozitáře,
- je znám pracovní název, sponsor a dominantní typ projektu,
- `project_id` ještě není použit,
- žádný Miro token se nebude ukládat do Gitu.

## Postup

1. Zvolte stabilní `project_id`, například `life-insurance-greenfield`.
2. Vyberte typ podle `docs/product/05-typy-projektu.md`.
3. Vytvořte adresář `projects/<project_id>/` a podadresáře dle produktové dokumentace.
4. Vytvořte `project.yaml`.
5. Do `README.md` zapište business problém, očekávané rozhodnutí, scope, out-of-scope, role a známá omezení.
6. Do `inputs/catalog.yaml` zapište dostupné vstupy a jejich důvěryhodnost.
7. Do `artifacts/align/hotspots.yaml` zapište počáteční nejistoty.
8. V `sync/miro-map.yaml` ponechte board ID jako odkaz na environment variable.
9. Proveďte schema validaci.
10. Založte feature branch a commitněte bootstrap odděleně od doménových závěrů.

## Minimální manifest

```yaml
schema_version: 1.0.0
project_id: claims-modernization
name: Modernizace likvidace pojistných událostí
project_type: legacy-modernization
language: cs
status: proposed
workflow:
  profile: legacy-modernization
  current_stage: align
  completed_gates: []
miro:
  board_id_env: DDDA_CLAIMS_MIRO_BOARD_ID
owners:
  business_sponsor: null
  architecture_owner: null
```

## Kontroly

- `project_id` je unikátní a nemění se s názvem.
- Typ projektu odpovídá hlavnímu problému, ne preferované technologii.
- Citlivost vstupů je explicitní.
- Board nebo board area není sdílena s jiným projektem bez explicitní izolace.
- V manifestu není token.

## Typické chyby

- projekt je pojmenován podle řešení, například `microservices-migration`, místo business scope,
- scope je celý podnik bez rozhodnutí, které má discovery umožnit,
- copied project obsahuje staré `artifact_id` a Miro mapping,
- tým začne vytvářet bounded contexts před G2.

## Navazující krok

Pokračujte kuchařkou `02-priprava-miro-boardu.md` a poté gate G1.