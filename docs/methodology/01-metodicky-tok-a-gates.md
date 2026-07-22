# Metodický tok a gates

## Princip

DDDA používá evoluční tok. Každá fáze snižuje jiný typ nejistoty. Gate potvrzuje dostatečnost podkladů pro další rozhodnutí; nepotvrzuje absolutní správnost modelu.

## Tok

### Align

**Otázka:** Proč tuto práci děláme a jaké rozhodnutí má umožnit?

Výstupy: business problém, cíle, scope, aktéři, constraints, assumptions, prioritní quality attributes, inventory vstupů.

Gate G1: scope, sponsor, experti a očekávané rozhodnutí jsou explicitní.

### Discover

**Otázka:** Co se v doméně skutečně děje a jak o tom lidé mluví?

Výstupy: Big Picture ES, slovník, aktéři, systémy, hotspoty, pozorované životní cykly.

Gate G2: end-to-end tok je dostatečně pokrytý a klíčové nejistoty jsou viditelné.

### Process Modeling

**Otázka:** Jak probíhají prioritní scénáře, rozhodnutí, výjimky a tvorba hodnoty?

Výstupy: process models a katalog scénářů. Fáze nemá samostatný povinný gate; její výsledky vstupují do G3.

### Decompose

**Otázka:** Kde se mění jazyk, pravidla, lifecycle, data ownership nebo tempo změn?

Výstupy: kandidátní subdomény, boundary hypotheses, kandidátní životní cykly.

Gate G3: hypotézy hranic mají důvody, nejistoty a validační plán.

### Strategize

**Otázka:** Kde se podnik diferencuje a kam má investovat?

Výstupy: Core/Supporting/Generic, diferenciace × komplexita, sourcing a evoluční strategie.

Gate G4: klasifikace má business zdůvodnění a vlastníka.

### Connect

**Otázka:** Jaké modelové hranice potřebujeme a jak spolu budou komunikovat?

Výstupy: bounded contexts, context map, data ownership, kontrakty, relationship patterns.

Gate G5: směry vztahů, ownership a očekávání kontraktů jsou explicitní.

### Organize

**Otázka:** Kdo vlastní změnu a jaké týmové interakce jsou potřeba?

Výstupy: team topology, interaction modes, cognitive load, governance a fitness functions.

Gate G6: prioritní hranice mají vlastníka nebo explicitní organizační gap.

### Define

**Otázka:** Jak se prioritní bounded context chová a jaká pravidla musí chránit?

Výstupy: Bounded Context Canvas, Design-Level ES, agregátní/consistency boundaries, invarianty, validované business lifecycle, quality attribute scénáře a ADR.

Gate G7: model je validován doménovým expertem a připraven na implementační rozhodnutí.

### Code

**Otázka:** Jak model převést do bezpečně evolvující implementace?

Výstupy: implementační hranice, kontrakty, testy invariantů, případné state machines, observabilita, migrační slices a rollback.

Gate G8: implementace a migrace mají testovatelný kontrakt, rizika a provozní strategii.

## Pravidla přechodu

- Fáze lze iterovat a vracet se zpět.
- Přeskočení fáze musí být zdůvodněno v decision logu.
- Gate lze schválit podmíněně; podmínky mají ownera a termín.
- Model s `candidate` statusem se nesmí prezentovat jako schválená cílová architektura.
- Technologická volba před G5 je výjimka vyžadující constraint nebo experimentální hypotézu.

## Evidence

Každé důležité tvrzení má obsahovat alespoň jeden typ evidence:

- workshop a seznam validujících účastníků,
- konkrétní zdrojový dokument,
- kód nebo databázové schéma,
- provozní měření,
- regulatorní požadavek,
- explicitní rozhodnutí vlastníka.

## Gate review

Gate review má 30–60 minut a používá strukturu:

1. rozhodnutí, které má gate umožnit,
2. změny od minulé revize,
3. evidence,
4. otevřené konflikty a rizika,
5. checklist,
6. rozhodnutí: pass / conditional pass / fail,
7. vlastníci akcí.
