# DDDA — Domain-Driven Design Accelerator

DDDA je Miro-first, multi-project pracovní prostředí pro řízenou doménovou analýzu, socio-technickou architekturu a inkrementální modernizaci systémů. Jedna instalace DDDA obsluhuje více oddělených projektů. Každý projekt má vlastní Git repozitář a vlastní historii, zatímco samotná platforma DDDA je verzována samostatně.

## Základní principy

- business problém a doména před technologií,
- Miro jako primární workshopová a modelovací plocha,
- YAML jako kanonický sémantický model,
- Git jako audit, historie a review mechanismus,
- Mermaid jako textový a verzovatelný odvozený pohled,
- explicitní hranice, ownership dat, integrační kontrakty a quality attributes,
- žádné automatické last-write-wins pro sémantické konflikty.

## Co je v tomto repozitáři

```text
.
├── .cursor/                    # pravidla pro práci agentů a scope guard
├── .github/                    # PR template a validační workflow
├── docs/
│   ├── cookbooks/              # praktické návody krok za krokem
│   ├── methodology/            # metodický tok a gates
│   └── product/                # produktová architektura a integrace
├── examples/                   # referenční projekty
├── migrations/                 # migrace projektových schémat
├── scaffolds/                  # Miro a další deklarativní scaffoldy
├── schemas/                    # JSON Schema kontrakty
├── scripts/                    # bootstrap, validace, scope guard a upgrade
├── templates/                  # šablony workspace a projektu
├── USAGE.md                    # hlavní provozní návod
└── README.md
```

## Rychlý start na Windows

```powershell
git clone https://github.com/romanhlavac/ddd-accelerator.git
Set-Location .\ddd-accelerator

.\scripts\Test-DDDAInstallation.ps1 -PlatformPath $PWD

.\scripts\Initialize-DDDAWorkspace.ps1 `
  -WorkspaceRoot C:\Work\DDDA-Workspace

.\scripts\New-DDDAProject.ps1 `
  -WorkspaceRoot C:\Work\DDDA-Workspace `
  -ProjectId life-insurance-greenfield `
  -Name "Nová životní pojišťovna" `
  -Type portfolio-program
```

## Dokumentace

- [Použití DDDA](USAGE.md)
- [Git a projektový model](docs/git-and-project-model.md)
- [Typy projektů a pracovní toky](docs/project-types-and-flows.md)
- [Architektura produktu](docs/product/01-architektura-ddda.md)
- [Workspace a více projektů](docs/product/02-workspace-a-projekty.md)
- [Miro scaffolding](docs/product/03-miro-scaffolding.md)
- [Synchronizace Miro ↔ YAML ↔ Git](docs/product/04-synchronizace.md)
- [Typy projektů](docs/product/05-typy-projektu.md)
- [Metodický tok a gates](docs/methodology/01-metodicky-tok-a-gates.md)
- [Miro scaffold podle referenčního boardu](docs/miro-scaffolds.md)
- [Kuchařky](docs/cookbooks/README.md)
- [Referenční projekt životní pojišťovny](examples/life-insurance-greenfield/README.md)

## Aktuální stav

Tato verze obsahuje použitelný multi-project bootstrap, samostatné projektové Git repozitáře, lockování verze DDDA, scope guard, upgrade mechanismus, dokumentaci, kuchařky, referenční příklad a deklarativní Miro scaffold.

Živý Miro API renderer a obousměrný synchronizační worker zatím nejsou implementovány. Současná dokumentace a metadata kontrakt připravují jejich bezpečnou následnou implementaci.