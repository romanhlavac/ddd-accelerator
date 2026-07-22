# DDDA — praktická kuchařka

Tento návod popisuje instalaci DDDA, vytvoření workspace, založení nezávislého projektu, práci s Git větvemi a Pull Requesty a bezpečné oddělení platformních a projektových commitů.

## 1. Předpoklady

Na Windows potřebuješ:

- Git,
- Cursor nebo Visual Studio Code,
- PowerShell 7 doporučeně, Windows PowerShell 5.1 minimálně,
- přístup k privátnímu repozitáři `romanhlavac/ddd-accelerator`.

Ověření:

```powershell
git --version
$PSVersionTable.PSVersion
cursor --version
```

## 2. Doporučená lokální struktura

```text
C:\Work\DDDA-Workspace\
├── platform\
│   └── ddd-accelerator\
├── projects\
├── workspace.yaml
└── DDDA.code-workspace
```

Adresář `platform\ddd-accelerator` je Git repozitář produktu DDDA. Každý adresář pod `projects\` je samostatný Git repozitář konkrétní iniciativy.

## 3. Stažení DDDA na PC

### 3.1 Doporučená varianta — Git clone

```powershell
New-Item -ItemType Directory -Force C:\Work\DDDA-Workspace\platform | Out-Null
Set-Location C:\Work\DDDA-Workspace\platform

git clone https://github.com/romanhlavac/ddd-accelerator.git
Set-Location .\ddd-accelerator

git status
git remote -v
```

`git clone` zachová historii, větve a vazbu na GitHub. Varianta **Download ZIP** je vhodná jen pro prohlížení; neobsahuje `.git` a není vhodná pro PR workflow.

### 3.2 Inicializace workspace

```powershell
.\scripts\Initialize-DDDAWorkspace.ps1 `
  -WorkspaceRoot C:\Work\DDDA-Workspace
```

Skript:

- ověří, že je spuštěn z platformního repozitáře,
- vytvoří `projects\`,
- vytvoří nebo zachová `workspace.yaml`,
- vytvoří `DDDA.code-workspace`,
- zapíše cestu a commit platformy.

## 4. Vytvoření nového projektu

```powershell
.\scripts\New-DDDAProject.ps1 `
  -WorkspaceRoot C:\Work\DDDA-Workspace `
  -ProjectId life-insurance-greenfield `
  -Name "Nová životní pojišťovna" `
  -Type portfolio-program
```

Volitelně lze připojit vzdálený repozitář:

```powershell
.\scripts\New-DDDAProject.ps1 `
  -WorkspaceRoot C:\Work\DDDA-Workspace `
  -ProjectId life-insurance-greenfield `
  -Name "Nová životní pojišťovna" `
  -Type portfolio-program `
  -RemoteUrl https://github.com/romanhlavac/life-insurance-greenfield.git
```

Skript vytvoří:

```text
projects\life-insurance-greenfield\
├── .git\
├── project.yaml
├── ddda.lock.yaml
├── ingestion\
├── artifacts\
├── decisions\
├── workshops\
├── miro\
├── reports\
└── exports\
```

Projekt je samostatný Git repozitář. První commit obsahuje pouze projektový scaffold a lock na konkrétní DDDA commit.

## 5. Typy projektů

| Kanonický typ | Starší/kompatibilní aliasy | Použití |
|---|---|---|
| `portfolio-program` | `enterprise-transformation`, `transformation-program` | Více produktů, domén nebo pracovních proudů; společná strategie, capability mapa, více context maps a roadmapa. |
| `greenfield-product` | `greenfield`, `new-product` | Návrh nové digitální služby nebo systému bez dominantního legacy omezení. |
| `legacy-modernization` | `modernization`, `legacy-transformation`, `brownfield` | Inkrementální modernizace, strangler slices, data ownership, koexistence a decommission. |
| `domain-discovery` | `discovery`, `strategic-ddd` | Rychlé doménové poznání, EventStorming, subdomény, bounded contexts a otevřené otázky. |
| `architecture-review` | `review`, `architecture-assessment` | Posouzení existujícího návrhu, quality attributes, rizika, ADR a akční plán. |
| `bounded-context-design` | `tactical-ddd`, `bc-design` | Detail jednoho bounded contextu: agregáty, invarianty, lifecycle, domain events a aplikační hranice. |

Projekt může uvést `type_alias`, ale automatizace používá kanonický `type`.

## 6. Otevření v Cursoru

```powershell
cursor C:\Work\DDDA-Workspace\DDDA.code-workspace
```

Multi-root workspace zobrazuje minimálně:

- `DDDA Platform`,
- každý registrovaný projekt.

V Source Control se zobrazí více Git repozitářů. Před commitem vždy ověř, který repozitář je aktivní.

## 7. Bezpečný pracovní režim

### 7.1 Projektová změna

Příklad požadavku pro chat/agenta:

> Pracuj pouze v projektu `life-insurance-greenfield`. Uprav projektové YAML artefakty a Mermaid projekce. Platformní repozitář DDDA neměň. Připrav projektový commit, ale nepushuj bez mého pokynu.

Před commitem:

