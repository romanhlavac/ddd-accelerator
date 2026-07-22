# Typy projektů, aliasy, toky a gaty

DDDA používá kanonické typy projektů. Staré nebo týmové názvy se zachovávají v `type_alias`, ale automatizace a schémata pracují s kanonickým `project.type`.

## 1. Portfolio program

**Kanonický typ:** `portfolio-program`  
**Aliasy:** `enterprise-transformation`, `transformation-program`

Použij pro transformaci, která zahrnuje více produktů, domén, systémů nebo týmů a vyžaduje společnou strategii, capability mapu a řízení závislostí.

Typický tok:

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

## 2. Greenfield produkt

**Kanonický typ:** `greenfield-product`  
**Aliasy:** `greenfield`, `new-product`

Použij pro nový produkt nebo službu bez dominantního legacy omezení. Greenfield neznamená bez constraints; stále existují enterprise platformy, regulace, provozní schopnosti a build/buy rozhodnutí.

Tok:

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

## 3. Legacy modernizace

**Kanonický typ:** `legacy-modernization`  
**Aliasy:** `modernization`, `legacy-transformation`, `brownfield`

Použij pro inkrementální změnu existujícího systému, rozdělení monolitu, náhradu COTS nebo odstranění vendor lock-in.

Tok:

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

## 4. Domain discovery

**Kanonický typ:** `domain-discovery`  
**Aliasy:** `discovery`, `strategic-ddd`

Použij pro časově omezené poznání domény, přípravu workshopu, vytěžení jazyka, procesů, pravidel a kandidátních hranic.

Tok:

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
- D4: BC návrhy jsou validovány nebo explicitně označeny jako kandidátní.

## 5. Architecture review

**Kanonický typ:** `architecture-review`  
**Aliasy:** `review`, `architecture-assessment`

Použij pro nezávislé nebo interní posouzení existující architektury.

Tok:

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

## 6. Bounded context design

**Kanonický typ:** `bounded-context-design`  
**Aliasy:** `tactical-ddd`, `bc-design`

Použij pro detailní návrh jednoho bounded contextu, nikoli pro hledání enterprise hranic od nuly.

Tok:

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

Zvol nejmenší typ, který pokryje rozhodovací problém. Portfolio program není automaticky vhodný jen proto, že je projekt velký. `bounded-context-design` nepoužívej, pokud ještě není jasné, kde BC začíná a končí. `domain-discovery` nemusí končit implementační architekturou; jeho výsledkem může být validační backlog.

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

Doplňkový tok nemění kanonický typ projektu. Rozšiřuje jeho konkrétní workflow a gaty.