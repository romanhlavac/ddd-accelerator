# Remote validation and remediation broker

DDDA používá GitHub Actions jako řízený vzdálený execution plane. Chat ani Work nedostává Miro token nebo GitHub write token používaný uvnitř secret-bearing jobu.

```text
DDDA-EXECUTION-MODE: CHAT-WORK-ONLY
```

Codex a legacy `/agent` nejsou podporovanou součástí tohoto workflow.

## Důvod

Lokální PowerShell může obsahovat ambientní `PYTHONPATH`, uživatelské instalace a lokální secrets. To je vhodné pro schválený lokální development, ale není to spolehlivý package-first acceptance runtime a není to předpoklad Chat/Work-only cesty.

Remote broker odděluje:

- požadavek na spuštění z Chat/Work workflow;
- autorizaci a exact-SHA binding;
- secret-bearing execution v GitHub Actions;
- evidence a human review.

GitHub Actions je autoritativní execution plane pro shell, build, test suites, candidate package a online Miro acceptance. Work orchestrace pouze připravuje nebo zapisuje reviewovatelnou změnu, spouští schválený standardní tok a vyhodnocuje evidence.

## Miro transport a execution profiles

Kanonická konfigurace je `config/platform/miro-execution-profiles.yaml` a ADR 0007.

```text
REST API = deterministic automation/data plane
MCP      = optional interactive AI control plane
```

GitHub Actions nesmí používat MCP pro online acceptance, reconcile nebo HVR materialization. MCP quota ani nedostupnost Miro connectoru není technical-gate dependency.

Profily mohou používat různé Miro identity/tokeny:

- `github_ci` — CI executor;
- `platform_lab` — persistentní board/resource binding;
- `hvr` — HVR REST principal;
- `example_project` — persistentní example resource;
- `mcp` — OAuth connector identity mimo GitHub secret store;
- `project_runtime` — projektově konfigurovaný Cursor/REST principal.

## Jednorázové nastavení

Aktivní PR #8 používá výhradně oddělené profile-specific bindingy:

    MIRO_GH_CI_ACCESS_TOKEN
    MIRO_PLATFORM_LAB_ACCESS_TOKEN
    MIRO_HVR_ACCESS_TOKEN
    MIRO_EXAMPLE_PROJECT_ACCESS_TOKEN

Cross-profile ani legacy fallback se nepovoluje. Každý workflow smí použít pouze
svůj vlastní binding; secret names jsou kontrakt a secret values nikdy nevstupují
do Chatu, Work kontextu, souboru ani Git historie.

Non-secret Repository/Environment variables mohou obsahovat identity labels, team ID, Space/project ID a board ID. Aktuální názvy jsou definované v `config/platform/miro-execution-profiles.yaml`.

Připojené GitHub a Miro Apps musí být schválené pro klasifikaci zpracovávaných dat a používat least-privilege oprávnění.

## Příkaz pro validation a online acceptance

Oprávněný actor vloží do PR komentář:

```text
/ddda validate-pr --with-miro --full --keep-review-board
```

Broker:

1. načte policy z `config/platform/development-policy.yaml`;
2. načte Miro execution-profile contract;
3. ověří Chat/Work-only execution policy;
4. ověří actor, same-repository PR a exact head SHA;
5. vyžaduje úspěšné checky `Platform validation` a `One-command PR validation`;
6. fail-closed vybere successful standardní CI run pro exact SHA a právě jeden neexpirovaný `ddda-candidate-<SHA>` artifact;
7. checkoutne exact SHA a stáhne canonical package do nového runneru;
8. spustí `ddda.ps1 validate-pr -PackagePath ...` s REST Miro tokenem pouze v secret-bearing kroku; package znovu nesestavuje;
9. zachová review board podle zvoleného scénáře;
10. publikuje evidence artifact a PR komentář včetně source workflow run/artifact identity.

Standardní PR workflow analogicky předává stejný candidate do offline `validate-pr-command`. Samostatný `Human Review readiness` coordinator pouze detekuje authoritativní marker a publikuje `ready=true|false`; jeho úspěch není merge-preflight PASS. Dokud marker chybí, dependent `Governed merge dry-run` je `skipped` a evidovaný stav je `NOT_RUN`. Po Human Review se znovu spustí readiness job a jeho dependent dry-run bez nového candidate buildu. Dry-run stáhne candidate artifact a validate-pr report ze stejného runu, vyžaduje právě jeden ZIP a právě jeden `result.json`, přepočítá hash a spustí governed preflight na čistém runneru. Chybějící, expirovaný nebo víceznačný artifact, jiný package kind/source SHA či neshoda report/Human Review skončí fail-closed.

