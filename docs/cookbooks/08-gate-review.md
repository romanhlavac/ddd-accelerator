# Kuchařka 08 — Gate review

## Výsledek

Auditovatelný závěr `pass`, `conditional` nebo `fail`, nikoli pouze zelená značka na boardu.

## Prompt

> Proveď gate review G5. Načti definici gate, vyhledej evidence v artifacts a decisions, u každého kritéria uveď path a status. Rozliš missing evidence, disagreement a accepted risk. Nenastavuj completed gate bez potvrzení ownerů.

## Postup

1. načti gate definition,
2. vytvoř evidence matrix,
3. ověř source a status,
4. identifikuj podmínky a owners,
5. zaznamenej approvals,
6. aktualizuj Miro gate marker,
7. commitni gate review odděleně od velkého modelového refactoringu.
