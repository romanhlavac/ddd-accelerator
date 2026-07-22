# DDDA — Domain-Driven Design Accelerator

DDDA je pracovní prostředí pro řízenou doménovou analýzu, návrh socio-technické architektury a inkrementální modernizaci systémů. Jedna instalace obsluhuje více navzájem oddělených projektů. Primárním workshopovým a modelovacím rozhraním je Miro; sémantickým zdrojem pravdy jsou verzované YAML artefakty v Gitu.

## Základní principy

- **Business a doména před technologií.**
- **Miro jako primární plocha pro spolupráci.**
- **YAML jako kanonický sémantický model.**
- **Git jako historie, audit a mechanismus review.**
- **Mermaid jako textová a automatizovatelná reprezentace diagramů.**
- **Explicitní hranice, ownership dat, integrační kontrakty a quality attributes.**
- **Hypotézy nejsou fakta:** každý artefakt má stav, původ, vlastníka a validační historii.

## Metodický tok

```text
Align
  ↓
Discover
  ↓
Big Picture EventStorming
  ↓
Process Modeling
  ↓
Decompose
  ↓
Strategize
  ↓
Connect
  ↓
Organize
  ↓
Define
  ↓
Design-Level EventStorming
  ↓
Code
```

EventStorming není jedna aktivita. DDDA rozlišuje:

1. **Big Picture EventStorming** pro společné porozumění doméně a hotspotům.
2. **Process Modeling** pro rozpad vybraných business toků.
3. **Design-Level EventStorming** pro návrh behaviorálního modelu uvnitř konkrétního bounded contextu.

Stavové modely vznikají postupně jako:

1. pozorovaný životní cyklus,
2. kandidátní životní cyklus,
3. validovaný business state machine,
4. implementační state machine, pouze pokud je skutečně potřebná.

## Struktura repozitáře

```text
.
├── ddda/
│   ├── schemas/              # validační schémata
│   └── scaffolds/            # definice Miro scaffoldů a metodického toku
├── docs/
│   ├── product/              # dokumentace produktu DDDA
│   ├── methodology/          # metodika a gates
│   └── cookbooks/            # praktické postupy krok za krokem
├── examples/
│   └── life-insurance-greenfield/
├── projects/                 # pracovní projekty; každý projekt je nezávislý
└── tools/                    # validační, renderovací a synchronizační nástroje
```

## Rychlý start

1. Vytvořte nový adresář projektu podle kuchařky `docs/cookbooks/01-zalozeni-projektu.md`.
2. Zvolte typ projektu a pracovní workflow.
3. Vytvořte nebo připojte Miro board.
4. Vygenerujte scaffold z `ddda/scaffolds/strategic-ddd-method-board.yaml`.
5. Veďte workshop v Miru a průběžně synchronizujte artefakty do YAML.
6. Validujte YAML proti schématům a generujte Mermaid pohledy.
7. Přijímejte změny přes Git review a metodické gates.

## Dokumentace

- [Architektura produktu](docs/product/01-architektura-ddda.md)
- [Struktura workspace a projektů](docs/product/02-workspace-a-projekty.md)
- [Miro scaffolding](docs/product/03-miro-scaffolding.md)
- [Synchronizace Miro ↔ YAML ↔ Git](docs/product/04-synchronizace.md)
- [Typy projektů](docs/product/05-typy-projektu.md)
- [Metodický tok a gates](docs/methodology/01-metodicky-tok-a-gates.md)
- [Kuchařky](docs/cookbooks/README.md)
- [Referenční příklad životní pojišťovny](examples/life-insurance-greenfield/README.md)

## Stav implementace

Tato větev zavádí cílovou strukturu, metodiku, scaffoldy, schémata, kuchařky a referenční příklad. Živý konektor k Miro API vyžaduje registraci Miro aplikace, OAuth tokeny a mapování konkrétního boardu; kontrakt, metadata a konfliktní strategie jsou již definovány v dokumentaci a schématech.
