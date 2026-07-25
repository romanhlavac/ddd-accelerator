# CLI reference — project steering

## `Install-DDDASteeringRuntime.ps1`

Instaluje izolovaný Python runtime do `.ddda/runtime/steering-venv`.

## `Initialize-DDDAProjectFirstRun.ps1`

Povinné parametry: `-WorkspaceRoot`, `-IntakeFile`.

Důležité přepínače:

- `-WithMiro` — vytvoří a otestuje projektový board;
- `-Resume` — bezpečně pokračuje v existujícím projektu;
- `-NoInitialCommit` — pouze pro offline testy;
- `-NonInteractive` — zakáže prompt na chybějící token;
- `-ForceRecreateRuntime` — znovu vytvoří steering runtime.

## `Get-DDDAProjectStatus.ps1`

Regeneruje status. `-Json` vrátí strojově čitelný výstup.

## `Test-DDDAGates.ps1`

Vypíše evidence status všech gatů nebo jedné gate přes `-Gate`.

## `Complete-DDDALifecycleStep.ps1`

Zaznamená explicitní outcome `passed`, `conditional` nebo `rejected`. `-Commit` vytvoří lokální commit po `diff --check`; push ani merge neprovádí.

## `Test-DDDAAcceptance.ps1`

```powershell
.\scripts\Test-DDDAAcceptance.ps1 -Suite project-steering [-WithMiro] [-Full] [-KeepReviewBoard]
```
