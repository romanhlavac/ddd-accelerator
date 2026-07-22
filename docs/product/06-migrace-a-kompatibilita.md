# Migrace a kompatibilita

## Princip

Platformní release nesmí automaticky přepsat projekty. Projekt se upgraduje na explicitní větvi, po kontrole locku, schémat a migračních skriptů.

## Tok

```text
platform PR → merge → tag → project branch → diagnostics → migration
→ lock update → dry-run Miro sync → project PR → merge
```

## Schema migrace

Migrace jsou sekvenční `migrations/<from>-to-<to>.ps1`. Každý krok musí být idempotentní, auditovatelný a musí odmítnout neznámý vstupní stav.

## Miro kompatibilita

Před upgradem runtime proveď doctor a dry-run. Změna identity markeru, mapping formátu nebo hash algoritmu vyžaduje migrační krok a recovery test.

## Rollback

Rollback platformy neznamená automatický rollback projektu. Projektový lock lze vrátit pouze tehdy, pokud jeho schema a Miro mapping zůstávají kompatibilní.
