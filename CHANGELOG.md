# Changelog

Všechny významné změny DDDA platformy jsou evidovány v tomto souboru.

Formát vychází z principu Keep a Changelog. Verze používají Semantic Versioning.

## [Unreleased]

Změny pro další verzi se během vývoje zapisují sem. Před promotion se všechny položky přesunou do jediné verze `X.Y.Z` s ISO datem a tato sekce zůstane bez release položek.

## [0.1.0] - 2026-07-28

### Added

- chat-first project intake, lifecycle tailoring, current status a next actions;
- evidence-driven gate records G1–G8 s explicitním lidským rozhodnutím;
- strukturovaný human gate decision contract vázaný na project ID, scope, Git commit, decision ownera a SHA-256 relevantních evidence artefaktů;
- read-only status query a explicitní status refresh;
- project-owned Miro bootstrap s frame `00 – Navigace, legenda a stav artefaktů`, samostatným DDD Starter journey přehledem, situačními kartami, vyplněnými mini-vzory, metodickými odkazy, managed artifact push, mappingem, sync state a idempotencí;
- přenositelný knowledge pack a capability catalog;
- stabilní platformní entry point `ddda.ps1`;
- izolovaná validace PR nad candidate package;
- generovaný minimal example workspace a manifest-driven ingestion;
- machine-readable i čitelný validation report;
- jednotný strukturovaný Miro acceptance evidence kontrakt pro candidate i release report včetně board identity, managed artifacts, mappingu, sync state, idempotence a cleanup auditu;
- kontrolovaný promotion a release lifecycle;
- GitHub Actions CI, které na přesném source SHA provádí source-level i package-first validaci a publikuje krátkodobý candidate package jako build artifact;
- GitHub REST promotion klient s autentizací přes `GH_TOKEN`, `GITHUB_TOKEN`, `gh auth token` nebo existující Git credential helper, bez povinné instalace GitHub CLI;
- deterministický changelog release cut a promotion preflight ověřující shodu `-Version`, changelog verze a tagu `vX.Y.Z`.

### Changed

- dokumentace je organizována do getting-started, methodology, capabilities, cookbooks, product, reference, developer-guide, user-guide, ADR a migration sekcí;
- projektový Miro bootstrap publikuje vedle scaffoldu také aktuální managed YAML artefakty;
- JSON reporty a jejich testy zachovávají prázdné kolekce jako skutečná pole v PowerShellu 7 i Windows PowerShellu 5.1;
- explicitní `-Resume` adopce pre-steering projektu vytváří pouze aditivní steering metadata a zachovává původní project/lock/workspace/repository/Miro ownership;
- automatický steering acceptance končí na `ready_for_review`; přechod G1 → G2 vyžaduje explicitní lidské rozhodnutí;
- Miro acceptance odděluje technical sync, deklarativní layout contract, remote Miro geometry contract, UTF-8 a human visual acceptance; technický PASS zůstává `PENDING_HUMAN_REVIEW`;
- povinné managed steering artefakty mají explicitní `control-center` placement a stabilní souřadnice;
- `conditional` a `rejected` nejsou completed gates; `conditional` vyžaduje ownera a termín podmínek;
- veškerá release dokumentace používá stejný GitHub auth kontrakt a stejné pořadí providerů jako implementace.

### Fixed

- automatizace, CI, bot ani obecný reviewer text již nemohou vytvořit produkční `passed`;
- změna relevantního scope, ownership nebo evidence hashů zneplatní dřívější gate decision;
- test-only gate simulation je omezena na explicitně označený dočasný fixture projekt;
- Miro renderer odmítá mojibake a DDDA-rendered blocking overlay; Miro Developer-team watermark je evidován jako externí environment constraint a final review podporuje explicitní standardní team;
- current-gate highlight se aktualizuje nad stabilními journey item ID bez recreation boardu; journey používá větší fonty, čtyřzónové seskupení, situační vektorové prvky a explicitní feedback loops;
- pracovní frames jsou zarovnané, obsahují top-left facilitační guide, DDDA kuchařku/metodiku a neprázdný mini-vzor očekávaných artefaktů;
- po renderu se validuje skutečná Miro geometrie, fonty, počty stage/example prvků a remote frame overlaps;
- Miro board ID a auditní metadata se po automatickém cleanupu již neztrácejí a reporty odmítají secret-like evidence;
- Miro child položky převádějí frame-center souřadnice na top-left parent souřadnice REST API a před API voláním validují hranice parent frame;
- syntetická legacy workspace compatibility regrese dokazuje non-breaking/aditivní kontrakt bez klientských dat;
- ADR odstranil zastaralý požadavek na GitHub CLI jako povinnou závislost promotion.

### Compatibility

- změna zachovává kanonický tok `Align → Discover → Decompose → Strategize → Connect → Organize → Define → Code` a gaty G1–G8;
- existující workspace a projektové repozitáře nevyžadují automatickou migraci;
- starší `passed` záznam bez strukturované human provenance není považován za platné schválení a dotčená gate vyžaduje nové lidské review;
- existující specializované PowerShell skripty zůstávají compatibility entry points.
