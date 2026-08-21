# Changelog

Všechny významné změny DDDA platformy jsou evidovány v tomto souboru.

Formát vychází z principu Keep a Changelog. Verze používají Semantic Versioning.

## [Unreleased]

### Added

- machine-readable `human-release-decision.schema.json`, `review-pr` scaffold a fail-closed Release Scope Gate pro exact release-candidate SHA / candidate package / release-version identity;
- governed implementation command `merge-pr` a machine-readable Human Review marker `ddda:human-pr-review:v1`, vázané na exact PR SHA a candidate package hash;
- ADR 0008 a developer runbook oddělující Human Review/implementation merge, Human Release Decision a mechanickou release-scope completeness;
- ADR 0009 a versioned merge-strategy contract zachovávající exact validated SHA ancestry pro HIGH/BREAKING změny a explicitní human squash exception pro LOW/MEDIUM.

### Changed

- GitHub-native backlog governance nyní považuje Issue/PR mutation, Project planning/delivery projection a release Milestone projection za jednu fail-closed transakci; DDDA 0.1.0/0.1.1 scope je versioned a canonical reconciler opravuje Project/Milestone drift před Ready/merge/release doporučením.
- platform lifecycle nyní explicitně odděluje governed merge implementačních PR od skutečného release/promotion; implementation merge nevyžaduje HRDR ani Release Scope Gate a nesmí vytvořit release package, release validation nebo tag;
- public `promote-pr` zůstává strict release-candidate command: před interním release executorem vyžaduje validní human HRDR a read-only Release Scope Gate PASS nad Milestone, native blockers a GitHub Project V2 projekcí;
- governed implementation merge používá po aktivaci #70 merge commit jako canonical default; HIGH/BREAKING a neklasifikované PR nesmějí squash/rebase, LOW/MEDIUM squash vyžaduje explicitní human exception a canonical merge ověřuje validated PR HEAD server-side jako parent/ancestor výsledného main state.

### Fixed

- exact-SHA PR governance nyní používá jeden canonical candidate artifact napříč platform CI, `validate-pr`, remote brokerem, validation reportem, Human Review a isolated `merge-pr -DryRun`; paralelní rebuildy, runner-local evidence paths a chybějící či víceznačné artifact identity failují closed;
- pre-HR merge orchestrace nyní odděluje `Human Review readiness` od skutečného `Governed merge dry-run`; bez Human Review je dry-run `skipped`/`NOT_RUN` a `success` může vzniknout pouze po provedeném `merge-pr -DryRun` nad existujícím exact-run candidate/reportem;
- promotion dry-run wrapper nyní používá operation-local výsledek a explicitní post-read-back side-effect assertions; očekávaná `404` absence tagu/GitHub Release je PASS assertion, zatímco auth/network/API chyby zůstávají FAIL, takže PR8-class `semantic PASS / wrapper FAIL` false-negative se nemůže opakovat přes stale `$LASTEXITCODE`;
- annotated release tag nyní používá deterministic non-secret Git identity pouze v izolovaném release-source clone; clean runner proto nezávisí na ambientním `user.name`/`user.email` a bounded recovery po post-validation tag failure je explicitně zdokumentována;
- Miro acceptance evidence zachová exact board ID/URL i při child failure po vytvoření boardu, ale před child reportem; konfliktní handoff identity nebo mismatch s reportem failují closed a cleanup může cílit na skutečně vytvořený board.

Změny pro další verzi se během vývoje zapisují sem. Před promotion se všechny položky přesunou do jediné verze `X.Y.Z` s ISO datem a tato sekce zůstane bez release položek.

## [0.1.0] - 2026-07-28

### Added

- `chat-atomic` implementační fallback pro vývoj DDDA platformy při nedostupném Work: exact-SHA source snapshot, jeden Git tree commit, non-force fast-forward update PR branche a povinné standardní CI;
- ADR `0006` a policy guardrails pro jednorázový self-removing bootstrap control-plane změn;
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
- deterministický changelog release cut a promotion preflight ověřující shodu `-Version`, changelog verze a tagu `vX.Y.Z`;
- kanonický `knowledge/ddda-platform-development-skill.md` s povinnými pravidly pro platformní vývoj, transakční remediation workflow, exact-SHA validaci a oddělení technického a lidského rozhodování;
- kanonický dvourovinný operating model: Chat/Work pro vývoj platformy a Cursor jako povinný agentic runtime konkrétního DDDA projektu;
- aktivní Cursor runtime assets `.cursor/rules/*.mdc` a `.cursor/skills.md` s project-only a no-platform-write guardrails;
- CI contract test oddělující platform-development policy od Cursor project runtime policy.

### Changed

