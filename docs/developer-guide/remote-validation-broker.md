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

Legacy PR #8 secret zůstává během migrace podporovaný:

```text
MIRO_ACCESS_TOKEN
```

Preferované nové bindings jsou:

```text
MIRO_CI_ACCESS_TOKEN
MIRO_PLATFORM_LAB_ACCESS_TOKEN
MIRO_HVR_ACCESS_TOKEN
MIRO_EXAMPLE_PROJECT_ACCESS_TOKEN
```

Ne všechny musí být současně nakonfigurovány. Každý workflow smí použít pouze svůj dokumentovaný fallback chain. Secret names jsou kontrakt; secret values nikdy nevstupují do Chatu, Work kontextu, souboru ani Git historie.

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
6. checkoutne exact SHA;
7. spustí `ddda.ps1 validate-pr` s REST Miro tokenem pouze v secret-bearing kroku;
8. zachová review board podle zvoleného scénáře;
9. publikuje evidence artifact a PR komentář.

Obecný acceptance může vytvářet izolovaný board, pokud testuje board-lifecycle. PR #8 HVR FAST-LOOP používá persistentní Platform Lab binding a nemá zakládat nový review board pro každý corrective run.

## HVR broker contract

HVR technical preflight používá REST API a exact-SHA candidate. Preferred credential chain během PR #8 je:

```text
MIRO_HVR_ACCESS_TOKEN
→ MIRO_PLATFORM_LAB_ACCESS_TOKEN
→ MIRO_ACCESS_TOKEN
```

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
