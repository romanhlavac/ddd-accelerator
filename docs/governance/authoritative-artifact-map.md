# Autoritativní mapa backlogu, delivery a release artefaktů

## Účel

Tento dokument určuje, který systém nebo artefakt je autoritativní pro jednotlivé druhy informací. Cílem je zabránit duplicitním backlogům, plánovaným změnám v changelogu, prázdným PR a nejasnému oddělení technické evidence od lidského rozhodnutí.

## Mapa autority

| Informace | Autoritativní místo | Co se zde eviduje | Co sem nepatří |
|---|---|---|---|
| Nápad nebo nalezený GAP | GitHub Issue | problém, očekávaná hodnota, prvotní scope, discovery evidence | implementační diff |
| Velký roadmap blok | Parent Issue / Work Package | outcome, hranice WP, závislosti, delivery slices, exit criteria | detail jednoho commitu |
| Dílčí implementační požadavek | Child Issue | konkrétní změna, acceptance criteria, testy, migration impact | dlouhodobá produktová vize |
| Backlog authority | GitHub Issues, PRs, labels, assignees, milestones and dependency links | požadavek, ownership, scope, stav a unresolved dependencies; Project status/blocked/target release jsou odvozené projekce | automatické lidské rozhodnutí |
| Operational priority/order | GitHub Project podle explicitního planning rozhodnutí | operativní priorita a pořadí; nevytvářejí release scope ani approval | technická release evidence |
| Cílová verze | Milestone | množina issues a PR určená pro release | neurčitý dlouhodobý backlog |
| Aktuální implementace | Branch + Draft PR | konkrétní Git diff, rozpracovanost, review diskuse | vzdálený plán bez kódu |
| Architektonické rozhodnutí | ADR v repozitáři | kontext, rozhodnutí, varianty, důsledky, validace | seznam všech backlog položek |
| Implementovaná změna | PR + CHANGELOG | merge evidence a změny zahrnuté do releasu | neimplementované plány |
| Breaking dopad | Migration note | dopad, podporované baseline, kroky migrace, rollback | obecný návod k produktu |
| Testovací evidence | CI + validation report | exact SHA, suites, package hash, výsledky, diagnostika | lidské schválení |
| Human GO/NO-GO | HRDR / review evidence | reviewer, scope, residual risks, přesný SHA, rozhodnutí | automatické předstírání lidského approval |
| Dlouhodobá produktová vize | Verzovaný roadmap dokument | směry, Work Packages, outcomes, závislosti a stav | operativní priorita jednotlivých issues |

## Source-of-truth pravidla

1. GitHub Issue je autoritou pro plánovaný požadavek a jeho acceptance criteria.
2. GitHub Project zachycuje explicitně určenou operativní prioritu a pořadí. Delivery status je projekce live Issue/PR state a unresolved blockers podle [WP ↔ Backlog ↔ Delivery consistency](wp-backlog-consistency.md); Project jej nesmí určovat nezávisle.
3. Milestone je autoritou pro plánovaný release scope. Pole `Target Release` v Projectu je projekce stejného rozhodnutí a nesmí se rozcházet.
4. PR je autoritou pro skutečný implementační rozsah. Scope review porovnává Issue/Work Package s reálným diffem.
5. ADR je autoritou pro schválené architektonické rozhodnutí; issue a PR na ADR pouze odkazují.
6. CHANGELOG obsahuje pouze změny určené k vydání, nikoli nápady a roadmapu.
7. CI a validation report dokazují technický stav. Nemohou vydat lidské GO.
8. HRDR je autoritou pro release decision a musí být navázán na exact PR SHA a candidate hash.
9. Roadmap dokument agreguje stav a záměr, ale detail požadavku zůstává v issues.

## Konzistence a drift

Při rozporu se postupuje takto:

- rozdíl Issue vs PR diff: upravit scope Issue nebo odstranit scope creep z PR před merge;
- rozdíl Project vs Issue/PR: Issue/PR drží požadavek a live lifecycle, Project je jejich projekce; opravit odvozená metadata, priority/order nevymýšlet;
- rozdíl Milestone vs `Target Release`: rozhodnout release scope a sjednotit obě reprezentace;
- rozdíl ADR vs implementace: PR nesmí být schválen bez aktualizace nebo supersede ADR;
- rozdíl CHANGELOG vs diff: opravit changelog před promotion;
- rozdíl validation report vs current SHA: report je neplatný a musí být vytvořen znovu;
- rozdíl HRDR vs current SHA nebo candidate hash: HRDR je neplatný a vyžaduje nové lidské rozhodnutí.

Project mismatch se klasifikuje podle [S3 mismatch taxonomy](mismatch-taxonomy.md). Projekční nebo prezentační nesoulad není release-scope authority ani release safety failure. Každá backlog/Project mutation přesto zůstává nedokončená až do repository-wide read-backu s `remaining_mismatches = 0`.

## Stav artefaktu

Artefakt může být označen jako:

- `authoritative` — zdroj pravdy pro danou informaci;
- `projection` — odvozený přehled nebo vizualizace;
- `evidence` — důkaz o provedené kontrole nebo rozhodnutí;
- `working-copy` — dočasná pracovní verze bez konečné autority.

Miro je projekce a workshopová plocha. GitHub Issues, Git, ADR, validation reports a HRDR drží příslušnou autoritu podle této mapy.
