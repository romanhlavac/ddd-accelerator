# Kuchařka 08 — Gate review

## Výsledek

Vznikne explicitní rozhodnutí `pass`, `conditional-pass` nebo `fail`, včetně evidence, podmínek, vlastníků a termínů.

## Příprava

1. Určete gate a rozhodnutí, které má umožnit.
2. Připravte odkazy na artefakty a změny od poslední revize.
3. Ověřte strukturální validaci.
4. Seznamte otevřené konflikty, rizika a assumptions.
5. Pozvěte business ownera, architektonického ownera a relevantní experty.

## Agenda 45 minut

- 5 min: cíl a rozhodovací práva,
- 10 min: playback hlavních závěrů,
- 10 min: evidence a změny,
- 10 min: rizika, konflikty a neznámé,
- 5 min: checklist,
- 5 min: rozhodnutí a akce.

## Rozhodnutí

### Pass

Kritéria jsou splněna a nejsou známé blokující nejistoty.

### Conditional pass

Lze pokračovat, ale podmínky mají explicitního ownera, termín a definovaný dopad při nesplnění.

### Fail

Podklady nestačí pro zamýšlené rozhodnutí. Review určí konkrétní doplnění; nejde o obecný požadavek „udělat více analýzy“.

## Záznam

```yaml
gate: G5
project_id: life-insurance-greenfield
decision: conditional-pass
date: 2026-07-22
decision_owner: Chief Architect
conditions:
  - action: Potvrdit ownership klientských kontaktních údajů.
    owner: Customer Director
    due: 2026-07-29
    blocking_for: G7
evidence:
  - artifacts/connect/context-map.yaml
  - artifacts/connect/data-ownership.yaml
```

## Chyby

- gate schvaluje pouze architekt bez business ownera,
- checklist nahrazuje diskusi o rizicích,
- conditional pass nemá termín,
- neexistuje odkaz na konkrétní revizi artefaktů,
- kandidátní model je přejmenován na validovaný bez evidence.