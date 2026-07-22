# Kuchařka 02 — Příprava Miro boardu

## Výsledek

Board obsahuje navigační osu, frame pro relevantní fáze, legendy, instrukce, gate checklisty a metadata projektu.

## Vstupy

- validní `project.yaml`,
- scaffold `scaffolds/miro/strategic-ddd-method-board.yaml`,
- schéma `schemas/miro-scaffold.schema.json`,
- Miro board přidělený pouze danému projektu,
- seznam účastníků a plán workshopů.

## Postup

1. Ověřte, že board ID odpovídá projektu.
2. Načtěte scaffold a zvolte workflow profile; nepovinné fáze lze skrýt, nikoli tiše odstranit z metodiky.
3. Vytvořte horní navigaci Align → Discover → Decompose → Strategize → Connect → Organize → Define → Code.
4. Vytvořte frame podle souřadnic a velikostí scaffoldu.
5. Do každého frame vložte cíl, vstupy, facilitační instrukci, legendu, pracovní oblast, otázky a gate.
6. Označte frame metadata `dd_d_a_id`, `dd_d_a_stage`, `dd_d_a_artifact_type` a `dd_d_a_source_path`.
7. Připravte parkoviště pro out-of-scope témata a oblast pro rozhodnutí.
8. Zamkněte navigaci, legendy a instrukce; pracovní plochy nechte editovatelné.
9. Připravte projektový soubor `miro/miro-map.yaml`; tokeny a secrets do něj nepatří.
10. Proveďte desetiminutový dry-run s facilitátorem.

## Aktuální omezení

Deklarativní scaffold a synchronizační kontrakt jsou součástí DDDA. Automatický Miro API renderer a obousměrný synchronizační worker zatím nejsou implementovány. Board je proto v této alpha verzi nutné připravit ručně podle scaffoldu nebo pomocí navazujícího integračního nástroje.

## Kontroly

- Big Picture ES je v Discover, nikoli v Define.
- Process Modeling je explicitní most mezi Discover a Decompose.
- Design-Level ES je až v Define a je vázán na konkrétní bounded context.
- Lifecycle frames jsou na úrovních observed, candidate, validated a volitelně implementation.
- Barvy odpovídají centrální legendě.
- Stabilní ID a YAML cesty nejsou nahrazeny pouze názvem sticky note.

## Chyby

- jeden obří frame bez metodického toku,
- import starého boardu bez stabilních ID,
- metadata jsou pouze v textu sticky note,
- zamknutá pracovní plocha nebo odemčená legenda,
- přepis workshopových poznámek automatickou synchronizací,
- tvrzení, že živá synchronizace funguje, přestože není nasazen Miro konektor.

## Navazující krok

Proveďte G1 a naplánujte Big Picture EventStorming.
