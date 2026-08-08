# Testovací strategie DDDA platformy

## Princip

DDDA netestuje pouze kód. Testuje také:

- CLI kontrakty;
- path a workspace isolation;
- schemas;
- manifest-driven ingestion;
- workflow a gate semantics;
- generated artifacts;
- package contents;
- example workspaces;
- Miro mapping a idempotenci;
- release lifecycle.

Automatizace řeší mechanické kontroly. Manuální review zůstává pro judgment.

```text
DDDA-EXECUTION-MODE: CHAT-WORK-ONLY
```

Codex a `/agent` nejsou součástí podporované testovací cesty.

## Execution plane

| Rozhraní | Odpovědnost za testování |
|---|---|
| Chat | definuje scénáře, acceptance criteria, vyhodnocuje evidence |
| Work | připravuje změnu, spouští/sleduje standardní workflows, analyzuje failures |
| GitHub Actions | **autoritativně spouští shell, build, suites, package-first a online acceptance** |
| člověk | hodnotí metodiku, architekturu, visual usability a riziko |

Work nesmí označit test jako provedený pouze na základě očekávaného příkazu nebo předchozího běhu. PASS musí být svázán s workflow evidence pro aktuální exact SHA.

Lokální příkazy v této dokumentaci jsou stabilní platformní kontrakt. Na Chat/Work-only cestě je vykonávají standardní GitHub Actions workflows; přístup k lokálnímu shellu není podmínkou pro uživatele ani pro Work.

## Taxonomie

| Suite | Účel | Typické kontroly |
|---|---|---|
| `lint` | rychlá formální kontrola | PowerShell parser, BOM, YAML/JSON/Markdown, trailing whitespace, struktura docs, execution policy |
| `schema` | datové kontrakty | intake, tailoring, gates, status, manifest, validation report, package manifest |
| `unit` | izolované funkce | steering engine, Miro model/sync, hashes, parsování, gate evaluation, governance policy |
| `component` | jedna schopnost jako celek | workspace generator, steering, Miro initializer, report generator |
| `integration` | spolupráce komponent | package → ingestion → workspace → steering |
| `smoke` | minimální funkční důkaz | package se rozbalí, vytvoří workspace a první status |
| `regression` | ochrana existujícího chování | first-run, multi-repo, Miro mapping, CRLF, whitespace a Chat/Work-only policy |
| `security` | bezpečnost a izolace | path escape, secrets, client data, package exclusions, forbidden execution interfaces |
| `e2e` | celý technický tok | package → example → ingestion → G1 → G2 |
| `acceptance` | uživatelská hodnota | one-command steering a volitelně Miro board |

## Příkazy

```powershell
.\ddda.ps1 test -Suite lint
.\ddda.ps1 test -Suite schema
.\ddda.ps1 test -Suite unit
.\ddda.ps1 test -Suite component
.\ddda.ps1 test -Suite regression
.\ddda.ps1 test -Suite security
```

Package-dependent test:

```powershell
.\ddda.ps1 test -Suite e2e -PackagePath $PackagePath
```

Kompletní PR validace:

```powershell
.\ddda.ps1 validate-pr -Pr 8 -WithMiro -Full -CleanupOnFailure
```

## Test pyramid a rozsah

Preferované pořadí zpětné vazby:

```text
lint + schema
→ unit
→ component
→ integration
→ smoke + regression
→ security
→ E2E
→ acceptance
→ online Miro acceptance
→ human visual acceptance
```

E2E testů má být málo a mají ověřovat stabilní uživatelské toky. Detailní kombinatorika patří do unit a component testů.

## Invariant-based regression

Generovaný architektonický text se nesrovnává celý po znacích, pokud není deterministický. Kontrolují se invarianty:

- povinné sekce existují;
- metadata odpovídají schématu;
- source inputs jsou dohledatelné;
- status a validation block existují;
- cesty neopouštějí workspace;
- není přítomný klientský obsah;
- gate se neposunula bez explicitního rozhodnutí;
- Miro mapping zůstává stabilní;
- povolená execution interfaces jsou přesně `chat` a `work`;
- `codex` a `agent` jsou policy-level zakázané;
- GitHub Actions zůstává autoritativní execution plane.

## Legacy workspace compatibility

`Test-DDDALegacyWorkspaceCompatibility.ps1` vytváří výhradně syntetický pre-steering workspace podle versioned manifestu `tests/fixtures/legacy-workspace/baseline.json`. Ověřuje read-only načtení bez změn, povinný explicitní `-Resume`, pouze aditivní steering metadata, zachování project/lock/workspace/repository/Miro mappingu a nulový počet automaticky schválených gates.

Test běží v component, integration i regression suite, aby byl kontrakt viditelný v CI a validation reportu.

## Package-first validace

Smoke, integration, E2E a acceptance během `validate-pr` běží z nově rozbaleného candidate package. Lokální Git baseline vytvořená uvnitř rozbaleného package slouží jen k ověření Git guardrails a není součástí distribuovaného ZIP.

Tím se odděluje:

```text
development working tree
≠ candidate package
≠ generated workspace
```

## Security a isolation

Povinné kontroly:

- source a target ingestion cest zůstávají uvnitř povolených rootů;
- ZIP neobsahuje `.git`, `.ddda`, cache, reports nebo credentials;
- example data jsou syntetická;
- textové soubory neobsahují uživatelské absolutní cesty;
- Miro token se neukládá do package, reportu, Git diffu, Chatu ani Work kontextu;
- validation nepoužívá klientský workspace;
- Work zapisuje pouze do deklarované PR branche;
- přímý write na `main` je zakázán;
- Codex a `/agent` nejsou podporované execution interfaces.

## Miro testování

Offline suite ověřuje model, rendering plan, sync semantics, konflikty a Git guardrails bez API.

Online acceptance navíc ověřuje:

1. izolovaný board;
2. scaffold render;
3. managed artifact push;
4. `miro-map.yaml`;
5. `sync-state.yaml`;
6. current-status a next-actions;
7. kontrolní render;
8. nulový počet dalších create/update operací;
9. cleanup.

Síťový nebo scope problém je diagnostický FAIL, ne důvod vypnout offline testy. Work jej musí explicitně oznámit a nesmí tvrdit, že board vizuálně analyzoval.

### Visual acceptance

Online API acceptance není visual acceptance. Pro změnu odvozenou z redline nebo referenčního boardu je povinné:

- načíst konkrétní reference frames přes Miro connector;
- načíst cílové frames;
- provést side-by-side porovnání;
- zkontrolovat obrázky, fonty, hierarchii, geometry, overlap a informační hustotu;
- ověřit first-viewer usability při `Fit to frame`;
- zachovat `human_visual_acceptance_status=PENDING`, dokud člověk nerozhodne.

## Manuální review

Manuálně se hodnotí:

- metodická správnost;
- business a architektonická smysluplnost;
- kvalita ubiquitous language;
- vhodnost gate evidence;
- srozumitelnost dokumentace;
- vizuální kvalita boardu;
- přijetí rizik.

Manuální review nenahrazuje lint, schema, package nebo security kontroly. Technický PASS nenahrazuje human visual acceptance.
