# DDDA — Domain-Driven Design Accelerator

DDDA je verzovatelný pracovní rámec pro doménovou analýzu, strategic a tactical DDD, socio-technický návrh, architektonická rozhodnutí a inkrementální modernizaci systémů.

DDDA odděluje dva životní cykly:

1. **platforma DDDA** — obecné skills, scaffoldy, schémata, automatizace a metodika,
2. **projektové repozitáře** — zadání, ingestion, doménové artefakty, ADR, workshopy, Miro vazby a výsledná architektura konkrétní iniciativy.

Jedna lokální instalace proto není jeden společný Git repozitář. Doporučený model je:

```text
DDDA-Workspace/
├── platform/
│   └── ddd-accelerator/        # Git repozitář produktu DDDA
├── projects/
│   ├── project-a/              # samostatný projektový Git repozitář
│   └── project-b/              # samostatný projektový Git repozitář
├── workspace.yaml              # lokální registr projektů
└── DDDA.code-workspace         # Cursor / VS Code multi-root workspace
```

## Základní principy

- Platformní změny a projektové změny se necommitují společně.
- Každý projekt má vlastní historii, přístupová práva a release/milestone lifecycle.
- Projekt eviduje přesný DDDA commit v `ddda.lock.yaml`.
- Upgrade DDDA vytváří kontrolovatelnou změnu v projektu; nepřepisuje projekty automaticky.
- YAML artefakty jsou verzovatelný kanonický model. Miro a Mermaid jsou projekce nad těmito artefakty, pokud projekt neurčí jinak.
- Agent před zápisem určí aktivní repozitář a scope změny.

## Obsah této distribuce

```text
.cursor/                 pravidla a skills pro agenty
.github/                 PR governance
schemas/                 JSON Schema kontrakty
scripts/                 bootstrap, validace scope a upgrade
migrations/              migrační mechanismus mezi verzemi DDDA
templates/               workspace a projektové scaffoldy
docs/                    produktová a metodická dokumentace
USAGE.md                  praktická kuchařka
```

## Rychlý start na Windows

```powershell
New-Item -ItemType Directory -Force C:\Work\DDDA-Workspace\platform | Out-Null
Set-Location C:\Work\DDDA-Workspace\platform

git clone https://github.com/romanhlavac/ddd-accelerator.git
Set-Location .\ddd-accelerator

.\scripts\Initialize-DDDAWorkspace.ps1 -WorkspaceRoot C:\Work\DDDA-Workspace
.\scripts\New-DDDAProject.ps1 `
  -WorkspaceRoot C:\Work\DDDA-Workspace `
  -ProjectId life-insurance-greenfield `
  -Name "Nová životní pojišťovna" `
  -Type portfolio-program

cursor C:\Work\DDDA-Workspace\DDDA.code-workspace
```

Podrobný postup je v [USAGE.md](USAGE.md). Git model a rozhodovací pravidla jsou v [docs/git-and-project-model.md](docs/git-and-project-model.md).

## Stav produktu

DDDA je zatím evoluční základ. Schémata a skripty definují bezpečný multi-project operating model. Plná obousměrná synchronizace Miro ↔ YAML ↔ Git vyžaduje samostatný synchronizační runtime a není tímto základem automaticky zajištěna.