# WP-09 — Strategy, portfolio & program lifecycle

## Outcome

DDDA rozšíří project-level DDD Starter workflow o samostatnou strategickou a programovou vrstvu, která propojí purpose, situational awareness, portfolio prioritizaci, modernizační rozhodování, doménovou strategii a socio-technický design bez smíchání s projektovými gatami G1–G8.

## State

```text
State: backlog
Target release: TBD
Depends on: WP-08 release-grade lifecycle and human review contracts
```

## Problem / GAP

Současná platforma podporuje jednotlivý DDD/architecture projekt a jeho journey G1–G8. Chybí ale explicitní model pro:

- program-level lifecycle P0–P10;
- strategické portfolio rozhodování před vznikem jednotlivých projektů;
- Wardley Mapping a situational awareness;
- propojení business outcomes, value chains, capabilities, subdomén a investic;
- prioritizaci build/buy/SaaS/modernize/retire/platformize;
- řízení programu složeného z více DDDA projektů;
- programové dependencies, decisions, risks a benefits;
- návaznost strategy → DDD → architecture → teams → delivery evidence.

Bez této vrstvy hrozí, že project-level discovery bude řešit lokální problém správně, ale nebude existovat evidence, proč byl projekt prioritizován a jak zapadá do širší změny.

## In scope

- program lifecycle P0–P10 jako samostatný kontrakt;
- program intake, purpose, outcomes, stakeholders a decision ownership;
- portfolio capabilities a investment hypotheses;
- Wardley Mapping artifact contract a workshop flow;
- value chain, user needs, visibility a evolution;
- capability/subdomain/BC/application mapping s explicitními hranicemi významu;
- core/supporting/generic classification v kontextu strategie;
- build/buy/SaaS/modernize/retire/platformize decisions;
- portfolio prioritization model a decision evidence;
- program dependencies, sequencing a roadmap slices;
- strategy-to-domain-to-team traceability;
- program risks, assumptions a benefits realization;
- Miro program/portfolio projection;
- Git/YAML authority a audit;
- program status, next decisions a human gates;
- example program a acceptance evidence.

## Out of scope

- nahrazení corporate portfolio management nástroje;
- finanční účetnictví a detailní budget management;
- automatické strategické rozhodování LLM nebo algoritmem;
- automatické schválení investice;
- plný enterprise ingestion — WP-10;
- multi-agent runtime — WP-11;
- změna významu project gates G1–G8;
- taktické DDD modelování uvnitř konkrétního BC jako hlavní scope.

## Boundary with project lifecycle

```text
Program/portfolio layer P0–P10
  rozhoduje proč, kde a v jakém pořadí investovat.

Project layer G1–G8
  vede konkrétní projekt od Align po Code.
```

Program může vytvářet nebo prioritizovat více projektů. Project artifacts se mohou agregovat do programu, ale jejich human gate decisions se nesmí automaticky propagovat jako program approval.

## Proposed delivery slices

1. **P0–P10 lifecycle and program gate contract**
   - stavy, evidence, ownership, transition rules, invalidation;
   - oddělení mechanické evidence a lidského rozhodnutí.
2. **Strategy intake, purpose and value chain**
   - user needs, outcomes, actors, constraints a capability landscape.
3. **Wardley Mapping artifact and workflow**
   - schema, Miro template, evolution model, traceability a validation.
4. **Portfolio prioritization and investment decisions**
   - explicitní kritéria, option comparison, residual risks a decision records.
5. **Strategy-domain-team traceability**
   - capability → subdomain → BC → team → system/investment links.
6. **Program roadmap, dependencies and benefits**
   - sequencing, dependency graph, outcomes a measurement.
7. **Program Miro projection and Control Center**
   - current strategic decision, portfolio view, program status a next actions.
8. **Reference example and acceptance**
   - program modernizace core systému nebo portfolio pojišťovny bez klientských dat.

## Acceptance criteria at WP level

- [ ] P0–P10 lifecycle is explicitly separate from G1–G8;
- [ ] program intake identifies purpose, outcomes, decision owners and constraints;
- [ ] Wardley map starts from user need/value chain and records evolution assumptions;
- [ ] BCs and application components are not treated as primary Wardley objects without explicit rationale;
- [ ] build/buy/SaaS/modernize decisions retain criteria, options and human decision evidence;
- [ ] program can reference multiple DDDA projects without merging their Git repositories;
- [ ] traceability links strategy, capabilities, subdomains, BCs, teams and investment decisions;
- [ ] portfolio scoring is decision support, not automatic approval;
- [ ] program gate `passed` requires human provenance;
- [ ] Miro is projection/workshop surface, not authority for strategic approval;
- [ ] all schemas and reports are package-first validated;
- [ ] example program demonstrates at least two projects and one dependency;
- [ ] docs explain when Wardley Mapping is useful and when it is not;
- [ ] no scope overlap silently implements enterprise ingestion or multi-agent runtime.

## Quality attributes

- strategic traceability;
- auditability;
- decision transparency;
- usability for executives, architects and product leadership;
- modifiability of program model;
- interoperability with G1–G8 projects;
- human control;
- low ceremony for smaller programs.

## Risks

| Risk | Impact | Mitigation |
|---|---:|---|
| P0–P10 duplicates G1–G8 | High | explicit boundary and separate schemas |
| Wardley Mapping becomes decorative | High | user need/value chain/evolution invariants and acceptance |
| Scoring automates strategy | High | decision support only, human record required |
| Global enterprise model suppresses BC language | High | context-specific traceability, no single canonical domain model |
| Program layer becomes heavyweight PPM | Medium | minimal required contract and tailoring |
| Scope expands into ingestion/agents | High | explicit dependencies on WP-10/WP-11 and scope gates |

## Dependencies

- WP-08 exact-SHA validation, packaging, Human Review and promotion lifecycle;
- WP-10 for richer evidence sources, but initial synthetic/manual inputs are sufficient;
- WP-11 optional for assisted analysis, never for autonomous approval.

## Exit criteria

- all agreed delivery slices are complete or explicitly deferred with accepted scope;
- parent and child issues have PASS acceptance evidence;
- program example is generated from release package;
- strategic and project lifecycles interoperate without state collision;
- one end-to-end program decision is human-reviewed and auditably recorded;
- roadmap and release documentation are updated.
