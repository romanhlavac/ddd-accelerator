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

Chybějící nebo zastaralá registrace je governance defect. U změn s dopadem `HIGH` nebo `BREAKING` se pokračování zastaví, dokud není routing opraven. Samotná existence skillu v repozitáři není důkazem, že jej runtime používá.

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

GitHub Actions je autoritativní execution plane pro shell, build, testy, candidate package a package-first acceptance. Work nesmí tvrdit, že provedl lokální příkaz, pokud jej ve skutečnosti nespustil schválený execution plane.

Kanonická pravidla jsou v:

```text
docs/developer-guide/chat-work-operating-model.md
docs/adr/0005-chat-work-only-development-operating-model.md
```

## Kanonický tok

```text
change request v Chat nebo Work
→ branch
→ Work implementation přes schválené Apps
→ standardní GitHub Actions nad exact SHA
→ validate-pr
→ human review
→ promote-pr
→ merge
→ release package
→ release validation
→ tag
```

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

## 2. Feature branch a implementace

`main` se nemění přímo. Doporučené názvy:

```text
feature/<change-id>-<short-name>
fix/<change-id>-<short-name>
docs/<change-id>-<short-name>
release/<version>
```

Behaviorální změna bez testu je neúplná. Změna kontraktu bez dokumentace a compatibility rozhodnutí je neúplná.

Work před prvním zápisem ověří:

- aktuální PR head SHA;
- deklarovanou target branch;
- allowed paths;
- že autorizace neobsahuje merge, promotion, release, tag ani force-push;
- že požadovaný GitHub/Miro connector je skutečně dostupný.

Pokud connector, board nebo oprávnění nejsou dostupné, Work zastaví a omezení oznámí. Nesmí je tiše nahradit předpokladem.

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

Na Chat/Work-only cestě tyto příkazy spouštějí standardní GitHub Actions workflows. Uživatel nemusí poskytovat Work lokální shell a nesmí být směrován do Codexu.

Package-dependent suites dostávají `-PackagePath` a používají nově rozbalený balíček.

## 4. Candidate package

`validate-pr` načte exact PR head SHA, vytvoří izolovaný checkout a candidate package pomocí `git archive`. Package dostane `ddda-package.json` s původem, verzí a source commit SHA.

Package nesmí obsahovat:

```text
.git/
.ddda/
.tmp/
.reports/
.releases/
dist/
Python caches
credentials
client data
uživatelské absolutní cesty
```

## 5. Validace PR

Stabilní kontrakt:

```powershell
.\ddda.ps1 validate-pr -Pr 8
```

S Miro:

```powershell
.\ddda.ps1 validate-pr -Pr 8 -WithMiro -Full -CleanupOnFailure
```

V Chat/Work-only režimu jej spouští standardní PR workflow nebo remote validation broker.

Příkaz:

1. ověří čistý aktivní repozitář;
2. načte `refs/pull/<PR>/head`;
3. vytvoří izolovaný checkout exact SHA;
4. vytvoří a validuje candidate package;
5. rozbalí package do nového adresáře;
6. inicializuje lokální baseline Git pouze pro testy, nikoli jako distribuovaný obsah;
7. spustí test suites;
8. vytvoří example workspace z package;
9. provede manifest-driven ingestion;
10. ověří G1 → G2;
11. volitelně provede Miro acceptance;
12. vytvoří JSON a Markdown report.

PASS automaticky uklidí pracovní clone a workspaces, pokud není použito `-KeepArtifacts`. Report a candidate package zůstávají pro promotion.

## 6. Lidské review

Člověk posuzuje pouze oblasti vyžadující judgment:

- metodickou správnost;
- architektonické hranice;
- semantics gatů;
- srozumitelnost chat-first workflow;
- vizuální kvalitu Miro boardu;
- release readiness a přijetí rizik.

Syntax, schémata, cesty, packaging, idempotence a absence secrets kontroluje automatizace.

### Miro visual review

Před tvrzením, že implementace odpovídá redline nebo referenčnímu boardu, musí Work skutečně načíst:

