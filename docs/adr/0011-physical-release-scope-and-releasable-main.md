# ADR 0011: Physical release scope and releasable main

Status: Accepted

Date: 2026-08-25

## Context

Milestone a Project mohou správně deklarovat release scope, zatímco canonical
`main` už obsahuje jinou, dříve integrovanou změnu. Původní Release Scope Gate
ověřoval pouze deklarovanou authority. Mohl proto propustit package obsahující
PR pro pozdější release nebo `TBD`.

## Decision

Pro exact release-candidate source se gate read-only odvodí:

```text
previous canonical SemVer tag
→ exact candidate source SHA
→ every physical commit
→ associated merged shipping PR
→ exactly one primary Implements/Closes CR
→ Milestone + Project Target Release projection
```

Invariant je:

```text
DECLARED_RELEASE_SCOPE == PHYSICAL_RELEASE_SOURCE_SCOPE
```

Chybějící commit→PR vztah, více nebo nula primary CR, non-merged PR, rozdíl
Milestone/Target Release nebo source ancestry je fail-closed. Gate publikuje
machine-readable inventory a `RECOVERY_DECISION_REQUIRED`. Automation nikdy
nevolí human scope expansion, controlled source recovery ani novou
release-source strategii.

Dokud existuje právě jeden otevřený Milestone `DDDA X.Y.Z`, governed
implementation merge smí do `main` pouze PR s jediným primary CR v tomto
Milestone. Tím se nová kontaminace zastaví před merge. Guard je read-only a
není Release Scope Gate, HRDR ani release authorization.

## Consequences

- již kontaminovaný current source nelze vydat bez explicitního lidského
  recovery decision;
- implementační merge zůstává oddělený od release promotion, ale budoucí
  later/TBD scope nemůže běžnou cestou kontaminovat otevřený train;
- release evidence obsahuje exact tag/source/commit/PR/CR inventory;
- `v0.1.0` ani historické tagy se nemění.

## Validation

- unit regrese A+B declared / A+B+E physical = FAIL;
- unit regrese pro TBD/later primary CR, chybějící commit mapping, více primary
  CR a wrong ancestry;
- contract test, že merge guard běží před merge side effect;
- exact-SHA standardní PR CI a package-first validation.
