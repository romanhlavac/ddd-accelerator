# Metodický tok DDDA a rozhodovací gaty

## Účel

Tok chrání tým před předčasným solutioningem. Každá fáze má jinou otázku, jinou úroveň jistoty a jiný očekávaný artefakt. Fáze lze iterovat; nelze však tiše přeskočit chybějící evidence a vydávat hypotézu za přijatý model.

```text
Align → Discover → Decompose → Strategize → Connect → Organize → Define → Code
   G1       G2          G3            G4          G5         G6        G7      G8
```

## Základní metodické zdroje

DDDA tok zachovává a operacionalizuje základní [DDD Starter Modelling Process – Kicking off a major program of work](https://ddd-crew.github.io/ddd-starter-modelling-process/#kicking-off-a-major-program-of-work). Detailní rozhodovací a workshopové postupy jsou dále vedeny v:

- [DDDA knowledge index](../../knowledge/00-knowledge-index.md);
- [Strategic DDD](../../knowledge/02-ddd-strategic-design.md) a [Tactical DDD](../../knowledge/03-ddd-tactical-design.md);
- [Architecture decision making](../../knowledge/04-architecture-decision-making.md);
- [Quality attributes](../../knowledge/05-quality-attributes.md);
- [Integration and data ownership](../../knowledge/07-integration-and-data-ownership.md);
- [Team Topologies and governance](../../knowledge/10-team-topologies-and-governance.md);
- [DDDA workshopových kuchařkách](../cookbooks/).

Board `01 – DDD Starter journey, gates a iterace` tyto zdroje pouze vizualizuje. Nezavádí alternativní metodiku a nesmí skrýt, odkud jednotlivé praktiky a rozhodovací otázky pocházejí.

## Statusy artefaktů

- `observed` — doložené pozorování ze zdroje nebo workshopu,
- `candidate` — pracovní hypotéza,
- `validated` — potvrzené doménovým expertem,
- `accepted` — přijaté jako rozhodnutí nebo baseline,
- `superseded` — historicky platné, nahrazené,
- `deleted_pending` — tombstone čekající na kontrolované odstranění.

## Align / G1

Business otázka: proč projekt existuje a jaké rozhodnutí má umožnit?

Povinné evidence: business outcomes, stakeholder map, scope/out-of-scope, assumptions, constraints, success metrics, decision owner.

Gate G1 projde pouze tehdy, pokud scope není definován názvem technologie a existuje owner, který může rozhodnout o prioritách.

Prompt:

> Zpracuj intake bez návrhu řešení. Odděl cíle, potřeby uživatelů, regulaci, omezení, metriky a otevřené předpoklady. U každé položky uveď ownera a source path.

## Discover / G2

Business otázka: co se v doméně děje, kdo rozhoduje a kde vzniká hodnota nebo riziko?

Praktiky: Big Picture EventStorming, source inventory, glossary, actor/system map, pozorované lifecycles, hotspoty.

Gate G2 nevyžaduje hotové bounded contexts. Vyžaduje dostatečně sdílený obraz doménového dění a explicitní rozpory.

## Decompose / G3

Otázka: které části modelu mají odlišný jazyk, pravidla, tempo změn nebo lifecycle?

Evidence: process slices, clustery pravidel, kandidátní subdomény, kandidátní BC, candidate lifecycle models, rationale rozkladu.

Anti-pattern: „jeden systém = jeden BC“ nebo „jeden tým = jeden BC“ bez doménového důvodu.

## Strategize / G4

Otázka: kde organizace diferencuje a kam má investovat?

Evidence: core/supporting/generic klasifikace, diferenciace vs. komplexita, build/buy/partner/retire, Wardley mapa tam, kde přináší rozhodovací hodnotu.

## Connect / G5

Otázka: jak spolu bounded contexts komunikují a kdo vlastní data?

Evidence: context map, upstream/downstream, source of truth, published language, ACL, integrační kontrakty, konzistence, latency a failure modes.

## Organize / G6

Otázka: je ownership proveditelný pro reálné týmy?

Evidence: stream-aligned ownership, platform/enabling support, complicated subsystem kandidáti, cognitive load, interaction modes, rozhodovací pravomoci.

## Define / G7

Otázka: je konkrétní BC dostatečně vymezen pro detailní návrh?

Evidence: Bounded Context Canvas, Design-Level EventStorming, validovaný lifecycle, quality attribute scenarios, inbound/outbound contracts.

## Code / G8

Otázka: chrání implementace skutečné invarianty a je provozovatelná?

Evidence: agregáty, invarianty, doménové události, aplikační porty, persistence/integration decisions, C4 pohledy, ADR, testy, observabilita a rollout.

CQRS nebo Event Sourcing vyžadují explicitní business a quality-attribute zdůvodnění.

## Gate review formát

```yaml
gate_review:
  gate: G5
  outcome: conditional
  reviewed_at: 2026-07-22
  evidence:
    - path: artifacts/connect/context-map.yaml
      criterion: context_map
      status: pass
  conditions:
    - owner: data-architecture
      due: 2026-08-05
      action: potvrdit source of truth pro party identity
  approvals:
    business_owner: pending
    architecture_owner: accepted
```

## Iterace a návrat

Návrat do předchozí fáze není selhání. Je to očekávaný důsledek nové evidence. Změna musí zanechat traceability: původní artefakt `superseded`, nový artefakt s odkazem na důvod a ADR nebo gate review.
