# Remote validation and remediation broker

DDDA používá GitHub Actions jako řízený vzdálený execution plane. ChatGPT ani jiný klient nedostává Miro token nebo GitHub write token.

## Důvod

Lokální PowerShell může obsahovat ambientní `PYTHONPATH`, uživatelské instalace a lokální secrets. To je vhodné pro development, ale není to spolehlivý package-first acceptance runtime.

Remote broker odděluje:

- požadavek na spuštění;
- autorizaci a exact-SHA binding;
- secret-bearing execution;
- evidence a human review.

## Jednorázové nastavení

Repository nebo environment secret:

```text
MIRO_ACCESS_TOKEN
```

Token musí mít jen potřebné Miro scopes a být omezen na používaný team. Token se nevkládá do chatu, souboru ani Git historie.

## Příkaz pro validation a online acceptance

Oprávněný actor vloží do PR komentář:

```text
/ddda validate-pr --with-miro --full --keep-review-board
```

Broker:

1. načte policy z `config/platform/development-policy.yaml`;
2. ověří actor, same-repository PR a exact head SHA;
3. vyžaduje úspěšné checky `Platform validation` a `One-command PR validation`;
4. checkoutne exact SHA;
5. spustí `ddda.ps1 validate-pr` s Miro tokenem pouze v secret-bearing kroku;
6. zachová review board;
7. publikuje evidence artifact a PR komentář.

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

## Governance

Remote broker nikdy automaticky neprovádí merge, tag, release ani promotion. Human visual acceptance a release decision zůstávají samostatnými lidskými kroky.
