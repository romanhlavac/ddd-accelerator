# VÃ½vojovÃ½ lifecycle DDDA platformy

## ÃšÄel

Tento postup platÃ­ pro vÃ½voj verzovanÃ© DDDA platformy. NeplatÃ­ pro domÃ©novou prÃ¡ci v klientskÃ©m projektu.

RozliÅ¡uj:

```text
platform repository
â†’ candidate/release package
â†’ generated validation workspace
â†’ example project
```

KlientskÃ½ workspace nenÃ­ test fixture platformy.

## PovinnÃ½ platform-development skill

KanonickÃ½ a verzovanÃ½ operating contract pro vÃ½voj platformy je:

```text
knowledge/ddda-platform-development-skill.md
```

KaÅ¾dÃ½ ChatGPT projekt, Chat nebo Work runtime pouÅ¾Ã­vanÃ½ pro zmÄ›ny DDDA platformy musÃ­ tento skill registrovat jako **povinnÃ½ pro vÃ½voj DDDA** alespoÅˆ jednÃ­m z tÄ›chto mechanismÅ¯:

1. poloÅ¾kou v `knowledge/00-knowledge-index.md`;
2. explicitnÃ­m odkazem v ChatGPT Project Instructions nebo Work bootstrap instructions.

Git a runtime activation jsou dva oddÄ™lenÃ© kontrolnÃ­ mechanismy:

- soubor v Gitu zajiÅ¡Å¥uje versioning, review a traceability;
- knowledge index nebo Project/Work Instructions zajiÅ¡Å¥ujÃ­, Å¾e jej konkrÃ©tnÃ­ Chat Äi Work skuteÄnÄ› naÄte.

PÅ™ed nÃ¡vrhem nebo aplikacÃ­ zmÄ›ny platformy se musÃ­ ovÄ›Å™it:

```text
- runtime naÄetl aktuÃ¡lnÃ­ repository verzi skillu;
- skill odpovÃ­dÃ¡ aktivnÃ­ branch/SHA;
- tento developer lifecycle a testing strategy jsou dostupnÃ©;
- Chat/Work policy odpovÃ­dÃ¡ config/platform/development-policy.yaml;
- pÅ™Ã­padnÃ½ rozpor mezi skillem a dokumentacÃ­ je vyÅ™eÅ¡en v Gitu.
```

ChybÄ›jÃ­cÃ­ nebo zastaralÃ¡ registrace je governance defect. U zmÄ›n s dopadem `HIGH` nebo `BREAKING` se pokraÄovÃ¡nÃ­ zastavÃ­, dokud nenÃ­ routing opraven. SamotnÃ¡ existence skillu v repozitÃ¡Å™i nenÃ­ dÅ¯kazem, Å¾e jej runtime pouÅ¾Ã­vÃ¡.

## PovolenÃ½ Chat/Work operating model

```text
DDDA-EXECUTION-MODE: CHAT-WORK-ONLY
```

PovolenÃ¡ rozhranÃ­:

- **Chat** pro analÃ½zu, nÃ¡vrh, rozhodnutÃ­, autorizaci a review;
- **Work** pro vÃ­cekrokovou prÃ¡ci se schvÃ¡lenÃ½mi GitHub/Miro Apps a ohraniÄenÃ© zÃ¡pisy na PR branch.

ZakÃ¡zÃ¡no:

- **Codex**;
- legacy **`/agent`**;
- jinÃ½ neschvÃ¡lenÃ½ cloudovÃ½ coding agent.

GitHub Actions je autoritativnÃ­ execution plane pro shell, build, testy, candidate package a package-first acceptance. Work nesmÃ­ tvrdit, Å¾e provedl lokÃ¡lnÃ­ pÅ™Ã­kaz, pokud jej ve skuteÄnosti nespustil schvÃ¡lenÃ½ execution plane.

KanonickÃ¡ pravidla jsou v:

```text
docs/developer-guide/chat-work-operating-model.md
docs/adr/0005-chat-work-only-development-operating-model.md
```

## KanonickÃ½ tok

```text
change request v Chat nebo Work
â†’ branch
â†’ Work implementation pÅ™es schvÃ¡lenÃ© Apps
â†’ standardnÃ­ GitHub Actions nad exact SHA
â†’ validate-pr
â†’ human review
â†’ review-pr / HRDR
â†’ Release Scope Gate
â†’ promote-pr dry-run
â†’ explicitnÃ­ human promotion decision
â†’ merge
â†’ release package
â†’ release validation
â†’ tag
```

