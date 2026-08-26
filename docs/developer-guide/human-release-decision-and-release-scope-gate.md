# Human Review, governed implementation merge a Release Scope Gate

## Účel

Tento runbook je závazný pro governance část DDDA platformního lifecycle. Odděluje čtyři různé otázky:

```text
technical evidence
≠ Human Review implementačního PR
≠ merge authorization
≠ Human Release Decision / release-scope completeness
```

Žádná z těchto dimenzí nenahrazuje ostatní.

## 1. Candidate validation implementačního PR

Pro exact PR HEAD musí existovat standardní PASS evidence:

```powershell
.\ddda.ps1 validate-pr -Pr <PR> ...
```

Validation report a candidate package SHA-256 tvoří technickou identitu Human Review.

## 2. Human Review implementačního PR

Člověk posoudí judgment-heavy oblasti změny. PASS musí být auditovatelně svázán minimálně s:

```text
repository
pr
reviewed_sha
candidate_package_sha256
reviewer
reviewed_at
verdict
```

Authoritativní PR comment používá marker:

```text
<!-- ddda:human-pr-review:v1 -->
```

a fenced JSON kontrakt:

```json
{
  "schema_version": 1,
  "kind": "implementation_pr_review",
  "repository": "owner/repository",
  "pr": 74,
  "reviewed_sha": "<40-char-sha>",
  "candidate_package_sha256": "<64-char-sha256>",
  "reviewer": "<github-login>",
  "reviewed_at": "<ISO-8601>",
  "verdict": "pass"
}
```

Povolené verdict semantics jsou lidské `PASS` nebo `CHANGES_REQUIRED`; machine-readable hodnoty jsou `pass` a `changes_required`.

Automation nesmí vytvořit `pass` pouze z technického PASS. Změna PR HEAD nebo candidate package hash před merge review invaliduje.

## 3. Governed implementation merge

Human Review PASS není sám o sobě merge authorization.

Preflight:

```powershell
.\ddda.ps1 merge-pr -Pr <PR> -DryRun
```

Skutečný merge:

```powershell
.\ddda.ps1 merge-pr -Pr <PR> -ConfirmMerge
```

`merge-pr` mechanicky ověřuje:

- PR je open a není Draft;
- base branch odpovídá policy;
- live head SHA je platné a mergeable;
- required CI je PASS pro exact SHA;
- `validate-pr` PASS existuje pro stejné SHA;
- candidate package SHA-256 odpovídá validation reportu;
- existuje právě jeden authoritativní Human Review marker;
- marker má lidskou GitHub provenance;
- reviewer, exact SHA a package hash odpovídají live evidence;
- Human Review verdict je `pass`;
- required governance documents existují;
- merge method odpovídá aktuální repository policy;
- actual merge má explicitní `-ConfirmMerge`.

`merge-pr` záměrně **nevyhodnocuje**:

- HRDR;
- Release Scope Gate;
- release milestone completeness jako podmínku implementation merge.

A záměrně **nevytváří**:

- release package;
- release-validation workspace/report;
- release tag;
- release decision;
- accepted risk.

To je hlavní anti-deadlock invariant pro multi-PR release.

## 4. Release candidate

Teprve když jsou všechny implementační změny určené pro release integrovány a jejich delivery Issues mohou být korektně terminal, vytvoří se explicitní release candidate, typicky `release/<version>` PR nebo jiný lifecyclem schválený ekvivalent.

Pro release candidate znovu platí exact-SHA validation. Implementation Human Review z jednotlivých PR **není** HRDR release candidate.

## 5. Vytvoření HRDR scaffoldu

Pro exact release candidate:

```powershell
.\ddda.ps1 review-pr `
  -Pr <RELEASE_PR> `
  -Version <X.Y.Z> `
  -Reviewer <github-login> `
  -DecisionOwner <github-login> `
  -PublishScaffold