- Miro integration používá explicitní execution profiles: REST API je deterministický automation plane, MCP je volitelný interaktivní kanál bez vlivu na technical gate; PR #8 HVR podporuje oddělený HVR/Platform-Lab credential chain a project runtime zachovává per-project token/team/Space/board binding s automatickým create-board flow;
- Work zůstává preferovaným implementačním režimem, ale Chat může bezpečně realizovat atomickou platformní změnu bez sekvenčních multi-file Contents API commitů;
- `issue_comment` broker se nepovažuje za dostupný bootstrap mechanismus, dokud jeho workflow není na default branchi;
- vývoj DDDA platformy používá pouze Chat a Work; GitHub Actions je autoritativní execution plane pro shell, build, testy, candidate package a package-first acceptance, secrets zůstávají mimo Chat/Work runtime a Work zapisuje pouze na explicitní platformní PR branch;
- vlastní práce architekta v konkrétním DDDA projektu probíhá v Cursoru, který poskytuje chat, agentic práci s projektovými soubory, artefakty a kódem; Cursor nesmí měnit DDDA platform repository;
- platformní defect nebo obecný enhancement nalezený při projektové práci se předává jako change request do Chat/Work platform-development flow;
- Miro visual acceptance vyžaduje skutečné načtení referenčních a cílových framů, side-by-side porovnání, obrázky, fonty, geometrii, překryvy, využití plochy a first-viewer usability; strukturální PASS zůstává oddělen od human review;
- corrective remediation `REM-PR8-HVA-CC-011`: syntetický claims scénář používá jednotný business problém a ubiquitous language; všechny povinné DDD Starter vazby míří na exact `moveToWidget` frame, G7 overview odpovídá Bounded Context Canvasu a odkazy označené jako kuchařka míří výhradně pod `docs/cookbooks/`;
- corrective remediation `REM-PR8-HVA-CC-010`: frame `01` vlastní nejméně 61 navigovatelných child items a zobrazuje exact redline/DDD Starter traceability; workshopové vzory citují konkrétní source frames a rozpoznatelně adaptují Business Model Canvas, EventStorming, Process Modelling, Strategic Classification, Context Map, Bounded Context Canvas a Domain Message Flow;
- Miro scaffold schema `2.5`, remote acceptance a content digest kontrolují parent vazby frame `01`, nejméně 280 remote items a nejméně 11 viditelných DDD Starter source captions; HUMAN REVIEW zůstává `PENDING`;
- korekce `REM-PR8-HVA-CC-002`: Miro scaffold schema `2.4` používá deterministické stage columns a ve frames `20–82` kanonický shell `method guide | editable work area | VZOR / LEGENDA`; frames `01` a `10` zůstávají interně beze změny;
- Control Center odděluje `Project / Gate State`, `Artifact Lifecycle` a `Artifact Provenance` a promítá managed YAML do jediného devítisloupcového Artifact Registry;
- method guides ve frames `20–82` obsahují method-specific recept, definition of done, otevřené otázky, heuristiky a anti-patterns;
- dokumentace je organizována do getting-started, methodology, capabilities, cookbooks, product, reference, developer-guide, user-guide, ADR a migration sekcí;
- projektový Miro bootstrap publikuje vedle scaffoldu také aktuální managed YAML artefakty;
- JSON reporty a jejich testy zachovávají prázdné kolekce jako skutečná pole v PowerShellu 7 i Windows PowerShellu 5.1;
- explicitní `-Resume` adopce pre-steering projektu vytváří pouze aditivní steering metadata a zachovává původní project/lock/workspace/repository/Miro ownership;
- automatický steering acceptance končí na `ready_for_review`; přechod G1 → G2 vyžaduje explicitní lidské rozhodnutí;
- Miro acceptance odděluje technical sync, deklarativní layout contract, remote Miro geometry contract, UTF-8 a human visual acceptance; technický PASS zůstává `PENDING_HUMAN_REVIEW`;
- povinné managed steering artefakty mají explicitní `control-center` placement a stabilní souřadnice;
- `conditional` a `rejected` nejsou completed gates; `conditional` vyžaduje ownera a termín podmínek;
- veškerá release dokumentace používá stejný GitHub auth kontrakt a stejné pořadí providerů jako implementace;
- knowledge index a developer lifecycle vyžadují explicitní runtime registraci platform-development skillu v knowledge routingu nebo Project/Work Instructions; samotná existence souboru v Gitu není považována za aktivaci instrukcí.

### Fixed

