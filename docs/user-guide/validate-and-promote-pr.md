# Validace, governed merge a promotion DDDA platformního PR

## Předpoklady

- pracuješ v čistém clone DDDA platformy;
- `origin` ukazuje na GitHub repository;
- je dostupný Git a Python 3.11+;
- GitHub autentizace používá podporovaný provider chain;
- secret-bearing online acceptance běží v GitHub Actions / schváleném secret store.

GitHub token se nikdy nevypisuje ani nepředává jako veřejný CLI argument.

Stav ověř:

```powershell
.\ddda.ps1 doctor
```

## Validace PR jedním příkazem

Offline:

```powershell
.\ddda.ps1 validate-pr -Pr 74
```

Včetně Miro, pokud je relevantní:

```powershell
.\ddda.ps1 validate-pr -Pr 74 -WithMiro -Full -CleanupOnFailure
```

Příkaz nemění aktivní větev ani working tree. PR načte přes exact head SHA, vytvoří izolovaný candidate package a package-first validation evidence.

## Governed implementation merge

Implementační PR se **nemerguje přes release promotion**.

Po exact-SHA CI + `validate-pr` PASS a explicitním Human Review PASS pro stejné SHA/package proveď nejdřív merge dry-run:

```powershell
.\ddda.ps1 merge-pr -Pr 74 -DryRun
```

Dry-run fail-closed ověří:

- PR je open, ready for review a míří do canonical base;
- current head SHA se nezměnilo;
- required GitHub checks jsou PASS;
- `validate-pr` report je PASS pro stejné SHA;
- candidate package SHA-256 odpovídá reportu;
- existuje právě jeden authoritativní Human Review marker `ddda:human-pr-review:v1`;
- Human Review má lidskou provenance, stejné PR/SHA/package a verdict `pass`;
- required governance documents existují;
- merge method odpovídá repository policy.

Dry-run neprovede merge, release, promotion ani tag.

Skutečný implementation merge:

```powershell
.\ddda.ps1 merge-pr -Pr 74 -ConfirmMerge
```

`-ConfirmMerge` je samostatná explicitní lidská merge authorization boundary.

`merge-pr` provede pouze merge implementačního PR a následný server read-back. Záměrně:

- nevyžaduje HRDR;
- nevyhodnocuje Release Scope Gate;
- nevytváří release package;
- nespouští release validation;
- nevytváří tag.

Tím lze bezpečně integrovat více implementačních PR pro jednu budoucí verzi, aniž by Release Scope Gate vytvořil kruhovou závislost.

## Release candidate

Až po integraci práce určené pro konkrétní release vytvoř explicitní release candidate — typicky `release/<version>` PR nebo jiný lifecyclem schválený ekvivalent.

Release candidate má vlastní exact-SHA `validate-pr` evidence. Human Review jednotlivých implementačních PR není Human Release Decision pro release candidate.

## HRDR pro release candidate

Po frozen release-candidate validation lze vytvořit Human Release Decision Record scaffold:

```powershell
.\ddda.ps1 review-pr `
  -Pr <RELEASE_PR> `
  -Version <X.Y.Z> `
  -Reviewer <login> `
  -DecisionOwner <login> `
  -PublishScaffold
```

Automation vytváří pouze `decision=pending`; nevytváří `GO`, nepřijímá residual risk a nevolí člověka, který smí release rozhodnout.

## Release cut v changelogu

Během vývoje zapisuj změny pod `## [Unreleased]`. Před finálním release dry-runem:

1. zvol `X.Y.Z`;
2. přesuň release položky pod `## [X.Y.Z] - YYYY-MM-DD`;
3. ponech `Unreleased` bez release položek;
4. použij stejné `X.Y.Z` v `-Version`;
5. canonical tag je `vX.Y.Z`.

## Release Scope Gate a promotion dry-run

Po explicitním Human Release Decision pro release candidate:

```powershell
.\ddda.ps1 promote-pr -Pr <RELEASE_PR> -Version <X.Y.Z> -DryRun
```

Public `promote-pr` nejdříve validuje právě jeden authoritativní HRDR a strict Release Scope Gate nad live Milestone, native blockers a GitHub Project V2 projection.

Release Scope Gate vyžaduje, aby current release scope byl před skutečným release terminal nebo explicitně deferred mimo release. Toto pravidlo **neplatí jako precondition pro předchozí implementation merges**.

Dry-run neprovede merge release candidate, release ani tag.

## Skutečný release promotion

Vyžaduje novou samostatnou explicitní human authorization:

```powershell
.\ddda.ps1 promote-pr -Pr <RELEASE_PR> -Version <X.Y.Z> -ConfirmMerge
```

S online Miro release acceptance, je-li relevantní:

```powershell
.\ddda.ps1 promote-pr -Pr <RELEASE_PR> -Version <X.Y.Z> -ConfirmMerge -WithMiro -Full -CleanupOnFailure
```

Implementation `merge-pr -ConfirmMerge` authorization nikdy neautorizuje release.

Canonical promotion po PASS gate:

1. provede release-candidate merge, pokud jej workflow vyžaduje;
2. načte nový canonical release source;
3. vytvoří release package;
4. vygeneruje release validation workspace;
5. provede ingestion, security, smoke, E2E a acceptance;
6. vytvoří release report;
7. vytvoří/pushne tag až po PASS.

Při release validation FAIL se tag nevytvoří.

## Diagnostické cesty

Lokální evidence jsou pod DDDA state rootem, typicky:

```text
validation/
validation-reports/
packages/
merge-reports/
promotion/
release-reports/
```

## Bezpečnostní pravidla

- nikdy nepředávej token jako CLI argument;
- necommituj validation/release workspaces;
- nepoužívej klientský workspace jako fixture;
- běžné testy nikdy nemergují ani netagují;
- Human Review PASS nevytváří automation;
- merge authorization a release authorization jsou oddělené;
- `merge-pr` nesmí být release bypass;
- `promote-pr` nesmí být použit jako obecný mechanismus merge implementačních PR.
