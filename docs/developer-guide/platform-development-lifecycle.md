# Vývojový lifecycle DDDA platformy

## Účel

Tento postup platí pro vývoj verzované DDDA platformy. Neplatí pro doménovou práci v klientském projektu.

Rozlišuj:

```text
platform repository
→ candidate/release package
→ generated validation workspace
→ example project
```

Klientský workspace není test fixture platformy.

## Povinný platform-development skill

Kanonický a verzovaný operating contract pro vývoj platformy je:

```text
knowledge/ddda-platform-development-skill.md
```

Každý ChatGPT projekt, Chat nebo Work runtime používaný pro změny DDDA platformy musí tento skill registrovat jako **povinný pro vývoj DDDA** alespoň jedním z těchto mechanismů:

1. položkou v `knowledge/00-knowledge-index.md`;
2. explicitním odkazem v ChatGPT Project Instructions nebo Work bootstrap instructions.

Git a runtime activation jsou dva oddělené kontrolní mechanismy:

- soubor v Gitu zajišťuje versioning, review a traceability;
- knowledge index nebo Project/Work Instructions zajišťují, že jej konkrétní Chat či Work skutečně načte.

Před návrhem nebo aplikací změny platformy se musí ověřit:

```text
- runtime načetl aktuální repository verzi skillu;
- skill odpovídá aktivní branch/SHA;
- tento developer lifecycle a testing strategy jsou dostupné;
- Chat/Work policy odpovídá config/platform/development-policy.yaml;
- případný rozpor mezi skillem a dokumentací je vyřešen v Gitu.
```

Chybějící nebo zastaralá registrace je governance defect. U změn s dopadem `HIGH` nebo `BREAKING` se pokračování zastaví, dokud není routing opraven.

## Povolený Chat/Work operating model

```text
DDDA-EXECUTION-MODE: CHAT-WORK-ONLY
```

Povolená rozhraní:

- **Chat** pro analýzu, návrh, rozhodnutí, autorizaci a review;
- **Work** pro vícekrokovou práci se schválenými GitHub/Miro Apps a ohraničené zápisy na PR branch.

Zakázáno:

- **Codex**;
- legacy **`/agent`**;
- jiný neschválený cloudový coding agent.

GitHub Actions je autoritativní execution plane pro shell, build, testy, candidate package a package-first acceptance.

## GitHub authentication contract

Governed merge/release commands používají stejný kanonický provider order:

1. `GH_TOKEN`;
2. `GITHUB_TOKEN`;
3. `gh auth token`;
4. `git credential helper`.

GitHub CLI není povinná závislost. Token se nikdy nepředává jako CLI argument a nesmí se objevit v Chat/Work kontextu, logu, reportu ani shell history. Secret-bearing execution zůstává v GitHub Actions nebo schváleném secret store.

## Kanonické toky

DDDA explicitně odděluje **integraci implementačního PR** od **release/promotion**.

### A. Governed implementation PR

```text
change request
→ branch
→ implementation
→ exact-SHA GitHub Actions
→ validate-pr
→ Human Review pro stejné SHA/package
→ merge-pr -DryRun
→ explicitní human merge authorization
→ merge-pr -ConfirmMerge
→ merge do main
→ NO release package
→ NO release validation
→ NO tag
```

`merge-pr` je merge-only command. Nevyžaduje HRDR ani Release Scope Gate a nesmí dosáhnout release/tag execution path.

### B. Release candidate

Až když je práce určená pro release integrována a release-scope Issues jsou terminal nebo explicitně deferred mimo release:

```text
release candidate (typicky release/<version> PR nebo ekvivalentní governed candidate)
→ exact-SHA candidate validation
→ release cut / changelog consistency
→ HRDR pro exact release candidate
→ Release Scope Gate
→ promotion dry-run
→ explicitní Human Release Decision
→ samostatná explicitní release/promotion authorization
→ canonical promotion
→ release-candidate merge, pokud je součástí canonical workflow
→ release package
→ release validation
→ release report
→ tag
```

Release Scope Gate zůstává striktní. Neaplikuje se ale jako podmínka integrace jednotlivých implementačních PR, jejichž merge je předpokladem pro uzavření release scope.

Dokud je otevřený právě jeden release train `DDDA X.Y.Z`, `merge-pr` navíc fail-closed odmítne PR, jehož jediný primary CR není v jeho Milestone. To je prevence nové kontaminace `main`; není to Release Scope Gate ani release authorization.

Git je source of truth. PR je jednotka změny. Package je jednotka distribuce a reprodukovatelné validace.

## 1. Příprava změny

Každá behaviorální změna musí určit:

- problém a cíl;
- klasifikaci změny;
- dopad na kontrakty a kompatibilitu;
- acceptance criteria;
- test suites;
- dokumentační dopad;
- potřebu ADR nebo migration note;
- povolený write scope pro Work;
- bezpečnostní a datovou klasifikaci připojených Apps.