- PR8 Miro Tips visual-arrow fidelity: po HVR důkazu, že Miro REST endpoint metadata + `shape=curved` neumí reprodukovat ručně routovanou křivku, je osm screenshot calloutů převedeno na osm těsně oříznutých transparentních golden-arrow overlay PNG s verzovanými SHA-256 a frozen frame geometrií; fyzické Miro connectory zůstávají pouze tři deterministické straight text callouty nad šesti per-endpoint controls. Acceptance zakazuje native curved screenshot connectors, ověřuje 8/8 overlay identity/geometry, 3/3 connector geometry, zero-mutation second reconcile a HVR copy se `HUMAN_VISUAL_ACCEPTANCE=PENDING`;
- opravena chybná plošná interpretace „Chat/Work-only“, která dočasně deaktivovala Cursor i pro vlastní DDDA project runtime; zákaz Cursoru nyní platí pouze pro vývoj platformy;
- candidate-package validation sanitizuje ambientní `PYTHONPATH`, `PYTHONHOME` a DDDA root proměnné před spuštěním child procesů;
- Miro CLI běží v Python isolated mode a před prvním vzdáleným zápisem ověřuje skutečně importovaný modul, jeho SHA-256 a render contract;
- GitHub Actions remote-execution broker umožňuje oprávněnému actorovi spouštět exact-SHA validation/acceptance bez předání Miro tokenu do ChatGPT runtime;
- lidské visual review už nemůže zaměnit gate state za lifecycle nebo provenance artefaktu;
- technický acceptance PASS už nemůže vzniknout pouze z lokálního mappingu: board musí prokázat exact candidate SHA, scaffold hash, render contract, minimálně 250 skutečně načtených items, povinný viditelný obsah a remote content digest;
- editovatelná workshopová plocha je explicitně `manual`, zatímco celý `VZOR / LEGENDA` zůstává `ignore` a je vyloučen z ingestion;
- Artifact Registry používá reprodukovatelný shape-grid a transparentně deklaruje omezení Miro REST API v2 namísto předstírání nativní Miro Table;
- automatizace, CI, bot ani obecný reviewer text již nemohou vytvořit produkční `passed`;
- změna relevantního scope, ownership nebo evidence hashů zneplatní dřívější gate decision;
- test-only gate simulation je omezena na explicitně označený dočasný fixture projekt;
- Miro renderer odmítá mojibake a DDDA-rendered blocking overlay; Miro Developer-team watermark je evidován jako externí environment constraint a final review podporuje explicitní standardní team;
- current-gate highlight se aktualizuje nad stabilními journey item ID bez recreation boardu; journey používá větší fonty, čtyřzónové seskupení, situační vektorové prvky a explicitní feedback loops;
- pracovní frames jsou zarovnané, obsahují top-left facilitační guide, DDDA kuchařku/metodiku a neprázdný mini-vzor očekávaných artefaktů;
- po renderu se validuje skutečná Miro geometrie, fonty, počty stage/example prvků a remote frame overlaps;
- Miro board ID a auditní metadata se po automatickém cleanupu již neztrácejí a reporty odmítají secret-like evidence;
- Miro child položky převádějí frame-center souřadnice na top-left parent souřadnice REST API a před API voláním validují hranice parent frame;
- Miro REST payloady normalizují velikosti písma na podporovanou diskrétní škálu před voláním text/shape endpointů;
- Miro REST connector payloady normalizují pozici caption z relativního čísla na percentage wire formát očekávaný živým API;
- Miro board obsahuje kompaktní first-user onboarding, základní DDD Starter/DDDA zdroje a explicitní Control Center název;
- vyšší metodické zóny jsou zarovnané a stage, gate, zone i feedback flow používají stabilní shapes a popsané Miro connectors;
- workshopové mini-vzory používají metodicky specifické sticky notes, shapes a table-grid reprezentace namísto generických karet;
- každý pracovní frame má oddělený panel `VZOR / LEGENDA`, jehož položky a connectors jsou explicitně vyřazeny z Miro → YAML synchronizace a ingestion;
- artifact-status projekce v Control Center používá deterministický shape-grid, protože Miro REST API v2 neposkytuje vytvoření nativní tabulky;
- syntetická legacy workspace compatibility regrese dokazuje non-breaking/aditivní kontrakt bez klientských dat;
- ADR odstranil zastaralý požadavek na GitHub CLI jako povinnou závislost promotion.

### Compatibility

- změna zachovává kanonický tok `Align → Discover → Decompose → Strategize → Connect → Organize → Define → Code` a gaty G1–G8;
- Cursor zůstává základním project runtime a existující Cursor-oriented pracovní postupy nejsou považovány za platformní development;
- existující workspace a projektové repozitáře nevyžadují automatickou migraci;
- starší `passed` záznam bez strukturované human provenance není považován za platné schválení a dotčená gate vyžaduje nové lidské review;
- existující specializované PowerShell skripty zůstávají compatibility entry points.
