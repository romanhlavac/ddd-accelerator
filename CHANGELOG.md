# Changelog

Všechny významné změny DDDA platformy jsou evidovány v tomto souboru.

Formát vychází z principu Keep a Changelog. Verze používají Semantic Versioning.

## Unreleased

### Added

- chat-first project intake, lifecycle tailoring, current status a next actions;
- evidence-driven gate records G1–G8 s explicitním lidským rozhodnutím;
- read-only status query a explicitní status refresh;
- project-owned Miro bootstrap s managed artifact push, mappingem, sync state a idempotencí;
- přenositelný knowledge pack a capability catalog;
- stabilní platformní entry point `ddda.ps1`;
- izolovaná validace PR nad candidate package;
- generovaný minimal example workspace a manifest-driven ingestion;
- machine-readable i čitelný validation report;
- kontrolovaný promotion a release lifecycle;
- GitHub Actions CI, které na přesném source SHA provádí source-level i package-first validaci a publikuje krátkodobý candidate package jako build artifact.

### Changed

- dokumentace je organizována do getting-started, methodology, capabilities, cookbooks, product, reference, developer-guide, user-guide, ADR a migration sekcí;
- projektový Miro bootstrap publikuje vedle scaffoldu také aktuální managed YAML artefakty;
- JSON reporty a jejich testy zachovávají prázdné kolekce jako skutečná pole v PowerShellu 7 i Windows PowerShellu 5.1.

### Compatibility

- změna je aditivní a zachovává kanonický tok `Align → Discover → Decompose → Strategize → Connect → Organize → Define → Code` a gaty G1–G8;
- existující workspace a projektové repozitáře nevyžadují automatickou migraci;
- existující specializované PowerShell skripty zůstávají compatibility entry points.
