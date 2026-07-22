# Kuchařka 12 — Miro troubleshooting

## Doctor selže

- ověř `MIRO_ACCESS_TOKEN`,
- ověř board ID environment variable,
- zkontroluj scopes `boards:read` a `boards:write`,
- zkontroluj, že tokenový uživatel vidí board.

## HTTP 429

Runtime používá retry a `Retry-After`. Omez počet zapisovaných artefaktů, používej dry-run a synchronizuj po menších slices.

## Duplikované frames

Zkontroluj `miro/miro-map.yaml`. Neodstraňuj mapping ručně bez recovery. Marker a Miro item ID musí ukazovat na stejný projekt.

## Konflikt exit code 2

Nejde o provozní chybu. Otevři `miro/conflicts/`, rozhodni variantu a proveď ruční merge.

## Item byl ručně smazán

Runtime vytvoří delete/missing konflikt. Obnov item z YAML push operací, nebo potvrď tombstone podle business rozhodnutí.

## Špatná čeština

PowerShell skripty musí být UTF-8 BOM. Diagnostika kontroluje BOM a Windows PowerShell 5.1 CI.
