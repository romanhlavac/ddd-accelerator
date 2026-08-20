# ADR 0009: Exact-SHA ancestry a merge strategy řízených platformních PR

Status: Accepted candidate — pending Human Review of PR implementing #70

Date: 2026-08-20

## Context

DDDA používá exact PR HEAD SHA a candidate-package SHA-256 jako základ auditovatelné technické evidence. Dosavadní repository policy používala `squash`, takže výsledný commit na `main` obsahoval reviewovaný obsah, ale reviewovaný PR HEAD nebyl součástí ancestry výsledného main state. Audit proto závisel na odděleném source→result mappingu.

Pro běžný produkt to může být přijatelný trade-off. Pro DDDA platformu ale mají `HIGH` a `BREAKING` změny silnější požadavek na auditability: commit, který prošel exact-SHA CI, `validate-pr` a Human Review, má zůstat přímo dohledatelný v Git historii po merge.

Prioritní quality attributes jsou:

- auditability;
- traceability;
- safety / fail-closed governance;
- reproducibility;
- readability historie;
- jednoduchost provozu.

## Decision

Po integraci změny #70 platí prospektivně tento contract:

```text
HIGH / BREAKING
  → merge commit REQUIRED
  → squash/rebase forbidden
  → validated PR HEAD musí být ancestor výsledného main state

LOW / MEDIUM
  → merge commit DEFAULT
  → squash pouze jako explicitní human-governed exception
  → rebase forbidden

UNKNOWN impact
  → merge commit only (fail-safe default)
```

`merge-pr` načte impact z jednoho autoritativního PR-body markeru:

```text
<!-- ddda:change-classification:v1 -->
```

s fenced JSON objektem `schema_version=1` a `impact=LOW|MEDIUM|HIGH|BREAKING`. Chybějící marker je `UNKNOWN`; malformed nebo duplicitní marker failuje closed.

### Proč merge commit

Merge commit zachová reviewovaný PR HEAD jako parent/ancestor výsledného main state. Tím je vazba:

```text
validated source SHA
→ Human Review stejného SHA/package
→ explicit merge authorization
→ resulting main state
```

ověřitelná přímo z Gitu a není závislá pouze na externím komentáři nebo reportu.

### Readability

Čitelnost hlavní historie se řeší pohledem first-parent (`git log --first-parent`), nikoli ztrátou auditní ancestry. Merge commits tvoří přehlednou delivery páteř, zatímco detailní commit historie zůstává dostupná podle potřeby.

## LOW/MEDIUM squash exception

Squash je legitimní pouze pro LOW/MEDIUM změnu a pouze po explicitním lidském rozhodnutí. Automatizace nesmí exception vytvořit ani inferovat.

Autoritativní PR comment obsahuje marker:

```text
<!-- ddda:squash-exception:v1 -->
```

a machine-readable record minimálně s:

```text
repository
pr
validated_source_head_sha
candidate_package_sha256
impact
reason
reviewer
approved_at
```

Comment musí mít lidskou GitHub provenance a reviewer musí odpovídat autorovi komentáře. SHA/package/impact musí přesně odpovídat aktuálnímu candidate. Změna identity exception invaliduje.

Po squash merge se evidence uloží jako explicitní source→result mapping:

```text
validated_source_head_sha
candidate_package_sha256
resulting_merge_sha
source_to_result_relation = explicit_squash_mapping
human exception metadata
```

Squash exception nemění Human Review ani explicitní merge authorization.

## Post-merge read-back

Pro canonical `merge` musí `merge-pr` po irreversible operaci ověřit server-side:

1. výsledný merge commit obsahuje validated PR HEAD mezi parenty;
2. GitHub compare read-back potvrzuje validated PR HEAD jako merge base / ancestor výsledného merge commit;
3. evidence zaznamená `source_to_result_relation=ancestor` a `ancestry_verified=true`.

Nesoulad je governance failure a musí být zachován jako diagnostika; shared history se automaticky nepřepisuje.

## Vztah k candidate package, HRDR a release