Git je source of truth. PR je jednotka zmÄ›ny. Package je jednotka distribuce a reprodukovatelnÃ© validace.

HRDR a Release Scope Gate jsou dvÄ› odliÅ¡nÃ© authority boundaries. HRDR zachycuje lidskÃ© rozhodnutÃ­; Release Scope Gate mechanicky ovÄ›Å™uje Ãºplnost a konzistenci autoritativnÃ­ho release scope. Podrobnosti jsou v `docs/developer-guide/human-release-decision-and-release-scope-gate.md` a ADR 0008.

## 1. PÅ™Ã­prava zmÄ›ny

KaÅ¾dÃ¡ behaviorÃ¡lnÃ­ zmÄ›na musÃ­ urÄit:

- problÃ©m a cÃ­l;
- klasifikaci zmÄ›ny;
- dopad na kontrakty a kompatibilitu;
- acceptance criteria;
- test suites;
- dokumentaÄnÃ­ dopad;
- potÅ™ebu ADR nebo migration note;
- povolenÃ½ write scope pro Work;
- bezpeÄnostnÃ­ a datovou klasifikaci pÅ™ipojenÃ½ch Apps.

HlavnÃ­ klasifikace:

```text
DOC, METHODOLOGY, TEMPLATE, SCHEMA, ORCHESTRATION,
INGESTION, CLI, WORKSPACE-GENERATOR, EXAMPLE,
TESTING, RELEASE, SECURITY-GOVERNANCE
```

## 2. Feature branch a implementace

`main` se nemÄ›nÃ­ pÅ™Ã­mo. DoporuÄenÃ© nÃ¡zvy:

```text
feature/<change-id>-<short-name>
fix/<change-id>-<short-name>
docs/<change-id>-<short-name>
release/<version>
```

BehaviorÃ¡lnÃ­ zmÄ›na bez testu je neÃºplnÃ¡. ZmÄ›na kontraktu bez dokumentace a compatibility rozhodnutÃ­ je neÃºplnÃ¡.

Work pÅ™ed prvnÃ­m zÃ¡pisem ovÄ›Å™Ã­:

- aktuÃ¡lnÃ­ PR head SHA;
- deklarovanou target branch;
- allowed paths;
- Å¾e autorizace neobsahuje merge, promotion, release, tag ani force-push;
- Å¾e poÅ¾adovanÃ½ GitHub/Miro connector je skuteÄnÄ› dostupnÃ½.

Pokud connector, board nebo oprÃ¡vnÄ›nÃ­ nejsou dostupnÃ©, Work zastavÃ­ a omezenÃ­ oznÃ¡mÃ­. NesmÃ­ je tiÅ¡e nahradit pÅ™edpokladem.

## 3. Test suites a execution plane

StabilnÃ­ platformnÃ­ kontrakt:

```powershell
.\ddda.ps1 doctor
.\ddda.ps1 test -Suite lint
.\ddda.ps1 test -Suite schema
.\ddda.ps1 test -Suite unit
.\ddda.ps1 test -Suite component
.\ddda.ps1 test -Suite regression
.\ddda.ps1 test -Suite security
```

Na Chat/Work-only cestÄ› tyto pÅ™Ã­kazy spouÅ¡tÄ›jÃ­ standardnÃ­ GitHub Actions workflows. UÅ¾ivatel nemusÃ­ poskytovat Work lokÃ¡lnÃ­ shell a nesmÃ­ bÃ½t smÄ›rovÃ¡n do Codexu.

Package-dependent suites dostÃ¡vajÃ­ `-PackagePath` a pouÅ¾Ã­vajÃ­ novÄ› rozbalenÃ½ balÃ­Äek.

## 4. Candidate package

`validate-pr` naÄte exact PR head SHA, vytvoÅ™Ã­ izolovanÃ½ checkout a candidate package pomocÃ­ `git archive`. Package dostane `ddda-package.json` s pÅ¯vodem, verzÃ­ a source commit SHA.

Package nesmÃ­ obsahovat:

```text
.git/
.ddda/
.tmp/
.reports/
.releases/
dist/
Python caches
credentials
client data
uÅ¾ivatelskÃ© absolutnÃ­ cesty
```

## 5. Validace PR

StabilnÃ­ kontrakt:

```powershell
.\ddda.ps1 validate-pr -Pr 8
```

S Miro:

```powershell
.\ddda.ps1 validate-pr -Pr 8 -WithMiro -Full -CleanupOnFailure
```

