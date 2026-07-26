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

## Kanonický tok

```text
change request
→ branch
→ implementation
→ CI
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
- potřebu ADR nebo migration note.

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

## 3. Lokální test suites

```powershell
.\ddda.ps1 doctor
.\ddda.ps1 test -Suite lint
.\ddda.ps1 test -Suite schema
.\ddda.ps1 test -Suite unit
.\ddda.ps1 test -Suite component
.\ddda.ps1 test -Suite regression
.\ddda.ps1 test -Suite security
```

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

```powershell
.\ddda.ps1 validate-pr -Pr 8
```

S Miro:

```powershell
.\ddda.ps1 validate-pr -Pr 8 -WithMiro -Full -CleanupOnFailure
```

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

## 7. Promotion

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
- `-ConfirmMerge` je explicitně zadáno.

Po merge vznikne release package. Tag se vytvoří až po package validation, generated release workspace, ingestion, smoke a acceptance.

## 8. Selhání a diagnostika

Lokální stav je pod uživatelským DDDA state rootem:

```text
validation/
validation-reports/
packages/
promotion/
release-reports/
```

Při FAIL zůstávají logy a diagnostický workspace. Miro board lze při testu odstranit přes `-CleanupOnFailure`.

## 9. Definition of Done

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
- merge nebyl proveden bez explicitního lidského rozhodnutí.