Obecný acceptance může vytvářet izolovaný board, pokud testuje board-lifecycle. PR #8 HVR FAST-LOOP používá persistentní Platform Lab binding a nemá zakládat nový review board pro každý corrective run.

## HVR broker contract

HVR technical preflight používá REST API a exact-SHA candidate. HVR používá
výhradně MIRO_HVR_ACCESS_TOKEN. Platform Lab reconcile používá výhradně
MIRO_PLATFORM_LAB_ACCESS_TOKEN; křížový ani legacy fallback není povolen.

HVR technicky připravený stav vyžaduje remote write/reconcile, fresh read-back a zero-mutation second reconcile. Potom vznikne stabilní Miro URL. Lidský reviewer může použít Miro GUI, screenshot nebo MCP; MCP není podmínkou `READY_FOR_HUMAN_REVIEW`.

## Příkaz pro remediation

```text
/ddda remediate scripts/remediation/<script>.ps1 --expected-sha <40-char-sha>
```

Remediation skript musí:

- být v `scripts/remediation/`;
- podporovat `-RepositoryRoot` a `-NoPush`;
- ověřit vlastní manifest, base SHA, allowed paths a integrity hashes;
- vytvořit maximálně jeden commit;
- skončit s čistým working tree;
- neprovést merge, tag, release, promotion ani force-push.

Broker spustí skript bez GitHub API tokenu, ověří jeden commit a teprve potom pushne přesný branch head.

Jednorázový bootstrap workflow není standardní mechanismus. Pokud chybí potřebná schopnost, rozšíří se reviewovatelně standardní broker nebo platformní workflow; nesmí se opakovaně zavádět ad hoc execution cesta bez dlouhodobého kontraktu a testů.

## Canonical GitHub Project reconciliation broker

Permanentní control-plane cesta pro GitHub Project V2 governance je:

```text
Chat / Work
→ GitHub connector PR comment
→ trusted issue_comment broker z default branch
→ exact PR SHA authorization
→ fixed canonical workflow dispatch
→ .github/workflows/reconcile-ddda-project-backlog.yml
→ environment ddda-backlog-governance
→ persistent Project credential v GitHub secret store
→ reconciliation + fresh read-back
→ zero remaining mismatches
→ audit artifact + broker evidence
```

Oprávněný actor používá jediný přesný příkaz:

```text
/ddda reconcile-project --expected-sha <40-char-current-pr-head-sha>
```

Příkaz nepřijímá workflow name, ref, shell fragment ani další volné argumenty. `--expected-sha` musí přesně odpovídat live head stejného PR; neshoda končí ještě před dispatch. Broker používá pouze allowlisted workflow `.github/workflows/reconcile-ddda-project-backlog.yml` a canonical source `main`.

### Credential boundary

Project credential zůstává výhradně v existujícím GitHub Actions environmentu `ddda-backlog-governance`, kde jej spotřebovává canonical reconciliation workflow. Chat, Work ani broker job Project credential nečte, nedostává a nezapisuje do evidence. Broker potřebuje jen úzké repository Actions oprávnění pro dispatch a read-back workflow evidence; zvýšené `actions: write` je izolované na `reconcile-project` job.

Nezavádí se druhý Project credential a broker nereplikuje Project GraphQL/reconciliation logiku. Pokud persistentní Project credential chybí, expiroval nebo nemá potřebnou capability, canonical workflow failne při credential checku a broker nesmí vydat PASS. Náprava se klasifikuje podle `github-capability-authorization.md`; pokud je programová cesta připravena a chybí jen consent/provisioning, jde o `HUMAN_BOOTSTRAP_ONLY`, nikoli o opakovaný operating step.

### Serialization a source identity

Před dispatch broker počká, dokud canonical reconciliation workflow nemá žádný `queued` ani `in_progress` run. Broker reconciliation joby mají navíc společný non-cancelling concurrency group. Tím se privileged Project mutation nespouští souběžně s již běžícím canonical reconciliation runem.

