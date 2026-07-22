# Rozšiřování DDDA

## Přidání artefaktu

1. definuj business účel a lifecycle,
2. přidej JSON Schema,
3. urč default Miro item type a barvu,
4. doplň cookbook a prompt,
5. přidej round-trip test,
6. ověř konflikt a tombstone.

## Přidání projektového typu

Typ musí řešit odlišný rozhodovací problém, ne pouze jiné odvětví. Doplň enum, aliases, workflow, gates, use cases, example a CI test.

## Přidání Miro adapteru

Nový item type vyžaduje create/update/delete endpoint mapping, serializaci sémantiky, parser markeru a fake-client testy. Unsupported items se nesmí potichu mapovat na ztrátovou reprezentaci.

## Extension governance

Obecná potřeba vzniklá v projektu se nejprve implementuje jako platformní PR. Projekt ji přijme samostatným upgrade PR. Tím se zachová ownership a auditní hranice.
