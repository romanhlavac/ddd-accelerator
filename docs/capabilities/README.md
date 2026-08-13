# Funkcionality DDDA

Tento dokument je lidsky čitelný katalog schopností. Strojově validovaný katalog je v `docs/reference/capability-catalog.yaml`.

## 1. Vývojový lifecycle platformy

- stabilní root entry point `ddda.ps1`;
- `doctor` a pojmenované test suites;
- exact-SHA validace PR v izolovaném checkoutu;
- candidate a release package vytvořený z čistého versioned source state;
- package manifest a SHA-256;
- package-content, path-isolation a secret-leak kontroly;
- generovaný minimal example workspace z rozbaleného package;
- manifest-driven ingestion syntetických vstupů;
- JSON a Markdown validation report;
- fail-closed `promote-pr` s CI, review, report a exact-SHA kontrolami;
- explicitní `-ConfirmMerge` jako lidská approval boundary;
- release tag až po úspěšné release validation.

## 2. Onboarding a workspace

- automatizovaný first-run po clone;
- offline i online Miro smoke test;
- multi-project workspace;
- samostatný Git repozitář každého projektu;
- materializace referenčního example projektu;
- řízený first-run libovolného projektu z intake;
- workspace a projekt lze generovat z Git distribuce i z validovaného package.

## 3. Chat-first řízení projektu

- konverzační intake zaměřený na business problém a rozhodnutí;
- lifecycle tailoring, který zachovává starter tok Align → Code;
- current status, další gate a doporučený prompt;
- evidence-driven gate review s lidským schválením;
- agentní scope a handoff kontrakt;
- doporučení Ask/Plan/Agent/Debug a context-budget pravidla;
- explicitní Git commit policy bez automatického push nebo merge.

## 4. DDD metodika

- strategic DDD, subdomény, bounded contexts a context mapping;
- Big Picture, Process Modeling a Design-Level EventStorming;
- tactical DDD, agregáty, invarianty a domain events;
- quality attributes, ADR, integrace, data ownership a Team Topologies;
- typově specifické workflow pro deset kanonických typů projektů.

## 5. Miro

- deklarativní metodický scaffold;
- živý REST renderer;
- stabilní item mapping;
- obousměrná YAML ↔ Miro synchronizace;
- dry-run, explicitní konflikty, tombstones a `PromoteNew`;
- polling worker;
- platformní a projektové online smoke testy;
- status a next-actions artefakty jako spravované projektové položky;
- online PR a release acceptance používající izolovaný testovací board.

## 6. Git, audit a governance

- Git jako source of truth a approval boundary;
- PR jako jednotka platformní změny;
- package jako jednotka distribuce a reprodukovatelné validace;
- oddělení platformních a projektových změn;
- auditní Miro sync reporty;
- gate decision records;
- changelog, ADR a migration note podle dopadu změny;
- exact SHA a package hash ve validation reportu;
- žádný implicitní commit, push, merge nebo last-write-wins.

## Plánované bloky

PR #9 rozšíří strategii, portfolio a socio-technické modely. PR #10 doplní enterprise ingestion a modelové importy. PR #11 doplní EventStorming session runtime a multi-agentní orchestrace. Tyto plánované schopnosti nejsou v tomto katalogu označeny jako implementované.
