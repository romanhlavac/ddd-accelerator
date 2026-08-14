# WP ↔ Backlog ↔ Delivery consistency

Tento dokument je závaznou součástí GitHub-native governance DDDA platformy.

## Povinný invariant

Planning authority a implementation delivery projection musí tvořit úplný a vzájemně konzistentní model:

```text
Work Package (nebo explicitní Other)
↔ Change Request Issue
↔ Project planning item

Change Request Issue
↔ implementation branch / Draft PR
↔ Project delivery item
```

Otevřený implementační PR je povinná Project delivery projection, nikoli druhý Change Request ani backlog authority. Jeho Work Package se odvozuje z primary CR. Planning `Item Type` se na PR nepoužívá.

Před i po každé změně backlogu, Work Package struktury, governance metadat nebo implementačních PR vztahů se provede fail-closed read-back celé aktivní struktury. Kontrola se nesmí omezit pouze na právě editovanou položku.

Post-change výsledek musí být:

```text
remaining_mismatches = 0
```

Jakýkoli zbývající mismatch blokuje technical governance PASS a doporučení Ready/merge, i když code CI a package-first validace jsou zelené.

## Kanonické Project projekce

Project se jmenuje `DDDA Platform Backlog & Delivery` a má dvě kanonické strojově spravované projekce:

```text
Plánování a Backlog
layout: Table
filter: is:issue

Implementace a Delivery
layout: Table
filter: is:pr is:open
```

Další analytické view mohou existovat pouze jako odvozené pohledy; nesmějí měnit planning nebo delivery authority.

## Povinné kontroly

### Planning

- Change Request má právě jedno autoritativní Work Package přes native Parent/Sub-issue, nebo je explicitně `Other`.
- Každý governed Change Request a Work Package požadovaný verzovaným kontraktem je planning položkou `DDDA Platform Backlog & Delivery`.
- Project `Work Package` a `Item Type` Issue odpovídají autoritativnímu WP a typu artefaktu.
- Native dependency vztahy odpovídají verzovanému governance kontraktu.

### Delivery

- Každý otevřený platformní PR má právě jednu primární vazbu `Implements #<CR>` nebo `Closes #<CR>`, pokud nejde o explicitní verzovanou legacy výjimku.
- `Refs`, `Related`, prefix názvu ani stacked Git ancestry nejsou primární implementation authority a neurčují WP ownership.
- Work Package implementačního PR se odvozuje od jeho primary CR; PR nesmí tvrdit jiné WP.
- Každý otevřený implementační PR je Project delivery item.
- Project `Work Package` PR odpovídá odvozenému WP primary CR.
- Project `Item Type` PR je prázdný; delivery PR se nesmí klasifikovat jako planning artefakt.
- Project `Status` PR je `Blocked`, pokud je `Blocked = Yes`; jinak Draft PR je `In progress` a non-draft open PR je `In review`.
- Pokud Issue/PR title obsahuje explicitní prefix `[WP-XX]`, prefix musí odpovídat autoritativnímu Work Package. Absence WP prefixu je povolená; zavádějící nebo historický prefix je `PRESENTATION_WP_MISMATCH` a blokuje technical governance PASS.
- Display/read-back názvu vychází z kanonického Issue/PR title, nikoli z náhodného nebo duplicitního Project text field se jménem `Title`.

### Project contract

- Project title je přesně `DDDA Platform Backlog & Delivery`.
- Planning view je `Plánování a Backlog`, `TABLE`, filter `is:issue`.
- Delivery view je `Implementace a Delivery`, `TABLE`, filter `is:pr is:open`.
- Pre-read-back může při remediation najít chyby; ty se uloží jako evidence.
- Post-read-back musí mít nula nevysvětlených mismatchů.

## Aktuální legacy výjimka

Jediná povolená výjimka k 2026-08-14 je:

```text
PR: #8
Work Package: WP-08 / #17
Reason: PR #8 vznikl před zavedením GitHub-native backlog governance a WP-08 explicitně vlastní uzavření tohoto již aktivního foundation PR. Retrospektivní syntetický CR by zhoršil traceability.
Expiry: okamžik merge nebo close PR #8
```

Výjimka se týká pouze chybějící primary CR vazby. PR #8 zůstává povinnou delivery Project položkou s WP-08 a nepřestává podléhat Human Review, promotion ani release governance. Po expiraci musí být výjimka odstraněna. Nové PR nesmějí používat tento precedent jako bypass.

## Fail-closed podmínky

Za governance failure se považuje zejména:

- governed WP/CR chybí v planning projekci bez explicitní policy výjimky;
- chybějící nebo víceznačný primary CR u aktivního PR;
- primary CR mimo řízený backlog;
- `CR.Project.Work Package != authoritative CR Work Package`;
- rozpor native parentu CR a jeho Project Work Package;
- chybějící nebo chybně klasifikovaný WP/CR planning item;
- explicitní `[WP-XX]` prefix Issue/PR title odporuje autoritativnímu WP (`PRESENTATION_WP_MISMATCH`);
- PR deklaruje jiné WP než jeho primary CR;
- otevřený implementační PR chybí v delivery projekci (`MISSING_DELIVERY_PROJECT_ITEM`);
- PR Project Work Package odporuje odvozenému WP (`DELIVERY_WORK_PACKAGE_MISMATCH`);
- PR Project Status odporuje delivery state (`DELIVERY_STATUS_MISMATCH`);
- PR má nastaven planning `Item Type` (`DELIVERY_HAS_PLANNING_ITEM_TYPE`);
- Project title nebo některá kanonická view/filter projekce neodpovídá kontraktu;
- nezdůvodněná legacy výjimka;
- libovolný nevysvětlený post-change mismatch.

## Hranice automatizace

Automatizace smí opravit mechanickou projekci pouze tehdy, když je produktová autorita explicitní. Nesmí sama vymyslet Work Package ownership, primary Change Request, prioritu, business value, Human Review PASS, gate decision, merge approval ani release approval.

Nejednoznačné vlastnictví je blocking condition vyžadující explicitní governance rozhodnutí.

## Versioned contracts

```text
config/governance/backlog-policy.yaml
config/governance/github-bootstrap.json
scripts/platform/Reconcile-DDDAProjectBacklog.py
```

Privileged live Project reconciliation musí zůstat oddělena od ne-reviewovaného PR kódu. Workflow s Project tokenem se nespouští automaticky z běžného `pull_request` triggeru.

## Povinná evidence

Governance/backlog/delivery změna uchovává minimálně:

- repository, branch a exact SHA;
- počet a seznam pre-read-back mismatchů;
- provedené mechanické opravy;
- post-read-back mismatch count;
- seznam aktivních WP/CR a všech otevřených PR zahrnutých do kontroly;
- výsledky native WP parent + planning Project membership/field read-backu;
- kontrolu explicitních WP prefixů v Issue/PR titles proti autoritativnímu WP;
- PR → primary CR mapping a odvozené WP;
- PR Project membership + `Work Package` + `Status` + absence `Item Type`;
- Project title a obě canonical view/filter hodnoty;
- workflow run a audit artifact při privileged live reconciliation.

Technical PASS a Human Review zůstávají oddělené dimenze.