- referenční board;
- konkrétní source frames;
- relevantní children, images a geometry;
- cílové frames pro side-by-side porovnání.

Vizuální acceptance hodnotí minimálně:

- čitelnost při `Fit to frame`;
- first-viewer srozumitelnost;
- fonty a vizuální hierarchii;
- překryvy frames/items;
- využití plochy;
- přítomnost požadovaných obrázků a examples;
- věrnost schválenému template;
- metodickou a doménovou koherenci.

Item count, parent ownership, schema PASS a idempotence nejsou visual acceptance. Technický PASS ponechává `human_review_status=PENDING`, dokud člověk výsledek nepřijme.

## 7. GitHub autentizace a release dokumentace

`promote-pr` používá GitHub REST API. GitHub CLI není povinná závislost. Implementace i dokumentace používají stejné pořadí providerů:

1. `GH_TOKEN`;
2. `GITHUB_TOKEN`;
3. `gh auth token`;
4. Git credential helper.

Token se nikdy nepředává jako CLI argument a nesmí se objevit v logu, reportu, Chat/Work kontextu ani shell history.

Během vývoje se změny zapisují pod `## [Unreleased]`. Před promotion se všechny release položky přesunou pod právě jednu sekci `## [X.Y.Z] - YYYY-MM-DD`, `Unreleased` zůstane bez release položek a stejná verze se předá jako `-Version X.Y.Z`. Tag je deterministicky `vX.Y.Z`.

Promotion preflight kontroluje syntaxi changelogu, platné ISO datum, neprázdnou release sekci, prázdnou `Unreleased` sekci a shodu verze s parametrem promotion.

## 8. Promotion

Nejdřív bezpečný preflight:

```powershell
.\ddda.ps1 promote-pr -Pr 8 -Version 0.8.0 -DryRun
```

Skutečný promotion vyžaduje explicitní potvrzení:

```powershell
.\ddda.ps1 promote-pr -Pr 8 -Version 0.8.0 -ConfirmMerge
```

Promotion je fail-closed. Ověřuje:

- PR je otevřený a není draft;
- head SHA se nezměnil;
- CI checks jsou PASS;
- validation report je PASS pro stejný SHA;
- candidate package hash odpovídá reportu;
- approvals odpovídají repository policy;
- povinné ADR, changelog a migration note existují;
- changelog release verze odpovídá `-Version` a budoucímu tagu `vX.Y.Z`;
- `Unreleased` neobsahuje nepřiřazené release položky;
- `-ConfirmMerge` je explicitně zadáno.

Po merge vznikne release package. Tag se vytvoří až po package validation, generated release workspace, ingestion, smoke a acceptance.

## 9. Selhání a diagnostika

Lokální stav je pod uživatelským DDDA state rootem:

```text
validation/
validation-reports/
packages/
promotion/
release-reports/
```

Při FAIL zůstávají logy a diagnostický workspace. Miro board lze při testu odstranit přes `-CleanupOnFailure`.

Work musí rozlišit:

- connector/access failure;
- implementation failure;
- CI/test failure;
- human review rejection.

Nesmí je sloučit do neurčitého statusu ani prezentovat nedokončenou práci jako PASS.

## 10. Definition of Done

PR je hotový, když:

- implementace, testy a dokumentace tvoří jeden change package;
- CI je PASS;
- `validate-pr` je PASS pro aktuální head SHA;
- candidate package je validní;
- example workspace vznikl z package;
- ingestion je manifest-driven;
- acceptance je PASS;
- změna kompatibility má migration note;
- dlouhodobé rozhodnutí má ADR;
- changelog je aktualizován;
- povinný platform-development skill je verzovaný a runtime routing jej skutečně načítá;
- Chat/Work-only policy je splněna;
- connector a visual-access omezení byla transparentně uvedena;
- secrets nevstoupily do Chat nebo Work kontextu;
- Codex ani `/agent` nebyly použity;
- merge nebyl proveden bez explicitního lidského rozhodnutí.
