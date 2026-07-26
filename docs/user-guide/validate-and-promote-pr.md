# Validace a promotion DDDA platformního PR

## Předpoklady

- pracuješ v čistém clone DDDA platformy;
- `origin` ukazuje na GitHub repository;
- je dostupný Git a Python 3.11+;
- pro `promote-pr` je dostupná GitHub autentizace alespoň jedním z podporovaných způsobů:
  - existující Git credential helper použitý už pro clone/push;
  - environment variable `GH_TOKEN`;
  - environment variable `GITHUB_TOKEN`;
  - autentizovaný GitHub CLI `gh`;
- pro online Miro test je token uložen v DDDA secret store nebo environment variable.

GitHub CLI není povinná závislost. Promotion používá GitHub REST API a automaticky preferuje `GH_TOKEN`, potom `GITHUB_TOKEN`, potom token z `gh auth token` a nakonec existující Git credential helper. Token se nevypisuje ani nepředává jako CLI argument.

Stav ověř:

```powershell
.\ddda.ps1 doctor
```

## Validace PR jedním příkazem

Offline:

```powershell
.\ddda.ps1 validate-pr -Pr 8
```

Včetně Miro:

```powershell
.\ddda.ps1 validate-pr -Pr 8 -WithMiro -Full -CleanupOnFailure
```

Příkaz nemění aktivní větev ani aktivní working tree. PR načte přes `refs/pull/<PR>/head`, vytvoří izolovaný checkout a testuje candidate package svázaný s exact head SHA.

## Co se provede automaticky

```text
clean-tree check
→ exact PR SHA
→ isolated checkout
→ candidate package
→ package security validation
→ unpacked package baseline
→ lint/schema/unit/component
→ integration/smoke/regression/security
→ E2E
→ steering acceptance
→ optional Miro acceptance
→ JSON + Markdown report
→ cleanup
```

Candidate package a validation report zůstávají pro následný promotion. Diagnostický workspace zůstává pouze při FAIL nebo při `-KeepArtifacts`.

## Výstup

Úspěch končí přehledem:

```text
DDDA PR validation: PASS
PR:       8
Branch:   <branch>
Commit:   <exact-sha>
Package:  <candidate-zip>
Report:   <report-directory>
```

Report obsahuje:

- PR a branch;
- exact SHA;
- package SHA-256;
- stav a délku každé suite;
- diagnostické logy;
- workspace a Miro board ID, pokud jsou relevantní.

## Review před promotion

Před promotion zkontroluj:

- obsah a rozsah PR;
- metodickou správnost;
- architektonická rozhodnutí a trade-offy;
- compatibility a migration note;
- changelog;
- relevantní části validation reportu;
- Miro board při vizuálně významné změně.

Mechanické kontroly neopakuj ručně.

## Promotion dry-run

```powershell
.\ddda.ps1 promote-pr -Pr 8 -Version 0.8.0 -DryRun
```

Dry-run ověří:

- PR je otevřený a není draft;
- target branch odpovídá policy;
- head SHA se nezměnil;
- CI je PASS;
- validation report je PASS pro stejný SHA;
- candidate package hash odpovídá reportu;
- approval policy je splněna;
- povinné governance dokumenty existují;
- release tag ještě neexistuje.

Neprovede merge, release ani tag.

## Skutečný promotion

```powershell
.\ddda.ps1 promote-pr -Pr 8 -Version 0.8.0 -ConfirmMerge
```

S online Miro release acceptance:

```powershell
.\ddda.ps1 promote-pr -Pr 8 -Version 0.8.0 -ConfirmMerge -WithMiro -Full -CleanupOnFailure
```

`-ConfirmMerge` je explicitní lidská approval boundary. Bez něj se merge neprovede.

Po merge promotion:

1. načte nový `main`;
2. ověří merge commit;
3. vytvoří release package;
4. vygeneruje release validation workspace;
5. provede ingestion, security, smoke, E2E a acceptance;
6. vytvoří release report;
7. vytvoří a pushne tag až po PASS.

Při release validation FAIL se tag nevytvoří.

## Diagnostické cesty

Lokální výstupy jsou pod DDDA state rootem:

```text
validation/
validation-reports/
packages/
promotion/
release-reports/
```

Na Windows typicky:

```text
%LOCALAPPDATA%\DDDA\
```

Tyto adresáře nejsou součástí platformního Git repozitáře.

## Bezpečnostní pravidla

- nikdy nepředávej token jako CLI argument;
- necommituj validation nebo release workspaces;
- nepoužívej klientský workspace jako fixture;
- nemaž diagnostický adresář ručně před přečtením FAIL reportu;
- nepoužívej `git clean -fdx` nad neověřenou cestou;
- nepoužívej promotion bez dry-run a review;
- běžné testy nikdy nemergují ani netagují.
