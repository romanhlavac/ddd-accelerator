# Git a projektový model DDDA

## 1. Rozhodnutí

DDDA používá **jeden platformní Git repozitář a N nezávislých projektových Git repozitářů**.

```text
DDDA Workspace
├── Platform repository
└── Project repositories 1..N
```

Nejde o monorepozitář ani o Git submodules.

## 2. Platformní repozitář

Repozitář `romanhlavac/ddd-accelerator` vlastní:

- obecnou metodiku,
- skills a agentní pravidla,
- JSON Schema kontrakty,
- scaffoldy,
- bootstrap a upgrade skripty,
- synchronizační runtime,
- obecnou dokumentaci,
- produktové releasy DDDA.

Platformní commit nesmí obsahovat klientská nebo projektová data.

## 3. Projektový repozitář

Každý projekt vlastní:

- `project.yaml`,
- `ddda.lock.yaml`,
- ingestion vstupy,
- doménové a architektonické artefakty,
- ADR,
- workshopové podklady a záznamy,
- Miro mapování,
- reporty a exporty.

Projektový commit nesmí měnit platformní skills, schémata ani bootstrap skripty.

## 4. Kanonické vlastnictví artefaktů

Výchozí model:

```text
YAML = kanonický verzovatelný model
Miro = kolaborativní vizuální projekce
Mermaid = textová projekce pro chat a dokumentaci
Git = auditní stopa změn a rozhodnutí
```

Projekt může nastavit jiný režim, ale musí jej uvést v `project.yaml`.

## 5. Verze a lock

`project.yaml` vyjadřuje kompatibilitní požadavek. `ddda.lock.yaml` eviduje konkrétní platformní commit, se kterým byl projekt naposledy validován nebo migrován.

Příklad:

```yaml
ddda:
  repository: romanhlavac/ddd-accelerator
  ref: main
  commit: 0123456789abcdef
  schema_version: 1
  locked_at: 2026-07-22T12:00:00Z
```

Lock není dekorace. Umožňuje:

- reprodukovat transformaci artefaktů,
- určit potřebné migrace,
- porovnat projekty na různých verzích DDDA,
- zabránit tichému použití nekompatibilního schématu.

## 6. Repository scope guard

Každá změna musí deklarovat scope:

- `platform`, nebo
- `project`.

Scope guard odmítne pokračovat, pokud je současně změněn druhý repozitář. Smyslem není nahrazovat review, ale zabránit náhodnému smíchání dvou change lifecycle.

Doporučená formulace pro agenta:

```text
Scope: project
Aktivní projekt: life-insurance-greenfield
Povoleno: project.yaml, ddda.lock.yaml, ingestion/, artifacts/, decisions/, workshops/, miro/, reports/, exports/
Zakázáno: platformní repozitář DDDA
```

## 7. Upgrade lifecycle

```text
DDDA změna
→ platformní PR
→ merge
→ tag/release
→ projektová diagnostika
→ migrace projektu
→ změna locku
→ projektový PR
→ merge
```

DDDA release nesmí sám commitovat do všech projektů. Projekty se mohou pohybovat různým tempem a mohou mít rozdílné regulační nebo provozní constraints.

## 8. Projektový lifecycle

```text
Intake
→ ingestion
→ discovery
→ modelování
→ validace
→ rozhodnutí
→ architektonický návrh
→ evoluce
```

Git commit má vyjadřovat význam změny, ne pouze technickou operaci synchronizace.

Dobře:

```text
model(policy): split lifecycle and servicing contexts
```

Slabě:

```text
update yaml files
```

## 9. Miro synchronizace

Budoucí synchronizační runtime musí při každé změně znát:

- workspace ID,
- project ID,
- board ID,
- artifact ID,
- typ artefaktu,
- revizi YAML,
- revizi Miro objektu,
- zdroj změny,
- merge policy.

Synchronizace musí vytvářet projektové změny. Samotný synchronizační kód se verzí v platformním repozitáři.

## 10. Konflikty

Při souběžné změně YAML a Miro nesmí platit implicitní last-write-wins. Výchozí politika:

1. detekovat rozdílné revize,
2. vytvořit konflikt report,
3. zachovat oba vstupy,
4. požadovat doménové nebo architektonické rozhodnutí,
5. teprve potom vytvořit sjednocený projektový commit.

## 11. Přístupová práva

Oddělené repozitáře umožňují:

- oddělit klientská data,
- dát týmu přístup pouze k jeho projektu,
- sdílet platformu bez sdílení doménového obsahu,
- samostatně archivovat nebo předat projekt,
- zavést odlišnou branch protection a review politiku.

## 12. Proč ne monorepozitář

Monorepozitář by spojil produktové releasy DDDA s projektovými milníky, zkomplikoval přístupová práva a zvýšil riziko náhodných cross-project commitů.

## 13. Proč ne Git submodules

Submodules přidávají druhou vrstvu commit pointerů, detached HEAD scénáře a složitější bootstrap. Pro lokální multi-root workspace nejsou potřebné. Workspace registry řeší navigaci bez vazby životních cyklů.