Každý pokus explicitně resolve `main` SHA. Přijatelný child run musí mít právě tento `head_sha`. Pokud se source před přijetím evidence posune, broker po dokončení běžícího runu provede bounded retry s novou explicitní source identity. Starý run se nesmí vydávat za aktuální evidence.

### PASS evidence

Broker vydá technical PASS pouze pokud:

- live PR head stále odpovídá `--expected-sha`;
- child run je právě canonical workflow a má accepted source `main` SHA;
- workflow conclusion je `success`;
- existuje právě jeden neexpirovaný audit artifact pro source SHA;
- `audit.json`, `presentation.json` a `release-planning.json` mají stejný `source_sha`;
- všechny jejich `remaining_count` jsou `0`;
- evidence nese repository, PR, requested actor, authorized/expected PR SHA, canonical workflow, source SHA, workflow run ID/conclusion a audit artifact ID/name.

Technical authorization ani reconciliation PASS nikdy nevytváří Human Review, merge authorization, Human Release Decision, release/promotion authorization nebo tag authorization.

### Default-branch activation boundary

GitHub `issue_comment` workflow je aktivní podle workflow definice na default branchi. Nová broker capability, která existuje pouze v dosud nemergovaném PR, proto nemůže sama sobě před merge vytvořit produkční `issue_comment` end-to-end důkaz. Statická/exact-SHA CI validace PR capability je možná, ale live connector-comment E2E je možné až po aktivaci reviewované broker definice na default branchi nebo přes samostatný explicitně autorizovaný bootstrap mechanismus podle platform-development skillu. Tento fakt se nesmí maskovat náhradním workflow nebo ruční Project GUI operací.

## Runtime isolation

Candidate validation odstraňuje z child procesu:

```text
PYTHONPATH
PYTHONHOME
DDDA_PLATFORM_ROOT
DDDA_REPO_ROOT
```

Miro CLI běží s `python -I`. Před prvním vzdáleným zápisem se ověřuje:

- skutečný `ddda_miro.render.__file__`;
- SHA-256 importovaného a očekávaného modulu;
- `RENDER_CONTRACT_VERSION`;
- `CANONICAL_GUIDE_HEADINGS`;
- candidate source SHA;
- scaffold SHA-256.

Nesoulad skončí před vytvořením nebo změnou boardu.

## Transparentní selhání přístupu

Work musí před použitím externího zdroje ověřit, že connector skutečně načetl požadovaný board, frame, PR, soubor nebo workflow evidence.

Pokud zdroj nelze načíst:

- operace se zastaví;
- omezení se oznámí uživateli;
- nevytváří se tvrzení o provedeném connector review;
- strukturální metadata se nevydávají za vizuální analýzu;
- nevytváří se náhradní zápis na základě odhadu.

Výjimka pro HVR není technický bypass: pokud MCP není dostupný, reviewer může otevřít již technicky validovanou stabilní Miro URL v GUI a vrátit screenshot/findings. V takovém případě se netvrdí, že proběhla MCP inspection.

## Governance

Remote broker nikdy automaticky neprovádí merge, tag, release ani promotion. Human visual acceptance a release decision zůstávají samostatnými lidskými kroky.

Technický PASS dokládá pouze provedené mechanické kontroly. Vizuální Miro acceptance vyžaduje explicitní lidské rozhodnutí; použití MCP je volitelné.

## Chat atomic implementation před aktivací default-branch brokeru

Work je preferovaný implementační režim. Pokud Work není dostupný a `issue_comment` broker ještě není aktivní na default branchi, může Chat použít schválený GitHub Git Data API transport.

Tento transport není sekvence Contents API zápisů. Chat musí z exact-SHA source snapshotu sestavit celý nový Git tree, vytvořit jediný commit s autorizovaným PR HEAD jako rodičem a provést pouze ne-force fast-forward aktualizaci stejné PR branche. Bezprostředně potom musí proběhnout standardní PR CI nad výsledným exact SHA.

Chat atomic transport nesmí provádět secret-bearing online operace. Online Miro REST acceptance a další secret-bearing validace zůstávají v GitHub Actions. Selhání CI se neopravuje přepisem historie; následuje korektivní commit nebo revert.

Workflow založený na `issue_comment` se spouští pouze tehdy, když je jeho workflow definice dostupná na default branchi. Existence workflow pouze v dosud nemergované PR branchi proto není dostatečný bootstrap mechanismus.
