# Workspace, Git a více projektů

## Topologie

```text
DDDA-Workspace/
├── platform/ddd-accelerator/.git
├── projects/project-a/.git
├── projects/project-b/.git
├── workspace.yaml
└── DDDA.code-workspace
```

Platforma a projekty jsou sibling repozitáře. Projekt nesmí být vnořen do platformního Git rootu.

## Proč ne monorepo

Monorepo by spojilo release lifecycle platformy s klientskými daty, přístupovými právy a projektovými milníky. DDDA potřebuje nezávislé PR, historii, archivaci a ownership.

## Proč ne submodules

Submodules přidávají commit pointery, detached HEAD a složitější onboarding. `ddda.lock.yaml` řeší verzi platformy explicitněji a bez vnořené Git topologie.

## Lock

Projekt eviduje přesný platformní commit, schema version a čas poslední validace. Upgrade je projektová změna a má vlastní PR.

## Scope guard

Před commitem se ověřuje dirty stav obou repozitářů. Projektový commit je odmítnut, pokud platforma obsahuje změny, a naopak.

## Chat-first pravidlo

Každá relace deklaruje scope, aktivní Git root a aktivní projekt. Agent nejprve ukáže diff a plán, teprve potom zapisuje nebo volá skript.
