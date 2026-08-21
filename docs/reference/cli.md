# CLI reference

## Stabilní entry point `ddda.ps1`

### Doctor

```powershell
.\ddda.ps1 doctor
```

Ověří platformní distribuci, povinné soubory, PowerShell syntax/BOM, JSON schemas a dokumentační strukturu.

### Test suites

```powershell
.\ddda.ps1 test -Suite <suite>
```

Podporované suite:

```text
lint
schema
unit
component
integration
smoke
regression
security
e2e
acceptance
all
```

### Validate PR

```powershell
.\ddda.ps1 validate-pr -Pr 74
```

Volitelné parametry:

- `-PackagePath` — použije předem sestavený canonical candidate; nový package se nevytvoří;
- `-PackageArtifactName` — uloží přenositelnou GitHub Actions artifact identity do reportu;
- `-PackageWorkflowRunId` — sváže report se source workflow runem candidate artifactu;
- `-WithMiro` — přidá online Miro acceptance;
- `-Full` — plný Miro smoke rozsah;
- `-CleanupOnFailure` — uklidí failed test resource podle ownership policy;
- `-KeepArtifacts` — zachová isolated validation artifacts;
- `-NonInteractive` — nepovolí prompt pro chybějící secret.

Příkaz testuje exact PR head SHA, candidate package a generovaný example workspace. Aktivní větev a working tree nemění.

Při `-PackagePath` musí ZIP mít `kind=candidate` a `source_commit` shodný s current PR HEAD. Report obsahuje nově přepočítaný hash tohoto souboru a nesmí obsahovat runner-local absolutní cestu.

### Merge PR

Governed implementation merge je samostatný příkaz oddělený od release promotion.

Preflight:

```powershell
.\ddda.ps1 merge-pr -Pr 74 -DryRun
```

Skutečný merge:

```powershell
.\ddda.ps1 merge-pr -Pr 74 -ConfirmMerge
```

`merge-pr` vyžaduje:

- open/ready/mergeable PR do canonical base;
- PASS required checks pro live exact head SHA;
- PASS `validate-pr` evidence pro stejné SHA;
- shodný candidate package SHA-256;
- právě jeden authoritativní Human Review marker `ddda:human-pr-review:v1` s lidskou provenance;
- Human Review `pass` pro stejné PR/SHA/package;
- required governance documents;
- explicitní `-ConfirmMerge` pro actual merge.

`merge-pr` je **merge-only**. Nečte HRDR, nevyhodnocuje Release Scope Gate a nevytváří release package, release validation ani tag.

Na čistém runneru lze evidence předat explicitně pomocí `-PackagePath <downloaded.zip> -ValidationReportPath <result.json>`. Oba vstupy jsou povinný pár; reportovaná stará cesta se v tomto režimu nepoužívá.

### Review PR / HRDR scaffold

`review-pr` je release-candidate command. Po frozen release-candidate validaci lze vytvořit HRDR scaffold:

```powershell
.\ddda.ps1 review-pr -Pr <RELEASE_PR> -Version 0.1.1 -Reviewer <login> -DecisionOwner <login> -PublishScaffold
```

Automation vytváří pouze `decision=pending`; nevytváří `GO`, nepřijímá residual risk a nevolí člověka, který smí release rozhodnout.

### Promote PR

`promote-pr` je **release command**, ne obecný implementation merge command.

Preflight:

```powershell
.\ddda.ps1 promote-pr -Pr <RELEASE_PR> -Version 0.1.1 -DryRun
```

Skutečný promotion:

```powershell
.\ddda.ps1 promote-pr -Pr <RELEASE_PR> -Version 0.1.1 -ConfirmMerge
```

Volitelné parametry:

- `-WithMiro`, `-Full`, `-CleanupOnFailure` — online release acceptance;
- `-KeepArtifacts` — zachová promotion workspace;
- `-NonInteractive` — zakáže secret prompt.

Public `promote-pr` nejdříve fail-closed validuje právě jeden authoritativní human HRDR a Release Scope Gate nad live Milestone, native blockers a GitHub Project V2 projection. Interní release executor se nespustí, dokud gate není `PASS`.

`-ConfirmMerge` zde znamená explicitní **release/promotion authorization** pro release candidate. Předchozí implementation `merge-pr -ConfirmMerge` authorization se sem nepřenáší.

GitHub autentizace se načítá v pořadí `GH_TOKEN` → `GITHUB_TOKEN` → `gh auth token` → Git credential helper. GitHub CLI není povinný. Release Scope Gate navíc používá `DDDA_GITHUB_PROJECT_TOKEN` pouze ze secret store/process environment.

Během běžného vývoje mohou být release položky pod `## [Unreleased]`. Promotion preflight vyžaduje release sekci `## [X.Y.Z] - YYYY-MM-DD` odpovídající `-Version X.Y.Z`, prázdnou release-content část `Unreleased` a volný tag `vX.Y.Z`.

## Interní platform lifecycle skripty

### `Invoke-DDDAGovernedMergePr.ps1`

Governed implementation merge executor. Ověří exact-SHA CI, `validate-pr`, candidate package hash a Human Review evidence. `-DryRun` je bez side effects; actual merge vyžaduje `-ConfirmMerge`. Script nesmí volat HRDR, Release Scope Gate, release package/validation ani tag path.

### `New-DDDAPlatformPackage.ps1`

Vytvoří candidate nebo release ZIP z čistého versioned source state a přidá `ddda-package.json`.

### `Test-DDDAPlatformPackage.ps1`

Kontroluje manifest, package hash, povinné soubory, zakázané lokální cesty, cache a secret-like obsah.

### `Invoke-DDDAExampleIngestion.ps1`

Načte example manifest, ověří source/target boundaries, ingestuje syntetické vstupy a vytvoří report.

### `New-DDDAValidationWorkspace.ps1`

Z rozbaleného package vytvoří workspace a inicializuje validation scenario.

### `New-DDDAValidationReport.ps1`

Vytvoří JSON a Markdown validation report svázaný se source SHA a package SHA-256.

### `Invoke-DDDAGovernedPromotePr.ps1`

Read-only governance wrapper pro release `promote-pr`: ověří HRDR human provenance, exact release-candidate identity a Release Scope Gate; teprve po PASS deleguje na interní release executor.

### `Test-DDDAReleaseScope.py`

Read-only collector/evaluator live GitHub release scope. Používá Milestone/Issue/native dependency evidence a Project V2 read-back. Chybějící/nejednoznačná evidence je FAIL.

## Project steering compatibility commands

### `Install-DDDASteeringRuntime.ps1`

Instaluje izolovaný Python runtime do `.ddda/runtime/steering-venv`.

### `Initialize-DDDAProjectFirstRun.ps1`

Inicializuje konkrétní DDDA project workspace. Project runtime je oddělen od platform-development merge/release lifecycle.

### `Get-DDDAProjectStatus.ps1`

Výchozí režim je read-only; `-Refresh` explicitně přepočítá status.

### `Test-DDDAGates.ps1`

Vypíše evidence status projektových gatů.

### `Complete-DDDALifecycleStep.ps1`

Zaznamená explicitní project-gate outcome. Produkční human decision nesmí vytvářet automatizace.
