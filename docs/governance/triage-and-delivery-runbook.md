# Backlog triage and delivery runbook

## 1. Nový nápad nebo GAP

1. Založ Issue přes šablonu `GAP`.
2. Uveď původ, evidence, problém, dopad a prvotní hranice.
3. Nastav Project metadata:
   - Status `Backlog`;
   - Item Type `GAP`;
   - Priority pouze pokud je dostatek evidence;
   - Target Release `TBD`.
4. Nezakládej branch ani PR.

## 2. Triage

Triage rozhodne jednu z variant:

- reject / not planned;
- duplicate;
- keep in backlog;
- discovery required;
- začlenit do existujícího Work Package;
- vytvořit nový Work Package;
- převést na samostatný Change Request.

Při triage určuj:

- business/platform value;
- impacted users;
- dominantní platform area;
- impact a migration impact;
- safety, security a release rizika;
- dependencies;
- první testovatelný outcome.

## 3. Vytvoření Work Package

1. Použij šablonu `Work Package`.
2. Přiděl stabilní `WP-XX`.
3. Definuj outcome, nikoli pouze seznam funkcí.
4. Vymez In scope a Out of scope.
5. Rozděl práci na delivery slices.
6. Pro každý slice založ nebo naplánuj Child Issue.
7. Propoj parent a children pomocí checklistu a vzájemných odkazů.
8. Přidej WP do roadmap dokumentu.
9. Milestone nastav pouze při rozhodnutém release scope.

## 4. Refinement Child Issue

Issue může přejít do `Ready`, když obsahuje:

- jednoznačný Goal a Problem;
- konkrétní In scope / Out of scope;
- classification, impact a migration impact;
- ověřitelná acceptance criteria;
- required repository changes;
- required tests;
- známé dependencies;
- risks a Definition of Done.

Pokud acceptance vyžaduje významné architektonické rozhodnutí, nejprve připrav Proposed ADR nebo explicitně zahrň jeho vytvoření do Issue.

## 5. Zahájení implementace

1. Přesuň Issue do `In progress`.
2. Vytvoř branch:

```text
feature/<issue>-<short-name>
fix/<issue>-<short-name>
docs/<issue>-<short-name>
```

3. Po prvním koherentním commitu vytvoř Draft PR.
4. V PR použij `Implements #<issue>` nebo `Closes #<issue>`.
5. Přidej PR do Projectu a nastav stejný Work Package a Target Release.
6. Implementuj change package: code/config, tests, docs, examples, ADR, changelog a migration note podle dopadu.

## 6. Review readiness

Před označením PR jako Ready for review:

- CI je zelené pro current SHA;
- scope PR odpovídá Issue;
- žádný známý scope creep není skrytý;
- behaviorální změna má testy;
- contract change má dokumentaci;
- significant decision má ADR;
- breaking change má migration note;
- changelog popisuje skutečnou změnu;
- validation instructions jsou aktuální.

## 7. Scope review

Pro každý požadavek z parent WP a Child Issue vytvoř evidence matrix:

| Požadavek | Implementační evidence | Testovací evidence | Dokumentační evidence | Stav |
|---|---|---|---|---|
| ... | ... | ... | ... | covered / partial / missing / scope creep |

Out-of-scope položka implementovaná bez schválení je `scope creep`, nikoli bonus.

## 8. Validation a Human Review

Technická evidence:

```text
CI
→ validate-pr pro exact SHA
→ candidate package hash
→ suite results
→ validation report
```

Human review:

```text
scope
→ methodology
→ architecture
→ usability
→ compatibility
→ residual risks
→ HRDR decision
```

Human Review nesmí měnit posuzovaný source SHA. Pokud je nutná oprava, review se vrací do `In progress`, vznikne nový SHA a evidence se obnoví.

## 9. Promotion a release

1. HRDR je finalizován pro exact SHA a candidate hash.
2. Spusť `promote-pr -DryRun`.
3. Ověř release version, changelog, milestone a tag availability.
4. Skutečný promotion spusť až po samostatném explicitním pokynu.
5. Po merge vzniká release package, release validation report a tag podle platformního lifecycle.
6. Uzavři implementační Issue až po splnění jeho Definition of Done.
7. Aktualizuj parent WP a roadmap.

## 10. Blocked work

Blocked Issue musí obsahovat:

- konkrétní blocker;
- blocking Issue/PR/WP;
- podmínku odblokování;
- ownera dalšího kroku;
- datum posledního review blockeru.

Pouhé „čeká“ není dostatečný blocker description.

## 11. Backlog review cadence

### Před každým release

- potvrdit milestone scope;
- prověřit P0/P1;
- prověřit Blocked items;
- sjednotit changelog a Target Release;
- ověřit otevřené RED/AMBER nálezy;
- potvrdit roadmap dopad.

### Měsíčně

- triage nových GAP;
- obsolete/duplicate cleanup;
- ownerless Ready items;
- dlouho neaktivní Draft PR;
- parent/child completeness;
- roadmap status.

### Po GAP analýze

- aktualizovat nebo vytvořit Work Packages;
- zachovat detailní evidence v Issues;
- nevytvářet prázdné budoucí PR;
- zapsat dlouhodobé směry do verzované roadmapy;
- prioritu rozhodnout v Projectu;
- cílovou verzi přidělit až schváleným Milestone.
