# Typy projektů a workflow profily

Typ projektu nastavuje výchozí metodický tok, povinné gates, očekávané vstupy a typická rizika. Nejde o pevnou škatulku; profil lze upravit, ale odchylka musí být explicitní v `project.yaml`.

## Přehled

| Kanonický typ | Legacy aliases | Použití | Důraz |
|---|---|---|---|
| `greenfield-product` | new-product, green-field, startup | nový produkt nebo systém s jedním dominantním product scopem | discovery, diferenciace, rychlá validace hranic |
| `greenfield-portfolio` | new-enterprise, program-greenfield | více produktů/domén v programu nebo nové společnosti | domain portfolio, context map, team topology, governance |
| `legacy-modernization` | brownfield, strangler, replatforming | postupná náhrada nebo rozdělení existujícího systému | as-is discovery, seams, data ownership, migrační inkrementy |
| `legacy-transformation` | core-replacement, business-transformation | souběžná změna business capability, operating modelu a core IT | cílové capability, přechodné stavy, governance, sourcing |
| `integration-landscape` | integration-review, api-program | primárně vztahy mezi systémy a kontexty | ownership, kontrakty, coupling, ACL |
| `purchased-product-adoption` | COTS, SaaS-adoption, package-implementation | bounded context je zčásti nebo zcela realizován koupeným produktem | fit-gap, konfigurační hranice, vendor model, anti-corruption layer |
| `architecture-review` | assessment, health-check | zhodnocení existujícího návrhu nebo implementace | quality attributes, rizika, evidence, ADR |
| `domain-discovery` | discovery-only, domain-analysis | časově omezené pochopení domény bez závazku implementace | jazyk, události, pravidla, subdomény, otázky |
| `operating-model-and-teams` | team-topologies, org-design | změna ownershipu a týmového uspořádání | sociotechnické hranice, cognitive load, interaction modes |

## 1. Greenfield product

**Kdy použít:** nový digitální produkt, samostatná business capability nebo nový bounded product scope.

Povinné fáze: Align, Discover, Process Modeling, Decompose, Strategize, Connect, Define. Organize je povinné před škálováním více týmů.

Typická rizika:

- předčasné mapování bounded context = mikroservisa,
- product vision bez doménových expertů,
- univerzální model pro všechny budoucí varianty,
- CQRS/Event Sourcing jako výchozí technická preference.

## 2. Greenfield portfolio

**Kdy použít:** nová pojišťovna, banka, marketplace nebo transformační program s více produkty a týmy.

Navíc vyžaduje:

- portfolio subdomén,
- schopnosti a value streams,
- strategickou klasifikaci,
- context map na více úrovních,
- team topology a governance,
- pravidla sdílených platforem a generic capabilities.

## 3. Legacy modernization

**Kdy použít:** stávající systém brání změnám, ale business scope zůstává převážně stabilní.

Povinné doplňky:

- mapa současných datových vlastníků a faktických system-of-record,
- runtime a change coupling,
- business kritičnost a provozní omezení,
- seams a migrační slices,
- přechodné integrační kontrakty,
- observabilita a rollback.

Big Picture ES zachycuje business realitu; technický tok legacy systému se dokumentuje odděleně, aby nekolonizoval cílový model.

## 4. Legacy transformation

**Kdy použít:** zároveň se mění produkty, procesy, regulace, organizace i core systém.

Vyžaduje paralelní modelování:

- as-is business reality,
- target business capabilities a policies,
- přechodných stavů,
- změn ownershipu a operating modelu,
- dočasných bounded contexts a anti-corruption vrstev.

## 5. Integration landscape

**Kdy použít:** hlavním problémem je nejasné vlastnictví dat, point-to-point integrace, konfliktní API nebo eventy.

Process Modeling může být omezeno na integračně kritické scénáře. Povinné jsou Connect a quality attribute scénáře pro dostupnost, konzistenci, latenci a recoverability.

## 6. Purchased product adoption

**Kdy použít:** capability je realizována SaaS nebo COTS produktem.

DDD modelování má smysl pro:

- vymezení business odpovědnosti bounded contextu,
- pojmenování interního a vendor jazyka,
- fit-gap analýzu pravidel a lifecycle,
- data ownership,
- integrační a konfigurační hranice,
- rozhodnutí, co chránit anti-corruption layerem.

Taktické DDD uvnitř vendor produktu se nemodeluje bez přístupu a business důvodu. Modeluje se vlastní odpovědnost, adaptace a kontrakty.

## 7. Architecture review

**Kdy použít:** existuje konkrétní návrh, repozitář nebo provozovaný systém a cílem je rozhodnutí o riziku či investici.

Workflow začíná Align a evidence inventory. EventStorming se používá pouze tam, kde je nutné ověřit, zda technické hranice odpovídají business chování.

Výstupem je review report, prioritizovaná rizika, varianty, ADR a evoluční plán; nikoli automaticky kompletní nový model.

## 8. Domain discovery

**Kdy použít:** potřebujeme ohraničený discovery sprint nebo přípravu workshopu.

Výchozí konec je G3. Další fáze jsou doporučením, ne součástí scope.

## 9. Operating model and teams

**Kdy použít:** hlavním problémem je ownership, fronty mezi týmy, kognitivní zátěž nebo nejasná role platform/enabling týmů.

Doménové hranice musí existovat alespoň jako pracovní hypotézy. Organizační diagram nesmí být použit jako primární zdroj bounded contexts.

## Volba typu

Položte postupně otázky:

1. Mění se především business model, software, integrace, nebo ownership týmů?
2. Existuje provozovaný systém a musí být zachován kontinuální provoz?
3. Je scope jeden produkt, nebo portfolio capability?
4. Je významná část řešení koupená?
5. Potřebujeme discovery, rozhodnutí, cílový návrh, nebo realizovatelnou migraci?

Pokud odpovědi ukazují na více profilů, zvolte dominantní typ a přidejte `workflow.extensions`, například:

```yaml
project_type: legacy-transformation
workflow:
  profile: legacy-transformation
  extensions:
    - purchased-product-adoption
    - operating-model-and-teams
```
