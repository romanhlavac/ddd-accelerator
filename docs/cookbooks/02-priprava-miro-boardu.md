# Kuchařka 02 — Příprava Miro boardu

## Výsledek

Board obsahuje navigační osu, frame pro relevantní fáze, legendy, instrukce, gate checklisty a metadata projektu.

## Vstupy

- validní `project.yaml`,
- scaffold `ddda/scaffolds/strategic-ddd-method-board.yaml`,
- Miro board přidělený pouze danému projektu,
- seznam účastníků a plán workshopů.

## Postup

1. Ověřte, že board ID odpovídá projektu.
2. Načtěte scaffold a zvolte workflow profile; nepovinné fáze lze skrýt, nikoli tiše odstranit z metodiky.
3. Vytvořte horní navigaci Align → Discover → Process Modeling → Decompose → Strategize → Connect → Organize → Define → Code.
4. Vytvořte frame podle souřadnic a velikostí scaffoldů.
5. Do každého frame vložte cíl, vstupy, facilitační instrukci, legendu, pracovní oblast, otázky a gate.
6. Označte frame metadata `project_id`, `stage`, `artifact_type=frame` a `scaffold_id`.
7. Připravte parkoviště pro out-of-scope témata a oblast pro rozhodnutí.
8. Zamkněte navigaci, legendy a instrukce; pracovní plochy nechte editovatelné.
9. Proveďte dry-run synchronizace a uložte počáteční `miro-map.yaml`.
10. Udělejte desetiminutovou technickou zkoušku s facilitátorem.

## Kontroly

- Big Picture ES je v Discover, nikoli v Define.
- Process Modeling je explicitní most před Decompose.
- Design-Level ES je až v Define a je vázán na konkrétní bounded context.
- Lifecycle frames jsou na úrovních observed, candidate, validated a volitelně implementation.
- Barvy odpovídají centrální legendě.

## Chyby

- jeden obří frame bez metodického toku,
- import starého boardu bez stabilních ID,
- metadata jsou pouze v textu sticky note,
- zamknutá pracovní plocha nebo naopak odemčená legenda,
- přepis workshopových poznámek automatickou synchronizací.

## Navazující krok

Proveďte G1 a naplánujte Big Picture EventStorming.