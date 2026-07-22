# Miro scaffolding

## Účel

Scaffold není výsledný doménový model. Je to řízená pracovní plocha, která účastníkům ukazuje, kde se v metodickém toku nacházejí, jaký typ otázky právě řeší, jaké artefakty mají vzniknout a jaká validační brána následuje.

## Zásady návrhu boardu

1. Tok je zleva doprava a vždy viditelný v horní navigaci.
2. Každá fáze má vlastní frame, cíl, vstupy, instrukce, pracovní plochu a gate.
3. Barvy mají stabilní význam napříč všemi projekty.
4. Workshopové poznámky nejsou automaticky považovány za kanonické artefakty.
5. Kandidátní a validované modely jsou vizuálně i metadatově odlišeny.
6. Stavové diagramy nejsou jednorázový výstup; jejich zralost se mění v toku.

## Umístění EventStormingu

### Big Picture EventStorming — Discover

Cíl: společné pochopení end-to-end business dění.

Používat:

- doménové události,
- časové události,
- pivot events,
- aktéry a externí systémy,
- hotspoty,
- horizontální časovou osu.

Nepoužívat zde agregáty, databáze ani návrh služeb.

### Process Modeling — mezi Discover a Decompose

Cíl: rozpracovat vybrané scénáře a rozhodování.

Doporučená sekvence:

```text
Actor → Command/Action → UI → Policy/Procedure → External System → Event → Read Model → Value
```

Jde o most mezi širokým Big Picture pohledem a dekompozičními hypotézami. Nejde ještě o taktický návrh.

### Design-Level EventStorming — Define

Cíl: modelovat chování uvnitř konkrétního bounded contextu.

Doporučená sekvence:

```text
Actor → Command → Aggregate/Consistency Boundary → Invariant → Domain Event
      → Policy/Procedure → Command → Projection/Read Model
```

Design-Level ES musí navazovat na validovaný scope bounded contextu. Nesmí sloužit k dodatečnému maskování nejasných strategických hranic.

## Stavové diagramy v metodickém toku

| Fáze | Varianta | Otázka |
|---|---|---|
| Discover | observed | Jaké stavy a přechody dnes skutečně pozorujeme? |
| Decompose | candidate | Jaké životní cykly naznačují odlišné modely nebo hranice? |
| Define | validated | Jaký business state machine doménový expert schvaluje? |
| Code | implementation | Je explicitní implementační automat potřebný a jak mapuje business model? |

Přechod mezi úrovněmi není kopie. Každá další úroveň musí obsahovat zdůvodněné změny a odkazy na předchozí artefakt.

## Struktura frame

Každý spravovaný frame má:

- identifikátor,
- název a metodickou fázi,
- cíl,
- vstupy,
- instrukci pro facilitátora,
- legendu,
- pracovní plochu,
- oblast pro otázky a rozhodnutí,
- gate checklist,
- metadata synchronizace.

## Spravované a nespravované objekty

**Spravovaný objekt** má `artifact_id` a mapuje se do YAML. Synchronizace smí měnit jeho sémantický obsah podle pravidel.

**Nespravovaný objekt** je dočasná workshopová poznámka, obrázek, hlasování nebo komentář. Synchronizace jej zachová, dokud jej člověk nepovýší na artefakt nebo neodstraní.

## Povýšení workshopové poznámky

1. Facilitátor označí poznámku jako kandidátní artefakt.
2. Doplní typ, název, zdroj a status.
3. Sync vytvoří YAML se stabilním `artifact_id`.
4. Git review potvrdí nebo upraví sémantiku.
5. Objekt v Miru obdrží `yaml_path` a `git_revision`.

## Vizuální konvence

Barvy jsou definovány v `ddda/scaffolds/strategic-ddd-method-board.yaml`. Barva pomáhá orientaci, ale není jediným nositelem významu. Typ artefaktu musí být vždy uložen i v metadatech a textovém označení.

## Praktické omezení

Miro je vhodné pro facilitaci a prostorové vztahy, nikoli jako jediný auditovatelný repozitář sémantiky. Proto se business význam, ownership, status a vztahy ukládají do YAML a verzují v Gitu.