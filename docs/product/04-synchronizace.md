# Synchronizace Miro ↔ YAML ↔ Git

## 1. Cíl

Synchronizace udržuje jednu doménovou informaci ve dvou pracovních reprezentacích:

- Miro pro lidskou spolupráci, prostorové uspořádání a facilitaci,
- YAML pro sémantiku, automatizaci, validaci a verzování.

Git není třetí editovatelná reprezentace; je transportem, historií a review mechanismem YAML souborů.

## 2. Rozdělení ownershipu

| Pole | Owner |
|---|---|
| `name`, `description`, `status`, vztahy, ownership, evidence | YAML |
| souřadnice, rozměry, z-index, vizuální seskupení | Miro |
| barva | odvozená z typu; lokální override jen pokud je povolen |
| komentáře a hlasování | Miro |
| historie změn | Git |
| Mermaid | generovaný výstup |

Změna sémantiky v Miru je povolena, ale po importu se stává návrhem změny YAML a musí projít validací a případně review.

## 3. Identita objektu

Každý spravovaný Miro objekt nese minimálně:

```yaml
artifact_id: evt-policy-issued
artifact_type: domain_event
project_id: life-insurance-greenfield
schema_version: 1.0.0
stage: discover
status: observed
yaml_path: artifacts/discover/events/evt-policy-issued.yaml
git_revision: 3f83a1d
```

Miro item ID není doménová identita. Při smazání a znovuvytvoření objektu se může změnit, zatímco `artifact_id` zůstává stabilní.

## 4. Synchronizační cyklus

### Pull z Mira

1. Načti board revision a spravované objekty.
2. Porovnej je s `miro-map.yaml` a posledním sync stavem.
3. Rozděl změny na vizuální, sémantické, nové a smazané.
4. Pro sémantické změny vytvoř nebo uprav YAML návrh.
5. Validuj schéma a metodická pravidla.
6. Ulož conflict records, pokud obě strany změnily stejné pole.
7. Vygeneruj Mermaid a sync report.
8. Commit provede člověk nebo schválená automatizace.

### Push do Mira

1. Validuj projekt a YAML.
2. Načti aktuální board revision.
3. Ověř, že od posledního pullu nevznikla neočekávaná změna.
4. Vytvoř nebo aktualizuj spravované objekty.
5. Zachovej vizuální vlastnosti vlastněné Mirem.
6. Aktualizuj metadata a `miro-map.yaml`.
7. Zapiš sync report.

## 5. Detekce konfliktu

Konflikt nastane, pokud se od společné base revision změnilo stejné sémantické pole na obou stranách.

Příklad:

```yaml
conflict_id: conflict-2026-07-22-001
artifact_id: bc-policy-administration
field: description
base: Spravuje životní cyklus pojistné smlouvy.
yaml_value: Spravuje nabídku, vznik a změny smlouvy.
miro_value: Spravuje aktivní pojistné smlouvy.
resolution: pending
owner: architecture-owner
```

Povolená řešení:

- `accept_yaml`,
- `accept_miro`,
- `merge_manual`,
- `supersede_artifact`.

Last-write-wins je zakázán pro sémantická pole.

## 6. Mazání

Používá se tombstone-first:

1. objekt dostane `status: deprecated` nebo `deleted_pending`,
2. synchronizace upozorní na příchozí a odchozí odkazy,
3. člověk potvrdí odstranění,
4. YAML zůstane v Git historii,
5. Miro objekt se odstraní nebo přesune do archivu.

## 7. Idempotence

Opakovaný pull nebo push bez mezilehlé změny nesmí vytvářet nové artefakty, měnit identifikátory ani posouvat prvky. Sync report musí uvádět nulový diff.

## 8. Dry-run

Každá write operace musí podporovat `--dry-run`. Výstup obsahuje:

- počet nových, změněných a odstraněných objektů,
- seznam dotčených YAML souborů,
- konflikty,
- validační chyby,
- předpokládané Miro API operace.

## 9. Miro mapping

`sync/miro-map.yaml` mapuje identitu a vizuální stav:

```yaml
board_id: ${DDDA_LIFE_MIRO_BOARD_ID}
board_revision: '18731'
items:
  evt-policy-issued:
    miro_item_id: '3458764512345'
    frame_id: big-picture-es
    x: 1220
    y: 840
    width: 220
    height: 140
```

## 10. Webhook versus polling

- Webhook je vhodný pro rychlou detekci změn, ale událost nemusí obsahovat celý stav.
- Polling je jednodušší pro lokální provoz a obnovu po výpadku.
- Doporučený návrh: webhook označí projekt jako dirty; worker následně provede idempotentní pull.

První implementace může používat pouze řízený pull/push z CLI. To omezuje provozní složitost a umožňuje ověřit model konfliktů před automatizací.

## 11. Bezpečnost

- Tokeny nikdy neukládat do YAML ani Gitu.
- Board ID lze skrýt přes environment variable, pokud je citlivé.
- Logovat pouze identifikátory a zkrácené diffy.
- Před exportem citlivých workshopových dat ověřit klasifikaci projektu.

## 12. Definition of Done konektoru

Živý konektor je považován za dokončený, pokud prokazatelně zvládá:

- create/update/read managed item,
- zachování unmanaged item,
- idempotentní opakování,
- konflikt na stejném poli,
- tombstone delete,
- recovery po částečném selhání,
- dry-run,
- auditní sync report,
- práci se dvěma projekty bez záměny boardů nebo namespace.