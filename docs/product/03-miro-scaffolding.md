# Miro scaffolding

## Účel

Scaffold není hotový model. Je to navigační a facilitační struktura, která ukazuje fázi, pracovní otázku, očekávané artefakty a gate.

## Renderované prvky

Renderer načte `scaffolds/miro/strategic-ddd-method-board.yaml` a pro každý frame vytvoří nebo aktualizuje:

- frame s názvem, souřadnicemi a rozměry,
- textový blok s pracovními oblastmi,
- záznam stabilní vazby v `miro/miro-map.yaml`.

## Metodický tok

- Big Picture EventStorming je v Discover,
- Process Modeling je most Discover → Decompose,
- Design-Level EventStorming je v Define,
- lifecycle model má observed, candidate, validated a implementation úroveň.

## Idempotence

Opakovaný render používá mapping a aktualizuje existující frames. Nezakládá kopie, pokud mapping zůstává konzistentní.

## Dry-run

Dry-run vypíše plánované create/update operace a nevolá write endpointy. Je vhodný jako první krok každého chatového workflow.

## Vlastní scaffold

Nový scaffold musí mít stabilní `id`, frames s unikátním `id`, souřadnice, rozměry, stage, title a seznam pracovních oblastí. Před přidáním je nutné rozšířit JSON Schema a testy.
