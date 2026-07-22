# Kuchařka 12 — Miro troubleshooting

## Diagnostický tok

```text
installation → local doctor → online doctor → dry-run render
→ list/sync dry-run → mapping/state review → API logs/report
```

## Runtime není nainstalován

Spusť `Install-DDDAMiroRuntime.ps1`. Ověř Python 3.11+, vytvořený `.ddda/runtime/miro-venv` a `python -m ddda_miro --help`. Lokální runtime adresář se necommitne.

## Doctor selže

- ověř `MIRO_ACCESS_TOKEN`,
- ověř board ID environment variable nebo `miro-map.yaml`,
- zkontroluj scopes `boards:read` a `boards:write`,
- zkontroluj, že tokenový uživatel vidí board,
- ověř správný projekt a board namespace.

## HTTP 401/403

401 obvykle znamená neplatný nebo expirovaný token. 403 znamená nedostatečný scope nebo board access. Token neukládej do logu ani Git diffu; obnov jej v secret store/environment a worker restartuj.

## HTTP 429

Runtime respektuje `Retry-After` a omezený backoff. Omez write batch, používej dry-run a synchronizuj po menších slices. Trvalý worker musí mít monitoring rate-limit chyb.

## Duplikované frames nebo items

Zkontroluj `miro/miro-map.yaml`, marker a board ID. Neodstraňuj mapping ručně bez recovery plánu. Duplicitní itemy nejprve označ jako unmanaged nebo superseded; fyzické smazání proveď explicitně.

## Conflict exit code 2

Nejde o provozní chybu. Otevři `miro/conflicts/`, porovnej common base, YAML a Miro variantu a rozhodni `accept_yaml`, `accept_miro`, `merge_manual` nebo `supersede_artifact`.

## Nový Miro item se neimportuje

Item musí obsahovat správný project marker, `Typ`, `Stav` a `Fáze`. Pull bez `-PromoteNew` pouze oznámí promotion candidate. Proveď promotion dry-run a zkontroluj cílový YAML path.

## Mapped remote item chybí

Runtime vytvoří `mapped_remote_item_missing`. Ověř, zda byl item smazán, přesunut, nebo není viditelný kvůli oprávnění. Obnova vyžaduje `-RecreateMissing`.

## Lokální YAML chybí

Runtime vytvoří `mapped_local_artifact_missing`; soubor obnov z Gitu, nebo vytvoř explicitní tombstone. Nikdy neinterpretuj náhodné smazání souboru jako požadavek odstranit Miro item.

## Špatná čeština

PowerShell skripty musí být UTF-8 BOM. `Test-DDDAInstallation.ps1` kontroluje BOM a CI používá Windows PowerShell 5.1.

## Support bundle

Pro analýzu sdílej pouze sanitizované: verzi DDDA, Python/PowerShell verzi, command, exit code, sync report bez citlivých textů, mapping IDs a API status. Nikdy nesdílej bearer token.
