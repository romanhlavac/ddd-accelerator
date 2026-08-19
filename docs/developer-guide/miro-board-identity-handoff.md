# Miro board identity handoff při acceptance failure

## Účel

Online Miro acceptance může vytvořit dočasný review board a následně selhat ještě před vytvořením child acceptance reportu. Board identity je auditní identifikátor, nikoli secret, a musí zůstat dostupná pro cleanup a evidence i v tomto failure pathu.

## Kontrakt

Jakmile Miro REST `POST /boards` úspěšně vrátí board ID, Miro CLI emituje na stderr jediný explicitní marker:

```text
DDDA_MIRO_BOARD_ID_HANDOFF:<board-id>
```

Marker vzniká bezprostředně po úspěšném vytvoření boardu, tedy dříve než navazující render, sync nebo child-report kroky. Neobsahuje token, Authorization metadata ani jiná secret-like data.

`Invoke-DDDAMiroAcceptanceEvidence.ps1` zachytí child stdout/stderr a board identity z markeru načte ještě před kontrolou existence child reportu. Pokud child report existuje, jeho `miro_board_id` musí být buď shodné s handoff identitou, nebo handoff nesmí být přítomen. Rozpor znamená fail-closed.

## Failure semantics

Pokud child selže po vytvoření boardu, ale před child reportem:

- wrapper zachová `board_id` a `board_url` ve fallback evidence;
- `-CleanupOnFailure` může board deterministicky odstranit;
- bez cleanup requestu může být board zachován a evidence musí uvést `cleanup.state=preserved`;
- více různých handoff identit je nejednoznačný stav a wrapper failuje closed;
- board identity se nikdy neregeneruje odhadem z logu, URL nebo názvu boardu.

Technický PASS tohoto kontraktu nenahrazuje Human Review. Handoff nemění HRDR, Release Scope Gate, release authorization ani tag governance.

## Regression contract

Automatické testy musí minimálně prokázat:

1. create-board proxy emituje přesně jednu identitu ihned po úspěšném vytvoření boardu;
2. syntetický child failure před reportem stále poskytne board ID/URL wrapperu;
3. konfliktní handoff identity failují closed;
4. existující success-path evidence a cleanup kontrakt zůstávají kompatibilní.
