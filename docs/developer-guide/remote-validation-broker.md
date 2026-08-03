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

## Jednorázové nastavení

Repository nebo environment secret:

```text
MIRO_ACCESS_TOKEN
```

Token musí mít jen potřebné Miro scopes a být omezen na používaný team. Token se nevkládá do Chatu, Work kontextu, souboru ani Git historie.

Připojené GitHub a Miro Apps musí být schválené pro klasifikaci zpracovávaných dat a používat least-privilege oprávnění.

## Příkaz pro validation a online acceptance

Oprávněný actor vloží do PR komentář:

```text
/ddda validate-pr --with-miro --full --keep-review-board
```

Broker:

1. načte policy z `config/platform/development-policy.yaml`;
2. ověří Chat/Work-only execution policy;
3. ověří actor, same-repository PR a exact head SHA;
4. vyžaduje úspěšné checky `Platform validation` a `One-command PR validation`;
5. checkoutne exact SHA;
6. spustí `ddda.ps1 validate-pr` s Miro tokenem pouze v secret-bearing kroku;
7. zachová review board;
8. publikuje evidence artifact a PR komentář.

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
- nevytváří se tvrzení o provedeném review;
- strukturální metadata se nevydávají za vizuální analýzu;
- nevytváří se náhradní zápis na základě odhadu.

## Governance

Remote broker nikdy automaticky neprovádí merge, tag, release ani promotion. Human visual acceptance a release decision zůstávají samostatnými lidskými kroky.

Technický PASS dokládá pouze provedené mechanické kontroly. Vizuální Miro acceptance vyžaduje skutečné načtení reference i cíle, side-by-side posouzení a explicitní lidské rozhodnutí.