Merge strategy nemění exact-SHA CI, `validate-pr`, candidate-package hash ani Human Review. Implementační merge je stále oddělen od release.

HRDR, Release Scope Gate a Human Release Decision vznikají až pro skutečný release candidate po integraci zamýšlených implementation PR. Release tag ukazuje na validovaný release state; merge ancestry poskytuje auditní trasu od release state zpět k reviewovaným implementation SHA.

Squash exception nikdy neoslabuje HRDR, Release Scope Gate, release authorization nebo tag governance.

## Bootstrap / prospective activation

#70 mění právě merge policy, podle které by měl být sám integrován. Proto se nesmí sám retroaktivně prohlásit za již účinnou autoritu.

Explicitní transition contract je:

```text
legacy governing base: 297f61f6012f180e70805999df2ac1abe9616a05
legacy merge method: squash
change issue: #70
new policy effective: až po integraci #70 do main
```

Pokud bude PR implementující #70 po exact-SHA PASS, Human Review a samostatné merge autorizaci skutečně mergován, jeho vlastní merge se řídí pre-existing policy z uvedeného base. Tento jediný transition případ je versioned a exact-base-bound; po posunu `main` už podmínku nelze splnit.

Tento bootstrap není precedent pro HIGH/BREAKING squash po aktivaci nové policy.

## Historical scope

Rozhodnutí je výhradně prospektivní. Nemění a nepřepisuje historii:

- PR #8 / `v0.1.0`;
- PR #74;
- PR #77;
- PR #78;
- PR #79;
- jiné již sdílené branche nebo tagy.

Historické squash merges zůstávají auditovatelné prostřednictvím existujících source→result evidence. Žádný force push, rebase nebo retag není součástí tohoto rozhodnutí.

## Options considered

### A. Zachovat globální squash

Výhoda: velmi kompaktní historie.

Nevýhoda: exact reviewed SHA se ztrácí z ancestry; audit musí spoléhat na externí mapping. Pro HIGH/BREAKING zamítnuto.

### B. Globální merge commit bez výjimek

Výhoda: nejjednodušší a nejsilnější ancestry invariant.

Nevýhoda: zbytečně rigidní pro triviální LOW/MEDIUM změny. Použito jako default, ale s úzkou human squash exception.

### C. Rebase merge

Výhoda: lineární historie.

Nevýhoda: přepisuje commit identity, takže exact validated PR HEAD není zachován. Zamítnuto pro canonical DDDA merge path.

### D. Risk-based merge commit + LOW/MEDIUM squash exception

Přijato. Zachovává auditní invariant tam, kde je nejdůležitější, a dovoluje explicitní, auditovatelnou výjimku pro nízké riziko.

## Consequences

Positive:

- HIGH/BREAKING reviewed SHA zůstává přímo v ancestry;
- wrong merge method failuje před irreversible side effect;
- first-parent history zachovává čitelnost;
- LOW/MEDIUM squash je explicitní lidské rozhodnutí, nikoli automation default;
- release traceability se zjednodušuje.

Negative:

- historie obsahuje více merge commits;
- impact classification se stává součástí merge preflightu;
- LOW/MEDIUM squash vyžaduje další auditní record;
- jeden exact-base-bound bootstrap je nutný pro samotnou aktivaci #70.

## Validation

Povinné regresní scénáře:

- HIGH + merge → PASS;
- HIGH/BREAKING + squash → FAIL před merge;
- UNKNOWN + squash → FAIL;
- LOW/MEDIUM default → merge;
- LOW/MEDIUM squash bez human exception → FAIL;
- validní human squash exception → PASS preflight;
- bot/identity/package drift exception → FAIL;
- canonical merge post-read-back → validated SHA je parent/ancestor;
- #70 bootstrap funguje pouze pro exact legacy base a nelze jej znovu použít.

## Decision ownership

Technická validace tohoto ADR neznamená jeho Human Review. Judgment-heavy trade-off — auditní ancestry versus kompaktnost historie a jednorázový bootstrap #70 — musí být explicitně schválen při HVR implementačního PR.
