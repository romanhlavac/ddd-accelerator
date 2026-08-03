# ADR: Chat/Work-only operating model pro vývoj DDDA

Status: Accepted

Date: 2026-08-03

## Context

Korporátní bezpečnostní politika uživatele zakazuje Codex. Vývoj DDDA má pokračovat pouze přes běžný Chat a režim Work.

DDDA přitom vyžaduje:

- změny verzovaného repozitáře;
- PR-based governance;
- exact-SHA validaci;
- build a test suites;
- package-first acceptance;
- práci s GitHubem a Miro;
- oddělení technického PASS a human review;
- auditovatelnou práci bez předávání secrets do asistentského runtime.

Work umí koordinovat vícekrokovou práci a schválené Apps, ale není lokální developer workstation. Nemá být považován za ekvivalent Codexu nebo shellového prostředí.

Prioritní quality attributes:

- security and compliance;
- auditability;
- reproducibility;
- testability;
- least privilege;
- transparency of limitations;
- usability pro jednoho správce platformy.

## Decision

Povolujeme pouze dvě uživatelská rozhraní:

```text
Chat
Work
```

Zakazujeme:

```text
Codex
legacy /agent mode
jiný neschválený cloudový coding agent
```

Rozdělení odpovědností:

```text
Chat
  návrh, konzultace, scope, rozhodnutí, autorizace, review.

Work
  vícekroková orchestrace, schválené connector reads/writes,
  práce s PR branchemi, Miro a CI evidence.

GitHub Actions
  autoritativní execution plane pro shell, build, testy,
  candidate package, package-first validation a online acceptance.

Human reviewer
  metodika, architektura, vizuální použitelnost, rizika,
  merge/promotion/release rozhodnutí.
```

GitHub je source of truth a PR je jednotka změny. Work smí zapisovat pouze na explicitně deklarovanou PR branch. Přímý zápis na `main`, force-push, merge, tag, release a promotion nejsou součástí běžné implementační autorizace.

Secrets nesmějí být zpřístupněny Chat nebo Work runtime. Secret-bearing operace běží pouze v GitHub Actions nebo source-system secret store.

Standardní technický tok:

```text
Chat change request / Work implementation
→ PR branch
→ standardní GitHub Actions nad exact SHA
→ candidate package
→ package-first suites
→ machine-readable evidence
→ Work/Chat vyhodnocení
→ human review
```

Miro vizuální acceptance vyžaduje skutečné načtení referenčních boardů a konkrétních framů. Strukturální item count, parent ownership nebo schema PASS nejsou náhradou za posouzení čitelnosti, obrázků, fontů, překryvů, využití plochy a first-viewer usability.

## Options considered

### A. Codex jako hlavní development environment

Pros:

- rychlá editace a testovací feedback;
- přímý shell a repository workspace.

Cons:

- zakázáno korporátní bezpečnostní politikou;
- varianta není přípustná.

### B. Ruční lokální vývoj operátorem bez Work

Pros:

- plná kontrola lokálního prostředí;
- nezávislost na agentním orchestration mode.

Cons:

- vyšší manuální práce;
- horší kontinuita vícekrokových GitHub/Miro úloh;
- větší riziko ad hoc postupů.

### C. Chat/Work-only s GitHub Actions execution plane

Pros:

- respektuje bezpečnostní constraint;
- secrets zůstávají mimo asistentský runtime;
- exact-SHA CI vytváří auditovatelnou evidenci;
- GitHub a Miro operace jsou řízené source-system oprávněními;
- člověk zůstává vlastníkem judgment-heavy rozhodnutí.

Cons:

- pomalejší iterace při test failures;
- vyšší závislost na kvalitě CI a self-service workflows;
- Work nemůže nahradit lokální debugging;
- více malých Git/CI iterací může prodloužit změnu.

## Consequences

Positive:

- jednoznačný povolený toolchain;
- Codex nemůže být tiše zaveden jako implicitní dependency;
- GitHub Actions jsou autoritativním technickým důkazem;
- secrets nejsou součástí Chat/Work kontextu;
- vizuální Miro review má explicitní acceptance kontrakt;
- omezení přístupu musí být sdělena, ne zamlčena.

Negative:

- některé změny budou vyžadovat více CI cyklů;
- složité ladění může vyžadovat schváleného lidského lokálního operátora;
- GitHub Actions a konektory jsou kritické provozní závislosti.

New obligations:

- udržovat standardní workflows a `ddda.ps1` jako self-service execution interface;
- technicky validovat Chat/Work-only policy v repository validatoru;
- dokumentovat connector nebo permission failure okamžitě;
- nikdy nevydávat strukturální Miro PASS za visual acceptance;
- pravidelně ověřovat least-privilege Apps a policy soulad.

## Impact

Platform areas:

- methodology;
- security governance;
- developer lifecycle;
- testing strategy;
- remote validation broker;
- Miro acceptance;
- documentation.

Compatibility:

- aditivní;
- nemění DDDA workspace contracts;
- nemění kanonický DDD starter tok G1–G8;
- zpřesňuje pouze povolený způsob vývoje platformy.

## Validation

- repository policy explicitně povoluje pouze `chat` a `work`;
- policy explicitně zakazuje `codex` a `agent`;
- GitHub Actions jsou deklarovány jako autoritativní execution plane;
- repository validator kontroluje policy a povinné dokumenty;
- unit tests ověřují přijetí kanonické policy a odmítnutí driftu;
- standardní PR CI běží nad výsledným SHA.

## Follow-up actions

- [ ] Udržovat Chat/Work-only policy při dalších změnách governance.
- [ ] Odstranit potřebu jednorázových bootstrap workflow; rozšiřovat pouze standardní self-service workflows.
- [ ] Pravidelně ověřovat, že GitHub/Miro Apps odpovídají firemní policy a datové klasifikaci.
- [ ] Zahrnout visual side-by-side checklist do dalších Miro remediation acceptance kritérií.
