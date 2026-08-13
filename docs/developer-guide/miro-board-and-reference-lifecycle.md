# Miro board taxonomy and reference-pattern lifecycle

## Purpose

Tento guide je praktický runbook pro vývojáře DDDA platformy. Říká, **kam patří konkrétní Miro vstup nebo artefakt**, kdy má vývojář pouze odkázat externí board/frame, kdy má vzniknout adopted DDDA pattern, kdy se má pracovat v Platform Labu a kdy se autoritou stává Git.

Semantic owner tohoto lifecycle je CHR #53. Credential/binding pravidla zůstávají v `docs/developer-guide/miro-execution-profiles.md`; obecný lifecycle vývoje platformy v `docs/developer-guide/platform-development-lifecycle.md`.

Základní pravidlo:

```text
External Reference Artifact
→ Adopted Platform Pattern
→ Canonical Git Template/Manifest/Generator Contract
→ Generated Baseline
→ CI Validation
→ HVR
→ Example/Runtime Project materialization
```

**Miro není source-code repository.** Přijatý DDDA pattern musí být reprodukovatelný z versioned Git/package contractu bez závislosti na tom, že původní referenční Miro board stále existuje.

---

## 1. Pět typů DDDA boardů

### 1.1 `DDDA_PLATFORM_LAB`

**Role:** persistentní platform-development workspace pro adopci referencí, návrh, remediation a porovnávání generated outputu.

Typické oblasti:

```text
CONTROL
REFERENCE / ADOPTED
WORKBENCH
GENERATED BASELINE
CI SANDBOX
FAIL DIAGNOSTICS
HVR CURRENT
```

Tyto názvy vyjadřují semantic namespaces; fyzická implementace může být frame/zone/tag/managed namespace podle runtime contractu.

**Kdo zapisuje:** DDDA developer a deterministic REST automation v explicitně managed scope.

**Co sem patří:**
- adopted reference patterns;
- pracovní normalizace patternů;
- remediation candidate;
- output aktuálního exact HEAD/candidate contractu pro side-by-side kontrolu;
- managed diagnostika platformního vývoje.

**Co sem nepatří:**
- skutečná klientská data;
- dlouhodobá historie CI runů;
- autoritativní release example;
- projektový runtime obsah skutečného projektu;
- nekontrolovaný archiv všech inspiračních boardů.

**Cleanup:** pouze explicitně DDDA-owned IDs/namespaces. Unknown/manual content = fail closed.

**Source of truth:** Git pro accepted/canonical pattern; Platform Lab je working/review projection.

---

### 1.2 `DDDA_GH_CI`

**Role:** machine-only deterministic validation target.

**Kdo zapisuje:** GitHub Actions přes REST credential profilu `github_ci`.

**Co sem patří:** pouze testovací/generated artefakty aktuální CI acceptance.

**Lifecycle:** rebuildable. Obsah může být před testem kompletně resetován pouze proto, že celý board má machine-only ownership.

**Source of truth:** exact Git SHA + candidate package + CI evidence.

**Zakázáno:**
- používat jako reference library;
- ručně opravovat výsledek;
- držet klientská data;
- používat jako persistentní design workspace.

---

### 1.3 `DDDA_HVR`

**Role:** Human Visual Review projection přesně validovaného candidate stavu.

**Kdo zapisuje:** automation při materializaci HVR targetu. Člověk reviewuje, neprovádí remediation in-place.

**Lifecycle:** logical review slot. Fyzické board ID se může při nové materializaci změnit.

**Source of truth:** source Git SHA/package + exact-SHA technical evidence; HVR board je review projection.

**Zakázáno:**
- ručně posouvat šipku, měnit text nebo layout jako „opravu“;
- používat HVR board jako zdroj pro další generování;
- prohlásit human PASS z technického read-backu.

Při nálezu:

```text
HVR finding
→ source/workbench/template fix
→ exact-SHA CI
→ Platform Lab read-back/idempotence
→ nová HVR materializace
→ nový human verdict
```

---

### 1.4 `DDDA_EXAMPLE_PROJECT`

**Role:** persistentní ukázka správně nasazené/released DDDA platformy.

**Kdo zapisuje:** release/example provisioning a řízená údržba example obsahu.

**Co sem patří:** synthetic, neklientská data a realisticky vyplněný průchod DDDA metodikou.

