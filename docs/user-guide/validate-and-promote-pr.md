# Validace, governed merge a promotion DDDA platformního PR

## Předpoklady

- pracuješ v čistém clone DDDA platformy;
- `origin` ukazuje na GitHub repository;
- je dostupný Git a Python 3.11+;
- GitHub autentizace používá podporovaný provider chain;
- secret-bearing online acceptance běží v GitHub Actions / schváleném secret store.

Kanonický GitHub authentication provider order je:

1. `GH_TOKEN`;
2. `GITHUB_TOKEN`;
3. `gh auth token`;
4. `git credential helper`.

GitHub CLI není povinná závislost. GitHub token se nikdy nevypisuje ani nepředává jako veřejný CLI argument a nesmí se objevit v Chat/Work kontextu, logu, reportu ani shell history.

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

Příkaz nemění aktivní větev ani working tree. Lokálně načte exact head SHA a vytvoří izolovaný candidate package. Ve standardním CI se candidate sestaví pouze jednou v `Platform validation`; `One-command PR validation` stáhne tentýž artifact a zavolá `validate-pr -PackagePath`, takže reportovaný hash patří fyzicky nahranému ZIPu.

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
- impact classification a merge method odpovídají repository merge-strategy policy.
- pokud existuje právě jeden otevřený release train `DDDA X.Y.Z`, primary CR PR patří do jeho Milestone; PR s pozdějším/TBD scope se fail-closed nemůže dostat do `main`.

Dry-run neprovede merge, release, promotion ani tag.

Standardní CI používá samostatný job `Human Review readiness`. Před Human Review je vlastní `Governed merge dry-run` job `skipped` a jeho stav je `NOT_RUN`; zelený readiness coordinator není důkaz provedeného dry-runu. Po publikaci exact-SHA Human Review se znovu spustí readiness job a jeho dependent dry-run, nikoli candidate build. Dry-run na novém čistém runneru stáhne již existující candidate a validation report ze stejného workflow runu, přepočítá hash a ověří shodu s reportem i Human Review. Dočasná cesta z validačního runneru se nepoužívá.

### Merge strategy a exact-SHA ancestry

Po aktivaci ADR 0009 je canonical default `merge`:

```text
HIGH / BREAKING → merge commit REQUIRED
LOW / MEDIUM    → merge commit DEFAULT
UNKNOWN impact  → merge commit only
rebase           → forbidden
```

LOW/MEDIUM může použít `squash` pouze s explicitním lidským `ddda:squash-exception:v1` recordem pro stejné PR/SHA/package/impact. Automation tuto exception nesmí vytvořit ani inferovat.

Explicitní dry-run varianty:

```powershell
.\ddda.ps1 merge-pr -Pr 74 -MergeMethod merge -DryRun
.\ddda.ps1 merge-pr -Pr <LOW_OR_MEDIUM_PR> -MergeMethod squash -DryRun
```

Pro canonical merge se po skutečném merge server-side ověří, že validated PR HEAD je parent/ancestor výsledného main state. Evidence používá `source_to_result_relation=ancestor`. U schváleného LOW/MEDIUM squash se místo ancestry ukládá explicitní source→result mapping s human exception metadata.

Detailní contract je v `docs/developer-guide/merge-strategy.md` a ADR 0009.

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

Public `promote-pr` nejdříve validuje právě jeden authoritativní HRDR a strict Release Scope Gate nad live Milestone, native blockers, GitHub Project V2 projection a skutečným source diffem od posledního canonical SemVer tagu.

Gate vytvoří inventory shipping commitů, PR a jejich právě jednoho primary CR. Každý shipping PR musí patřit do aktuálního Milestone i Project projection `Target Release=X.Y.Z`. Nezmapovaný commit, více primary CR nebo změna mimo scope znamená FAIL. U již integrované out-of-scope změny evidence obsahuje `RECOVERY_DECISION_REQUIRED`; automatizace sama nesmí scope rozšířit, historii přepsat ani změnu odstranit.

Release Scope Gate vyžaduje, aby current release scope byl před skutečným release terminal nebo explicitně deferred mimo release. Toto pravidlo **neplatí jako precondition pro předchozí implementation merges**.

Dry-run neprovede merge release candidate, release ani tag.

Governed wrapper navíc ukládá deterministickou machine-readable evidence pod DDDA state root `promotion/`. Výsledek rozlišuje:

```text
promotion_preflight_status
side_effect_assertions_status
wrapper_status
source_sha
candidate_package_sha256
version
release_scope_gate_status
```

Před a po dry-runu se čerstvým GitHub read-backem ověřuje, že PR nebyl mergnut, base SHA se nezměnilo a nevznikl canonical tag ani GitHub Release objekt. Očekávaná `404` pro neexistující tag/release je explicitní úspěšná absence assertion; `401/403`, síťová chyba nebo `5xx` zůstávají FAIL a nesmějí zdědit či kontaminovat výsledek jiné operace.

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
8. vytvoří GitHub Release pro canonical tag a publikuje validated DDDA ZIP, `result.json` a `result.md`; fresh read-back ověří identity a SHA-256 assets.

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
- wrong merge method musí failnout před irreversible side effect;
- LOW/MEDIUM squash exception musí mít lidskou provenance a exact candidate binding;
- `merge-pr` nesmí být release bypass;
- `promote-pr` nesmí být použit jako obecný mechanismus merge implementačních PR.
