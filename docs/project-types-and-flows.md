# Typy projektů, aliasy, toky a gaty

DDDA používá kanonické typy projektů. Staré nebo týmové názvy se zachovávají v `project.type_alias`, ale automatizace a schémata pracují s kanonickým `project.type`.

## 1. Portfolio program

**Kanonický typ:** `portfolio-program`  
**Aliasy:** `enterprise-transformation`, `transformation-program`, `greenfield-portfolio`, `new-enterprise`, `program-greenfield`

Použijte pro transformaci, která zahrnuje více produktů, domén, systémů nebo týmů a vyžaduje společnou strategii, capability mapu a řízení závislostí.

```text
Strategický záměr
→ stakeholder a capability landscape
→ portfolio domains/subdomains
→ kandidátní bounded contexts
→ ownership a Team Topologies
→ programová context map
→ architektonické guardrails
→ transformační roadmapa
→ inkrementální delivery streams
```

Gaty:

- P1: potvrzené business outcomes a scope programu,
- P2: potvrzené core/supporting/generic oblasti,
- P3: přijatelná portfolio context map a data ownership,
- P4: přiřazené týmy a rozhodovací pravomoci,
- P5: prioritizované inkrementy a decommission cíle.

## 2. Greenfield product

**Kanonický typ:** `greenfield-product`  
**Aliasy:** `greenfield`, `new-product`

```text
Product vision
→ user needs a outcomes
→ Big Picture EventStorming
→ subdomény a bounded contexts
→ quality attributes
→ první end-to-end slice
→ Design-Level EventStorming
→ tactical design
→ solution architecture
→ validace a delivery
```

Gaty:

- G1: ověřená potřeba a value proposition,
- G2: validovaný problémový prostor,
- G3: kandidátní hranice a ownership,
- G4: měřitelné quality attribute scenarios,
- G5: schválený první slice bez předčasné distribuované komplexity,
- G6: implementační návrh chrání invarianty a provozní cíle.

## 3. Legacy modernization

**Kanonický typ:** `legacy-modernization`  
**Aliasy:** `modernization`, `brownfield`

```text
Business pain a změnové cíle
→ capability a legacy landscape
→ charakterizační evidence
→ EventStorming a skrytá pravidla
→ cílové bounded contexts
→ migrační seams a ACL
→ strangler slices / parallel run
→ data ownership migration
→ decommission
```

Gaty:

- M1: měřitelný modernizační outcome, nikoli pouze technologický rewrite,
- M2: identifikovaná skrytá pravidla a kritické integrace,
- M3: definované target boundaries a transition architecture,
- M4: ověřený první slice a rollback,
- M5: reconciliation a provozní observabilita,
- M6: splněná decommission kritéria.

## 4. Legacy transformation

**Kanonický typ:** `legacy-transformation`  
**Aliasy:** `core-replacement`, `business-transformation`

Použijte, pokud se zároveň mění business model, produkty, procesy, organizace a core IT.

```text
Transformation outcomes
→ as-is business a technology evidence
→ target capabilities a policies
→ target bounded contexts a ownership
→ transition contexts a ACL
→ sourcing a vendor strategy
→ program increments a parallel run
→ operating-model transition
→ decommission a knowledge retention
```

Gaty:

- T1: business a IT outcomes jsou společně měřitelné,
- T2: kritická pravidla a znalostní rizika mají vlastníky,
- T3: target i transition architecture mají explicitní data ownership,
- T4: sourcing neobnovuje vendor lock-in,
- T5: první inkrement má rollback, reconciliation a provozní model,
- T6: decommission a převzetí know-how mají akceptační kritéria.

## 5. Integration landscape

**Kanonický typ:** `integration-landscape`  
**Aliasy:** `integration-review`, `api-program`

```text
Integrační problém a business dopad
→ systémy, aktéři a system-of-record
→ kritické end-to-end scénáře
→ context map a upstream/downstream
→ data ownership
→ kontrakty, SLA a konzistence
→ ACL a migrační plán
→ observabilita a governance
```

Gaty:

- I1: kritické business scénáře a data jsou známé,
- I2: každý klíčový datový objekt má vlastníka a system-of-record,
- I3: kontrakty mají verzi, kompatibilitu a provozní cíle,
- I4: coupling a failure modes jsou přijatelné,
- I5: migrace má koexistenci a decommission plán.