**Lifecycle:** persistentní, ale reprodukovatelný z release/package contractu.

**Source of truth:** release package + versioned example inputs/invariants.

**Zakázáno:**
- ručně kopírovat Workbench frame jako release truth;
- používat citlivý klientský reference content;
- používat jako platformní experimentální sandbox.

---

### 1.5 `DDDA_PROJECT_X`

**Role:** skutečný projektový runtime board konkrétního DDDA projektu.

**Kdo zapisuje:** projektoví uživatelé + DDDA runtime v explicitních managed ownership boundaries.

**Lifecycle:** lifecycle projektu; není rebuildable jako CI board.

**Source of truth:** project Git/YAML semantic state + explicitně definovaný Miro layout/ownership contract.

**Zakázáno:**
- platformním CI mazat celý board;
- používat jako platform-development fixture;
- měnit human-owned content bez explicitního ownership contractu.

Per-project identity/team/Space/token/board provisioning se aktivuje až v deployment/project-initialization fázi, ne v běžném platform-development FAST-LOOP.

---

## 2. Typy externích referencí

Každý externí/non-DDDA board nebo frame, který ovlivňuje návrh DDDA, musí mít explicitní roli.

| Role | Význam | Typické použití |
|---|---|---|
| `authoritative-reference` | schválený externí vzor, vůči němuž se posuzuje konkrétní aspekt | přesná struktura, wording nebo schválená referenční kompozice |
| `style-reference` | autorita pouze pro vizuální principy | spacing, hierarchy, arrows, typography, alignment |
| `content-example` | příklad obsahu, ne nutně layoutu | facilitace, typy sticky notes, příklady hotspotů |
| `inspiration-only` | podnět bez DDDA authority | nápad, který může být později odmítnut nebo adoptován |

Jedna reference může mít více explicitně popsaných rolí pro různé aspekty; vývojář nesmí implicitně předpokládat, že „reference board“ je autorita pro všechno.

---

## 3. Link versus copy

### Použij pouze link, pokud

- potřebuješ provenance nebo vizuální comparison;
- reference je `inspiration-only`;
- ještě nebylo rozhodnuto, že pattern DDDA adoptuje;
- licence/confidentiality nedovoluje kopii;
- není potřeba referenci řízeně normalizovat uvnitř Platform Labu.

V tom případě zaregistruj stabilní reference ID a přesný board/frame URL nebo ID. Externí board zůstává mimo DDDA managed writes.

### Vytvoř `REFERENCE / ADOPTED`, pokud

- existuje explicitní rozhodnutí pattern začlenit do DDDA;
- potřebuješ stabilní DDDA representation pro side-by-side design/remediation;
- musíš odlišit invariant od example-specific obsahu;
- pattern bude převeden do generovatelného contractu.

Adopted representation není automaticky release source of truth. Je to řízený DDDA design artefakt.

### Snapshot externí reference

Snapshot je povolen pouze pokud je oprávněný z hlediska licence, confidentiality a provenance. Snapshot:

- musí mít zachovaný odkaz na source/provenance;
- nesmí se tiše stát canonical DDDA contractem;
- nesmí přenést klientská/citlivá data do CI, example nebo package artefaktů.

---

## 4. Reference catalog contract

Každá reference použitá pro aktivní DDDA vývoj má mít minimálně:

```yaml
reference_id: REF-<domain>-<nnn>
role:
  - style-reference
source:
  system: miro
  board_url: <url>
  frame_id: <id-or-null>
provenance:
  owner: <person/team/source>
  confidentiality: <classification>
status:
  adoption: inspiration-only | evaluating | adopted | superseded | rejected
  availability: verified | unavailable | unknown
adoption:
  pattern_id: <DDDA-pattern-id-or-null>
  rationale: <why/what was adopted>
canonical_git:
  template_id: <id-or-null>
  path: <path-or-null>
```

Konkrétní schema/path bude dokončeno v #53; význam polí je závazný už pro developer workflow.

Změna externí reference sama **nesmí** přepsat DDDA generated output. Vyvolá pouze re-review/re-adoption decision.

Pokud reference zmizí, `availability` se stane `unavailable/degraded`, ale accepted canonical Git pattern musí zůstat reprodukovatelný.

---

## 5. Rozhodovací tabulka: kam tento artefakt patří?

