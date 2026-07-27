# 17 Current status, gaty a další krok

## Zobrazení stavu

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot
```

Výchozí režim je read-only. Načte již vytvořený `reports/project-status.yaml` a nemění projektový Git working tree.

Výstup ukazuje aktuální fázi, další gate, chybějící evidence a doporučený chatový prompt.

Strojově čitelný read-only výstup:

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot -Json
```

## Explicitní přepočet stavu

Po ruční změně evidence lze status výslovně přepočítat:

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot -Refresh
```

Přepočet aktualizuje:

- `artifacts/status/current-status.yaml`;
- `artifacts/status/next-actions.yaml`;
- `reports/project-status.yaml`.

Jde o write operaci. Před navazující Miro inicializací nebo synchronizací musí být změny zkontrolované a commitnuté.

## Kontrola gatů

```powershell
.\scripts\Test-DDDAGates.ps1 -ProjectPath $ProjectRoot
```

Konkrétní gate:

```powershell
.\scripts\Test-DDDAGates.ps1 -ProjectPath $ProjectRoot -Gate G3
```

`ready_for_review` neznamená schváleno. Znamená pouze, že konfigurace našla požadované evidence paths.

## Povinný human decision contract

Stavy `passed`, `conditional` a `rejected` jsou lidská rozhodnutí. Produkční příkaz vyžaduje:

- `-HumanDecision` jako explicitní approval boundary;
- decision ownera, který odpovídá roli nebo konkrétní identitě v `project.yaml owners`;
- konkrétní lidskou identitu reviewera a approvera;
- explicitně posuzovaný scope;
- čistý projektový Git working tree a platný HEAD commit.

Příkaz automaticky zaznamená commit, hash scope/ownership a SHA-256 relevantních evidence artefaktů. Změna relevantních podkladů dřívější rozhodnutí zneplatní.

Automatizační identity jako `CI`, `bot`, `pipeline`, `automation` nebo `Acceptance runner` nejsou přijatelné jako reviewer ani approver.

## Explicitní gate review — passed

Nejprve ověř čistý projekt:

```powershell
git -C $ProjectRoot status --short
```

Potom zaznamenej lidské rozhodnutí:

```powershell
.\scripts\Complete-DDDALifecycleStep.ps1 `
  -ProjectPath $ProjectRoot `
  -Gate G1 `
  -Outcome passed `
  -DecisionOwner 'business_owner' `
  -Reviewer 'Jana Nováková' `
  -Approver 'Jana Nováková' `
  -Scope 'Project purpose, scope, out-of-scope a decision ownership' `
  -HumanDecision `
  -Note 'Scope a decision owner potvrzeny'
```

`DecisionOwner` může být role z `project.yaml owners`, například `business_owner`, nebo konkrétní identita uvedená u této role. Automatizace kontroluje konzistenci, ale neurčuje, kdo má oprávnění rozhodnout.

Skript aktualizuje gate record, `project.yaml`, current status a next actions. Commit standardně nevytvoří.

## Kontrolovaný commit

Nejprve:

```powershell
git -C $ProjectRoot diff
git -C $ProjectRoot diff --check
```

Potom lze stejný příkaz spustit s `-Commit`. Vytvoří lokální commit, nikoli push nebo merge.

Po commitu lze stav bezpečně číst bez dalších změn:

```powershell
.\scripts\Get-DDDAProjectStatus.ps1 -ProjectPath $ProjectRoot
```

## Conditional gate

`conditional` není completed gate a neposune standardní workflow jako `passed`. Vyžaduje podmínky, jejich ownera a termín:

```powershell
.\scripts\Complete-DDDALifecycleStep.ps1 `
  -ProjectPath $ProjectRoot `
  -Gate G5 `
  -Outcome conditional `
  -DecisionOwner 'architecture_owner' `
  -Reviewer 'Petr Svoboda' `
  -Approver 'Petr Svoboda' `
  -Scope 'Context map a source of truth pro party identity' `
  -HumanDecision `
  -Condition 'Potvrdit source of truth pro party identity' `
  -ConditionOwner 'Identity domain owner' `
  -ConditionDueAt '2026-08-31'
```

## Rejected gate

`rejected` je explicitní lidské rozhodnutí, ale není completed gate. Zůstává auditovatelně zaznamenáno a workflow nepokračuje.

## Test-only simulation

`-TestSimulation` není zkratka pro produkční schválení. Funguje pouze při současném splnění všech guardů:

- projekt je pod systémovým temp adresářem;
- existuje marker `.ddda/test-fixture`;
- proces má `DDDA_GATE_TEST_SIMULATION=1`.

Takový záznam má `provenance: test_simulation` a bez testovacího runtime guardu není považován za platný.
