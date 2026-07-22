# Kuchařka 09 — Přidání typu projektu

## Výsledek

Vznikne nový konzistentní workflow profil, který nemění stávající projekty a má dokumentaci, scaffoldové odchylky, gate pravidla a referenční použití.

## Postup

1. Popište problém, který stávající typy nepokrývají.
2. Ověřte, zda nestačí `workflow.extensions`.
3. Zvolte kanonický název a legacy aliases.
4. Definujte kdy typ použít a kdy jej nepoužít.
5. Určete povinné, volitelné a vynechané fáze; každé vynechání zdůvodněte.
6. Doplňte specifické vstupy, rizika, artefakty a gates.
7. Určete změny Miro scaffoldů bez duplikace celého boardu.
8. Aktualizujte katalog typů, schema enum/profil a bootstrap validaci.
9. Přidejte varianty do dotčených kuchařek.
10. Přidejte minimální referenční projekt nebo fixture.
11. Ověřte zpětnou kompatibilitu existujících manifestů.

## Kontroly

- typ není pojmenován podle technologie,
- profil řeší odlišný rozhodovací problém, ne pouze jiné názvosloví,
- aliases jsou mapovány na jeden kanonický typ,
- gate kritéria jsou rozhodnutelná,
- nový typ má alespoň jeden příklad a negativní příklad,
- dokumentace, schema a kuchařky jsou změněny v jednom pull requestu.