| Situace | Akce | Umístění | Canonical authority |
|---|---|---|---|
| našel jsem zajímavý frame | zaregistrovat link + `inspiration-only` | externí board + catalog | žádná DDDA authority |
| frame používám jako style/content reference | přesný link, provenance, role; read-only comparison | externí board + catalog | reference pro deklarovaný aspekt |
| rozhodli jsme pattern adoptovat | allocate stable DDDA pattern ID; vytvořit adopted representation | Platform Lab / `REFERENCE / ADOPTED` | adopted design candidate |
| pattern aktivně upravuji | pracovat jen v managed working scope | Platform Lab / `WORKBENCH` | design intent, ještě ne release contract |
| pattern je metodicky/designově přijat | převést do template/manifest/generator + tests | Git | **Git** |
| chci vidět, co generuje exact HEAD | generovat z Git contractu | Platform Lab / `GENERATED BASELINE` | exact SHA/package |
| chci mechanicky validovat | fresh render/read-back/idempotence | `DDDA_GH_CI` | exact-SHA CI evidence |
| chci human visual review | materializovat validated candidate | `DDDA_HVR` | Git/candidate + human verdict |
| chci release example | generovat z release package + synthetic inputs | `DDDA_EXAMPLE_PROJECT` | release package |
| inicializuji reálný projekt | provision project-specific board a render released templates | `DDDA_PROJECT_X` | project Git/YAML + released templates |

---

## 6. Povinný adoption recipe

Když vývojář dostane externí vzorový frame, postupuje takto:

1. **Identify source.** Zaznamenej přesný board a frame/widget URL/ID.
2. **Classify role.** Urči `authoritative-reference`, `style-reference`, `content-example` nebo `inspiration-only`.
3. **Register provenance.** Přiděl stable reference ID, owner/source, confidentiality a availability status.
4. **Decide disposition.** `inspiration-only` / `evaluating` / `adopt` / `reject`.
5. **Allocate pattern ID.** Při adopci přiděl stable DDDA pattern/template ID.
6. **Create adopted representation.** Vytvoř/aktualizuj řízený artefakt v `REFERENCE / ADOPTED` Platform Labu.
7. **Work in WORKBENCH.** Normalizaci/remediation dělej jen v DDDA-owned scope; source reference neměň.
8. **Separate invariants.** Explicitně rozliš, co je DDDA invariant, co je pouze style hint a co je example-specific content.
9. **Canonicalize in Git.** Přijatý design převeď do template/manifest/generator configu a reference metadata.
10. **Add tests.** Přidej invariants/tests pro reprodukovatelnost a relevantní geometry/semantics; ne brittle full-board snapshot, pokud to není nutné.
11. **Generate baseline.** Vytvoř `GENERATED BASELINE` z exact HEAD/candidate package; nikdy ručním copy/paste jako finální stav.
12. **Validate technically.** Fresh read-back, comparison a second reconcile = zero mutation; CI podle impact classification.
13. **Materialize HVR.** Vytvoř HVR candidate a získej explicitní human verdict.
14. **Promote only accepted contract.** Pouze accepted Git/package contract může být zdrojem Example Project nebo Project X bootstrapu.

Pokud kterýkoli krok není splněn, nepřeskakuj rovnou do Example/runtime materializace.

---

## 7. `REFERENCE / ADOPTED`, `WORKBENCH`, `GENERATED BASELINE`

Tyto tři stavy jsou odlišné i tehdy, když fyzická implementace nepoužívá tři kopie každého frame.

### `REFERENCE / ADOPTED`

Odpovídá na otázku:

> Co DDDA vědomě převzalo jako pattern a vůči čemu design porovnáváme?

Obsah je persistentní a řízený. Nemusí být přesnou kopií externího frame; může být anonymizovaná nebo rekonstruovaná reprezentace.

### `WORKBENCH`

Odpovídá na otázku:

> Co právě měníme a proč?

Sem patří design iteration, remediation, varianty a nehotový stav. Workbench nesmí být automaticky vydáván za generated truth.

### `GENERATED BASELINE`

Odpovídá na otázku:

> Co skutečně vytvoří aktuální exact Git HEAD/candidate package?

Generated baseline se negeneruje ručním copy/paste z Workbenche. Pokud je špatně, oprav source contract a vygeneruj ho znovu.

---

## 8. Manual-edit policy

### Ručně lze měnit

