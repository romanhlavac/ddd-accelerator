# DDDA operating model: Chat/Work pro platformu, Cursor pro projekt

## Status a rozsah

DDDA má dvě odlišné execution roviny, které se nesmějí zaměňovat:

```text
A. Vývoj DDDA platformy
   Chat + Work + GitHub Actions

B. Používání DDDA v architektonickém projektu
   Cursor jako základní agentic systém
```

Tento rozdíl je závazný.

## 1. Vývoj DDDA platformy

```text
DDDA-PLATFORM-DEVELOPMENT-MODE: CHAT-WORK-ONLY
```

Povolená rozhraní:

- **Chat**;
- **Work**.

Zakázaná rozhraní pro změnu platformy:

- **Codex**;
- **Cursor**;
- legacy nebo jiný samostatný coding-agent režim.

GitHub Actions je autoritativní execution plane pro shell, build, testy, candidate package a package-first validation.

### Rozdęlení odpovědností

| Oblast | Chat | Work | GitHub Actions | Člověk |
|---|---|---|---|---|
| návrh, scope a trade-offy | ano | ano | ne | review |
| klasifikace změny a acceptance criteria | ano | ano | kontrola kontraktů | schválení scope |
| změny PR branche přes schválené konektory | ano, pouze atomickým Git tree commitem a při nedostupném Work | ano, preferovaný režim | ověření exact SHA | kontrola diffu |
| shell, build, testy a packaging | ne | ne | **autoritativně** | posouzení evidence |
| secrets | nikdy | nikdy | pouze secret-bearing job | správa a rotace |
| merge, promotion, release a tag | pouze návrh | jen po samostatné autorizaci | guardrails | explicitní rozhodnutí |

### Work guardrails

Work musí:

1. před změnou načíst aktuální PR head SHA;
2. zapisovat jen do deklarované platformní PR branche a allowed paths;
3. nikdy nepoužít `main` jako write target;
4. nepřenášet secrets do chatu, commitů, logů nebo argumentů;
5. při nedostupném konektoru nebo boardu zastavit a omezení explicitně oznámit;
6. po změně vyžadovat standardní CI nad výsledným SHA;
7. nerozšiřovat autorizaci na merge, release, tag, promotion nebo force-push.

### Chat atomic guardrails

Work zůstává preferovaným implementačním režimem. Pokud Work není dostupný, Chat smí provést změnu platformy pouze jako jeden atomický Git tree commit přes schválený GitHub konektor.

Chat atomic změna musí:

1. načíst a zafixovat exact PR head SHA před sestavením změny;
2. použít immutable candidate package nebo jiný exact-SHA source snapshot pro přípravu a lokální statické ověření změny;
3. vytvořit celý nový Git tree bez sekvenčních více-souborových Contents API commitů;
4. vytvořit právě jeden commit s rodičem rovným autorizovanému SHA;
5. aktualizovat pouze deklarovanou PR branch a pouze fast-forward, nikdy `main`;
6. po zápisu vyžadovat standardní exact-SHA CI; technický PASS vzniká až po jeho dokončení;
7. při selhání CI nepřepisovat historii, ale použít opravný commit nebo revert;
8. nevkládat secrets do Chat kontextu, stromu, commitu ani evidence;
9. nerozšiřovat autorizaci na merge, promotion, release, tag nebo force-push.

Přímé sekvenční multi-file zápisy přes GitHub Contents API jsou zakázané. Jednorázový bootstrap control-plane změny vyžaduje explicitní autorizaci, self-removing staging artefakt a samostatnou evidenci.

## 2. Používání DDDA v projektu

```text
DDDA-PROJECT-RUNTIME: CURSOR
```

Cursor je základní a povinný agentic systém, ve kterém architekt realizuje vlastní DDDA práci nad konkrétním project workspace.

Cursor zajišťuje:

