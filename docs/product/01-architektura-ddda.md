# Architektura produktu DDDA

## Cíl

DDDA odděluje platformní produkt od projektových dat. Platforma poskytuje starter metodiku, knowledge pack, konfiguraci, schémata, runtime, scaffoldy, skripty a dokumentaci. Projekt obsahuje business evidence, intake, tailoring, doménové artefakty, gate decisions, Miro stav a rozhodnutí.

## Komponenty

```text
Chat / Cursor agent
  ├─ načte project intake, tailoring, current status a knowledge index
  ├─ vede otázky, varianty, review a gate framing
  ├─ respektuje agent contract a repository scope
  └─ po potvrzení volá PowerShell wrappers
       ├─ Python steering runtime
       │    ├─ intake validation
       │    ├─ lifecycle tailoring
       │    ├─ evidence-driven gate evaluation
       │    ├─ current status a next actions
       │    └─ agent/session contracts
       └─ Python Miro runtime
            ├─ REST API v2 client
            ├─ scaffold renderer
            ├─ YAML/Miro sync engine
            ├─ conflict detector
            └─ audit reports

Project repository
  ├─ project-intake.yaml
  ├─ project-profile.yaml
  ├─ lifecycle-tailoring.yaml
  ├─ ingestion/
  ├─ artifacts/
  │    └─ status/current-status.yaml + next-actions.yaml
  ├─ decisions/gates/
  ├─ workshops/prompts/
  ├─ .ddda/session-context.yaml + agent-contract.yaml
  ├─ miro/miro-map.yaml + sync-state.yaml + conflicts/
  └─ reports/
```

## Architektonická rozhodnutí

1. DDD starter metodika Align → Code je kanonické metodické jádro.
2. Tailoring rozšiřuje a parametrizuje starter tok; nenahrazuje jej.
3. Chat je primární rozhraní pro porozumění, review a potvrzení execution kroku.
4. Skripty a runtime jsou deterministické execution mechanismy.
5. YAML je kanonická sémantika.
6. Miro vlastní layout a kolaboraci.
7. Git je approval a audit boundary.
8. Evidence status lze automatizovat; gate decision vyžaduje explicitní lidské review.
9. Runtime používá REST API v2 a OAuth bearer token.
10. Synchronizace je řízená; polling worker se zastaví při konfliktu.
11. Dry-run je povinný před Miro write operací v chat-first workflow.
12. Sémantické konflikty se ukládají jako explicitní records.
13. Mazání je tombstone-first.
14. Push, merge a gate approval nejsou implicitní automatizace.

## Quality attributes

- **auditability** — každý sync a gate decision zanechá report nebo Git diff;
- **safety** — tokeny nejsou v repozitáři, žádný implicitní merge ani gate approval;
- **idempotence** — mapping drží stabilní Miro item ID a status generátor je opakovatelný;
- **recoverability** — marker a mapping umožňují obnovit identitu, resume omezuje write scope;
- **portability** — workspace používá relativní cesty, knowledge pack je součástí clone;
- **evolvability** — steering, Miro runtime, schémata a capability catalog lze rozšiřovat odděleně;
- **explainability** — current status uvádí chybějící evidence a doporučený další krok.

## Omezení

Miro REST API nepodporuje libovolná skrytá metadata pro všechny item typy, proto DDDA používá mapping a viditelný marker. Evidence-driven gate engine ověřuje existenci a strukturu podkladů, nikoli jejich business pravdivost. Schválení zůstává odpovědností příslušného ownera.