- adopted/workbench design v explicitně human/developer-owned scope;
- externí reference pouze pokud jsi jejím vlastníkem a změna není prováděna jako DDDA automation;
- skutečný Project X v human-owned scope podle project ownership contractu.

### Ručně se nesmí „opravovat“

- `GENERATED BASELINE` jako způsob dokončení implementace;
- `DDDA_GH_CI` output;
- `DDDA_HVR` candidate;
- generated Example Project tak, aby přestal být reprodukovatelný z package.

Správný remediation path je vždy zpět k nejbližšímu skutečnému source contractu.

---

## 9. REST versus MCP

Používej tento princip:

```text
REST API
  deterministic automation/data plane

MCP
  optional interactive AI/control/review plane
```

REST používej pro:
- create/update/delete/reconcile v managed scope;
- CI;
- read-back;
- idempotence;
- HVR materialization;
- deterministic project provisioning.

MCP používej pouze tam, kde má přidanou hodnotu pro interaktivní inspection, semantic exploration nebo AI-assisted review. MCP quota nesmí být technical gate platformního vývoje.

Credential/binding detaily jsou v `miro-execution-profiles.md`.

---

## 10. Board inventory a cleanup

Před rebindingem, consolidací nebo destruktivním cleanupem proveď read-only inventory DDDA-related boardů a klasifikuj každý board jako:

```text
ACTIVE_BOUND
REFERENCE_EXTERNAL
CANDIDATE_REBIND
LEGACY_ORPHAN
UNKNOWN
```

### Význam

- `ACTIVE_BOUND` — používá aktuální execution profile nebo runtime project binding.
- `REFERENCE_EXTERNAL` — vědomě zachovaná externí reference mimo DDDA managed cleanup.
- `CANDIDATE_REBIND` — potenciální cílový board, který vyžaduje explicitní rebinding decision.
- `LEGACY_ORPHAN` — historický test/bootstrap board bez aktivního bindingu.
- `UNKNOWN` — ownership/původ není prokázán; fail closed.

Inventory evidence má obsahovat minimálně:
- board ID;
- název;
- team/Space pokud dostupné;
- execution-profile/runtime binding status;
- ownership/managed marker;
- item-count nebo jiný usage signal;
- reference status;
- navrženou akci.

### Cleanup rules

1. Nikdy nemaž board jen podle názvu.
2. Aktivní binding má přednost před naming heuristikou.
3. `UNKNOWN` se nemaže automaticky.
4. Před delete musí být prokázáno, že board není active profile target, HVR target, external reference ani project-owned board.
5. Destructive cleanup musí být explicitně scoped a auditovatelný.
6. Po cleanupu musí inventory prokázat jednoznačné role Platform Lab / GH CI / HVR bez duplicitních aktivních významů.
7. Cleanup nikdy nesmí zasáhnout Project X nebo externí reference jen proto, že jejich název obsahuje `DDDA`.

Known candidate evidovaný v #53:

```text
DDDA Platform CI Lab
uXjVHyjgwlk=
```

Je pouze `LEGACY_ORPHAN candidate`, dokud inventory neprokáže ownership a bezpečný cleanup. Samotný název/prázdný stav není dostatečné oprávnění k delete.

---

## 11. Security a confidentiality decision point

Před adopcí externí reference zkontroluj:

- zda obsahuje klientská nebo osobní data;
- zda může být obsah kopírován do privátního/corporate Platform Labu;
- zda licence dovoluje snapshot/reconstruction;
- zda reference může být součástí public repository metadata;
- zda je potřeba anonymizace nebo synthetic reconstruction.

Pokud reference obsahuje citlivá data:

```text
reference link/provenance
→ extract allowed invariants/style
→ anonymized/synthetic adopted representation
→ canonical Git contract without sensitive content
```

Nikdy nepřenášej citlivý source frame do `DDDA_GH_CI`, package nebo `DDDA_EXAMPLE_PROJECT`.

---

## 12. Multiple references a konflikty

Jeden DDDA pattern může být odvozen z více referencí. Každá musí mít explicitní roli.

Příklad:

```text
REF-ES-001 authoritative-reference → process structure
REF-ES-002 style-reference         → spacing/arrows
REF-ES-003 content-example         → sample sticky semantics
```

