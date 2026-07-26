# PR #8 migration note — aditivní steering a platform lifecycle

## Scope

PR #8 přidává chat-first project steering, project-owned Miro publikaci a platformní development lifecycle. Nemění kanonickou starter metodiku ani neruší stávající veřejné PowerShell entry points.

## Compatibility

Migration impact: **Non-breaking / additive**.

Zachováno:

- `workspace.yaml` a multi-repository workspace model;
- `project.yaml` a `ddda.lock.yaml`;
- samostatný Git repozitář každého projektu;
- existující example projekt `life-insurance-greenfield`;
- starter tok Align → Code a gaty G1–G8;
- project-owned Miro board;
- stávající Miro mapping a sync semantics;
- Windows PowerShell 5.1 tam, kde je již podporován;
- PowerShell 7 jako kanonický platformní runtime;
- offline first-run.

## New additive files

Nově řízený projekt může obsahovat:

```text
project-intake.yaml
project-profile.yaml
lifecycle-tailoring.yaml
artifacts/status/current-status.yaml
artifacts/status/next-actions.yaml
decisions/gates/G1.yaml ... G8.yaml
.ddda/session-context.yaml
.ddda/agent-contract.yaml
reports/project-status.yaml
```

Platforma dále přidává `ddda.ps1`, candidate/release packaging, validation reporty a manifest-driven minimal example.

## Existing workspaces

Existující workspace se nemění automaticky. Starší projekt lze dál používat původními příkazy.

Pro zavedení steering metadat do existujícího projektu:

1. připrav intake soubor;
2. spusť `Initialize-DDDAProjectFirstRun.ps1 -Resume`;
3. zkontroluj vytvořené a změněné soubory;
4. commitni je v projektovém repozitáři;
5. Miro bootstrap spusť až nad čistým projektovým repozitářem.

Žádná existující gate nebude automaticky označena jako `passed`.

## Git and generated outputs

Platformní validation a release outputs se ukládají mimo Git nebo do ignorovaných adresářů:

```text
.tmp/
.reports/
.releases/
dist/
```

Klientské workspaces se nesmějí kopírovat do example fixtures ani release package.

## Rollback

Rollback PR #8 nevyžaduje konverzi projektových dat. Nové steering soubory jsou aditivní. Starší platformní verze je pouze nebude interpretovat.

Miro board a mapping lze zachovat; access token zůstává mimo Git.