- chat nad projektovým workspace;
- agentic práci se soubory a projektovými artefakty;
- analýzu business a technických vstupů;
- vytváření a aktualizaci DDD artefaktů;
- práci s projektovým Git repository;
- spouštění projektových DDDA příkazů a validací;
- práci s projektovou dokumentací, rozhodnutími, workshopovými výstupy a projektovým kódem.

Aktivní Cursor runtime assets:

```text
.cursor/rules/010-ddda-project-steering.mdc
.cursor/rules/ddda-chat-first.mdc
.cursor/rules/ddda-repository-scope.mdc
.cursor/skills.md
```

Tyto soubory jsou produktové runtime artefakty DDDA, nikoli development bootstrapy platformy.

### Cursor scope

Cursor smí měnit pouze aktivní project repository a jeho projektové artefakty. Nesmí měnit DDDA platform repository.

Při nálezu platformního defectu nebo potřeby obecného enhancementu Cursor:

1. zachytí problém a evidence;
2. oddělí projektový workaround od platformního návrhu;
3. vytvoří change request;
4. předá jej do Chat/Work platform-development flow.

Cursor nesmí provést cross-repository commit, automatický gate approval, implicitní last-write-wins konflikt, neautorizovaný push nebo merge.

## 3. Hranice mezi rovinami

| Otázka | Správná rovina |
|---|---|
| měním obecný DDDA runtime, CLI, schema, template nebo release lifecycle | Chat/Work platform development |
| opravuji bug použitelný pro všechny DDDA projekty | Chat/Work platform development |
| analyzuji konkrétní doménu klienta | Cursor project runtime |
| vytvářím glossary, context map, ADR nebo workshop artifacts konkrétního projektu | Cursor project runtime |
| měním projektový kód nebo project-owned dokumentaci | Cursor project runtime |
| validuji platformní candidate package | GitHub Actions |
| rozhoduji gate nebo přijímám riziko | člověk |

## 4. Git a ownership

### Platform repository

- source of truth pro DDDA produkt;
- změny pouze přes platformní PR;
- implementace preferenčně přes Work; při nedostupném Work je povolen Chat atomic transport podle exact-SHA guardrails;
- validace přes GitHub Actions;
- Cursor write zakázán.

### Project repository

- source of truth pro konkrétní DDDA projekt;
- Cursor je hlavní pracovní prostředí;
- obsahuje project intake, tailoring, artefakty, rozhodnutí, evidence, Miro mapping a případně projektový kód;
- platformní obecné změny se do něj nesmějí maskovat jako project customization.

## 5. Miro a human review

V platform-development flow Work provádí strukturální a referenční kontrolu platformních Miro šablon; technický PASS nenahrazuje human visual acceptance.

V project runtime Cursor pracuje s project-owned boardem a artefakty podle project rules. Gate decisions a významné metodické nebo architektonické závěry zůstávají lidské.

## 6. Bezpečnostní podmínky

- ChatGPT Work musí být schválen pro klasifikaci dat používanou při platformním vývoji.
- Cursor musí být schválen pro data konkrétního DDDA projektu.
- GitHub, Miro a další Apps používají least privilege.
- Secrets zůstávají v source-system secret store nebo GitHub environmentu.
- Client data se nepoužívají jako platformní fixture.
- Projektová data se nesmějí přenést do platformního repository.

## 7. Definition of Done

### Platformní změna

- změna je na platformní PR branchi;
- Chat/Work-only boundary je dodržena;
- standardní exact-SHA CI a package-first validace jsou PASS;
- human review je odděleno od technického PASS;
- nebyl použit Cursor ani Codex pro změnu platformy.

### Projektová DDDA práce

- práce proběhla v Cursor project runtime;
- aktivní project repository a scope byly explicitní;
- fakta, hypotézy, rozhodnutí a projekce jsou oddělené;
- změny mají project-level traceability a validaci;
- platform repository nebylo změněno;
- lidská rozhodnutí a gate approvals zůstala explicitní.
