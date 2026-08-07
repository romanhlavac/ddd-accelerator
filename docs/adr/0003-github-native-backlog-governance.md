# ADR 0003: GitHub-native backlog governance

Status: Proposed

Date: 2026-07-27

## Context

DDDA platforma se vyvíjí jako verzovaný produkt. Dosavadní vývoj používal pull requesty jako hlavní delivery mechanismus, ale chyběl jednoznačný model pro:

- dlouhodobé roadmap bloky;
- GAP a discovery položky;
- parent/child vazby;
- prioritizaci a pořadí;
- cílové verze;
- rozlišení plánované změny od zahájené implementace;
- vazbu na ADR, changelog, migration note, validation evidence a HRDR.

Původní roadmap formulovala některé budoucí bloky jako „PR #9–#11“. GitHub však používá společnou číselnou řadu pro issues a PR a tato čísla byla mezitím použita pro Human Review remediation issues. PR číslo proto není stabilní identita roadmap bloku.

Současně je nutné nepoškodit probíhající Human Review PR #8. Governance změna proto nesmí měnit jeho source branch ani head SHA. Překlopení PR #8 se provádí pouze pomocí issue relationships a review komentářů, dokud není dokončen jeho současný lifecycle.

Prioritní quality attributes:

- traceability;
- auditability;
- modifiability;
- process safety;
- clarity of ownership;
- low operational overhead;
- compatibility with GitHub-native workflows.

## Decision

DDDA bude používat GitHub-native backlog governance:

```text
GitHub Issue
  autorita pro nápad, GAP a plánovaný požadavek.

Parent Issue / Work Package
  autorita pro velký roadmap outcome se stabilním WP-XX ID.

Child Issue
  autorita pro konkrétní implementační Change Request.

GitHub Project
  autorita pro prioritu, pořadí a delivery status.

Milestone
  autorita pro cílový release scope.

Branch + Draft PR
  vzniká až po zahájení skutečné implementace.

ADR
  autorita pro dlouhodobé architektonické rozhodnutí.

PR + CHANGELOG
  evidence implementované a vydávané změny.

Migration note
  autorita pro breaking dopad a migrační postup.

CI + validation report
  technická evidence pro exact source SHA.

HRDR
  autorita pro lidské GO/NO-GO.

Versioned roadmap
  dlouhodobá produktová vize a agregovaný stav Work Packages.
```

Stabilní roadmap identity jsou `WP-XX`, nikoli GitHub čísla PR.

Plánované nebo prázdné PR se nepoužívají jako backlog. Draft PR vzniká až při aktivní implementaci.

## Options considered

### Option A: Plánované Draft PR jako roadmap backlog

Výhody:

- rychlá vazba na budoucí diff;
- známé PR místo pro diskusi.

Nevýhody:

- branch existuje bez implementace;
- scope driftuje od budoucího diffu;
- PR číslo se chybně používá jako stabilní roadmap ID;
- zbytečné CI a review notifikace;
- jeden velký GAP často vyžaduje více PR;
- míchá plánování a delivery.

Riziko:

- dlouhodobě otevřené prázdné PR ztrácejí význam a komplikují release governance.

### Option B: Repository-only backlog v Markdown/YAML

Výhody:

- plná verzovatelnost;
- snadná machine-readable reprezentace;
- nezávislost na GitHub Project.

Nevýhody:

- slabší diskuse, assignments a notifications;
- souběžné editace vytvářejí merge konflikty;
- duplicita vůči Issues a PR;
- horší operativní prioritizace.

Riziko:

- backlog dokument se stane zastaralým paralelním source of truth.

### Option C: GitHub Issues + Project + Milestones, repository governance contracts

Výhody:

- oddělení plánování, prioritizace a implementace;
- nativní diskuse, ownership, links a automation;
- stabilní Work Package ID nezávislé na GitHub číslech;
- repository může verzovat pravidla, šablony, roadmapu a ADR;
- podporuje exact traceability až k release evidence.

