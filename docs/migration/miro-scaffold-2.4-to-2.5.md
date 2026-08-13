# Miro scaffold migration: 2.4 → 2.5

Schema `2.5` zavádí REM-010 human-review traceability a samostatný obsahový kontrakt frame `01`.

## Změny kontraktu

- povinné `review_sources.redline` a `review_sources.ddd_starter` s exact board ID, URL a `mode: read_only`;
- každá stage uvádí `reference_board_id`, `reference_frame_title`, `reference_frame_url` a `reference_artifacts_cs`;
- DDD Starter example templates uvádějí source frame a `adaptation_cs`;
- `minimum_remote_item_count` se zvyšuje z 250 na 280;
- přibývá `minimum_overview_child_items: 61` a `minimum_starter_reference_captions: 11`;
- render contract je `REM-PR8-HVA-CC-010`.

## Dopad

Projektové YAML artefakty ani gate decisions se nemění. Při příštím explicitním renderu se existující journey položky přesunou pod frame `01`, doplní se osm source cards a rozšířené mini-vzory. Změní se `scaffold_sha256` a `remote_content_digest`.

Zdrojové redline/reference boardy se nemodifikují. Pro human review se vytváří nový izolovaný board z exact candidate SHA.
