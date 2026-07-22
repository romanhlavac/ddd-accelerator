# Miro REST runtime a obousměrná synchronizace

## Autentizace

Runtime čte bearer token z environment variable, výchozí `MIRO_ACCESS_TOKEN`. Projekt může board, team a Miro project/space ID načítat z manifestu nebo environment variables.

Požadované scopes:

- `boards:read` pro doctor a pull,
- `boards:write` pro create/update/delete a render.

## Podporované item typy

- frame,
- sticky note,
- shape,
- text.

Doménové typy se mapují na item typy. Například domain event → sticky note, bounded context → shape, explanatory note → text.

## Identita

Primární vazba je v `miro/miro-map.yaml`. Každá spravovaná položka navíc obsahuje marker:

```text
DDDA:<project-id>:<artifact-id>
```

Marker umožní obnovit identitu, pokud je mapping poškozen nebo item přesunut.

## Společná base

`miro/sync-state.yaml` ukládá hash lokální a vzdálené sémantiky z posledního úspěšného syncu. Konflikt vznikne, pokud se obě strany změnily a nejsou shodné.

## Pull

Pull načte všechny board items, vybere pouze položky se správným project markerem, porovná hash a aktualizuje YAML. Unmapped managed item vyžaduje explicitní promotion; unmanaged item se ignoruje.

## Push

Push vytvoří nebo aktualizuje Miro item. Standardně mění pouze sémantický obsah a styl odvozený z typu. Layout zůstává vlastnictvím Mira. `-IncludeLayout` se používá při prvním vytvoření nebo explicitním resetu.

## Both

Režim Both provede kontrolovaný pull a push nad jednou společnou base. Konflikt blokuje automatické sjednocení.

## Mazání

`deleted_pending` je tombstone. Fyzické DELETE vyžaduje `-ConfirmDelete`. Mapping a sync state se aktualizují až po úspěšné API operaci.

## Audit

Každý skutečný sync zapisuje report do `reports/miro-sync/`. Report obsahuje direction, operace, konflikty, board ID a čas.

## Rate limit a retry

Client respektuje HTTP 429, `Retry-After` a používá omezený exponenciální backoff. Hromadné write operace se proto mají plánovat a kontrolovat dry-runem.

## Polling worker

`Start-DDDAMiroSyncWorker.ps1` spouští kontrolovaný polling nad režimem `Both`. Minimální interval je 30 sekund. Worker používá stejný common-base a conflict model jako jednorázový sync; nevytváří zvláštní paralelní stav.

Provozní vlastnosti:

- po každém cyklu vzniká auditní report,
- při konfliktu proces končí s exit code `2`,
- API nebo konfigurační chyba končí exit code `1`,
- normální ukončení přes `-MaxCycles` vrací `0`,
- worker necommitne a nepushne změny,
- OAuth token se nerefreshuje uvnitř runtime.

Lokální worker je určen pro facilitované nebo vývojové použití. Pro trvalý provoz jej hostuj v řízené službě se secret store, restart policy, log shippingem a externím token refresh mechanismem.

## Chybějící mapped item

Pokud `miro-map.yaml` obsahuje item ID, ale API položku nevrátí, runtime nepředpokládá, zda šlo o záměrné smazání, změnu oprávnění nebo přesun. Vytvoří konflikt `mapped_remote_item_missing`. Znovuvytvoření je povoleno pouze explicitně přes `-RecreateMissing`, ideálně nejprve v dry-run režimu.

## Omezení první produkční verze

Runtime synchronizuje spravované frame, sticky note, shape a text položky. Nespravuje komentáře, hlasování, obrázky, konektory ani tagy. Tyto objekty zůstávají workshopovým obsahem vlastněným Mirem. Worker používá polling; webhook může později sloužit jako trigger, ale nesmí obcházet stejný idempotentní pull/sync algoritmus.
