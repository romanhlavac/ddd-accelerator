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
3. zkontroluj vytvořené aditivní soubory;
4. commitni je v projektovém repozitáři;
5. Miro bootstrap spusť až nad čistým projektovým repozitářem.

Resume adopce zachovává beze změny existující `project.yaml`, `ddda.lock.yaml`, `workspace.yaml`, repository origin a existující `miro/miro-map.yaml`. Stav adopce je zaznamenán v `.ddda/adoption.yaml`. Bez explicitního `-Resume` existující projekt nevytvoří steering metadata.

Kontrakt je automaticky dokazován syntetickým invariant-based testem:

```text
tests/powershell/Test-DDDALegacyWorkspaceCompatibility.ps1
tests/fixtures/legacy-workspace/baseline.json
```

Test je součástí component, integration a regression suite. Nepoužívá klientská data a ověřuje také, že žádná gate není automaticky označena jako `passed`.

Starší `passed` bez strukturované human provenance se po novém status přepočtu nepovažuje za platné schválení; evidence zůstává zachována a dotčená gate vyžaduje nové lidské review.

## Existing Miro boards

Při explicitním opakovaném Miro initializeru se existující project-owned board aktualizuje idempotentně:

- frames a systémové journey/legend items používají stabilní mapping;
- `00 – Control Center / Project State / Artifact Registry`, DDD Starter journey G1–G8 a vyšší zóny se aktualizují podle nového layout contractu;
- frames `20–82` přejdou na deterministické stage columns a třízónový shell; frames `01` a `10` se interně nemění;
- Artifact Registry nově odděluje Project/Gate State, Artifact Lifecycle a Artifact Provenance;
- unmanaged workshopový obsah se nemaže;
- layout existujícího managed doménového artefaktu se bez explicitního `--include-layout` nepřepisuje;
- project charter, current status a next actions se přesunou do `control-center` pouze jako řízené managed artefakty;
- technická aktualizace boardu končí `PENDING_HUMAN_REVIEW`, nikoli automatickým vizuálním PASS.

Před aktualizací produkčně používaného boardu zkontroluj dry-run a projektový Git diff. Pro validační a release testy používej izolovaný review board, nikoli klientský board.

### REM-PR8-HVA-CC-001 review isolation

Baseline board `uXjVH2o4NRU=`, human-review target `uXjVH2vcvRI=` a metodický reference board `uXjVH27wYU4=` jsou pouze read-only vstupy. Remediation acceptance musí vytvořit nový izolovaný board z exact candidate SHA; nesmí tyto boardy znovu použít ani modifikovat.

Změna scaffold schema `2.2 → 2.3` je aditivní vůči projektovým YAML artefaktům. Historický klíč `artifact_status_tables` zůstává čitelný kvůli kompatibilitě, ale jeho projekce je jeden devítisloupcový Artifact Registry. Nativní Miro Table se nevytváří, protože REST API v2 tento programový kontrakt neposkytuje.

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