## 6. Purchased product adoption

**Kanonický typ:** `purchased-product-adoption`  
**Aliasy:** `cots`, `saas-adoption`, `package-implementation`

```text
Capability a sourcing cíl
→ business model a vendor model
→ fit-gap pravidel a lifecycle
→ data ownership a exportabilita
→ konfigurační a integrační hranice
→ ACL / extension strategy
→ provozní a exit scénáře
→ přijetí nebo odmítnutí produktu
```

Gaty:

- C1: capability a diferenciace ospravedlňují build/buy rozhodnutí,
- C2: fit-gap odděluje konfiguraci, rozšíření a nepřijatelnou mezeru,
- C3: data ownership, export a exit jsou smluvně i technicky možné,
- C4: vendor model nekolonizuje vlastní core domain,
- C5: provoz, bezpečnost, SLA a kontinuita jsou přijatelné.

## 7. Domain discovery

**Kanonický typ:** `domain-discovery`  
**Aliasy:** `discovery`, `strategic-ddd`

```text
Intake
→ ingestion scan
→ glossary
→ commands / decisions / events
→ actors / systems
→ lifecycle a hotspoty
→ subdomény
→ kandidátní bounded contexts
→ validační workshop
```

Gaty:

- D1: zdroje a scope jsou dohledatelné,
- D2: fakta jsou oddělena od hypotéz,
- D3: klíčové hotspoty mají vlastníky otázek,
- D4: BC návrhy jsou validovány nebo označeny jako kandidátní.

## 8. Architecture review

**Kanonický typ:** `architecture-review`  
**Aliasy:** `review`, `architecture-assessment`

```text
Review scope
→ evidence a constraints
→ business/domain alignment
→ quality attributes
→ boundaries a data ownership
→ integration/security/operations
→ risks and findings
→ recommendations
→ ADR backlog a akční plán
```

Gaty:

- R1: dohodnutá hodnoticí kritéria,
- R2: evidence je dostatečná pro závěr,
- R3: findings oddělují symptom, root cause a dopad,
- R4: doporučení mají prioritu, vlastníka a validační krok.

## 9. Operating model and teams

**Kanonický typ:** `operating-model-and-teams`  
**Aliasy:** `team-topologies`, `org-design`

```text
Business flow a současné fronty
→ doménové hranice a změnové tempo
→ současný ownership a cognitive load
→ stream-aligned ownership
→ platform/enabling/complicated-subsystem potřeby
→ interaction modes
→ governance a evoluční změna týmů
```

Gaty:

- O1: problémy týmového toku jsou podložené evidence,
- O2: navržené týmy mají udržitelný scope a kognitivní zátěž,
- O3: platformní a enabling role mají explicitní zákazníky a outcomes,
- O4: interaction modes jsou časově omezené a měřitelné,
- O5: organizační změna respektuje doménové a datové vlastnictví.

## 10. Bounded context design

**Kanonický typ:** `bounded-context-design`  
**Aliasy:** `tactical-ddd`, `bc-design`

```text
BC purpose a published contracts
→ Design-Level EventStorming
→ commands / policies / read models
→ lifecycle
→ aggregates a invariants
→ domain events
→ application ports
→ persistence a integration decisions
→ component/code projection
```

Gaty:

- B1: scope a ubiquitous language BC jsou stabilní,
- B2: lifecycle a business decisions jsou validované,
- B3: agregáty chrání skutečné invarianty,
- B4: integrační eventy nejsou zaměněny za interní technické události,
- B5: architektura je testovatelná, provozovatelná a evolučně přiměřená.

## Volba typu

Zvolte nejmenší typ, který pokryje rozhodovací problém. `portfolio-program` není automaticky vhodný jen proto, že je iniciativa velká. `bounded-context-design` nepoužívejte, pokud ještě není jasné, kde BC začíná a končí. `domain-discovery` nemusí končit implementační architekturou.

## Doplňkové toky

Projekt může aktivovat doplňkové toky nezávisle na typu:

- Wardley Mapping,
- Team Topologies,
- Quality Attribute Workshop,
- threat modeling,
- data ownership a integration design,
- solution architecture,
- migration planning,
- architecture decision records.

Doplňkový tok se ukládá do `workflow.extensions` a nemění kanonický typ projektu.
