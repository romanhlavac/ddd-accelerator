# Kuchařka 08 — Gate review

## Účel

Gate review vytváří auditovatelný závěr `pass`, `conditional` nebo `fail`. Gate není projektový status report ani hlasování podle pocitu. Každé kritérium musí odkazovat na evidence a ownera rozhodnutí.

## Entry criteria

- definice gate a povinných artefaktů je dostupná,
- relevantní YAML a ADR jsou ve reviewovatelném stavu,
- pending konflikty a hotspoty jsou známé,
- business a architecture owner mohou review provést.

## Chat prompt

> Scope: project. Proveď gate review G5. Načti definici gate, vyhledej evidence v `artifacts/`, `decisions/` a sync reports. U každého kritéria uveď path, status, confidence a chybějící evidence. Rozliš disagreement, accepted risk a missing work. Navrhni pass/conditional/fail, ale nenastavuj completed gate bez potvrzení ownerů.

## Postup

1. Načti gate definition a project profile.
2. Vytvoř evidence matrix.
3. Ověř source, status a poslední změnu artefaktu.
4. Zkontroluj pending Miro konflikty.
5. Identifikuj podmínky, owners a termíny.
6. Proveď business a architecture review.
7. Zaznamenej approvals a dissent.
8. Aktualizuj gate artefakt a Miro marker.
9. Připrav samostatný checkpoint commit.

## Výstup

```yaml
gate_review:
  gate: G5
  outcome: conditional
  evidence:
    - criterion: data_ownership
      path: artifacts/connect/data-ownership.yaml
      status: pass
  conditions:
    - owner: data-architecture
      action: potvrdit source of truth pro party identity
  approvals:
    business_owner: pending
    architecture_owner: accepted
```

## Kontroly

- každé `pass` má konkrétní evidence,
- condition má ownera a ověřovací krok,
- accepted risk má explicitní rozhodnutí,
- Miro gate barva odpovídá YAML review,
- completed gate je aktualizován až po schválení.

## Anti-patterny

- gate jako administrativní checklist,
- zelená značka bez evidence,
- condition bez ownera,
- změna modelu a schválení gate v neprůhledném jednom commitu.