Hlavní klasifikace:

```text
DOC, METHODOLOGY, TEMPLATE, SCHEMA, ORCHESTRATION,
INGESTION, CLI, WORKSPACE-GENERATOR, EXAMPLE,
TESTING, RELEASE, SECURITY-GOVERNANCE
```

Impact je `LOW`, `MEDIUM`, `HIGH` nebo `BREAKING`. Pro governed merge jej lze auditovatelně zapsat do PR body markeru `ddda:change-classification:v1`; chybějící marker se při merge považuje za `UNKNOWN` a používá fail-safe merge-commit-only policy.

## 2. Feature branch a implementace

`main` se nemění přímo. Doporučené názvy:

```text
feature/<change-id>-<short-name>
fix/<change-id>-<short-name>
docs/<change-id>-<short-name>
release/<version>
```

Behaviorální změna bez testu je neúplná. Změna kontraktu bez dokumentace a compatibility rozhodnutí je neúplná.

Work před prvním zápisem ověří aktuální PR head SHA, target branch, allowed paths, side-effect authorization a dostupnost connectorů.

## 3. Test suites a execution plane

Stabilní platformní kontrakt:

```powershell
.\ddda.ps1 doctor
.\ddda.ps1 test -Suite lint
.\ddda.ps1 test -Suite schema
.\ddda.ps1 test -Suite unit
.\ddda.ps1 test -Suite component
.\ddda.ps1 test -Suite regression
.\ddda.ps1 test -Suite security
```

Na Chat/Work-only cestě tyto příkazy spouštějí standardní GitHub Actions workflows.

## 4. Candidate package

Standardní PR CI načte exact PR head SHA a vytvoří pomocí `git archive` právě jeden canonical candidate package. Stabilní package metadata jsou odvozena z exact SHA; package dostane `ddda-package.json` s původem, verzí a `source_commit`.

Navazující `validate-pr-command` čeká na package job, stáhne jeho exact-SHA artifact a předá ZIP do `validate-pr -PackagePath`. V tomto režimu `validate-pr` package znovu nesestavuje: ověří `kind=candidate`, `source_commit=current PR HEAD`, přepočítá SHA-256 a stejný hash zapíše do `result.json` i `result.md`. Lokální spuštění bez `-PackagePath` zůstává convenience cestou, ale jeho package není CI governance evidence.

Candidate artifact a validation report jsou společně dohledatelné přes repository, PR, exact HEAD SHA, workflow run, artifact ID/name a package SHA-256. Publikovaný report používá přenositelné reference; runner-local cesta není součástí evidence.

Package nesmí obsahovat `.git/`, `.ddda/`, `.tmp/`, reports, releases, dist, caches, credentials, client data ani uživatelské absolutní cesty.

## 5. Validace PR

```powershell
.\ddda.ps1 validate-pr -Pr 8
```

S Miro:

```powershell
.\ddda.ps1 validate-pr -Pr 8 -WithMiro -Full -CleanupOnFailure
```

Příkaz ověřuje exact PR SHA, candidate package, package-first suites, example workspace, ingestion, acceptance a report.

## 6. Human Review implementačního PR

Člověk posuzuje judgment-heavy oblasti, zejména metodiku, architekturu, semantics gatů, použitelnost a relevantní rizika. Syntax, schemas, packaging, idempotence a absence secrets kontroluje automatizace.

Human Review implementačního PR musí být auditovatelně vázán minimálně na:

```text
repository
pr
reviewed_sha
candidate_package_sha256
reviewer
reviewed_at
verdict
```

`PASS` Human Review je oddělen od **merge authorization**. Změna reviewed SHA nebo candidate package hash Human Review pro merge invaliduje.

### 6.1 Governed implementation merge

Bezpečný preflight:

```powershell
.\ddda.ps1 merge-pr -Pr 74 -DryRun
```

Skutečný merge:

```powershell
.\ddda.ps1 merge-pr -Pr 74 -ConfirmMerge
```

`merge-pr` fail-closed ověřuje live PR state, exact head SHA, required CI, exact-SHA `validate-pr`, candidate package hash, Human Review PASS stejného SHA/package, required governance docs a repository merge policy. Standardní CI nejprve spustí samostatný `Human Review readiness` coordinator. Dokud chybí Human Review marker, vlastní `Governed merge dry-run` job je `skipped` a merge preflight má stav `NOT_RUN`; úspěch coordinatoru není merge-preflight PASS. Po publikaci exact-SHA Human Review se znovu spustí readiness job a jeho dependent dry-run bez nového candidate buildu. Dry-run na čistém runneru stáhne candidate i report ze stejného workflow runu a předá jejich nové lokální cesty přes `-PackagePath` a `-ValidationReportPath`; nikdy nepoužívá cestu uloženou na předchozím runneru.

