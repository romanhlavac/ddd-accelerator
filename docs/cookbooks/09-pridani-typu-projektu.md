# Kuchařka 09 — Přidání typu projektu

## Rozhodovací kritérium

Nový typ je oprávněný pouze tehdy, když má odlišný decision problem, mandatory evidence, workflow, gate nebo výsledný hand-off. Odvětvový název, velikost nebo interní zkratka samy nestačí; často stačí alias nebo `workflow.extensions`.

## Chat prompt

> Scope: platform. Posuď, zda požadavek vyžaduje nový kanonický typ, alias nebo workflow extension. Porovnej decision problem, entry criteria, mandatory evidence, gaty, Miro frames, outputs a anti-patterny se všemi existujícími profily. Nejprve navrhni ADR, nic neměň.

## Postup

1. Popiš nový decision problem.
2. Porovnej existující profily.
3. Rozhodni type vs alias vs extension.
4. Definuj entry/exit criteria.
5. Navrhni workflow a gates.
6. Urči mandatory/optional Miro frames.
7. Doplň manifest enum a aliases.
8. Aktualizuj bootstrap validaci.
9. Přidej metodiku, USAGE, cookbook a example.
10. Přidej schema a CI test.
11. Navrhni migraci existujících projektů.

## Povinné platformní změny

- `project.schema.json`,
- `New-DDDAProject.ps1`,
- metodický katalog a USAGE,
- scaffold profile/optional frames,
- chat prompts,
- example manifest,
- compatibility/migration notes.

## Kontroly

- nový typ není synonymum existujícího,
- project type nevyjadřuje technologii,
- gates mají evidence,
- example demonstruje odlišný tok,
- staré projekty zůstávají validní nebo mají migraci.
