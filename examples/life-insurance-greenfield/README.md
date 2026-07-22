# Referenční projekt — greenfield životní pojišťovna

Tento example ukazuje typický `portfolio-program` s aliasem `greenfield-portfolio`. Cílem není dodat jediný „správný“ model pojišťovny, ale předvést opakovatelný způsob práce: ingestion → chatové zpracování → Miro workshop → spravované YAML → gate review → context map → týmový ownership → detail prvního bounded contextu → architektura.

## 0. Výchozí business situace

Nová životní pojišťovna má uvést první individuální rizikový produkt. První inkrement zahrnuje digitální distribuci, underwriting, vznik smlouvy, inkaso, základní servicing, claim intake a regulatorní/finanční integrace. Group life a investiční produkty jsou mimo první inkrement.

Prioritní quality attributes:

- auditability a explainability underwriting rozhodnutí,
- ochrana osobních a zdravotních dat,
- modifiability produktových pravidel,
- dostupnost digitálního prodeje,
- recoverability platebních a issuance procesů.

## 1. Vytvoření projektu

Z parent adresáře workspace:

```powershell
$WorkspaceRoot = (Resolve-Path .\DDDA-Workspace).Path
$PlatformRoot = (Resolve-Path .\DDDA-Workspace\platform\ddd-accelerator).Path

& (Join-Path $PlatformRoot 'scripts\New-DDDAProject.ps1') `
  -WorkspaceRoot $WorkspaceRoot `
  -ProjectId life-insurance-greenfield `
  -Name 'Nová životní pojišťovna' `
  -Type portfolio-program `
  -TypeAlias greenfield-portfolio

$ProjectRoot = Join-Path $WorkspaceRoot 'projects\life-insurance-greenfield'
```

## 2. První chat — potvrzení scope

Prompt:

> Scope: project. Aktivní projekt: `life-insurance-greenfield`. Načti `project.yaml` a metodiku pro `portfolio-program`. Shrň business problém, předpoklady, in/out scope, aktéry, regulatorní omezení, quality attributes a rozhodnutí, která musí program učinit. Nevytvářej bounded contexts ani technologie. Navrhni seznam chybějících vstupů a interview plán.

Očekávaný výstup:

- seznam stakeholderů: sponsor, product, underwriting, claims, operations, finance, compliance, data protection, distribution, architecture,
- seznam rozhodnutí: product scope, underwriting authority, policy lifecycle, payment ownership, party identity ownership, claims boundary, build/buy,
- ingestion backlog.

## 3. Ingestion

Do `ingestion/` vlož:

- product vision a business case,
- regulatorní a privacy požadavky,
- draft produktu a pojistných podmínek,
- underwriting guidelines,
- target journeys,
- finance/accounting constraints,
- enterprise platform constraints,
- interview notes.

Aktualizuj `ingestion/catalog.yaml`:

```yaml
sources:
  - id: product-vision-v1
    path: ingestion/product-vision.md
    type: business_vision
    owner: chief-product-officer
    observed_at: 2026-07-22
    trust: authoritative
    sensitivity: internal
  - id: underwriting-interview-01
    path: ingestion/interviews/underwriting-01.md
    type: interview
    owner: chief-underwriter
    observed_at: 2026-07-24
    trust: elicited
    sensitivity: confidential
```

Prompt:

> Analyzuj pouze ingestion katalog a dostupné soubory. U každého tvrzení uveď source ID. Rozděl fakta, policy statements, hypotézy, rozpory a otázky. Vytvoř glossary seed a interview gaps. Neopravuj terminologii obecným pojišťovacím know-how bez označení inference.

## 4. Align frame v Miru

Miro změny:

- `10 – Align / Intake`: project charter, business outcomes, stakeholders, scope, assumptions, success metrics,
- control center: status projektu, upcoming workshops, open decisions,
- G1 checklist.

Prompt:

> Připrav candidate YAML pro project charter a assumptions. Proveď push dry-run do frame `align-intake`. Ukaž, které sticky notes budou vytvořeny a které položky zůstanou unmanaged workshop notes.

G1 projde, když sponsor a architecture owner potvrdí scope, rozhodnutí a měřitelné outcomes.

## 5. Instalace a render Miro boardu

```powershell
$env:MIRO_ACCESS_TOKEN = '<token>'
$env:LIFE_INSURANCE_GREENFIELD_MIRO_BOARD_ID = '<board-id>'

