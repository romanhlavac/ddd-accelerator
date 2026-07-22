# Typy projektů, workflow profily a use cases

## 1. Princip volby

Vyber nejmenší profil, který pokrývá rozhodovací problém. Velikost rozpočtu, počet systémů ani počet lidí samy o sobě neznamenají `portfolio-program`. Typ nastavuje výchozí tok, povinnou evidence, doporučené workshopy a gaty. Rozšíření se zapisují do `workflow.extensions`.

| Typ | Hlavní rozhodnutí | Typický konec |
|---|---|---|
| `portfolio-program` | portfolio domén, ownership, roadmapa | programové inkrementy |
| `greenfield-product` | první hodnotný slice a hranice produktu | implementovatelný slice |
| `legacy-modernization` | evoluční náhrada a decommission | ověřený migrační slice |
| `legacy-transformation` | nový business + operating model + IT | transition architecture |
| `integration-landscape` | data ownership a kontrakty | integrační guardrails |
| `purchased-product-adoption` | fit-gap a ochrana vlastního modelu | implementační boundary |
| `domain-discovery` | jazyk, události, hotspoty, kandidátní hranice | G3 / backlog otázek |
| `architecture-review` | riziko a investiční doporučení | review report + ADR backlog |
| `operating-model-and-teams` | týmový ownership a interaction modes | cílová topology |
| `bounded-context-design` | chování a taktický model jednoho BC | G8 |

## 2. Kombinace profilů

Příklad modernizace s COTS a změnou týmů:

```yaml
project:
  type: legacy-modernization
workflow:
  profile: legacy-modernization
  extensions:
    - purchased-product-adoption
    - operating-model-and-teams
```

Dominantní profil určuje hlavní výsledek a pořadí práce. Extension doplňuje povinnou evidence a rozhodnutí, ale nesmí vytvořit paralelní metodiku bez společných artefaktů a gatů.

## 3. `portfolio-program`

### Kdy použít

- nová pojišťovna, banka nebo marketplace,
- transformace core systému napříč několika value streams,
- program s více produkty, doménami a stream-aligned týmy,
- potřeba společné context mapy, ownershipu a roadmapy.

### Hlavní otázky

- Které business outcomes jsou společné programu?
- Které subdomény jsou core, supporting a generic?
- Kde je skutečný data ownership?
- Které hranice jsou stabilní a které pouze přechodné?
- Jaké týmy mohou nést end-to-end odpovědnost?
- Jak rozdělit program do autonomních inkrementů?

### Povinné vstupy

Strategie, capability landscape, value streams, regulatorní omezení, systémová mapa, ownership dat, sourcing strategie, týmová kapacita a prioritní quality attributes.

### Tok

```text
Strategický záměr
→ stakeholder a capability landscape
→ Big Picture ES podle value streams
→ portfolio subdomén
→ kandidátní bounded contexts
→ strategic classification
→ programová context map
→ team topology a governance
→ transition architecture
→ prioritizované programové slices
```

### Gaty

- P1/G1: outcomes, scope a decision owners,
- P2/G3: portfolio decomposition a otevřené hypotézy,
- P3/G5: context map a data ownership,
- P4/G6: týmový ownership a governance,
- P5: roadmapa, dependency strategy a decommission cíle.

### Miro

Control center, capability landscape, několik Big Picture lanes, portfolio decomposition, sourcing matrix, programová context map, ownership overlay, Team Topologies a roadmapa.

### Prompt

> Proveď portfolio intake. Odděl capabilities, subdomény, bounded contexts, systémy a organizační útvary. Neodvozuj BC z org chartu ani z dnešních aplikací. Navrhni programové gaty a pořadí workshopů.

### Anti-patterny

- jeden enterprise model pro všechny kontexty,
- programová roadmapa podle komponent místo business outcomes,
- centrální platform team jako vlastník všech sdílených domén,
- „core“ jako synonymum kritického systému.

## 4. `greenfield-product`

### Kdy použít

Nový produkt nebo služba s jedním dominantním product scopem a bez nutnosti současně řídit celé portfolio organizace.

### Tok

```text
Product vision
→ user outcomes
→ Big Picture ES
→ process slices
→ subdomény a BC hypotheses
→ quality attribute scenarios
→ první hodnotný end-to-end slice
→ Design-Level ES
→ tactical a solution design
```

### Povinná evidence

Product vision, target users, value proposition, constraints, externí platformy, regulace, provozní cíle, první měřitelný outcome.

### Gate emphasis

G1 potřeba a value proposition; G2 problémový prostor; G3 hranice a ownership; G4 quality attributes; G7 první BC připravený pro detail; G8 implementovatelný slice.

### Miro

Jedna hlavní timeline, prioritní process slices, candidate BCs, first-slice overlay, detailní Define frames pouze pro vybraný BC.

### Prompt

