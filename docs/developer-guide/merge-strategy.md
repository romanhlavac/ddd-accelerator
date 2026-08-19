# Merge strategy řízených DDDA platformních PR

## Účel

Tento runbook konkretizuje ADR 0009 a `config/platform/development-policy.yaml`. Řeší pouze způsob integrace implementačního PR do `main`; nemění Human Review, HRDR, Release Scope Gate ani release/tag authorization.

## Kanonická pravidla

```text
HIGH / BREAKING
  merge commit REQUIRED
  squash forbidden
  rebase forbidden

LOW / MEDIUM
  merge commit DEFAULT
  squash jen s explicitní human squash exception
  rebase forbidden

UNKNOWN impact
  merge commit only
```

Důvodem není preference „hezčího Gitu“, ale auditability exact-SHA evidence. Commit, který prošel CI, `validate-pr` a Human Review, má u HIGH/BREAKING zůstat ancestor výsledného main state.

## Impact classification

Governed PR může nést právě jeden marker `<!-- ddda:change-classification:v1 -->`, bezprostředně následovaný fenced JSON objektem například:

```json
{"schema_version":1,"impact":"HIGH"}
```

Povolené hodnoty jsou `LOW`, `MEDIUM`, `HIGH`, `BREAKING`. Pokud marker chybí, merge preflight použije `UNKNOWN` a dovolí pouze merge commit. Duplicitní, malformed nebo nepodporovaný marker failuje closed.

Impact je judgment-heavy governance vstup. Automatizace smí marker validovat, ale nesmí sama změnit risk classification jen proto, aby povolila jiný merge method.

## Dry-run

Default:

```powershell
.\ddda.ps1 merge-pr -Pr <PR> -DryRun
```

Explicitní metoda pro kontrolu policy:

```powershell
.\ddda.ps1 merge-pr -Pr <PR> -MergeMethod merge -DryRun
```

Pro LOW/MEDIUM lze vyžádat squash pouze po existenci platné human exception:

```powershell
.\ddda.ps1 merge-pr -Pr <PR> -MergeMethod squash -DryRun
```

Dry-run musí skončit před `Merge-DDDAGitHubPullRequest`; wrong method, chybějící exception nebo identity drift tedy nemohou vytvořit irreversible side effect.

## Human squash exception

Squash je výjimka, nikoli default. Je povolen pouze pro LOW/MEDIUM a vyžaduje právě jeden PR Conversation comment s markerem `<!-- ddda:squash-exception:v1 -->` a fenced JSON recordem:

```json
{
  "schema_version": 1,
  "kind": "squash_exception",
  "repository": "romanhlavac/ddd-accelerator",
  "pr": 123,
  "validated_source_head_sha": "<40-char-sha>",
  "candidate_package_sha256": "<64-char-sha256>",
  "impact": "LOW",
  "reason": "Proč je ztráta ancestry v tomto nízkorizikovém případě přijatelná.",
  "reviewer": "<human-login>",
  "approved_at": "<ISO-8601>"
}
```

Marker musí mít lidskou GitHub provenance. `reviewer` musí odpovídat autorovi komentáře. SHA, package hash a impact musí přesně odpovídat current PR candidate. Bot/automation marker, stale SHA nebo prázdný reason znamenají FAIL.

Human squash exception nenahrazuje HVR ani samostatnou merge authorization.

## Post-merge evidence

Pro `merge` se po server-side merge ověřuje:

- validated PR HEAD je parent výsledného merge commit;
- compare read-back potvrzuje validated HEAD jako ancestor;
- `result.json` obsahuje `source_to_result_relation=ancestor` a `ancestry_verified=true`.

Pro povolený LOW/MEDIUM squash se ukládá explicitní source→result mapping:

```text
validated_source_head_sha
candidate_package_sha256
resulting_merge_sha
source_to_result_relation = explicit_squash_mapping
human squash exception metadata
```

Post-merge read-back failure se neopravuje force-pushem nebo přepisem shared history. Je to governance failure vyžadující diagnostiku a explicitní recovery rozhodnutí.

## First-parent historie

Pro běžné čtení delivery historie používej:

```bash
git log --first-parent
```

Tím zůstává hlavní tok kompaktní, aniž by se ztrácela reviewovaná commit ancestry.

## Prospective bootstrap #70

#70 mění samotný merge contract. Jeho vlastní integraci proto stále řídí pre-existing policy na exact base:

```text
297f61f6012f180e70805999df2ac1abe9616a05
```

Tato policy používala squash. Versioned `bootstrap_transition` dovoluje tento jediný exact-base-bound transition a po integraci #70 je neaktivní. Nový contract se aplikuje na následné PR. Historické PR/tagy se nepřepisují.

HVR #70 musí explicitně posoudit a přijmout tento bootstrap trade-off. Technický PASS jej nemůže schválit.

## Release boundary

Merge strategy je implementation-integration concern. Po merge jednotlivých PR stále platí samostatný release-candidate tok:

```text
integrated work
→ release candidate
→ exact-SHA validation
→ HRDR
→ Release Scope Gate
→ Human Release Decision
→ separate release authorization
→ release validation
→ tag
```

Implementation merge ani squash exception nikdy neautorizují promotion, release nebo tag.
