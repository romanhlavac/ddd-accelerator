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

Package-dependent suites dostávají:

```powershell
.\ddda.ps1 test -Suite e2e -PackagePath $PackagePath
```

Online acceptance:

```powershell
.\ddda.ps1 test -Suite acceptance -WithMiro -Full -CleanupOnFailure
```

### Validate PR

```powershell
.\ddda.ps1 validate-pr -Pr 8
```

Volitelné parametry:

- `-WithMiro` — přidá online Miro acceptance;
- `-Full` — plný Miro smoke rozsah;
- `-CleanupOnFailure` — odstraní neúspěšný testovací Miro board, pokud je znám;
- `-KeepArtifacts` — zachová isolated checkout a workspaces i při PASS;
- `-NonInteractive` — nepovolí prompt pro chybějící secret.

Příkaz testuje exact PR head SHA, candidate package a generovaný example workspace. Aktivní větev a working tree nemění.

### Promote PR

Preflight:

```powershell
.\ddda.ps1 promote-pr -Pr 8 -Version 0.8.0 -DryRun
```

Skutečný promotion:

```powershell
.\ddda.ps1 promote-pr -Pr 8 -Version 0.8.0 -ConfirmMerge
```

Volitelné parametry:

- `-WithMiro`, `-Full`, `-CleanupOnFailure` — online release acceptance;
- `-KeepArtifacts` — zachová promotion workspace;
- `-NonInteractive` — zakáže secret prompt.

`-ConfirmMerge` je povinná explicitní approval boundary. Bez něj se merge neprovede.

GitHub autentizace se načítá v pořadí `GH_TOKEN` → `GITHUB_TOKEN` → `gh auth token` → Git credential helper. GitHub CLI není povinný. Token nemá veřejný CLI parametr.

Preflight vyžaduje release sekci `## [X.Y.Z] - YYYY-MM-DD` odpovídající `-Version X.Y.Z`, prázdnou `## [Unreleased]` sekci a volný tag `vX.Y.Z`.

## Interní platform lifecycle skripty

### `New-DDDAPlatformPackage.ps1`

Vytvoří candidate nebo release ZIP z čistého versioned source state a přidá `ddda-package.json`.

### `Test-DDDAPlatformPackage.ps1`

Kontroluje manifest, package hash, povinné soubory, zakázané lokální cesty, cache a secret-like obsah.

### `Invoke-DDDAExampleIngestion.ps1`

Načte `examples/minimal/manifest.yaml`, ověří source/target boundaries, zkopíruje syntetické vstupy a vytvoří ingestion report.

### `New-DDDAValidationWorkspace.ps1`

Z rozbaleného package vytvoří workspace, ingestuje minimal example a inicializuje steering projekt v `align/G1`.

### `New-DDDAValidationReport.ps1`

Vytvoří JSON a Markdown validation report svázaný se source SHA a package SHA-256.

## Project steering compatibility commands

### `Install-DDDASteeringRuntime.ps1`

Instaluje izolovaný Python runtime do `.ddda/runtime/steering-venv`.

### `Initialize-DDDAProjectFirstRun.ps1`

Povinné parametry: `-WorkspaceRoot`, `-IntakeFile`.

Důležité přepínače:

- `-WithMiro` — vytvoří a otestuje projektový board;
- `-Resume` — bezpečně pokračuje v existujícím projektu;
- `-NoInitialCommit` — pouze pro offline testy;
- `-NonInteractive` — zakáže prompt na chybějící token;
- `-ForceRecreateRuntime` — znovu vytvoří steering runtime.

### `Get-DDDAProjectStatus.ps1`

Výchozí režim je read-only a načte `reports/project-status.yaml` bez změny Git working tree.

- `-Json` — vrátí strojově čitelný výstup;
- `-Refresh` — explicitně přepočítá a zapíše current status, next actions a status report.

Po `-Refresh` zkontroluj a commitni změny před navazující Miro operací.

### `Test-DDDAGates.ps1`

Vypíše evidence status všech gatů nebo jedné gate přes `-Gate`.

### `Complete-DDDALifecycleStep.ps1`

Zaznamená explicitní outcome `passed`, `conditional` nebo `rejected`. `-Commit` vytvoří lokální commit po `diff --check`; push ani merge neprovádí.

### `Test-DDDAAcceptance.ps1`

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering [-WithMiro] [-Full] [-KeepReviewBoard] [-CleanupOnFailure]
```
