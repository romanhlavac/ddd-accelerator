# REM-PR8-HVA-CC-010 — nová human-review revize

Status: IMPLEMENTED, PENDING_HUMAN_REVIEW

Date: 2026-08-02

Scope: PR #8, branch `feat/project-steering-and-documentation`

Read-only review sources:

- redline: `https://miro.com/app/board/uXjVH2vcvRI=/`;
- DDD Starter artefakty: `https://miro.com/app/board/uXjVH27wYU4=/`.

## Proč předchozí náprava nesplnila požadavky

1. **Chybný normativní předpoklad.** ADR 0003 výslovně požadoval ponechat frame `01` interně beze změny. Implementace tak optimalizovala jiný kontrakt, než požadoval redline review.
2. **Globální místo frame-scoped akceptace.** Testy počítaly osm stages, osm gates, konektory a texty na celém boardu. Neověřily, že tyto položky jsou children frame `01`.
3. **Geometrie byla zaměněna za vlastnictví.** Journey byla vizuálně umístěna přes plochu frame `01`, ale Miro `parent` zůstal prázdný. Při navigaci na frame byl proto `01` prázdný.
4. **Traceability skončila u obecného odkazu.** Scaffold odkazoval na web DDD Starter Modelling Process, ale ne na konkrétní frames a artefakty v uživatelem určeném boardu `uXjVH27wYU4=`.
5. **Generické mini-vzory prošly jako metodická věrnost.** Acceptance kontrolovala počet items a jejich role, ne rozpoznatelnou strukturu Business Model Canvas, Strategic Classification, Bounded Context Canvas nebo Context Map notace.
6. **Technický PASS byl nesprávně komunikován jako dostatečný výsledek.** Zelený online test dokazoval reprodukovatelnost a synchronizaci, nikoli vizuální shodu s redline ani kvalitu lidského review.

## Požadavek versus odmítnutý stav versus REM-010

| Požadavek | Odmítnutý board | REM-010 | Automatická evidence |
|---|---|---|---|
| Přepracovat `01` podle redline | frame `01` měl 0 child items; cesta byla top-level | cesta, gates, stage visuals, zones, resources a osm source cards jsou children `01` | `overview_child_count >= 61`; negativní detached-item test |
| Zachovat čitelnou G1–G8 journey a iterace | globální items bez frame ownership | 8 stage cards, 8 gate diamonds, stage mini-vzory a feedback connectors ve frame `01` | parent role contract + connector counts |
| Převzít/inspirovat vzory z `uXjVH27wYU4=` | pouze obecný webový odkaz | exact board ID, source frame URL a viditelná source caption v `VZOR / LEGENDA` | nejméně 11 source captions a povinné source titles |
| Align podle přiloženého vzoru | obecný problém/rozhodnutí/owner/scope | devítipolový Business Model Canvas | položky Key Partners, Activities, Resources, Value Propositions, Relationships, Channels, Segments, Costs, Revenue |
| Decompose podle DDD Starter | Core/Supporting/Generic bez přechodu prostorů | event clusters/subdomains + `PROBLEM SPACE` → `SOLUTION SPACE` + team-boundary otázka | source title a template structure |
| Strategize podle DDD Starter | tři boxy bez matice | osy `MODEL COMPLEXITY` × `BUSINESS DIFFERENTIATION`, zóny a plotted domain | source title a template structure |
| Context/Define/Code vzory | generické, bez původu | Context Map notation, Bounded Context Canvas a Domain Message Flow mají exact source frame | viditelné source titles a board ID |
| Nedeklarovat human PASS automaticky | technický PASS byl prezentován jako dostatečný | `overall_status: PENDING_HUMAN_REVIEW` | runtime i acceptance assertions |

## Zdrojové artefakty a cílové vzory

| DDD Starter source frame | Cílový template/frame | Převzatý princip |
|---|---|---|
| `Business model canvas - exercise` | `align` / frame `10` | devět kanonických polí canvasu |
| `Big Picture organized` | `big_picture`, `evidence` / frames `20`, `21` | event timeline, actors, policies, hotspots a otevřené otázky |
| `Process Modelling` | `process` / frame `22` | actor, command, policy, event, read model |
| `Finding Domains and subdomains - group 1` | `decompose` / frame `30` | clustery událostí a subdomény |
| `Bounded Contexts - Group 1` | frame `30` guide | Problem Space → Solution Space a boundary heuristiky |
| `Strategic classification` | `strategize` / frame `40` | 2D klasifikační matice |
| `Context Maps - Examples` | `context_map` / frame `50` | upstream/downstream a integrační patterny |
| `Starter Modelling Process - Organize` | `teams` / frame `60` | BC ownership a týmové interaction modes |
| `Bounded Context Canvas` | `bc_canvas` / frame `70` | purpose, decisions, language a komunikace |
| `Domain Message Flow Modelling - Example` | `design_es` / frame `71` | messages mezi aktérem, systémy a bounded contexts |

## Co automatizace stále neposuzuje

Automatizace prokazuje strukturu, parent vazby, zdrojové citace, reprodukovatelnost, čitelné minimální fonty a idempotenci. Neposuzuje, zda je výsledná kompozice pro člověka dostatečně přehledná, esteticky vyvážená nebo metodicky přesvědčivá. Tyto body zůstávají výhradně v HUMAN REVIEW.

## Zakázané operace

Tato remediation neautorizuje merge, promotion, release, tag, force-push ani změnu zdrojových Miro boardů. Nový review board je izolovaný výstup exact candidate SHA.
