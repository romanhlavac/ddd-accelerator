# Kuchařka 07 — Synchronizace Miro ↔ YAML ↔ Git

## Bezpečný cyklus

```text
doctor → pull dry-run → promotion/conflict review → pull → YAML review
→ push dry-run → push → scope guard → commit → PR
```

## Pull dry-run

```powershell
& (Join-Path $PlatformRoot 'scripts\Invoke-DDDAMiroSync.ps1') `
  -ProjectPath $ProjectRoot -Direction Pull -DryRun
```

## Both

```powershell
& (Join-Path $PlatformRoot 'scripts\Invoke-DDDAMiroSync.ps1') `
  -ProjectPath $ProjectRoot -Direction Both
```

## Chat prompt

> Proveď sync dry-run. Rozděl operace na create, update, delete_pending, promotion_required, unmanaged a conflict. U každé ukaž artifact ID, YAML path a Miro item ID. Bez potvrzení nic nezapisuj.

## Nový artefakt vytvořený přímo v Miru

Nový Miro item se stane kandidátem pro YAML pouze tehdy, když obsahuje úplný marker a sémantické řádky:

```text
Typ: hotspot
Stav: candidate
Fáze: discover
DDDA:life-insurance-greenfield:hotspot-medical-evidence
```

První pull bez přepínače pouze oznámí `pull_unmapped_requires_promotion`. Chat má zkontrolovat ID, typ, stage, popis, cílový frame a případné duplicity.

Dry-run promotion:

```powershell
& (Join-Path $PlatformRoot 'scripts\Invoke-DDDAMiroSync.ps1') `
  -ProjectPath $ProjectRoot `
  -Direction Pull `
  -PromoteNew `
  -DryRun
```

Po potvrzení spusť stejný příkaz bez `-DryRun`. Runtime vytvoří YAML pod `artifacts/<stage>/<type>/<artifact-id>.yaml`, doplní mapping a společnou sync base. Worker nové položky automaticky nepromuje; promotion je záměrný review krok.

## Konflikty

Conflict record se řeší business rozhodnutím. Po ručním merge uprav YAML, nastav resolution, proveď push dry-run a teprve potom commit.

## Idempotence

Druhý sync bez změn musí vrátit nulový sémantický diff. Pokud vytváří nové itemy, mapping je poškozen nebo marker chybí.

## Průběžný worker

Použij jen tehdy, když je projektová větev čistá nebo je tým srozuměn s tím, že worker může měnit YAML a sync metadata.

```powershell
& (Join-Path $PlatformRoot 'scripts\Start-DDDAMiroSyncWorker.ps1') `
  -ProjectPath $ProjectRoot `
  -IntervalSeconds 60
```

Doporučený chat prompt před startem:

> Ověř Miro konfiguraci, čistotu projektového repozitáře, pending konflikty a poslední sync report. Navrhni, zda je bezpečné spustit worker. Worker nesmí provádět commit, promovat nové položky ani automaticky řešit konflikty.

Worker zastaví první sémantický konflikt. Neřeš to jeho opakovaným restartem; nejdřív vyřeš conflict record.

## Ručně odstraněný Miro item

Mapped item, který v Miru chybí, je bezpečnostní konflikt. Po potvrzení obnovy:

```powershell
& (Join-Path $PlatformRoot 'scripts\Invoke-DDDAMiroSync.ps1') `
  -ProjectPath $ProjectRoot `
  -Direction Push `
  -RecreateMissing `
  -DryRun
```

Teprve po review proveď skutečný push.

## Acceptance checklist

- doctor online prošel,
- board ID a token pocházejí z environment variables nebo persisted mappingu,
- pull dry-run nehlásí nevysvětlené změny,
- nové Miro itemy byly explicitně promované nebo ponechané unmanaged,
- pending konflikty mají vlastníka,
- druhý sync bez změn má nulový sémantický diff,
- `reports/miro-sync/` obsahuje auditní záznam,
- projektový Git diff neobsahuje platformní soubory.
