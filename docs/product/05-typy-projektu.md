# Typy projektů a workflow profily

Typ projektu nastavuje výchozí metodický tok, povinné gates, očekávané vstupy a typická rizika. Nejde o pevnou škatulku; profil lze rozšířit, ale odchylka musí být explicitní v `project.yaml`.

Kanonický typ se ukládá do `project.type`. Starší nebo lokální označení lze uchovat v `project.type_alias`.

## Přehled kanonických typů

| Kanonický typ | Typické aliasy | Použití | Důraz |
|---|---|---|---|
| `portfolio-program` | greenfield-portfolio, enterprise-transformation, transformation-program | více produktů, domén, systémů nebo týmů v jednom programu | portfolio domén, context map, Team Topologies, governance |
| `greenfield-product` | greenfield, new-product | nový produkt nebo systém s jedním dominantním product scopem | discovery, diferenciace, první end-to-end slice |
| `legacy-modernization` | modernization, brownfield | inkrementální změna stávajícího systému | as-is evidence, seams, data ownership, migrace |
| `legacy-transformation` | core-replacement, business-transformation | souběžná změna business capability, operating modelu a core IT | cílové capability, přechodné stavy, governance |
| `integration-landscape` | integration-review, api-program | nejasné vlastnictví dat a integrační vztahy | ownership, kontrakty, coupling, ACL |
| `purchased-product-adoption` | cots, saas-adoption, package-implementation | capability realizovaná koupeným produktem nebo SaaS | fit-gap, vendor model, konfigurační hranice, ACL |
| `architecture-review` | review, architecture-assessment | zhodnocení existujícího návrhu nebo implementace | quality attributes, rizika, evidence, ADR |
| `domain-discovery` | discovery, strategic-ddd | časově omezené pochopení domény | jazyk, události, pravidla, subdomény, otázky |
| `operating-model-and-teams` | team-topologies, org-design | změna ownershipu a týmového uspořádání | sociotechnické hranice, cognitive load, interaction modes |
| `bounded-context-design` | tactical-ddd, bc-design | detailní návrh již vymezeného bounded contextu | behaviorální model, agregáty, invarianty, kontrakty |

## 1. Portfolio program

Použijte pro novou společnost, velký transformační program nebo portfolio capability s více produkty a týmy.

Vyžaduje zejména:

- portfolio domén a subdomén,
- capability a value-stream pohled,
- strategickou klasifikaci,
- context map na více úrovních,
- týmový ownership a governance,
- pravidla sdílených platforem a generic capabilities.

`greenfield-portfolio` je zachovaný alias; kanonický typ je `portfolio-program`.

## 2. Greenfield product

Použijte pro nový digitální produkt, samostatnou business capability nebo nový bounded product scope.

Typická rizika:

- předčasné mapování bounded context = mikroservisa,
- product vision bez doménových expertů,
- univerzální model pro všechny budoucí varianty,
- CQRS nebo Event Sourcing jako výchozí technická preference.

## 3. Legacy modernization

Použijte, když stávající systém brání změnám, ale business scope zůstává převážně stabilní.

Povinné doplňky:

- skuteční vlastníci dat a faktické system-of-record,
- runtime a change coupling,
- business kritičnost a provozní omezení,
- seams a migrační slices,
- přechodné integrační kontrakty,
- observabilita, rollback a reconciliation.

Big Picture EventStorming zachycuje business realitu; technický tok legacy systému se dokumentuje odděleně, aby nekolonizoval cílový model.

## 4. Legacy transformation

Použijte, pokud se současně mění produkty, procesy, regulace, organizace i core systém.

Modelujte paralelně:

- as-is business realitu,
- target business capabilities a policies,
- přechodné stavy,
- změny ownershipu a operating modelu,
- dočasné bounded contexts a anti-corruption vrstvy.

## 5. Integration landscape

Použijte, pokud je hlavním problémem nejasné vlastnictví dat, point-to-point integrace, konfliktní API nebo eventy.

Povinné jsou Connect a quality attribute scénáře pro dostupnost, konzistenci, latenci a recoverability. Process Modeling lze omezit na integračně kritické scénáře.

## 6. Purchased product adoption

Použijte, pokud capability realizuje SaaS nebo COTS produkt.

DDD modelování má smysl pro:

- vymezení business odpovědnosti bounded contextu,
- rozlišení interního a vendor jazyka,
- fit-gap pravidel a lifecycle,
- data ownership,
- integrační a konfigurační hranice,
- rozhodnutí, co chránit anti-corruption layerem.

Taktické DDD uvnitř vendor produktu se nemodeluje bez přístupu a business důvodu. Modeluje se vlastní odpovědnost, adaptace a kontrakty.

## 7. Architecture review

Použijte, pokud existuje konkrétní návrh, repozitář nebo provozovaný systém a cílem je rozhodnutí o riziku či investici.

Výstupem je review report, prioritizovaná rizika, varianty, ADR a evoluční plán; nikoliv automaticky kompletní nový model.

## 8. Domain discovery

Použijte pro ohraničený discovery sprint nebo přípravu workshopů. Výchozí konec je G3; další fáze jsou doporučením, ne automatickou součástí scope.

## 9. Operating model and teams

Použijte, pokud je hlavním problémem ownership, fronty mezi týmy, kognitivní zátěž nebo nejasná role platformních a enabling týmů.

Doménové hranice musí existovat alespoň jako pracovní hypotézy. Organizační diagram nesmí být primárním zdrojem bounded contexts.

## 10. Bounded context design

Použijte pro detailní návrh jednoho již vymezeného bounded contextu.

Typický tok:

```text
BC purpose a published contracts
→ Design-Level EventStorming
→ commands, policies a read models
→ lifecycle
→ aggregates a invariants
→ domain events
→ application ports
→ persistence a integration decisions
→ component/code projection
```

Tento typ není vhodný, pokud ještě není jasné, kde bounded context začíná a končí.

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

Doplňkový tok se eviduje v `workflow.extensions`; nemění kanonický typ projektu.

## Příklad manifestu

```yaml
project:
  id: life-insurance-greenfield
  name: "Nová životní pojišťovna"
  type: portfolio-program
  type_alias: greenfield-portfolio
  schema_version: 1
  language: cs
  status: active
workflow:
  profile: portfolio-program
  current_stage: discover
  completed_gates:
    - G1
  extensions:
    - purchased-product-adoption
```

Podrobné toky a gaty jsou v `docs/project-types-and-flows.md`.
