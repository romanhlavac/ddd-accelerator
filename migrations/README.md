# DDDA migrations

Migrační skripty převádějí projektové artefakty mezi verzemi projektového schématu DDDA.

## Konvence názvu

```text
migrations/<from>-to-<to>.ps1
```

Příklad:

```text
migrations/1-to-2.ps1
```

## Kontrakt skriptu

Každá migrace musí:

- přijímat parametr `-ProjectPath`,
- měnit pouze obsah projektového repozitáře,
- být idempotentní nebo bezpečně detekovat již provedenou změnu,
- nesmazat původní data bez explicitního zálohování nebo transformačního záznamu,
- skončit chybou při nejednoznačnosti,
- nevytvářet Git commit,
- popsat změnu v projektovém migration reportu.

Minimální skeleton:

```powershell
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$reportDirectory = Join-Path $ProjectPath ".ddda/migrations"
New-Item -ItemType Directory -Force -Path $reportDirectory | Out-Null

# Validace vstupního stavu
# Transformace
# Validace výsledného stavu

Set-Content `
  -Path (Join-Path $reportDirectory "1-to-2.md") `
  -Value "# Migrace 1 -> 2`n`nMigrace dokončena." `
  -Encoding UTF8
```

## Spouštění

Migrace nespouštěj ručně bez důvodu. Používej:

```powershell
scripts/Update-DDDAProject.ps1
```

Ten ověří čistý Git stav, pořadí verzí, dostupnost všech mezikroků a nakonec aktualizuje `ddda.lock.yaml`.

## Governance

Změna migračního skriptu je platformní změna DDDA a musí projít platformním PR. Výsledek migrace konkrétního projektu je projektová změna a musí projít projektovým PR.