> Najdi nejmenší hodnotný end-to-end slice. Ukaž business události, rozhodnutí, invarianty, závislosti a měřitelný outcome. Nezačínej mikroservisami ani univerzálním modelem pro budoucí produkty.

### Anti-patterny

- greenfield bez enterprise a regulatorních constraints,
- CQRS/Event Sourcing jako startovní preference,
- návrh všech budoucích variant před ověřením prvního produktu.

## 5. `legacy-modernization`

### Kdy použít

Existující systém omezuje změny, ale business scope zůstává převážně stabilní a cílem je evoluční náhrada, rozdělení nebo odstranění vendor lock-in.

### Povinné vstupy

Runtime topology, data stores, system-of-record, integration inventory, incidenty, release lead time, batch windows, provozní omezení, skrytá pravidla, vendor knowledge, SLA a recovery postupy.

### Tok

```text
Business pain a outcome
→ as-is evidence
→ Big Picture business reality
→ skrytá pravidla a coupling
→ target subdomains/BC
→ seams a ACL
→ transition context map
→ migrační slice
→ parallel run/reconciliation
→ decommission
```

### Povinné výstupy

Characterization evidence, target boundaries, seam catalog, transition contracts, data migration ownership, rollback, reconciliation, observability a decommission criteria.

### Miro

Business timeline oddělená od technického as-is, runtime/coupling overlay, seam map, transition context map, migration lanes, reconciliation checkpoints a decommission dashboard.

### Prompt

> Odděl business realitu od současné implementace. Zmapuj skrytá pravidla, system-of-record, runtime coupling, change coupling, failure modes a rollback. Navrhni nejmenší migrační slice s měřitelným business outcome.

### Anti-patterny

- rewrite jako cíl,
- target BC kopírující dnešní moduly,
- shared database jako dočasné řešení bez exit kritérií,
- decommission bez reconciliation a provozní observability.

## 6. `legacy-transformation`

### Kdy použít

Současně se mění produkty, procesy, regulace, operating model, sourcing a core IT. Nestačí pouze modernizovat implementaci.

### Paralelní modely

- as-is business reality,
- target capabilities a policies,
- transition states,
- dočasné bounded contexts,
- změny týmového ownershipu,
- změny datového a provozního modelu.

### Tok

```text
Transformační outcomes
→ as-is business/system/team evidence
→ target capability model
→ target domain boundaries
→ transition BC a ACL
→ operating-model changes
→ migrační vlny
→ decommission a knowledge transfer
```

### Prompt

> Odděl změnu business modelu, operating modelu a technologie. Navrhni cílové a přechodné bounded contexts, změny ownershipu, knowledge-retention opatření a roadmapu, která nezávisí na jednom big-bang release.

### Anti-patterny

- target architecture bez transition architecture,
- outsourcing klíčového doménového knowledge,
- jeden programový tým bez stream ownershipu,
- greenfield model ignorující nutnost koexistence.

## 7. `integration-landscape`

### Kdy použít

Hlavním problémem je nejasné vlastnictví dat, point-to-point integrace, duplicitní API, nekonzistentní eventy nebo nejasné provozní odpovědnosti.

### Tok

```text
Kritické business scénáře
→ context map
→ source-of-truth a data ownership
→ published language
→ API/event contracts
→ consistency, latency, security
→ failure/recovery modes
→ ACL a observability
```

### Povinné výstupy

Integration catalog, ownership matrix, contract versioning, idempotence, ordering, retry/DLQ, reconciliation, consumer expectations a deprecation policy.

### Prompt

> Pro každý integrační tok uveď business důvod, producer, consumer, owned data, contract, latency, consistency, idempotence, failure mode, recovery a observability. Nevytvářej centrální canonical model bez doménového ownera.

### Anti-patterny

- event bus jako řešení nejasných boundaries,
- „single source of truth“ bez konkrétního ownera,
- synchronní řetězení přes několik BC,
- technický event bez business kontraktu.

## 8. `purchased-product-adoption`

### Kdy použít

Capability je realizována SaaS nebo COTS produktem a je nutné rozhodnout fit-gap, ownership, konfiguraci, integrace a exit strategy.

### Modelovací rozsah

Modeluj vlastní business odpovědnost, data ownership, lifecycle, vendor language, published contracts, konfiguraci a ACL. Nemodeluj interní agregáty produktu, které organizace neovládá.

### Tok

```text
Business responsibility
→ canonical language a vendor language
→ fit-gap
→ configuration boundary
→ data ownership
→ integrations a ACL
→ operating ownership
→ continuity/exit plan
```

### Prompt

> Proveď fit-gap mezi naším business modelem a vendor modelem. U každého gapu rozhodni configure, extend, adapt, change process, reject product nebo retain capability. Navrhni ACL, ownership dat, upgrade impact a exit criteria.

### Anti-patterny