Pokud se reference rozcházejí, nevytvářej implicitní last-write-wins. Zaznamenej adoption rationale a rozhodni, který invariant DDDA přijímá.

Změna nebo drift reference po adopci:

```text
external reference changed
→ mark verification/review pending
→ assess impact
→ explicit re-adoption CR if needed
→ Git contract changes only through normal platform lifecycle
```

---

## 13. Worked example A — externí EventStorming frame se adoptuje

Situace: máš externí Process EventStorming frame, jehož strukturu a vizuální navigaci chceš dostat do DDDA.

1. Založ `REF-ES-010` a ulož přesný board/frame URL.
2. Označ například `authoritative-reference` pro sequence zones a `style-reference` pro arrows/spacing.
3. Zkontroluj confidentiality; klientské stickies nesmí do DDDA examples.
4. Rozhodni `adopted` a allocate pattern ID, např. `event-storming-process-v1`.
5. V Platform Labu vytvoř anonymizovanou/normalizovanou `REFERENCE / ADOPTED` reprezentaci.
6. Ve `WORKBENCH` proveď DDDA úpravy: legends, controls, guidance, Miro Tips, managed anchors.
7. Zaznamenej invariants: required zones, ordering, spacing constraints, connector semantics.
8. Převeď pattern do Git template/manifest/generator contractu a přidej testy.
9. Vygeneruj `GENERATED BASELINE` z exact HEAD.
10. Porovnej s deklarovanými referenčními aspekty; ručně baseline nedorovnávej.
11. Spusť GH CI read-back/idempotence.
12. Materializuj HVR a získej human verdict.
13. Po acceptance může release package tento template použít pro Example Project a později Project X.

---

## 14. Worked example B — inspiration-only frame

Situace: najdeš zajímavý Big Picture frame, ale zatím nevíš, zda jej chce DDDA převzít.

1. Založ `REF-ES-011`.
2. Role = `inspiration-only`.
3. Ulož link + provenance + dostupnost.
4. **Nevytvářej adopted kopii v Platform Labu.**
5. Nevytvářej nový template/generator contract.
6. Můžeš na něj odkázat v design discussion.
7. Pokud se později rozhodne pattern adoptovat, změň adoption status explicitním rozhodnutím a pokračuj adoption recipe od kroku 5.

Tím se Platform Lab nestává archivem všeho, co vývojář kdy viděl.

---

## 15. Anti-patterns

### `Miro-as-source-code`

> „Frame je správně v Platform Labu, tak ho při bootstrapu prostě zkopírujeme.“

Ne. Accepted runtime musí být reprodukovatelný z Git/package contractu.

### `HVR hotfix`

> „Review našel špatnou šipku, posunu ji ručně na HVR boardu.“

Ne. Oprav source/workbench/generator, revalidateuj a znovu materializuj HVR.

### `CI reference library`

> „Necháme si staré testovací frames na DDDA_GH_CI pro příště.“

Ne. GH CI je machine-only rebuildable target; reference patří do catalogu/external boardu nebo adopted Platform Lab scope.

### `Copy everything`

> „Každý zajímavý externí frame hned zkopírujeme do Platform Labu.“

Ne. `inspiration-only` zůstává linkem, dokud neexistuje explicitní adoption decision.

### `Delete by name`

> „Board se jmenuje podobně jako starý Lab, tak ho smažeme.“

Ne. Inventory + binding/ownership evidence je povinné; `UNKNOWN` = fail closed.

---

## 16. Current implementation status

Tento guide definuje **cílovou developer methodology #53**. Neznamená, že všechny namespaces, reference-catalog schema, inventory tooling nebo Example/Project runtime provisioning jsou již implementovány.

Aktuální PR #8 poskytuje foundation:

- oddělené Miro execution profiles pro Platform Lab, GH CI a HVR;
- REST-first deterministic execution;
- exact-SHA CI/read-back/idempotence;
- project-runtime configuration contract jako deferred capability.

#53 musí následně implementovat persistentní Platform Lab namespaces, reference catalog contract, inventory/cleanup tooling a související tests. #54 vlastní Example Project lifecycle, #55 per-project Cursor/runtime provisioning a #35 musí tento generic reference/template lifecycle reuse pro EventStorming-specific templates.

Při konfliktu mezi tímto guide, execution-profile contractem a mandatory platform-development skill se změna zastaví fail closed a pravidla se nejprve sjednotí v Git.