Po aktivaci ADR 0009 je merge strategy risk-based:

```text
HIGH / BREAKING → merge commit REQUIRED
LOW / MEDIUM    → merge commit DEFAULT; squash jen explicitní human exception
UNKNOWN         → merge commit only
rebase           → forbidden
```

Wrong merge method musí failnout před irreversible merge. Pro canonical merge následuje server-side ancestry read-back: validated PR HEAD musí být parent/ancestor výsledného main state. LOW/MEDIUM squash exception je samostatný human record vázaný na stejné PR/SHA/package/impact; automation jej nesmí vytvořit. Detailní kontrakt je v ADR 0009 a `docs/developer-guide/merge-strategy.md`.

`merge-pr`:

- **nevyhodnocuje HRDR**;
- **nevyhodnocuje Release Scope Gate**;
- **nevytváří release package**;
- **nespouští release validation**;
- **nevytváří tag**;
- bez explicitního `-ConfirmMerge` nemerguje.

To umožňuje bezpečně integrovat více implementačních PR před sestavením release candidate bez kruhové závislosti na release-scope completeness.

### 6.2 Prospective transition #70

#70 mění samotný merge contract. Jeho vlastní integraci proto stále řídí pre-existing `main` policy z exact base `297f61f6012f180e70805999df2ac1abe9616a05`, která používala squash. Nová merge-commit policy se stává autoritativní až po integraci #70 do `main`.

Transition je versioned, exact-base-bound a single-purpose; není to HIGH/BREAKING squash exception pro budoucí PR. HVR #70 musí tento bootstrap trade-off explicitně posoudit. Historické PR/tagy se nepřepisují.

## 7. Release candidate a HRDR

Po integraci zahrnutých implementačních PR se připraví explicitní release candidate. Pro jeho exact SHA se provede standardní validation a vytvoří Human Release Decision Record.

HRDR je **release decision evidence**, nikoli implementační merge evidence. Obsahuje exact release-candidate identity, findings, residual risks, reviewer/decision owner a explicitní lidské rozhodnutí.

Během vývoje se změny zapisují pod `## [Unreleased]`. Před promotion se release položky přesunou pod právě jednu sekci `## [X.Y.Z] - YYYY-MM-DD`; stejná verze se předá jako `-Version X.Y.Z` a tag je `vX.Y.Z`.

## 8. Release Scope Gate a promotion

Release Scope Gate se vyhodnocuje **výhradně na release-candidate boundary**.

```powershell
.\ddda.ps1 promote-pr -Pr <RELEASE_PR> -Version <X.Y.Z> -DryRun
```

Gate fail-closed ověřuje zejména:

- current release/version/milestone identity;
- všechny release-scope Issues terminal nebo explicitně deferred mimo release;
- žádné unresolved native blockers;
- Project/Milestone consistency;
- accepted-risk owner/follow-up/horizon;
- přesnou shodu HRDR risk setu;
- žádný RED/neakceptovaný blocker;
- exact SHA/package/version identity.

Skutečný promotion vyžaduje novou explicitní lidskou autorizaci:

```powershell
.\ddda.ps1 promote-pr -Pr <RELEASE_PR> -Version <X.Y.Z> -ConfirmMerge
```

Implementation merge authorization nikdy neimplikuje release/promotion/tag authorization.

Po canonical release-candidate merge vznikne release package; tag se vytvoří až po package validation, generated release workspace, ingestion, smoke a acceptance PASS.

## 9. Selhání a diagnostika

Work musí rozlišit connector/access failure, implementation failure, CI/test failure, Human Review rejection, implementation merge failure, release-scope failure a release validation failure. Nedokončená práce se nesmí prezentovat jako PASS.

Post-merge ancestry failure se nikdy neopravuje automatickým force-pushem nebo přepisem shared history; vyžaduje zachování diagnostiky a explicitní recovery rozhodnutí.

## 10. Definition of Done

Implementační PR je připraven k merge pouze když:

- implementace, testy a dokumentace tvoří jeden change package;
- CI je PASS;
- `validate-pr` je PASS pro aktuální head SHA;
- candidate package je validní;
- relevantní acceptance je PASS;
- compatibility/ADR/changelog obligations jsou splněny;
- mandatory Human Review je PASS pro stejné SHA/package;
- impact/merge strategy preflight je PASS;
- merge nebyl proveden bez explicitní human merge authorization.

Release je připraven pouze když navíc existuje validní release candidate, HRDR, Release Scope Gate PASS, explicitní Human Release Decision a samostatná release/promotion authorization. Technický PASS ani implementační merge sám o sobě release neautorizuje.
