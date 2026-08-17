# 16 Založení řízeného projektu

## Účel

Založit libovolný DDDA projekt jedním potvrzeným execution krokem. Chat nejprve připraví intake; skript následně vytvoří workspace, projektový Git repozitář, tailoring, gate records, status a volitelně Miro board.

## 1. Intake přes chat

Doporučený prompt:

> Pomoz mi připravit DDDA project intake. Nezačínej technologií. Ptej se na business problém, rozhodnutí, goal, scope/out-of-scope, aktéry, ownery, omezení, předpoklady, quality attributes, existující systémy a týmy. Doporuč nejmenší vhodný kanonický project type. Výsledkem má být YAML podle `templates/project/project-intake.template.yaml`. Nic nevytvářej, dokud intake nepotvrdím.

Ulož potvrzený soubor například jako:

```text
..\claims-modernization.intake.yaml
```

## 2. Automatizované vytvoření

```powershell
$WorkspaceRoot = (Resolve-Path '..\..').Path

.\scripts\Initialize-DDDAProjectFirstRun.ps1 `
  -WorkspaceRoot $WorkspaceRoot `
  -IntakeFile '..\claims-modernization.intake.yaml' `
  -WithMiro `
  -Full
```

Skript:

1. nainstaluje steering runtime;
2. validuje intake;
3. vytvoří nebo použije workspace;
4. vytvoří samostatný projektový Git repozitář;
5. zapíše `project-intake.yaml`, `project-profile.yaml` a `lifecycle-tailoring.yaml`;
6. vytvoří project charter, G1–G8 records, session context a agent contract;
7. vygeneruje current status a next actions;
8. vytvoří iniciační commit;
9. provede projektové kontroly;
10. volitelně vytvoří Miro board a ověří idempotenci.

## 3. Bez Mira

```powershell
.\scripts\Initialize-DDDAProjectFirstRun.ps1 `
  -WorkspaceRoot $WorkspaceRoot `
  -IntakeFile '..\claims-modernization.intake.yaml'
```

## 4. Bezpečné pokračování po přerušeném běhu

```powershell
.\scripts\Initialize-DDDAProjectFirstRun.ps1 `
  -WorkspaceRoot $WorkspaceRoot `
  -IntakeFile '..\claims-modernization.intake.yaml' `
  -WithMiro `
  -Resume
```

Resume přijme pouze změny v řízených DDDA cestách. Cizí necommitnuté změny zastaví běh.

## 5. Následující chat

> Scope: project. Aktivní projekt: `claims-modernization`. Načti project intake, tailoring, current status a knowledge index. Vysvětli, proč je další gate právě tato, vypiš chybějící evidence a nabídni maximálně tři další kroky. Zápis proveď až po potvrzení.
