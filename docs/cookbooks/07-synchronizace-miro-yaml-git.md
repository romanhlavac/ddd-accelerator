# Kuchařka 07 — Synchronizace Miro, YAML a Git

## Výsledek

Změny jsou bezpečně přeneseny mezi Mirem a YAML, konflikty jsou explicitní a Git obsahuje auditovatelný commit.

## Předpoklady

- projekt má validní manifest,
- board mapping patří správnému projektu,
- Miro token je v prostředí,
- pracovní větev je čistá,
- před write operací byl proveden pull nebo kontrola board revision.

## Doporučený rytmus

### Před workshopem

1. Pull z Gitu.
2. Validace YAML.
3. Dry-run push do Mira.
4. Push scaffoldů a posledních schválených artefaktů.
5. Kontrola board revision a mapování.

### Po workshopu

1. Uzavřete aktivní editaci boardu.
2. Proveďte dry-run pull.
3. Zkontrolujte nové, změněné, smazané a nespravované objekty.
4. Vyřešte strukturální chyby a konflikty.
5. Povýšte relevantní workshopové poznámky na artefakty.
6. Vygenerujte Mermaid výstupy.
7. Zkontrolujte diff.
8. Commitněte se zdrojem workshopu a board revision.
9. Otevřete pull request pro významné sémantické změny.

## Řešení konfliktu

1. Neprovádějte další push.
2. Otevřete conflict record.
3. Porovnejte base, YAML a Miro hodnotu.
4. Určete sémantického ownera pole.
5. Zvolte accept YAML, accept Miro nebo manual merge.
6. Zapište důvod a řešitele.
7. Validujte a proveďte nový dry-run.
8. Conflict record ponechte jako auditní stopu.

## Mazání

Nepoužívejte okamžité hard delete. Nejprve nastavte tombstone, ověřte odkazy a ownership, teprve poté potvrďte odstranění.

## Kontroly

- nulový diff při opakovaném běhu,
- žádná změna `artifact_id`,
- nespravované Miro objekty zůstaly zachovány,
- Mermaid odpovídá YAML,
- token ani citlivý obsah není v logu,
- commit zpráva uvádí projekt a zdroj změny.

## Příklad commit message

```text
sync(life-insurance): import Big Picture ES workshop 2026-07-22

Board revision: 18731
Validated by: Product Director, Head of Underwriting
Conflicts resolved: 2
```