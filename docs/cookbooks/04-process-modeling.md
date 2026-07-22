# Kuchařka 04 — Process Modeling

## Výsledek

Prioritní scénář je rozpracován do aktérů, akcí/commandů, rozhodovacích policies, externích systémů, událostí, read modelů, hodnoty a výjimek.

## Postup

1. Vyberte scénář podle business hodnoty, nejistoty nebo rizika.
2. Definujte spouštěč, očekávaný výsledek a hranici scénáře.
3. Vyznačte aktéra a jeho záměr.
4. Přidejte command/action; používejte business jazyk.
5. Doplňte UI pouze jako interakční bod, nikoli návrh obrazovky.
6. U rozhodovacích míst popište policy/procedure a požadovaná fakta.
7. Vyznačte externí systém pouze tam, kde má vlastní odpovědnost nebo kontrakt.
8. Po každé významné změně zapište doménovou událost.
9. Doplňte read model nebo informaci, kterou aktér potřebuje k rozhodnutí.
10. Označte vytvořenou business hodnotu a náklady zpoždění/chyby.
11. Projděte alternativy, timeouty, ruční zásahy a zamítnutí.
12. Zapište signály pro kandidátní hranice: změna jazyka, pravidel, vlastníka, lifecycle nebo tempa změn.

## Kontroly

- model lze přečíst jako příčinný příběh,
- policy není zaměněna za technický workflow engine,
- read model neimplikuje databázovou tabulku,
- technický endpoint není command bez business záměru,
- hodnotu lze spojit s business cílem z Align.

## Navazující krok

Výsledky použijte v Decompose pro formulaci subdomén a boundary hypotheses.