& (Join-Path $PlatformRoot 'scripts\Install-DDDAMiroRuntime.ps1')
& (Join-Path $PlatformRoot 'scripts\Test-DDDAMiroConfiguration.ps1') `
  -ProjectPath $ProjectRoot -Online
& (Join-Path $PlatformRoot 'scripts\Initialize-DDDAMiroBoard.ps1') `
  -ProjectPath $ProjectRoot -DryRun
& (Join-Path $PlatformRoot 'scripts\Initialize-DDDAMiroBoard.ps1') `
  -ProjectPath $ProjectRoot
```

Miro nyní obsahuje kompletní metodický spine a pracovní frames.

## 6. Big Picture EventStorming

Workshop scope: od prvního kontaktu klienta po active policy, první servicing a claim notification.

Seed otázky:

- Co se musí stát před vytvořením application?
- Kdy vzniká underwriting case?
- Co znamená „offer prepared“, „accepted“, „policy issued“ a „in force“?
- Kdy je nutná první platba?
- Kdy lze policy zrušit, změnit nebo obnovit?
- Co se děje při claim notification?

Facilitační tok:

1. účastníci zapisují business events,
2. události se seřadí v čase,
3. doplní se temporal events a pivoty,
4. označí se actors a external systems,
5. hotspoty: medical evidence, sanctions, payment failure, backdating, cancellation, claim fraud,
6. vyberou se slices pro detail.

Po workshopu:

> Proveď pull dry-run. Importuj pouze položky s DDDA markerem nebo explicitně schválené k promotion. Vytvoř domain-event YAML s source workshop ID. Hotspoty ponech jako candidate s ownerem otázky. Připrav Git diff, necommituj.

Příklad spravovaného eventu je v `artifacts/discover/events/policy-issued.yaml`.

## 7. Glossary a observed lifecycle

V `discover-evidence` frame tým sjednocuje rozdíl mezi:

- application,
- proposal/offer,
- policy,
- coverage,
- underwriting case,
- premium obligation,
- claim.

Prompt:

> Z validovaných events odvoď observed lifecycle pro Application, Underwriting Case, Offer, Policy a Claim. Nezaměň milestone za state. U každého stavu uveď vstupní event, opuštění stavu a source.

## 8. Process Modeling vybraných slices

Vyber minimálně:

1. application → underwriting decision,
2. accepted offer → policy issuance,
3. premium due → payment allocation,
4. claim notification → claim registration.

Prompt:

> Pro slice `accepted offer → policy issuance` vytvoř Actor → Command → Policy → Event → Read Model model. Zahrň rejected/timeout branches, authority, idempotency a externí dependencies. Neurčuj zatím agregáty.

Miro změny: procesní rows, commands, policies, read models, exceptions a hotspoty ve frame `discover-process-modeling`.

## 9. Decomposition

Chat analyzuje clustery jazyka, lifecycle, pravidel, change cadence a ownershipu.

Prompt:

> Navrhni candidate subdomains a bounded contexts. Pro každý uveď purpose, language, key decisions, lifecycle, data owned, inbound/outbound dependencies a rationale. Rozliš business capability, subdomain, BC, system a team. Nevytvářej 1:1 mapping BC = microservice.

Typické candidate oblasti:

- Product Definition,
- Distribution Journey,
- Application Intake,
- Underwriting,
- Policy Administration,
- Billing & Collections,
- Claims,
- Party & Consent,
- Document/Communication,
- Finance Integration,
- Regulatory Reporting,
- Fraud/Risk Analytics.

G3 projde, když jsou hypotézy validovatelné a hotspoty mají owners.

## 10. Strategická klasifikace

Prompt:

> Klasifikuj subdomény core/supporting/generic podle diferenciace a business komplexity. U každé navrhni build/buy/partner/retire a zdůvodni, co musí pojišťovna vlastnit jako knowledge. Nezaměň core s kritičností.

Miro změny: matrix core/supporting/generic, differentiation vs complexity a sourcing decisions.

Příklad očekávaného výsledku:

- Underwriting/Product capabilities jako core nebo differentiating,
- document generation a notifications často generic/supporting,
- finance ledger integration supporting s vysokou compliance kritičností.

## 11. Context Map a data ownership

Prompt:

