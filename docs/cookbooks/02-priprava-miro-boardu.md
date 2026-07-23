# Kuchařka 02 — Příprava Miro boardu

## Výsledek

Projekt má ověřené Miro credentials, renderovaný metodický board, stabilní mapping framů a připravený dry-run synchronizace.

## Předpoklady

- Miro app se scopes `boards:read` a `boards:write`,
- token v `MIRO_ACCESS_TOKEN`,
- board ID v environment variable z `project.yaml`, nebo oprávnění vytvořit board,
- nainstalovaný Python 3.11+.

## Instalace runtime

```powershell
& (Join-Path $PlatformRoot 'scripts\Install-DDDAMiroRuntime.ps1')
```

## Chat prompt

> Zkontroluj Miro konfiguraci bez vypsání tokenu. Proveď doctor, potom dry-run renderu. Shrň frames, create/update operace a rizika. Skutečný render spusť až po mém potvrzení.

## Doctor

```powershell
& (Join-Path $PlatformRoot 'scripts\Test-DDDAMiroConfiguration.ps1') `
  -ProjectPath $ProjectRoot -Online
```

## Render

```powershell
& (Join-Path $PlatformRoot 'scripts\Initialize-DDDAMiroBoard.ps1') `
  -ProjectPath $ProjectRoot -DryRun

& (Join-Path $PlatformRoot 'scripts\Initialize-DDDAMiroBoard.ps1') `
  -ProjectPath $ProjectRoot
```

## Miro změny

Vzniknou frames pro control center, Align, Big Picture ES, evidence, Process Modeling, decomposition, lifecycle, strategy, context map, teams, BC canvas, Design-Level ES, quality attributes, tactical model a C4/ADR.

## Kontroly

- mapping obsahuje Miro item ID každého frame,
- opakovaný render nevytvoří duplikáty,
- unmanaged poznámky zůstanou zachovány,
- board není sdílen širšímu publiku bez rozhodnutí data ownera.
