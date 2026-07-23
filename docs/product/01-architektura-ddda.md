# Architektura produktu DDDA

## Cíl

DDDA odděluje platformní produkt od projektových dat. Platforma poskytuje metodiku, schémata, scaffoldy, runtime a skripty. Projekt obsahuje business evidence, doménové artefakty, Miro stav a rozhodnutí.

## Komponenty

```text
Chat / Cursor agent
  ├─ čte dokumentaci a project.yaml
  ├─ navrhuje prompty, artefakty a rozhodnutí
  └─ volá PowerShell wrappers
        └─ Python Miro runtime
             ├─ REST API v2 client
             ├─ scaffold renderer
             ├─ YAML/Miro sync engine
             ├─ conflict detector
             └─ audit reports

Project repository
  ├─ ingestion/
  ├─ artifacts/
  ├─ decisions/
  ├─ workshops/prompts/
  ├─ miro/miro-map.yaml
  ├─ miro/sync-state.yaml
  ├─ miro/conflicts/
  └─ reports/miro-sync/
```

## Architektonická rozhodnutí

1. YAML je kanonická sémantika.
2. Miro vlastní layout a kolaboraci.
3. Git je approval a audit boundary.
4. Runtime používá REST API v2 a OAuth bearer token.
5. Synchronizace je řízená; polling worker se zastaví při konfliktu.
6. Dry-run je povinný před write operací v chat-first workflow.
7. Sémantické konflikty se ukládají jako explicitní records.
8. Mazání je tombstone-first.

## Quality attributes

- **auditability** — každý sync vytváří report a Git diff,
- **safety** — tokeny nejsou v repozitáři; žádný implicitní merge,
- **idempotence** — mapping drží stabilní Miro item ID,
- **recoverability** — marker umožňuje obnovit identitu po ztrátě mappingu,
- **portability** — workspace používá relativní cesty,
- **evolvability** — item adapters a schémata lze rozšiřovat nezávisle.

## Omezení

Miro REST API nepodporuje libovolná skrytá metadata pro všechny item typy. DDDA proto používá mapping soubor a viditelný, strojově čitelný marker. Unmanaged položky nejsou automaticky importovány.
