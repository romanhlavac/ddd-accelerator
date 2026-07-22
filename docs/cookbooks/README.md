# Kuchařky DDDA

Kuchařky jsou provozní návody krok za krokem. Metodická dokumentace vysvětluje proč a kdy; kuchařka říká co připravit, co udělat, jak ověřit výsledek a co dělat při problému.

## Katalog

| Kuchařka | Použijte, když |
|---|---|
| [01 — Založení projektu](01-zalozeni-projektu.md) | vytváříte nový izolovaný projekt v existující instalaci |
| [02 — Příprava Miro boardu](02-priprava-miro-boardu.md) | potřebujete založit scaffold a připravit workshop |
| [03 — Big Picture EventStorming](03-big-picture-eventstorming.md) | facilitujete doménové discovery napříč end-to-end tokem |
| [04 — Process Modeling](04-process-modeling.md) | rozpracováváte prioritní scénář a rozhodování |
| [05 — Design-Level EventStorming](05-design-level-eventstorming.md) | navrhujete chování uvnitř validovaného bounded contextu |
| [06 — Stavové modely](06-stavove-modely.md) | převádíte observed lifecycle na candidate, validated a případně implementation model |
| [07 — Synchronizace](07-synchronizace-miro-yaml-git.md) | přenášíte změny mezi Mirem a YAML/Gitem |
| [08 — Gate review](08-gate-review.md) | potvrzujete připravenost k dalšímu kroku |
| [09 — Přidání typu projektu](09-pridani-typu-projektu.md) | rozšiřujete DDDA o nový workflow profil |
| [10 — Legacy modernizace](10-legacy-modernizace.md) | připravujete seams, strangler slices a přechodné stavy |

## Standardní struktura kuchařky

Každá kuchařka má:

1. účel a očekávaný výsledek,
2. předpoklady,
3. vstupy,
4. role,
5. postup,
6. kontrolní body,
7. výstupy a jejich umístění,
8. typické chyby,
9. varianty podle typu projektu,
10. navazující krok.

## Pravidlo konzistence

Při změně metodického toku, scaffoldů, schémat nebo synchronizačního kontraktu je nutné ve stejném pull requestu aktualizovat:

- produktovou dokumentaci,
- dotčené kuchařky,
- referenční příklad,
- validační schéma nebo test, pokud se mění formát.