Nevýhody:

- část konfigurace Projectu není standardně verzována;
- vyžaduje backlog hygiene;
- parent/child vazby mohou být reprezentovány checklisty, pokud není dostupná funkce sub-issues;
- GitHub Project a Milestone potřebují administrátorskou konfiguraci.

## Consequences

### Positive

- plánované GAP bloky mají stabilní identitu;
- PR zůstává jednotkou skutečné změny;
- scope review má jednoznačné vstupy;
- prioritizace a release scope jsou odděleny;
- roadmap může agregovat stav bez duplikace detailního backlogu;
- Human Review a validation evidence mají jasné autoritativní místo.

### Negative

- vzniká povinnost udržovat Project metadata;
- issue body a repository roadmap musí být periodicky synchronizovány na úrovni statusu a odkazů;
- Project configuration nelze plně vynutit pouze Gitem bez další automatizace;
- starší PR a issues musí být postupně navázány na Work Packages.

### New obligations

- každý významný GAP má Issue;
- každý velký roadmap blok má parent Work Package Issue a `WP-XX`;
- každý aktivní implementační PR odkazuje na Change Request;
- Project metadata drží priority a pořadí;
- Milestone drží cílový release scope;
- roadmap se aktualizuje po významném rozhodnutí nebo dokončení WP;
- CI má později ověřovat repository governance contracts, které lze deterministicky kontrolovat.

## Impact

Platform areas:

- `METHODOLOGY`;
- `DOC`;
- `RELEASE`;
- `SECURITY-GOVERNANCE`;
- `TESTING`.

Existing workspaces:

- žádný dopad;
- governance se týká pouze platform repository.

Migration:

- non-breaking;
- existující PR #8 zůstává beze změny source SHA;
- Issues #9–#15 se vztahově začlení pod WP-08;
- budoucí bloky přestanou používat označení „PR #9–#11“ a použijí `WP-09` až `WP-11`.

## Validation

Ověřit:

- existence governance dokumentace;
- validní YAML `config/governance/backlog-policy.yaml`;
- Issue templates pro GAP, Work Package a Change Request;
- Pull Request template vyžadující Issue link a scope evidence;
- vytvořené parent Work Package Issues;
- vytvořené child Issues pro delivery slices;
- vztahové komentáře u PR #8 a Issues #9–#15 bez změny PR head SHA;
- scope review před merge governance PR.

## Risks and mitigations

| Riziko | Dopad | Pravděpodobnost | Mitigace |
|---|---:|---:|---|
| Project metadata driftuje od Issues | Medium | Medium | pravidelný backlog review, machine-readable policy a views |
| Work Packages budou příliš velké | High | Medium | povinné delivery slices a child issues |
| Issues se stanou detailními design dokumenty | Medium | Medium | dlouhodobá rozhodnutí přesunout do ADR, Issue na ně odkazuje |
| PR #8 bude poškozen změnou governance | High | Low | neměnit source branch ani SHA; použít pouze relations/comments |
| Roadmap bude paralelní backlog | Medium | Medium | roadmap drží outcome a stav, detail zůstává v Issues |
| Automatizace bude předstírat lidské rozhodnutí | High | Low | HRDR a human provenance zůstávají explicitní a oddělené |

## Follow-up actions

- [ ] vytvořit GitHub Project `DDDA Platform Backlog` podle runbooku;
- [ ] vytvořit Milestone `DDDA 0.1.0` a naplnit pouze schválený release scope;
- [ ] přidat existující a nové Issues/PR do Projectu;
- [ ] po dokončení PR #8 rebase governance PR na nový `main`;
- [ ] aktualizovat centrální docs index a CHANGELOG po rebase;
- [ ] zvážit automatický repository contract test pro issue/PR templates a backlog policy;
- [ ] po stabilizaci HRDR doplnit jeho template/schema odkazy do governance dokumentace.
