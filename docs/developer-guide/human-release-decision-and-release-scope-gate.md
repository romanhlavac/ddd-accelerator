# Human Release Decision a Release Scope Gate

## Účel

Tento runbook je závazný pro release-governance část DDDA platformního lifecycle. Odděluje:

```text
technical evidence
≠ human release decision
≠ release-scope completeness
```

Žádná z těchto dimenzí nenahrazuje ostatní.

## 1. Candidate validation

Nejdříve musí pro exact PR HEAD existovat standardní PASS evidence:

```powershell
.\ddda.ps1 validate-pr -Pr <PR> ...
```

Validation report a candidate package SHA-256 jsou součást identity budoucího HRDR.

## 2. Vytvoření HRDR scaffoldu

```powershell
.\ddda.ps1 review-pr `
  -Pr <PR> `
  -Version <X.Y.Z> `
  -Reviewer <github-login> `
  -DecisionOwner <github-login> `
  -PublishScaffold
```

Příkaz:

- načte live PR head;
- najde PASS `validate-pr` report pro stejný SHA;
- znovu ověří candidate package hash;
- načte Milestone `DDDA <X.Y.Z>`;
- vytvoří working JSON/Markdown mimo source tree;
- volitelně vytvoří nebo aktualizuje právě jeden top-level PR comment s markerem `ddda:human-release-decision:v1`;
- nastaví vždy pouze `decision=pending`.

Automation tím **nevydává rozhodnutí**.

## 3. Lidské rozhodnutí

Človęk vyhodnotí judgment-heavy oblasti a explicitně zvolí:

```text
GO
GO_WITH_ACCEPTED_RISKS
NO_GO
```

Machine-readable hodnoty:

```text
go
go_with_accepted_risks
no_go
```

Pro pozitivní rozhodnutí musí HRDR obsahovat:

- konkrétního `reviewer`;
- konkrétního `decision_owner`;
- `decided_at`;
- exact candidate identity;
- kompletní release-scope Issue set;
- GREEN/AMBER/RED findings;
- u každého accepted risku stable `risk_id`, follow-up Issue, owner, rationale a target/horizon.

`go` nesmí obsahovat accepted risks. `go_with_accepted_risks` musí mít neprázdný accepted-risk set. RED blokuje promotion.

Aktualizace rozhodnutí je explicitní human action. Automation nesmí decision nebo risk set doplnit odhadem.

## 4. Release Scope Gate

`promote-pr` před legacy release executorem provede read-only live gate:

```text
current PR head
+ candidate hash
+ Milestone DDDA <version>
+ milestone Issues
+ native unresolved blockers
+ Project V2 planning rows/views
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
- Accepted-risk Issues jsou mimo current release milestone.
- Accepted-risk Issues jsou otevřené follow-ups.
- Owner v HRDR je současně live assignee Issue.
- Follow-up Issue obsahuje explicitní Target Release/resolution/horizon.
- HRDR nemá RED.
- Human decision je pozitivní.
- Live PR head, source SHA, candidate hash a version se shodují.

Chybějící `DDDA_GITHUB_PROJECT_TOKEN`, nedostupný Project nebo API ambiguity jsou FAIL.

## 5. Promotion dry-run

Po lidském rozhodnutí:

```powershell
.\ddda.ps1 promote-pr -Pr <PR> -Version <X.Y.Z> -DryRun
```

Public command nejdřív spouští governed preflight. Pokud Release Scope Gate selže, interní release executor se nezavolá.

## 6. Skutečný promotion

Vyžaduje samostatnou explicitní human authorization:

```powershell
.\ddda.ps1 promote-pr -Pr <PR> -Version <X.Y.Z> -ConfirmMerge
```

HRDR ani `GO` není automatická autorizace merge. `-ConfirmMerge` odpovídá samostatné governance boundary.

## 7. Invalidation

Human decision se nesmí použít, pokud se změnilo něco relevantního:

- PR HEAD SHA;
- candidate package hash;
- version;
- release scope;
- accepted-risk set/provenance;
- RED status.

Automation nesmí staré rozhodnutí „přemapovat“ na nový candidate.

## 8. PR8-class regression

Povinný negativní test:

```text
CI PASS
validate-pr PASS
HVR PASS
HRDR positive
BUT current release Issue open
→ Release Scope Gate FAIL
→ side_effects_allowed=false
```

Stejně pro unresolved blocker nebo Project/Milestone mismatch.

## 9. Authority

```text
Git/Issue/native dependency/Milestone
  release-scope authority

GitHub Project
  validated operational projection

CI/validate-pr/package
  technical evidence

HRDR
  human decision evidence

promote-pr
  mechanical enforcement
```

Žádná Project hodnota, CI status ani automation comment nemůže vytvořit Human Release Decision.
