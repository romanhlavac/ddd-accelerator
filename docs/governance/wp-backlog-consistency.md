# WP ↔ Backlog ↔ Implementation consistency

Tento dokument je závaznou součástí GitHub-native governance DDDA platformy.

## Povinný invariant

Pro každou aktivní implementaci musí být úplný a vzájemně konzistentní řetězec:

```text
Work Package (nebo explicitní Other)
↔ Change Request
↔ branch / Draft PR
↔ DDDA Platform Backlog Project item
```

Před i po každé změně backlogu, Work Package struktury, governance metadat nebo implementačních PR vztahů se provede fail-closed read-back celé aktivní struktury. Kontrola se nesmí omezit pouze na právě editovanou položku.

Post-change výsledek musí být:

```text
remaining_mismatches = 0
```

Jakýkoli zbývající mismatch blokuje technical governance PASS a doporučení Ready/merge, i když code CI a package-first validace jsou zelené.

## Povinné kontroly

- Change Request má právě jedno autoritativní Work Package přes native Parent/Sub-issue, nebo je explicitně `Other`.
- Project `Work Package` a `Item Type` odpovídají autoritativnímu artefaktu.
- Každý otevřený platformní PR je položkou `DDDA Platform Backlog`.
- Každý otevřený platformní PR má právě jednu primární vazbu `Implements #<CR>` nebo `Closes #<CR>`.
- `Refs`, `Related`, prefix názvu ani volný text nejsou primární implementation authority.
- Project `Work Package` PR se rovná Work Package jeho primárního Change Requestu.
- Legacy PR bez primárního CR je přípustný pouze jako explicitní verzovaná výjimka s číslem PR, očekávaným WP, důvodem a podmínkou expirace.
- Pre-read-back může při remediation najít chyby; ty se uloží jako evidence. Post-read-back musí mít nula chyb.

## Aktuální legacy výjimka

Jediná povolená výjimka k 2026-08-13 je:

```text
PR: #8
Work Package: WP-08 / #17
Reason: PR #8 vznikl před zavedením GitHub-native backlog governance a WP-08 explicitně vlastní uzavření tohoto již aktivního foundation PR. Retrospektivní syntetický CR by zhoršil traceability.
Expiry: okamžik merge nebo close PR #8
```

Tato výjimka neobchází Project membership, WP projection, Human Review ani release governance. Po expiraci musí být z metodiky odstraněna. Nové PR nesmějí používat tento precedent jako bypass.

## Fail-closed podmínky

Za governance failure se považuje zejména:

- orphan aktivní PR;
- chybějící nebo víceznačný primární CR;
- primární CR mimo řízený backlog;
- chybějící Project item PR;
- `PR.Work Package != CR.Work Package`;
- rozpor native parentu CR a jeho Project Work Package;
- chybějící nebo chybně klasifikovaný WP Project item;
- nezdůvodněná legacy výjimka;
- libovolný post-change mismatch.

## Hranice automatizace

Automatizace smí opravit mechanickou projekci pouze tehdy, když je produktová autorita explicitní. Nesmí sama vymyslet Work Package ownership, primární Change Request, prioritu, business value, Human Review PASS, gate decision, merge approval ani release approval.

Nejednoznačné vlastnictví je blocking condition vyžadující explicitní governance rozhodnutí.

## Versioned contracts

```text
config/governance/backlog-policy.yaml
config/governance/github-bootstrap.json
```

Privileged live reconciliation musí zůstat oddělena od ne-reviewovaného PR kódu. Workflow s Project tokenem se nespouští automaticky z běžného `pull_request` triggeru.

## Povinná evidence

Governance/backlog změna uchovává minimálně:

- repository, branch a exact SHA;
- počet a seznam pre-read-back mismatchů;
- provedené mechanické opravy;
- post-read-back mismatch count;
- počet otevřených a governed PR;
- výsledky WP/CR/PR Project projekce;
- workflow run a audit artifact při privileged live reconciliation.

Technical PASS a Human Review zůstávají oddělené dimenze.