V Chat/Work-only reÅ¾imu jej spouÅ¡tÃ­ standardnÃ­ PR workflow nebo remote validation broker.

PÅ™Ã­kaz:

1. ovÄ›Å™Ã­ ÄistÃ½ aktivnÃ­ repozitÃ¡Å™;
2. naÄte `refs/pull/<PR>/head`;
3. vytvoÅ™Ã­ izolovanÃ½ checkout exact SHA;
4. vytvoÅ™Ã­ a validuje candidate package;
5. rozbalÃ­ package do novÃ©ho adresÃ¡Å™e;
6. inicializuje lokÃ¡lnÃ­ baseline Git pouze pro testy, nikoli jako distribuovanÃ½ obsah;
7. spustÃ­ test suites;
8. vytvoÅ™Ã­ example workspace z package;
9. provede manifest-driven ingestion;
10. ovÄ›Å™Ã­ G1 â†’ G2;
11. volitelnÄ› provede Miro acceptance;
12. vytvoÅ™Ã­ JSON a Markdown report.

PASS automaticky uklidÃ­ pracovnÃ­ clone a workspaces, pokud nenÃ­ pouÅ¾ito `-KeepArtifacts`. Report a candidate package zÅ¯stÃ¡vajÃ­ pro promotion.

## 6. LidskÃ© review a HRDR

ÄŒlovÄ›k posuzuje pouze oblasti vyÅ¾adujÃ­cÃ­ judgment:

- metodickou sprÃ¡vnost;
- architektonickÃ© hranice;
- semantics gatÅ¯;
- srozumitelnost chat-first workflow;
- vizuÃ¡lnÃ­ kvalitu Miro boardu;
- release readiness a pÅ™ijetÃ­ rizik.

Syntax, schÃ©mata, cesty, packaging, idempotence a absence secrets kontroluje automatizace.

Po frozen-candidate review lze vytvoÅ™it machine-readable HRDR scaffold:

```powershelll
.\ddda.ps1 review-pr -Pr <PR> -Version <X.Y.Z> -Reviewer <login> -DecisionOwner <login> -PublishScaffold
```

Automation vÅ¾dy vytvoÅ™Ã­ pouze `decision=pending`. FinÃ¡lnÃ­ `GO`, `GO_WITH_ACCEPTED_RISKS` nebo `NO_GO` je explicitnÃ­ lidskÃ© rozhodnutÃ­. Positive decision musÃ­ bÃ½t svÃ¡zÃ¡no se stejnÃ½m exact source SHA, candidate package SHA-256, version a release scope, kterÃ½ nÃ¡slednÄ› ovÄ›Å™uje Release Scope Gate.

### Miro visual review

PÅ™ed tvrzenÃ­m, Å¾e implementace odpovÃ­dÃ¡ redline nebo referenÄnÃ­mu boardu, musÃ­ Work skuteÄnÄ› naÄÃ­st:

- referenÄnÃ­ board;
- konkrÃ©tnÃ­ source frames;
- relevantnÃ­ children, images a geometry;
- cÃ­lovÃ© frames pro side-by-side porovnÃ¡nÃ­.

VizuÃ¡lnÃ­ acceptance hodnotÃ­ minimÃ¡lnÄ™:

- ÄÃ­telnost pÅ™i `Fit to frame`;
- first-viewer srozumitelnost;
- fonty a vazualÃ­nÃ­ hierarchii;
- pÅ™ekryvy frames/items;
- vyuÅ¾itÃ­ plochy;
- pÅ™Ã­tomnost poÅ¾adovanÃ½ch obrÃ¡zkÅ¯ a examples;
- vÄ›rnost schvÃ¡lenÃ©mu template;
- metodickou a domÃ©novou koherenci.

Item count, parent ownership, schema PASS a idempotence nejsou visual acceptance. TechnickÃ½ PASS ponechÃ¡vÃ¡ `human_review_status=PENDING`, dokud ÄlovÄ›k vÃ½sledek nepÅ™ijme.

## 7. GitHub autentizace a release dokumentace

`promote-pr` pouÅ¾Ã­vÃ¡ GitHub REST API. GitHub CLI nenÃ­ povinnÃ¡ zÃ¡vislost. Implementace i dokumentace pouÅ¾Ã­vajÃ­ stejnÃ© poÅ™adÃ­ providerÅ¯:

1. `GH_TOKEN`;
2. `GITHUB_TOKEN`;
3. `gh auth token`;
4. Git credential helper.

Token se nikdy nepÅ™edÃ¡vÃ¡ jako CLI argument a nesmÃ­ se objevit v logu, reportu, Chat/Work kontextu ani shell history.

