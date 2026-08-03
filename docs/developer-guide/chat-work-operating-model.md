# Chat/Work-only operating model pro vývoj DDDA

## Status a rozsah

Tento dokument je závazný pro vývoj DDDA platformy v prostředí ChatGPT.

```text
DDDA-EXECUTION-MODE: CHAT-WORK-ONLY
```

Povolená uživatelská rozhraní:

- **Chat**;
- **Work**.

Zakázaná rozhraní a vývojové režimy:

- **Codex**;
- legacy příkaz nebo režim **`/agent`**;
- jakýkoli jiný cloudový vývojový agent, který nebyl samostatně schválen bezpečnostní politikou.

Zákaz Codexu je governance constraint, nikoli preference. Návrh řešení jej nesmí obcházet přejmenováním nástroje nebo přesunem stejné činnosti do jiného neschváleného agenta.

## Rozdělení odpovědností

| Oblast | Chat | Work | GitHub Actions | Člověk |
|---|---|---|---|---|
| vysvětlení, návrh a trade-offy | ano | ano | ne | review |
| klasifikace změny a acceptance criteria | ano | ano | kontrola kontraktů | schválení scope |
| vícekroková práce s GitHubem, Miro a dokumenty | ne jako výchozí režim | ano | technická exekuce | autorizace rizikových zápisů |
| editace PR branche přes schválené konektory | ne | ano | ověření exact SHA | kontrola diffu |
| shell, build, testy a package-first validace | ne | ne | **autoritativní execution plane** | posouzení výsledku |
| secrets | nikdy | nikdy | pouze secret-bearing job | správa a rotace |
| merge, promotion, release a tag | pouze návrh | pouze po zvláštní autorizaci | guardrails a evidence | explicitní rozhodnutí |
| vizuální metodické review Miro | konzultace | načtení a porovnání boardů | strukturální kontroly | finální acceptance |

## Chat

Chat je výchozí pro:

- konzultace;
- návrh změny;
- doménovou a architektonickou analýzu;
- přípravu REM/change requestu;
- vyhodnocení evidence;
- autorizaci ohraničeného zápisu;
- lidské review a rozhodnutí.

Chat se nepoužívá k předstírání dlouhého implementačního běhu. Pokud úloha vyžaduje více konektorových operací, změny souborů, opakované ověření nebo koordinaci Miro a GitHubu, přepne se do Work.

## Work

Work je povolený orchestration mode pro:

- čtení a porovnání GitHub, Miro a dalších schválených zdrojů;
- přípravu a provedení ohraničených změn na PR branchi;
- sledování CI;
- vyhodnocení logs, reports a exact-SHA evidence;
- tvorbu dokumentace a review artefaktů;
- práci s Miro pouze v rozsahu schváleném uživatelem a source-system oprávněními.

Work není lokální developer workstation. Nesmí tvrdit, že provedl lokální shell, build nebo test, pokud je skutečně nespustil GitHub Actions nebo jiný explicitně schválený execution plane.

Work musí fail-closed:

1. před změnou načíst aktuální PR head SHA;
2. pracovat jen proti deklarované branchi a allowed paths;
3. nepoužívat `main` jako write target;
4. neposílat secrets do chatu, commitů, logů nebo argumentů;
5. při nedostupném konektoru nebo boardu zastavit a explicitně popsat omezení;
6. po změně vyžadovat standardní CI nad výsledným SHA;
7. nerozšiřovat autorizaci zápisu na merge, release, tag, promotion nebo force-push.

## GitHub Actions jako autoritativní execution plane

Bez Codexu zajišťuje GitHub Actions technickou exekuci:

```text
Work připraví nebo zapíše reviewovatelnou změnu na PR branch
→ GitHub Actions checkoutne exact SHA
→ spustí ddda.ps1 a požadované suites
→ vytvoří candidate package
→ provede package-first validation
→ publikuje machine-readable evidence
→ Work a člověk vyhodnotí výsledek
```

GitHub Actions musí být self-service a reprodukovatelné. Povinné schopnosti:

- jeden stabilní entry point `ddda.ps1`;
- standardní PR workflows bez jednorázových bootstrap workflow;
- exact-SHA binding;
- package-first smoke, integration, E2E a acceptance;
- izolovaný workspace;
- artifact retention a dohledatelné logs;
- oddělený secret-bearing online Miro acceptance;
- fail-closed výsledek.

Lokální PowerShell příkazy v dokumentaci definují platformní kontrakt a mohou je používat schválení lokální operátoři. Uživatel DDDA na Chat/Work-only cestě není povinen používat Codex ani poskytovat Work přístup k lokálnímu shellu.

## Git a zápisová pravidla

- Git je source of truth.
- PR je jednotka změny.
- Work zapisuje pouze na explicitně deklarovanou feature/fix/docs branch.
- Každý zápis musí být dohledatelný v Git historii.
- Přímý zápis na `main` je zakázán.
- Force-push je zakázán, pokud samostatná policy výslovně neurčí jinak.
- Neúspěšná validace se opravuje následným korektivním commitem; sdílená historie se automaticky nepřepisuje.
- Merge, promotion, release a tag jsou oddělené governance akce.

## Miro a vizuální acceptance

Strukturální Miro kontrola není vizuální acceptance.

Před implementací změny odvozené z referenčního boardu musí Work:

1. skutečně otevřít referenční board přes Miro connector;
2. načíst konkrétní source frames a jejich children;
3. ověřit obrázky, geometrii, hierarchii, fonty, překryvy a informační hustotu;
4. porovnat reference a implementaci side-by-side;
5. explicitně oznámit, pokud některý board nebo vizuální prvek nelze načíst.

Human review hodnotí minimálně:

- čitelnost při `Fit to frame`;
- first-viewer srozumitelnost;
- vizuální hierarchii;
- nepřekrývání frames a items;
- přiměřené využití plochy;
- přítomnost požadovaných obrázků a examples;
- věrnost schválenému redline/template;
- metodickou a doménovou koherenci.

Technický PASS nesmí změnit `human_review_status` na `ACCEPTED`.

## Bezpečnostní podmínky

Použití Work je povolené pouze tehdy, když:

- firemní policy povoluje ChatGPT Work pro danou klasifikaci dat;
- GitHub, Miro a další Apps jsou schválené;
- oprávnění Apps odpovídají least privilege;
- neveřejná nebo korporátní data smějí být zpracována v použitém ChatGPT workspace/tarifu;
- secrets zůstávají ve source-system secret store nebo GitHub environmentu;
- klientská data nejsou použita jako platformní fixture.

Pokud tato podmínka není doložená, Work smí připravit návrh nebo offline change package, ale nesmí načítat ani zapisovat dotčená chráněná data.

## Definition of Done pro Chat/Work-only změnu

- změna je na PR branchi;
- diff je reviewovatelný;
- standardní CI běží nad výsledným exact SHA;
- required suites jsou PASS;
- package-first evidence je dostupná, pokud ji change class vyžaduje;
- žádný secret nebyl předán Chat/Work runtime;
- human review je odděleno od technického PASS;
- Work transparentně uvedl všechna omezení přístupu;
- nebyl použit Codex ani `/agent`;
- neproběhl merge, promotion, release, tag ani force-push bez samostatné autorizace.
