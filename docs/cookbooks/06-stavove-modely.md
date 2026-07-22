# Kuchařka 06 — Stavové modely v metodickém toku

## Výsledek

Životní cyklus klíčového doménového objektu je dohledatelně rozvíjen od pozorované reality přes kandidátní a validovaný business model až k případné implementační state machine.

## 1. Observed lifecycle — Discover

Zachyťte pouze to, co je podloženo vstupy nebo zkušeností expertů:

- pozorované stavy,
- události nebo akce, které do nich vedou,
- role oprávněné stav změnit,
- výjimky a ruční zásahy,
- zdroj evidence,
- nejistotu.

Neopravujte zde současnou realitu podle cílové představy.

## 2. Candidate lifecycle — Decompose

Použijte observed model jako vstup a formulujte hypotézu:

- které stavy mají vlastní business význam,
- kde se mění pravidla nebo odpovědnost,
- zda jeden objekt neskrývá více nezávislých lifecycle,
- které přechody jsou zakázané,
- které lifecycle indikují hranici subdomény nebo bounded contextu.

Každá změna proti observed modelu má důvod.

## 3. Validated business state machine — Define

S doménovým expertem schvalte:

- počáteční a terminální stavy,
- povolené přechody,
- business command nebo rozhodnutí,
- vzniklou událost,
- preconditions a invarianty,
- oprávněného aktéra,
- časové a regulatorní podmínky.

Model nesmí obsahovat technické retry, fronty nebo interní statusy, pokud nemají business význam.

## 4. Implementation state machine — Code

Vytvářejte pouze tehdy, pokud explicitní automat zlepšuje správnost, audit nebo srozumitelnost. Může obsahovat technické mezistavy, ale musí mapovat zpět na business model.

Doplňte:

- persistence a recovery,
- souběh a idempotenci,
- timeouty a retry,
- observabilitu,
- migraci existujících instancí,
- testy zakázaných přechodů.

## Povinná traceability

```yaml
artifact_id: lifecycle-policy-validated
artifact_type: lifecycle
maturity: validated
supersedes: lifecycle-policy-candidate
based_on:
  - lifecycle-policy-observed
validated_by:
  - Head of Policy Operations
validation_date: 2026-07-22
```

## Kontroly

- stav není pouze hodnota z legacy databáze bez business významu,
- přechod má příčinu a výsledný business fakt,
- kandidátní model není označen jako validovaný,
- implementační stav nemění význam business lifecycle,
- dva bounded contexts nesdílejí jeden autoritativní stav bez jasného ownershipu.