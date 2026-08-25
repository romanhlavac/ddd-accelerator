# Recovery canonical annotated release tagu

## Účel

Tento runbook platí pouze pro úzký případ, kdy canonical release promotion už vytvořil a úspěšně validoval release package a release report, ale finální annotated-tag krok selhal při vytvoření, push nebo následném read-backu.

Selhání tagu po validačním PASS neznamená `RELEASED`. Release zůstává nedokončený, dokud canonical tag neexistuje a neprojde read-backem.

## Preconditions

Recovery je přípustná pouze po **separate explicit human recovery authorization**. Před jakýmkoli zápisem musí být doloženo:

- same version jako v původním promotion;
- same validated release SHA;
- same release report se stavem PASS;
- same release package SHA-256;
- canonical tag odvozený ze stejného release/version kontraktu;
- žádná nová release validation ani jiný release candidate mezitím nenahradily původní evidence.

Pokud některý z těchto invariantů nelze prokázat, recovery se zastaví fail closed a musí se rozhodnout nový release postup.

## Deterministic tagger identity

Canonical annotated tag používá ne-secret identitu:

```text
DDDA Release Tagger <ddda-release-tagger@example.invalid>
```

`promote-pr` ji nastavuje pouze v izolovaném `release-source` clone. Nespoléhá na runner/global `user.name` ani `user.email` a nepoužívá token nebo osobní identitu jako tagger metadata.

Canonical message zůstává přesně:

```text
DDDA <version>
```

Tag musí dereferencovat na same validated release SHA.

## Bounded recovery

Recovery neopakuje implementation merge ani celý promotion jen kvůli mechanickému tag failure.

Nejdříve proveď fresh read-back existing canonical tagu:

1. **Tag chybí** — po explicitní recovery authorization lze zopakovat pouze vytvoření canonical annotated tagu se stejnou verzí, stejným validated release SHA, canonical message a deterministic tagger identity; poté push a fresh read-back.
2. **Tag existuje a přesně odpovídá** očekávanému target SHA, message a canonical identity — neprováděj další mutation; read-back je evidence dokončení tag kroku.
3. **Existing canonical tag existuje, ale liší se** target SHA, message nebo očekávaný význam — recovery okamžitě fail closed. Tag se nesmí přepsat ani přesunout.

Recovery nikdy:

- nepřepisuje ani nepřesouvá existing canonical tag;
- nepoužívá force push;
- nemění release package ani release report;
- neopakuje merge bez nové odpovídající autorizace;
- dodržuje invariant `no history rewrite` a neprovádí jiný přepis Git historie.

## Evidence

Recovery evidence musí minimálně obsahovat:

```text
repository
version
canonical_tag
validated_release_sha
release_package_sha256
release_report
human_recovery_authorization
remote_tag_state_before
remote_tag_state_after
result
```

`result=PASS` je možné pouze tehdy, když fresh remote read-back prokáže canonical tag na exact validated release SHA. Technický recovery PASS nenahrazuje žádné další Human Release Decision nebo release governance rozhodnutí, které je podle aktuálního lifecycle stále vyžadováno.

## Navazující GitHub Release publication

Canonical tag sám o sobě není published DDDA distribution. Po vytvoření tagu musí promotion vytvořit nebo fresh read-backem ověřit GitHub Release a jeho canonical package/report assets. Pokud tag existuje, ale Release nebo některý asset chybí, tag se nepřepisuje; postupuje se podle `github-release-publication.md` se samostatnou recovery authorization.