```

Příkaz načte live release-candidate HEAD, PASS `validate-pr` evidence, candidate hash a current release milestone. Automation vytváří pouze `decision=pending`.

## 6. Human Release Decision

Člověk explicitně zvolí:

```text
GO
GO_WITH_ACCEPTED_RISKS
NO_GO
```

Machine-readable:

```text
go
go_with_accepted_risks
no_go
```

Pro pozitivní rozhodnutí HRDR obsahuje konkrétního reviewer/decision ownera, timestamp, exact candidate identity, kompletní release scope, GREEN/AMBER/RED findings a explicitní accepted risks.

`go` nesmí obsahovat accepted risks. `go_with_accepted_risks` musí mít neprázdný explicitní risk set. RED blokuje release promotion.

Automation nesmí decision ani risk set doplnit odhadem.

## 7. Release Scope Gate

`promote-pr` pro release candidate provede read-only live gate nad:

```text
current release-candidate head
+ candidate hash
+ previous canonical SemVer tag → exact release-source SHA → shipping commit/PR/primary-CR inventory
+ Milestone DDDA <version>
+ milestone Issues
+ native unresolved blockers
+ Project V2 planning projection
+ accepted-risk follow-up Issues
+ HRDR
```

Gate je fail-closed.

### PASS invariants

- Milestone identity je jednoznačná.
- HRDR scope Issues přesně odpovídají current milestone Issues.
- Všechny current-release Issues jsou closed/terminal.
- Žádný current-release Issue nemá aktivního blockeru.
- Project rows mají `Status=Done` a `Blocked=No`.
- Project planning/delivery view odpovídají governance contractu.
- Accepted-risk Issues jsou mimo current release milestone a zůstávají open follow-ups.
- Owner v HRDR odpovídá live owner/assignee kontraktu.
- Follow-up Issue obsahuje target release/resolution/horizon.
- HRDR nemá RED.
- Human Release Decision je pozitivní.
- live release-candidate head, source SHA, candidate hash a version se shodují.
- každý commit mezi předchozím canonical SemVer tagem a release source je dohledatelný k právě jednomu merged shipping PR a jeho právě jednomu primary CR;
- každý shipping primary CR je v aktuálním Milestone a jeho Project `Target Release` je stejná verze;
- physical scope se přesně rovná declared Milestone scope: ani extra shipping CR, ani declared CR bez shipping změny. Při rozdílu gate vydá inventory a `RECOVERY_DECISION_REQUIRED`; nevolí scope expansion ani source recovery.
- controlled reconstructed source je přípustný pouze po explicitním human recovery decision a s validním versioned recovery ledgerem; ledger musí pokrýt každý reconstructed commit, kromě jediného metadata-only ledger commitu, a fresh read-backem prokázat původní merged PR/CR/SHA i changed-path result hashes.

Chybějící Project credential, nedostupný Project nebo API ambiguity jsou FAIL.

## 8. Release promotion

Dry-run:

```powershell
.\ddda.ps1 promote-pr -Pr <RELEASE_PR> -Version <X.Y.Z> -DryRun
```

Skutečný release vyžaduje samostatnou explicitní human authorization:

```powershell
.\ddda.ps1 promote-pr -Pr <RELEASE_PR> -Version <X.Y.Z> -ConfirmMerge
```

Implementation `merge-pr -ConfirmMerge` autorizace se na release nikdy nepřenáší.

## 9. Invalidation

### Human Review implementačního PR

Review se nesmí použít, pokud se změnilo:

- PR HEAD SHA;
- candidate package hash;
- judgment-heavy scope relevantní pro review.

### HRDR release candidate

Human Release Decision se nesmí použít, pokud se změnilo:

- release-candidate HEAD SHA;
- candidate package hash;
- version;
- release scope;
- accepted-risk set/provenance;
- RED status.

Automation nesmí staré rozhodnutí přemapovat na nový candidate.

## 10. Povinné regressions

### Multi-PR anti-deadlock

```text
implementation PR CI PASS
validate-pr PASS
Human Review PASS
explicit merge authorization
AND jiné release-scope Issues jsou stále open
→ merge-pr může PASS/merge
→ Release Scope Gate se nevyhodnotí
→ release/tag side effects = zero
```

### PR8-class release-scope regression

```text
release candidate technical evidence PASS
HRDR positive
BUT current release Issue open
→ Release Scope Gate FAIL
→ release promotion FAIL
→ release/tag side effects = zero
```

Stejně pro unresolved blocker nebo Project/Milestone mismatch.

## 11. Authority

```text
CI/validate-pr/package
  technical evidence

Human PR Review marker
  judgment evidence pro implementation PR

merge-pr
  mechanical implementation merge enforcement

Git/Issue/native dependency/Milestone
  release-scope authority

GitHub Project
  validated operational projection

HRDR
  human release decision evidence

Release Scope Gate + promote-pr
  mechanical release enforcement
```

Žádný CI status, Project field ani automation comment nemůže vytvořit Human Review PASS, Human Release Decision ani merge/release authorization.
