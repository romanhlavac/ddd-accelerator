# 13 Inicializace DDDA po clone

## Účel a rozhodnutí

Tato aktivita ověřuje, že nový clone platformy je provozně použitelný dříve, než se nad ním založí klientský workspace nebo projekt. Odděluje dvě úrovně:

1. **offline inicializaci** — Git root, povinné soubory, PowerShell syntaxi, Python a instalaci Miro runtime;
2. **online Miro smoke test** — skutečné vytvoření testovacího boardu, obousměrná synchronizace, `PromoteNew`, idempotence a cleanup.

Online smoke test není projektová práce. Používá izolovaný dočasný workspace, dočasný projekt a dočasný board.

## Entry criteria

- repozitář byl právě naklonován nebo výrazně aktualizován;
- pracovní strom platformy je čistý;
- je dostupný Git, PowerShell a Python 3.11+;
- pro online test existuje Miro Developer team a aplikace se scopes `boards:read` a `boards:write`;
- uživatel má access token této aplikace.

## Jednorázová online inicializace

Z kořene platformního repozitáře:

```powershell
.\scripts\Initialize-DDDAAfterClone.ps1 -WithMiro -Full
```

Při prvním běhu skript vyžádá token skrytým promptem. Na Windows jej uloží pomocí DPAPI mimo Git root:

```text
%LOCALAPPDATA%\DDDA\secrets\miro-access-token.xml
```

Token se nepíše do repozitáře, reportu ani příkazové historie. Při dalších bězích se použije uložená hodnota.

## Rutinní offline kontrola

Bez volání Miro API:

```powershell
.\scripts\Initialize-DDDAAfterClone.ps1
```

Skript provede:

1. ověření, že `PlatformPath` je Git root;
2. kontrolu čistého pracovního stromu;
3. `Test-DDDAInstallation.ps1`;
4. detekci funkčního `python` nebo `py`;
5. instalaci runtime do `.ddda/runtime/miro-venv`;
6. kontrolu vstupního bodu `python -m ddda_miro --help`;
7. závěrečnou kontrolu čistého platformního repozitáře.

## Rutinní online smoke test

Zkrácený test bez polling workeru:

```powershell
.\scripts\Invoke-DDDAMiroSmokeTest.ps1
```

Plný test včetně dvou cyklů workeru:

```powershell
.\scripts\Invoke-DDDAMiroSmokeTest.ps1 -Full
```

Smoke test ověřuje:

- token context a požadované scopes;
- vytvoření izolovaného workspace a projektu;
- offline a online doctor;
- dry-run a vytvoření boardu;
- YAML → Miro;
- Miro → YAML;
- explicitní `PromoteNew`;
- volitelně polling worker;
- závěrečný `Both --dry-run` s nulou operací a konfliktů;
- čistotu platformního Git rootu.

## Cleanup a diagnostika

Výchozí chování:

| Výsledek | Board | Workspace | Report |
|---|---|---|---|
| PASS | odstraní se | odstraní se | ponechá se |
| FAIL | ponechá se | ponechá se | ponechá se |

Report je mimo Git root:

```text
%LOCALAPPDATA%\DDDA\smoke-reports\<run-id>\result.json
```

Ponechání prostředků i po úspěchu:

```powershell
.\scripts\Invoke-DDDAMiroSmokeTest.ps1 -Full -KeepArtifacts
```

Cleanup také po chybě:

```powershell
.\scripts\Invoke-DDDAMiroSmokeTest.ps1 -Full -CleanupOnFailure
```

Výměna uloženého tokenu:

```powershell
.\scripts\Invoke-DDDAMiroSmokeTest.ps1 -ResetToken -Full
```

## YAML/Git výstupy

Online smoke test nesmí měnit platformní repozitář. Všechny projektové soubory vznikají v dočasném workspace a po úspěchu jsou odstraněny. Trvale zůstává pouze lokální report a bezpečně uložený token.

## Kontroly

Definition of Done:

- výstup končí `DDDA Miro smoke test: PASS`;
- report má `result: passed`;
- testovací board a workspace byly při výchozím režimu odstraněny;
- `git status --short` platformy je prázdný;
- v repozitáři není token ani lokální report.

## Anti-patterny

- ruční vykonávání jednotlivých REST kroků místo runneru;
- ukládání tokenu do `.env`, Markdownu nebo PowerShell skriptu v repozitáři;
- používání klientského projektového boardu pro smoke test;
- pokračování po neúspěchu bez přečtení `failure_step` a Miro response body;
- automatické mazání diagnostického boardu při chybě bez explicitního `-CleanupOnFailure`.

## Navazující krok

Po úspěšné inicializaci založ workspace a projekt. Cílový projektový board vytvoř podle kuchařky [14 Inicializace cílového Miro boardu](14-inicializace-ciloveho-miro-boardu.md).
