# WP ↔ Backlog ↔ Implementation consistency

Tento dokument je závaznou součástí GitHub-native governance DDDA platformy.

## Povinný invariant

Backlog authority a implementation traceability musí tvořit úplný a vzájemně konzistentní model:

```text
Work Package (nebo explicitní Other)
↔ Change Request Issue
↔ DDDA Platform Backlog Project item

Change Request Issue
↔ implementation branch / Draft PR
```

Implementační PR není automaticky druhá backlogová položka. Samostatná Project membership PR je povinná pouze tehdy, pokud ji explicitně vyžaduje planning policy. Pokud PR v Projectu je, jeho `Work Package` nesmí odporovat autoritativnímu CR.

Před i po každé změně backlogu, Work Package struktury, governance metadat nebo implementačních PR vztahů se provede fail-closed read-back celé aktivní struktury. Kontrola se nesmí omezit pouze na právě editovanou položku.

Post-change výsledek musí být:

```text
remaining_mismatches = 0
```

Jakýkoli zbývající mismatch blokuje technical governance PASS a doporučení Ready/merge, i když code CI a package-first validace jsou zelené.

## Povinné kontroly

- Change Request má právě jedno autoritativní Work Package přes native Parent/Sub-issue, nebo je explicitně `Other`.
- Každý governed Change Request je položkou `DDDA Platform Backlog`, pokud policy výslovně nedefinuje výjimku.
- Project `Work Package` a `Item Type` CR odpovídají autoritativnímu WP a typu artefaktu.
- Každý otevřený platformní PR má právě jednu primární vazbu `Implements #<CR>` nebo `Closes #<CR>`, pokud nejde o explicitní verzovanou legacy výjimku.
- `Refs`, `Related`, prefix názvu ani stacked Git ancestry nejsou primární implementation authority a neurčují WP ownership.
- Work Package implementačního PR se odvozuje od jeho primárního CR; PR nesmí tvrdit jiné WP.
- Pokud planning policy vede PR také jako Project item, jeho Project `Work Package` a `Item Type` musí být konzistentní s primárním CR.
- Pre-read-back může při remediation najít chyby; ty se uloží jako evidence. Post-read-back musí mít nula nevysvětlených mismatchů.

## Aktuální legacy výjimka

Jediná povolená výjimka k 2026-08-13 je:

```text
PR: #8
Work Package: WP-08 / #17
Reason: PR #8 vznikl před zavedením GitHub-native backlog governance a WP-08 explicitně vlastní uzavření tohoto již aktivního foundation PR. Retrospektivní syntetický CR by zhoršil traceability.
Expiry: okamžik merge nebo close PR #8
```

Tato výjimka neobchází WP projection, Human Review ani release governance. Po expiraci musí být z metodiky odstraněna. Nové PR nesmějí používat tento precedent jako bypass.

## Fail-closed podmínky

Za governance failure se považuje zejména:

- governed CR chybí v `DDDA Platform Backlog` bez explicitní policy výjimky;
- chybějící nebo víceznačný primární CR u aktivního PR;
- primární CR mimo řízený backlog;
- `CR.Project.Work Package != authoritative CR Work Package`;
- rozpor native parentu CR a jeho Project Work Package;
- chybějící nebo chybně klasifikovaný WP/CR Project item;
- PR deklaruje jiné WP než jeho primární CR;
- PR je veden jako Project item a jeho Project WP odporuje CR;
- nezdůvodněná legacy výjimka;
- libovolný nevysvětlený post-change mismatch.

## Hranice automatizace

Automatizace smí opravit mechanickou projekci pouze tehdy, když je produktová autorita explicitní. Nesmí sama vymyslet Work Package ownership, primární Change Request, prioritu, business value, Human Review PASS, gate decision, merge approval ani release approval.

Nejednoznačné vlastnictví je blocking condition vyžadující explicitní governance rozhodnutí.

## Versioned contracts

```text
config/governance/backlog-policy.yaml
config/governance/github-bootstrap.json
```

Privileged live Project reconciliation musí zůstat oddělena od ne-reviewovaného PR kódu. Workflow s Project tokenem se nespouští automaticky z běžného `pull_request` triggeru.

## Povinná evidence

Governance/backlog změna uchovává minimálně:

- repository, branch a exact SHA;
- počet a seznam pre-read-back mismatchů;
- provedené mechanické opravy;
- post-read-back mismatch count;
- seznam aktivních WP/CR a otevřených PR zahrnutých do kontroly;
- výsledky native WP parent + CR Project membership/field read-backu;
- PR → primary CR mapping a odvozené WP;
- případnou kontrolu PR Project fields, pokud planning policy PR items používá;
- workflow run a audit artifact při privileged live reconciliation.

Technical PASS a Human Review zůstávají oddělené dimenze.