> Vytvoř programovou context map. Pro každý relationship uveď upstream/downstream, pattern, owned data, contract, latency, consistency a failure mode. Zvlášť řeš Party identity, Policy, Payment a Claim identifiers.

Miro změny:

- bounded context map,
- source-of-truth overlay,
- upstream/downstream arrows,
- ACL u vendor/external systems,
- integrační hotspoty.

Příklad `artifacts/connect/context-map.yaml` ukazuje minimální vztahy.

## 12. Team Topologies

Prompt:

> Navrhni stream-aligned ownership podle toku hodnoty a cognitive load. Platform team použij pouze pro interní platform product. Enabling team použij časově omezeně pro capability uplift. U COTS/SaaS urč owning stream-aligned team nebo service ownera a vendor management responsibility.

Výstup:

- stream-aligned týmy pro acquisition/underwriting, policy servicing, billing, claims,
- platform capabilities pro identity, delivery platform, observability nebo data platform jen s jasným product modelem,
- enabling support pro DDD, security nebo test automation.

## 13. Bounded Context Canvas

Vyber první detailní BC, například `Policy Administration`.

Prompt:

> Připrav Bounded Context Canvas pro Policy Administration. Uveď purpose, strategic role, ubiquitous language, business decisions, lifecycle, inbound/outbound contracts, assumptions, metrics a open questions. Všechny vazby musí odkazovat na context map.

## 14. Design-Level EventStorming

Scope: accepted offer → policy issuance → activation → cancellation/change.

Prompt:

> Pro Policy Administration vytvoř Design-Level ES. Navrhni commands, aggregate candidates, invariants, domain events, policies a projections. Vyznač cross-context dependencies a zakaž synchronní transakci přes BC. Každý invariant odkaž na business rule source.

## 15. Validovaný lifecycle

Prompt:

> Vytvoř validovaný Policy lifecycle a transition table. Zahrň Draft, PendingIssue, Issued, InForce, Suspended, Lapsed, Cancelled, Terminated pouze tam, kde je doložen význam. U přechodů uveď authorization, guards, event, timeout a compensation.

Miro změny: frame `define-lifecycle`, forbidden transitions a acceptance tests.

## 16. Quality Attribute Workshop

Scénáře:

- audit underwriting decision po 10 letech,
- obnova po dvojím payment callbacku,
- dostupnost quote/application journey,
- ochrana medical evidence,
- změna product rule bez plošného regresního rizika.

Prompt:

> Přepiš quality attributes do měřitelných scénářů stimulus → environment → artifact → response → measure. Ukaž architektonické trade-offy a potřebná ADR.

## 17. Tactical design a architektura

Prompt:

> Navrhni nejjednodušší implementační styl pro první slice. Začni modulárním monolitem nebo explicitně zdůvodni distribuci. Agregáty navrhni pouze pro skutečné invarianty. CQRS/Event Sourcing nepoužívej bez auditního, temporal nebo scale důvodu.

Výstup:

- aggregates a value objects,
- application ports,
- domain/integration events,
- persistence decisions,
- C4 context/container/component,
- ADR backlog,
- observability a rollout.

## 18. Synchronizace po každém workshopu

```powershell
& (Join-Path $PlatformRoot 'scripts\Invoke-DDDAMiroSync.ps1') `
  -ProjectPath $ProjectRoot -Direction Pull -DryRun

& (Join-Path $PlatformRoot 'scripts\Invoke-DDDAMiroSync.ps1') `
  -ProjectPath $ProjectRoot -Direction Both
```

Prompt:

> Po syncu rozděl změny na evidence, candidate model, accepted decision, layout-only a conflict. Připrav projektový PR se souhrnem business dopadu. Nezahrnuj tokeny ani platformní změny.

## 19. Gate a program roadmap

Po G5/G6 vytvoř portfolio slices:

1. quote/application skeleton,
2. underwriting happy path,
3. issuance + first premium,
4. policy servicing,
5. claim intake,
6. reconciliation, audit a regulatory readiness.

Každý slice má business outcome, owned data, integration contracts, quality scenarios, rollback a decommission/transition dopad.

## 20. Co tento example záměrně neurčuje

- konkrétní cloud, vendor nebo policy administration package,
- počet mikroservis,
- definitivní regulatorní interpretaci,
- detail zdravotního underwriting modelu,
- účetní chart of accounts.

Tyto body vyžadují projektovou evidence a explicitní rozhodnutí.
