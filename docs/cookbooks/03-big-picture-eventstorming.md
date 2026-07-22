# Kuchařka 03 — Big Picture EventStorming

## Výsledek

Vznikne společný obraz významného end-to-end business dění, pracovní slovník, hotspoty, pivot events a pozorované životní cykly.

## Předpoklady

- G1 je splněn nebo podmíněně schválen,
- účastní se business role s reálnou znalostí procesu,
- scope workshopu je formulován businessově,
- frame `big-picture-es` je připraven.

## Role

- facilitátor řídí postup a chrání business-first diskusi,
- doménoví experti popisují fakta a výjimky,
- zapisovatel spravuje otázky a rozhodnutí,
- architekt sleduje hranice, pravidla a quality attributes, ale nenavrhuje služby.

## Postup

1. Připomeňte cíl, scope, časový limit a barevnou legendu.
2. Účastníci zapisují samostatně významné doménové události v minulém čase.
3. Události se řadí na časovou osu; duplicity se dočasně zachovají, pokud mohou vyjadřovat rozdílný význam.
4. Doplňte časové události a externí spouštěče.
5. Označte pivot events, které mění fázi procesu, odpovědnost nebo business riziko.
6. Doplňte aktéry a externí systémy pouze tam, kde pomáhají porozumění.
7. Červeně evidujte nejasnosti, výjimky, konfliktní jazyk a chybějící vlastníky.
8. Projděte unhappy paths, ruční zásahy, storna a regulatorní scénáře.
9. Identifikujte klíčové objekty s pozorovanými stavy; přesuňte je do frame observed lifecycles.
10. Proveďte společný playback od začátku do konce.
11. Povýšte stabilní poznámky na spravované artefakty; ostatní ponechte jako workshopové poznámky.
12. Synchronizujte do YAML a vytvořte backlog otázek.

## Facilitační otázky

- Co se stalo předtím a jak to víme?
- Co je business fakt a co pouze technická notifikace?
- Kdo může tento výsledek zpochybnit nebo zvrátit?
- Jaká výjimka je drahá, častá nebo regulatorně významná?
- Používají dvě skupiny stejný pojem jinak?
- Kdy se mění odpovědnost za data nebo rozhodnutí?

## Definition of Done

- hlavní tok lze přehrát jako srozumitelný příběh,
- události jsou businessové a v minulém čase,
- existuje explicitní seznam hotspotů,
- důležité pojmy mají pracovní definice,
- životní cykly jsou označeny jako observed, nikoli target,
- nejasnosti mají ownera nebo plán validace.

## Typické chyby

- kreslení současné systémové architektury místo business dění,
- nahrazování událostí stavovými hodnotami `StatusChanged`,
- snaha vyřešit všechny hotspoty během jednoho workshopu,
- předčasné zakreslení bounded contexts,
- dominance jednoho technického účastníka.

## Navazující krok

Vyberte scénáře s vysokou hodnotou, nejistotou nebo rizikem a pokračujte Process Modelingem.