Release Scope Gate navÃ­c vyÅ¾aduje `DDDA_GITHUB_PROJECT_TOKEN` pro read-only Project V2 evidence. Tento token zÅ¯stÃ¡vÃ¡ v GitHub Actions / secret store a pÅ™edÃ¡vÃ¡ se pouze pÅ™es process environment.

BÄ™hem vÃ½voje se zmÄ›ny zapisujÃ­ pod `## [Unreleased]`. PÅ™ed promotion se vÅ¡echny release poloÅ¾ky pÅ™esunou pod prÃ¡vÄ› jednu sekci `## [X.Y.Z] - YYYY-MM-DD`, `Unreleased` zÅ¯stane bez release poloÅ¾ek a stejnÃ¡ verze se pÅ™edÃ¡ jako `-Version X.Y.Z`. Tag je deterministicky `vX.Y.Z`.

Promotion preflight kontroluje syntaxi changelogu, platnÃ© ISO datum, neprÃ¡zdnou release sekci, prÃ¡zdnou `Unreleased` sekci a shodu verze s parametrem promotion.

## 8. Promotion a Release Scope Gate

NejdÅ™Ã­v bezpeÄnÃ½ preflight:

```powershell
.\ddda.ps1 promote-pr -Pr 8 -Version 0.8.0 -DryRun
```

SkuteÄnÃ½ promotion vyÅ¾aduje explicitnÃ­ potvrzenÃ­:

```powershell
.\ddda.ps1 promote-pr -Pr 8 -Version 0.8.0 -ConfirmMerge
```

Public `promote-pr` nejdÅ™Ã­ve provede governed preflight. InternÃ­ release executor se nezavolÃ¡, dokud Release Scope Gate nemÃ¡ `PASS`.

Release Scope Gate fail-closed ovÄ›Å™uje minimÃ¡lnÄ›:

- prÃ¡vÄ› jeden autoritativÃ­ Milestone `DDDA <version>`;
- HRDR scope pÅ™esnÄ™ odpovÃ­dÃ¡ current milestone Issues;
- vÅ¡echny current-release Issues jsou terminal;
- Å¾Ã¡dnÃ½ current-release Issue nemÃ¡ unresolved native blocker;
- Project planning projection odpovÃ­Ã¡ Issue/native authority (`Status=Done`, `Blocked=No`);
- Project title a kanonickÃ© planning/delivery views odpovÃ­Ã¡jÃ­ governance contractu;
- deferred accepted-risk Issues jsou mimo current milestone, zÅ¯stÃ¡vÃ¡jÃ­ otevÅ™enÃ©, majÃ­ HRDR ownera jako live assignee a explicitnÃ­ target/horizon;
- HRDR neobsahuje RED a mÃ¡ positive human decision;
- live PR head, HRDR source SHA, candidate package hash a version se shodujÃ­.