```powershell
.\platform\ddd-accelerator\scripts\Test-DDDARepositoryScope.ps1 `
  -PlatformPath C:\Work\DDDA-Workspace\platform\ddd-accelerator `
  -ProjectPath C:\Work\DDDA-Workspace\projects\life-insurance-greenfield `
  -Scope project
```

Potom v projektu:

```powershell
Set-Location C:\Work\DDDA-Workspace\projects\life-insurance-greenfield

git switch main
git pull --ff-only
git switch -c model/policy-context-boundary

# úpravy
git status
git diff

git add artifacts project.yaml
git commit -m "model(policy): refine context boundary"
git push -u origin model/policy-context-boundary
```

### 7.2 Platformní změna

Příklad požadavku:

> Toto je obecné rozšíření DDDA. Měň pouze platformní repozitář. Projektové repozitáře nesmí být součástí změny.

```powershell
Set-Location C:\Work\DDDA-Workspace\platform\ddd-accelerator

git switch main
git pull --ff-only
git switch -c feat/new-artifact-schema

# úpravy
git status
git diff

.\scripts\Test-DDDARepositoryScope.ps1 `
  -PlatformPath $PWD `
  -ProjectPath C:\Work\DDDA-Workspace\projects\life-insurance-greenfield `
  -Scope platform

git add schemas templates docs scripts
git commit -m "feat(artifacts): add stakeholder influence map"
git push -u origin feat/new-artifact-schema
```

## 8. Pull Request workflow

Jedna logická změna má mít jednu větev a jeden PR.

### 8.1 Kontrola PR v GitHub UI

- **Conversation** — účel, diskuse, kontroly.
- **Commits** — jednotlivé kroky změny.
- **Files changed** — skutečný diff; hlavní místo pro review.

### 8.2 Doporučené výsledky review

- `Comment` — připomínka bez blokace.
- `Request changes` — změna nemá být mergována.
- `Approve` — změna je přijatelná.

### 8.3 Draft versus Ready for review

Draft PR znamená, že je změna rozpracovaná. Po dokončení validace se přepne na **Ready for review**.

### 8.4 Merge strategie

Pro DDDA doporučeně **Squash and merge**:

- jedna logická změna se objeví v `main` jako jeden commit,
- dílčí technické commity nezatěžují historii,
- PR zůstane auditní stopou.

Po merge:

```powershell
git switch main
git pull --ff-only
git fetch --prune
```

## 9. Práce s existujícím PR před merge

```powershell
Set-Location C:\Work\DDDA-Workspace\platform\ddd-accelerator

git fetch origin
git switch --track origin/agent/miro-method-flow-scaffolds
```

Návrat:

```powershell
git switch main
```

## 10. Upgrade projektu na novou DDDA verzi

Projekt se neupgraduje implicitně. Nejprve vytvoř projektovou větev:

```powershell
Set-Location C:\Work\DDDA-Workspace\projects\life-insurance-greenfield
git switch main
git pull --ff-only
git switch -c chore/upgrade-ddda
```

Potom:

```powershell
C:\Work\DDDA-Workspace\platform\ddd-accelerator\scripts\Update-DDDAProject.ps1 `
  -PlatformPath C:\Work\DDDA-Workspace\platform\ddd-accelerator `
  -ProjectPath $PWD `
  -TargetRef main
```

Skript:

- vyžaduje čistý pracovní strom,
- resolve cílový commit DDDA,
- spustí dostupné migrační kroky,
- aktualizuje `ddda.lock.yaml`,
- změny necommitne automaticky, pokud není uvedeno `-Commit`.

Zkontroluj diff a otevři projektový PR.

## 11. Doporučené názvy commitů

Platforma:

```text
feat(miro): add scaffold renderer
fix(schema): reject duplicate artifact identifiers
docs(usage): clarify project bootstrap
chore(release): prepare v0.3.0
```

Projekt:

```text
model(claims): add claim assessment lifecycle
adr: select modular monolith for initial delivery
workshop: record big-picture event storming outcomes
miro(context-map): synchronize underwriting dependency
chore(ddda): upgrade accelerator lock
```

## 12. Co nedělat

- Necommitovat projektové artefakty do platformního repozitáře.
- Nevkládat více klientských projektů do jednoho Git repozitáře.
- Nepoužívat Git submodules jako výchozí mechanismus.
- Nemergovat draft PR bez kontroly `Files changed`.
- Neupgradovat projekty hromadným přepisem bez projektových PR.
- Nevydávat Miro nebo Mermaid projekci za kanonický model, pokud `project.yaml` určuje YAML jako source of truth.

## 13. Diagnostika

Přehled stavů:

```powershell
git -C C:\Work\DDDA-Workspace\platform\ddd-accelerator status
git -C C:\Work\DDDA-Workspace\projects\life-insurance-greenfield status
```

Ověření remotes:

```powershell
git -C C:\Work\DDDA-Workspace\platform\ddd-accelerator remote -v
git -C C:\Work\DDDA-Workspace\projects\life-insurance-greenfield remote -v
```

Ověření locku projektu:

```powershell
Get-Content C:\Work\DDDA-Workspace\projects\life-insurance-greenfield\ddda.lock.yaml
```