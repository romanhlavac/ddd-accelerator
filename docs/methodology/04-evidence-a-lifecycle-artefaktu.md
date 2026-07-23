# Evidence a lifecycle artefaktů

## Evidence-first

Každý významný závěr musí obsahovat původ: source path, workshop, interview nebo explicitní rozhodnutí. Chat nesmí doplňovat chybějící doménová fakta obecným know-how bez označení inference.

## Čtyři úrovně lifecycle modelu

| Fáze | Status | Význam |
|---|---|---|
| Discover | observed | skutečně pozorované stavy a přechody |
| Decompose | candidate | hypotéza hranic a lifecycle |
| Define | validated | business state model schválený expertem |
| Code | implementation | technická state machine pouze pokud přináší hodnotu |

Každý přechod mezi úrovněmi má mít rationale a odkazy na původní artefakty.

## Spravované a nespravované Miro položky

Spravovaná položka má marker `DDDA:<project>:<artifact>`, YAML source path a záznam v `miro-map.yaml`. Nespravovaná položka je workshopová poznámka, hlasování, komentář nebo dočasná vizuální pomůcka. Runtime ji nemaže ani neimportuje automaticky.

## Povýšení poznámky

1. facilitátor vybere poznámku,
2. chat navrhne typ, ID, stage a status,
3. vznikne YAML candidate,
4. dry-run push ukáže Miro operaci,
5. po potvrzení se položka stane spravovanou,
6. změna projde Git review.

## Souběžná změna

Záznam souběžné změny je podklad pro doménové rozhodnutí. Uchovává společnou base, YAML a Miro variantu. Rozhodnutí se provede v YAML; následný push vytvoří novou společnou base.
