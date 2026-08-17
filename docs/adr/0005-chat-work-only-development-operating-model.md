# ADR: Oddělit Chat/Work vývoj platformy od Cursor project runtime

Status: Accepted

Date: 2026-08-03

## Context

DDDA má dvě sociotechnicky odlišné roviny:

1. **vývoj DDDA platformy** jako verzovaného produktu;
2. **používání DDDA v konkrétním architektonickém projektu**.

Korporátní bezpečnostní politika zakazuje použití Codexu a Cursoru pro vývoj DDDA platformy. Platformní vývoj proto probíhá přes Chat a Work a technicky se validuje v GitHub Actions.

Současně je Cursor nezbytný pro vlastní práci architekta v DDDA. Poskytuje chat nad workspace, agentic práci se soubory, projektovými artefakty a kódem a tvoří základní execution environment konkrétního DDDA projektu.

Předchozí formulace „Chat/Work-only pro DDDA“ byla nebezpečně široká: mohla být vyložena jako zákaz Cursoru i pro project runtime a vedla k deaktivaci produktových `.cursor` artefaktů.

Prioritní quality attributes:

- security and compliance;
- jasné ownership boundaries;
- auditability;
- reproducibility platformních změn;
- usability projektového runtime;
- traceability;
- prevention of cross-repository changes.

## Decision

Zavádíme dvourovinný operating model.

### A. Vývoj DDDA platformy

```text
Chat
→ Work
→ platform PR branch
→ GitHub Actions exact-SHA validation
→ human review
```

Pro platformní vývoj:

- povoleny jsou pouze Chat a Work;
- Codex a Cursor jsou zakázány;
- GitHub Actions je autoritativní execution plane;
- Work zapisuje pouze na platformní PR branch;
- secrets nesmějí vstoupit do Chat/Work runtime;
- merge, promotion, release a tag vyžadují samostatné rozhodnutí.

### B. Používání DDDA v projektu

```text
Cursor project workspace
→ Cursor Chat / agentic execution
→ project repository a project-owned artefakty
→ human gate decisions
```

Pro project runtime:

- Cursor je povinný základní agentic systém;
- aktivní `.cursor` rules a skills jsou produktové runtime artefakty DDDA;
- Cursor smí pracovat pouze v konkrétním project repository;
- Cursor nesmí měnit DDDA platform repository;
- platformní defect nebo enhancement se předává jako change request do Chat/Work flow;
- cross-repository commit je zakázán;
- gate approval a zásadní architektonická rozhodnutí zůstávají lidská.

## Boundary rule

```text
Obecná změna DDDA produktu
  → platform development přes Chat/Work.

Změna konkrétního klientského nebo interního DDDA projektu
  → Cursor project runtime.
```

Projektový workaround nesmí být maskovaný platformní fork. Platformní enhancement nesmí být implementován z Cursoru přímo v platform repository.

## Options considered

### A. Chat/Work-only pro platformu i projektovou práci

Pros:

- jeden toolchain;
- jednoduchá obecná policy.

Cons:

- neodpovídá zamýšlenému produktu;
- odstraňuje základní agentic workspace architekta;
- znemožňuje aktivní `.cursor` rules, chat a práci s projektovými artefakty;
- nepřijatelná varianta.

### B. Cursor pro platformní vývoj i project runtime

Pros:

- jednotné lokální prostředí;
- rychlá práce se soubory a kódem.

Cons:

- v rozporu s bezpečnostním omezením platformního vývoje;
- slabší centrální exact-SHA evidence;
- riziko smíchání platformního a project repository.

### C. Dvě explicitní execution roviny

Pros:

- respektuje bezpečnostní policy;
- zachovává Cursor jako základ DDDA project runtime;
- jasné ownership a repository boundaries;
- GitHub Actions poskytuje reprodukovatelnou platformní evidenci;
- project work zůstává praktický pro architekta.

Cons:

- nutnost explicitně určovat scope;
- dva různé operating modely a onboarding;
- potřeba technických guardrails proti cross-repository změnám.

## Consequences

Positive:

- Cursor zůstává plnohodnotnou součástí DDDA produktu;
- platformní bezpečnostní constraint je dodržen;
- `.cursor` runtime assets jsou aktivní a testované;
- platformní a projektová data mají jasné ownership hranice;
- platformní defecty se řeší řízeným change-request tokem.

Negative:

- uživatel i runtime musí vždy znát aktivní scope;
- některé opravy vyžadují přechod z Cursor project flow do Chat/Work platform flow;
- project customization a platform enhancement musí být vědomě oddělovány.

New obligations:

- policy musí mít samostatnou sekci `platform_development` a `ddda_project_runtime`;
- Cursor rules musí explicitně zakazovat platform repository writes;
- repository tests musí ověřovat aktivní Cursor runtime assets;
- dokumentace nesmí používat formulaci, která zakazuje Cursor pro vlastní DDDA práci;
- každá změna musí určit platform nebo project scope.

## Impact

Platform areas:

- operating model;
- security governance;
- developer lifecycle;
- project runtime;
- Cursor rules and skills;
- testing;
- documentation.

Compatibility:

- opravuje chybnou governance interpretaci v dosud nemergovaném PR;
- obnovuje zamýšlené Cursor runtime artefakty;
- nemění kanonický DDD starter tok G1–G8;
- nemění existující project workspace contracts.

## Validation

- platform policy povoluje pro platform development pouze `chat` a `work`;
- stejná policy deklaruje `cursor` jako required system pro project runtime;
- platform repository writes z Cursoru jsou zakázané;
- všechny požadované `.cursor` runtime assets existují a jsou aktivní;
- Cursor rules obsahují project-only a no-platform-write guardrails;
- standardní PR CI běží nad výsledným exact SHA.

## Follow-up actions

- [ ] Doplnit onboarding, který uživateli vysvětlí rozdíl platform development versus project runtime.
- [ ] Zahrnout scope guard do generování nového DDDA project workspace.
- [ ] Udržovat Cursor rules jako verzované produktové artefakty.
- [ ] Pravidelně ověřovat schválení Cursoru pro klasifikaci konkrétních projektových dat.