Nedostupn°ïH›Ú™Xİ™XYX˜XÚÈ™X›È[XšYİZ]H™HRS™HØ\›š[™Ë‚‚”ÈØÛÜKYØ]HTÔÈ[\›°ëH›Û[İ[ÛˆÚÜ˜q#]Z™H^\İZ°ëXğë[ZHÚXÚÜÎ‚‚‹Hˆ™Hİ]±fY[°ïHH™[°ëH˜YÂ‹HXYÒHÙH™^›q&Ûš[Â‹HÒHÚXÚÜÈœÛİHTÔÎÂ‹H˜[Y][Ûˆ™\Ü™HTÔÈ›ÈİZ›°ïHÒNÂ‹HØ[™Y]HXÚØYÙH\ÚÙİ°ëY0èH™\ÜNÂ‹H\›İ˜[ÈÙİ°ëYZ°ëH™\ÜÚ]ÜHÛXŞNÂ‹Hİš[›°êHQ‹Ú[™Ù[ÙÈHZYÜ˜][Ûˆ›İH^\İZ°ëNÂ‹HÚ[™Ù[ÙÈ™[X\ÙH™\™HÙİ°ëY0èHU™\œÚ[Û˜HYİ\ğë[]HYİH––K–˜Â‹H[œ™[X\ÙY™[ØœØZZ™H™\1fZqfX^™[°êH™[X\ÙHÛñošŞNÂ‹HPÛÛ™š\›SY\™ÙX™H^XÚ]±&È˜Y0è[›È›ÈÚİ]q#[°ïH›Û[İ[Û‹‚‚˜ÓØØÓ×ÕÒUĞPĞÑTQÔ’TÒÔØˆ‘ˆ™[°ëHØ[[ÈÈÛØ±&ÈY\™ÙH]]Üš^˜][Û‹ˆÚİ]q#[°ïHY\™ÙKÜ›Û[İ[Ûˆİ0è[Hqo˜YZ™HØ[[Üİ]›İH^XÚ]°ëHÛİ™\›˜[˜ÙHXİ[Û‹‚‚”ÈY\™ÙH›šZÛ™H™[X\ÙHXÚØYÙKˆYÈÙH]›ñfpëHqoˆÈXÚØYÙH˜[Y][Û‹Ù[™\˜]Y™[X\ÙHÛÜšÜÜXÙK[™Ù\İ[Û‹Û[ÚÙHHXØÙ\[˜ÙK‚‚ˆÈÈKˆÙ[0è[°ëHHXYÛ›ÜİZØB‚“Úğè[°ëHİ]ˆ™HÙqoš]˜][Úğï[HHİ]H›Ûİ[N‚‚˜^˜[Y][Û‹Â˜[Y][Û‹\™\ÜËÂš[X[‹\™]šY]ÜËÂœ™[X\ÙK\ØÛÜKYØ]\ËÂœXÚØYÙ\ËÂœ›Û[İ[Û‹Âœ™[X\ÙK\™\ÜËÂ˜‚”1fZHRS±kÜİ0è]˜Z°ëHÙŞHHXYÛ›ÜİXÚğïHÛÜšÜÜXÙKˆZ\›È›Ø\™™H1fZH\İHÙİ˜[š]1fY\ÈPÛX[\Û‘˜Z[\™X‚‚•ÛÜšÈ]\ğëH›Ş›qhZ]‚‚‹HÛÛ›™XİÜ‹ØXØÙ\ÜÈ˜Z[\™NÂ‹H[\[Y[][Ûˆ˜Z[\™NÂ‹HÒKİ\İ˜Z[\™NÂ‹H™[X\ÙHØÛÜHØ]H˜Z[\™NÂ‹H[X[ˆ™]šY]È™Z™Xİ[Û‹‚‚“™\ÛpëH™HÛİq#Z]È™]\±#Z]0êZÈİ]\İH[šH™^™[İ˜]™YÚÛÛ±#Y[›İH°èXÚH˜ZÛÈTÔË‚‚ˆÈÈLˆYš[š][ÛˆÙˆÛ™B‚”ˆ™Hİİ°ïKÙqo‚‚‹H[\[Y[XÙK\İHHÚİ[Y[XÙH›ñfpëH™Y[ˆÚ[™ÙHXÚØYÙNÂ‹HÒH™HTÔÎÂ‹H˜[Y]K\˜™HTÔÈ›ÈZİpè[°ëHXYÒNÂ‹HØ[™Y]HXÚØYÙH™H˜[Y°ëNÂ‹H^[\HÛÜšÜÜXÙH›šZÛˆXÚØYÙNÂ‹H[™Ù\İ[Ûˆ™HX[šY™\İYš]™[Â‹HXØÙ\[˜ÙH™HTÔÎÂ‹H›q&Û˜HÛÛ\]Xš[]HpèHZYÜ˜][Ûˆ›İNÂ‹HİZÙØ°êH›ŞšÙ]0ëHpèHQÂ‹HÚ[™Ù[ÙÈ™HZİX[^›İ°è[Â‹Hİš[›°ïH]›Ü›KY]™[ÜY[ÚÚ[™H™\›İ˜[°ïHH[[YH›İ][™È™ZˆÚİ]q#[±&È˜q#pë]0èNÂ‹HÚ]ÕÛÜšË[Û›HÛXŞH™HÜ±&Û˜NÂ‹HÛÛ›™XİÜˆHš\İX[XXØÙ\ÜÈÛY^™[°ëH[H˜[œÜ\™[±&È]™Y[˜NÂ‹HÙXÜ™]È™]œİİ\[HÈÚ]™X›ÈÛÜšÈÛÛ^NÂ‹HÛÙ^[šHØYÙ[™X[Hİqoš]NÂ‹H™[X\ÙHØÛÜHØ]H™][[ño±bZ™H\œ™]™\œÚX›HÚYHY™™Xİ1fZH™pîœ°ê[H™[X\ÙHØÛÜNÂ‹HY\™ÙH™X[›İ™Y[ˆ™^ˆ^XÚ]°ëZÈYÚğêZÈ›ŞšÙ]0ëK‚