- vendor object model jako enterprise ubiquitous language,
- SaaS bez interního owning teamu/service ownera,
- customizace bez upgrade strategie,
- data export označený za exit plan bez ověření sémantiky a provozu.

## 9. `domain-discovery`

### Kdy použít

Časově omezený discovery sprint, příprava programu, ověření business problému nebo vytěžení jazyka a skrytých pravidel.

### Tok

```text
Intake
→ ingestion catalog
→ glossary
→ commands/events/actors/systems
→ Big Picture ES
→ observed lifecycles
→ process slices
→ subdomains a candidate BC
→ hotspot a validation backlog
```

### Typický konec

G3. Výstupem nemusí být implementační architektura. Musí být jasné, co je evidence, co hypotéza, co bylo validováno a jaké rozhodnutí je potřeba dál.

### Prompt

> Z dostupných zdrojů vytvoř evidence map, glossary, seed otázky a workshop plan. Nevytvářej finální bounded contexts bez validace. Každý závěr odkaž na source path.

### Anti-patterny

- discovery bez decision ownera,
- syntetické sjednocení rozporů,
- kompletní solution design v časově omezeném discovery,
- workshop sticky notes bez následné kurace a traceability.

## 10. `architecture-review`

### Kdy použít

Existuje konkrétní návrh, repozitář nebo provozovaný systém a cílem je rozhodnutí o riziku, investici, readiness nebo modernizační prioritě.

### Hodnoticí oblasti

Business/domain alignment, quality attributes, boundaries, data ownership, integration, security, resilience, observability, delivery, governance a evolvability.

### Tok

```text
Review scope a criteria
→ evidence inventory
→ domain alignment
→ quality-attribute scenarios
→ architecture/runtime analysis
→ findings
→ risks a options
→ recommendations
→ ADR/action backlog
```

### Finding formát

```text
evidence → symptom → root cause → business/operational impact
→ risk → recommendation → verification step → owner
```

### Prompt

> Každý finding založ na evidence. Rozliš symptom, root cause a dopad. U doporučení uveď varianty, trade-offy, prioritu, ownera a ověřovací krok. EventStorming použij pouze tam, kde je sporný vztah business chování a technických hranic.

### Anti-patterny

- checklist bez business kontextu,
- technologická preference vydávaná za finding,
- doporučení bez ověřovacího kroku,
- kompletní redesign bez migrační priority.

## 11. `operating-model-and-teams`

### Kdy použít

Hlavním problémem je ownership, cognitive load, hand-off fronty, nejasná role platform/enabling týmů nebo nesoulad organizace s tokem změn.

### Vstupy

Candidate domain boundaries, change demand, team cognitive load, incident/release ownership, dependency queues, skills a regulatory responsibilities.

### Tok

```text
Doménové hypotheses
→ change-flow evidence
→ ownership gaps
→ cognitive load
→ team types
→ interaction modes
→ platform product boundaries
→ transition plan
```

### Prompt

> Navrhni stream-aligned ownership podle toku hodnoty a doménových boundaries. Platform team použij jen pro interní platform product. Enabling interaction omez cílem a časem. U COTS/SaaS urč permanentního owning teamu nebo service ownera.

### Anti-patterny

- org chart jako primární context map,
- enabling team jako permanentní delivery dependency,
- platform team vlastnící business backlog všech týmů,
- rozdělení odpovědnosti bez provozního ownershipu.

## 12. `bounded-context-design`

### Entry criteria

BC má validovaný purpose, scope, ubiquitous language, inbound/outbound contracts a ownera. Tento profil není vhodný pro hledání enterprise boundaries od nuly.

### Tok

```text
BC purpose a contracts
→ Design-Level ES
→ commands/policies/read models
→ validated lifecycle
→ aggregates a invariants
→ domain events
→ application ports
→ persistence/integration decisions
→ C4/code projection
→ tests a observability
```

### Prompt

> Pracuj pouze uvnitř BC X. Pro každý command uveď autoritu, invariant, consistency boundary, resulting domain event, projection a externí contract. Označ cross-context synchronní transakce jako hotspot. Navrhni nejjednodušší implementační styl.

### Anti-patterny

- aggregate podle tabulky,
- jeden aggregate pro celý BC,
- domain event jako technický log,
- CQRS/Event Sourcing bez business nebo quality-attribute důvodu,
- persistence model určující ubiquitous language.

## 13. Rozhodovací otázky

1. Mění se primárně business, software, integrace, nebo ownership?
2. Musí běžet současný systém bez přerušení?
3. Je scope jeden produkt, nebo portfolio?
4. Je významná část řešení koupená?
5. Potřebujeme discovery, cílový návrh, review, nebo realizovatelnou migraci?
6. Jaké quality attributes mají architektonickou prioritu?
7. Kdo je decision owner a kdo vlastní výsledná data a provoz?
8. Jaký je nejmenší výstup, který umožní další investiční nebo delivery rozhodnutí?
