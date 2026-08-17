# GitHub Project setup — DDDA Platform Backlog & Delivery

## Účel

Tento dokument popisuje administrátorský kontrakt GitHub Projectu pro vývoj DDDA platformy. Project kombinuje dvě odlišné projekce nad jedním společným Projectem:

- **planning projection** — Work Packages a Change Request Issues;
- **delivery projection** — všechny otevřené implementační Pull Requests.

Planning artefakty zůstávají autoritou pro scope, Work Package ownership, prioritu a plán. Pull Request je delivery projection skutečně zahájené implementace, nikoli druhý Change Request ani náhrada backlogu.

Přesné mapování WP/CR, dependencies, field options a bootstrap metadata je verzováno v `config/governance/github-bootstrap.json` a `config/governance/backlog-policy.yaml`. Tento runbook je čitelná provozní interpretace těchto kontraktů.

## Project

```text
Name: DDDA Platform Backlog & Delivery
Owner: romanhlavac nebo budoucí DDDA organizace
Visibility: podle visibility repozitáře; preferováno public pro public repository
Scope: pouze vývoj DDDA platformy
```

Klientské DDDA projekty se do tohoto Projectu nepřidávají.

## Authority model

```text
Work Package / explicit Other
↔ Change Request Issue
↔ Project planning item

Change Request Issue
↔ implementation branch / Pull Request
↔ Project delivery item
```

Pravidla:

- každý governed CR má jedno autoritativní WP nebo `Other`;
- každý otevřený implementační PR má právě jeden primary `Implements #<CR>` nebo `Closes #<CR>` vztah, kromě verzované legacy výjimky PR #8;
- PR Work Package se odvozuje z primary CR;
- otevřený implementační PR musí být Project item;
- planning `Item Type` se na PR nenastavuje;
- plánované/prázdné PR jsou jako backlog zakázány.

## Povinná pole

Project používá verzované field options z `config/governance/github-bootstrap.json`. Z hlediska tohoto kontraktu jsou povinná zejména:

```text
Status
Priority
Work Package
Item Type
Platform Area
Impact
Blocked
Human Review
Target Release
Start date
Target date
Outcome summary
Dependency
```

Systémová pole používaná v relevantních views:

```text
Parent issue
Sub-issue progress
Milestone
Linked pull requests
```

### Planning semantics

- `Item Type` je používán pro Issues (`Work Package`, `Change Request`, případně další planning typy).
- Native Parent/Sub-issue je primární WP hierarchy, pokud je dostupná.
- Project `Work Package` musí odpovídat autoritativnímu WP.
- `Milestone` je release scope; není release approval.

### Delivery semantics

Pro otevřený PR:

```text
Work Package = Work Package(primary CR)
Item Type    = <unset>
Status       = Blocked      if Blocked = Yes
               In progress  if Draft and not blocked
               In review    if open non-draft and not blocked
```

PR #8 je dočasná verzovaná legacy výjimka pouze pro primary CR relationship. Jeho delivery WP je WP-08 do merge/close. Výjimka neobchází Human Review ani release governance.

## Kanonické views

Kanonické machine-managed views jsou přesně dvě:

### 1. Plánování a Backlog

```text
Layout: Table
Filter: is:issue
```

Účel: Work Packages, Change Requests, priority, hierarchy, dependencies a release planning.

### 2. Implementace a Delivery

```text
Layout: Table
Filter: is:pr is:open
```

Účel: aktuálně otevřené implementační PR, jejich derived WP, delivery status, blocker a Human Review visibility.

Další analytické views jsou volitelné. Nejsou authority a jejich existence nesmí být podmínkou governance PASS.

## Hierarchy a dependencies

Přesný seznam Parent/Sub-issue vazeb a `Blocked by` hran je definován v `config/governance/github-bootstrap.json`. Administrátor je nesmí ručně odvozovat z title prefixů nebo Git ancestry.

Prefix `[WP-XX]` je pouze presentation metadata. Pokud je uveden, musí souhlasit s autoritativním WP; rozpor je fail-closed governance chyba.

## Automations

Automatizace smí mechanicky synchronizovat pouze explicitně odvoditelné hodnoty:

- přidání governed Issues do planning projection;
- přidání všech open implementation PRs do delivery projection;
- PR Work Package podle primary CR;
- PR delivery Status podle Draft/Ready a `Blocked`;
- odstranění planning `Item Type` z PR;
- closed Issue → `Done`/`Cancelled` podle state reason;
- Project title a canonical view filters.

Automatizace nesmí sama nastavovat nebo odvozovat:

- produktové WP ownership bez explicitního CR mappingu;
- primary CR, pokud je vazba chybějící nebo víceznačná;
- Priority;
- Target Release/Milestone;
- Human Review PASS/FAIL;
- gate decision;
- merge, promotion, tag nebo release approval.

Nejednoznačnost je blocker, nikoli podnět k heuristickému rozhodnutí.

## Privileged reconciliation

Live Project se spravuje pouze přes ručně spuštěný privileged workflow `.github/workflows/reconcile-ddda-project-backlog.yml` s prostředím `ddda-backlog-governance` a persistent Project credentialem.

Workflow musí:

1. běžet nad exact source SHA;
2. validovat versioned governance kontrakty;
3. provést idempotentní reconciliation;
4. provést repository-wide read-back planning i delivery projekce;
5. skončit FAIL při libovolném nevysvětleném mismatchu;
6. uložit audit evidence do `.reports/cr-delivery-audit-v6/`;
7. nikdy neudělat Human Review, merge, promotion, tag ani release.

## Milestones

Milestone zůstává autoritou pro release scope. Project membership ani `Target Release` samy o sobě nejsou release approval.

`DDDA 0.1.0` se řídí verzovaným bootstrap kontraktem. PR #8 zůstává jeho stávajícím implementation PR; tato governance změna nesmí měnit jeho source branch ani head SHA.

## Kontrolní checklist po reconciliation

- [ ] Project title je přesně `DDDA Platform Backlog & Delivery`.
- [ ] `Plánování a Backlog` existuje jako Table s filtrem `is:issue`.
- [ ] `Implementace a Delivery` existuje jako Table s filtrem `is:pr is:open`.
- [ ] Každý governed WP/CR je přítomen v planning projection a má správný typ/WP.
- [ ] Každý open implementation PR je přítomen v delivery projection.
- [ ] Každý non-legacy open PR má právě jeden primary CR.
- [ ] PR Work Package odpovídá primary CR.
- [ ] PR `Item Type` je prázdný.
- [ ] PR `Status` odpovídá blocked/draft/review state.
- [ ] Native hierarchy a dependencies odpovídají versioned contractu.
- [ ] Explicitní WP title prefixy neodporují autoritativnímu WP.
- [ ] Post-read-back `remaining_mismatches = 0`.
- [ ] Audit artifact je svázán s exact source SHA.
- [ ] Technical PASS není prezentován jako Human Review, Ready, merge nebo release approval.
