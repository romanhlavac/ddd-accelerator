# Miro scaffolding

## Účel

Scaffold není hotový model ani dekorativní prezentace. Je to deterministická navigační, facilitační a auditní projekce DDDA projektu. Ukazuje metodickou cestu, aktuální gate, pracovní otázky, očekávané evidence a vazbu na Git/YAML.

Miro není autoritou pro gate approval. Stav `passed`, `conditional` nebo `rejected` vzniká pouze explicitním human decision recordem v projektovém Gitu.

## Cílová struktura boardu

Renderer načte `scaffolds/miro/strategic-ddd-method-board.yaml` a vytvoří nebo aktualizuje:

1. dominantní **Control Center**;
2. persistentní journey mapu `G1–G8`;
3. pět explicitních gate stavů s textem a symbolem;
4. pracovní frames podle DDD Starter Modelling Process;
5. vyšší zóny:
   - Align & Understand,
   - Strategic Architecture,
   - Strategy & Org Design,
   - Tactical Architecture;
6. stabilní traceability `starter step → stage → gate → work frame → evidence → human acceptance`;
7. strukturované workshop templates uvnitř každého frame.

## Control Center

Control Center musí na první pohled ukázat:

- project name a project ID;
- current stage a current gate;
- gate status;
- decision question;
- decision owner;
- chybějící nebo sporné evidence;
- doporučené next actions;
- project/source commit;
- last render/sync;
- pravidlo, že Git/YAML a human gate decision jsou autorita.

Povinné managed artefakty mají explicitní placement:

```text
project-charter       → control-center
DDDA current status   → control-center
DDDA next actions     → control-center
```

Každý placement má stabilní `frame_id`, `x`, `y` a `width`. `frame_id: null` je u těchto artefaktů contract violation.

## Journey G1–G8

Journey je persistentní a aktualizuje se bez vytvoření nového boardu nebo nových journey items:

```text
G1 Align → G2 Discover → G3 Decompose → G4 Strategize
→ G5 Connect → G6 Organize → G7 Define → G8 Code
```

Každý krok zobrazuje:

- gate ID a stage;
- status text a symbol;
- `AKTUÁLNÍ`, `DOKONČENO` nebo `NÁSLEDUJÍCÍ`;
- počet otevřených blockerů;
- rozhodovací význam;
- ID pracovního frame.

## Gate states

| Stav | Symbol | Význam |
|---|---:|---|
| `not_ready` | ⛔ | chybí povinné evidence nebo owner |
| `ready_for_review` | ◉ | mechanicky připraveno k lidskému review |
| `conditional` | △ | lidské rozhodnutí s podmínkou, ownerem a termínem; gate není dokončena |
| `rejected` | ✕ | lidské rozhodnutí gate odmítlo |
| `passed` | ✓ | explicitní lidské schválení |

Barva je pouze podpůrná. Board musí být čitelný i bez rozlišení barev.

## Workshop templates

Každý frame obsahuje:

- účel frame;
- pojmenované pracovní oblasti;
- stručné facilitační instrukce;
- pravidlo oddělit fakta, hypotézy, rozhodnutí, ownery a otevřené otázky.

Big Picture EventStorming je v Discover, Process Modeling tvoří most Discover → Decompose, Design-Level EventStorming je v Define a tactical model je v Code.

## Idempotence a zachování ruční práce

Opakovaný render:

- používá stabilní `miro_item_id` z `miro/miro-map.yaml`;
- aktualizuje existující frames a system items;
- nevytváří nový board;
- nemění množinu journey item ID;
- nesmí překrýt pracovní plochu watermarkem nebo jiným blocking overlay;
- nemaže unmanaged workshopový obsah;
- při běžném syncu nepřepisuje ručně upravený layout existujícího managed artefaktu, pokud není explicitně požadován `--include-layout`.

## Acceptance contract

Online automatizace smí vyhodnotit pouze technickou část:

```text
technical_sync_status: PASS
layout_contract_status: PASS
utf8_status: PASS
human_visual_acceptance_status: PENDING
overall_status: PENDING_HUMAN_REVIEW
```

Technický PASS není vizuální ani metodický human PASS. Finální lidské review se provádí jednou nad zmrazeným boardem po dokončení všech online automatických oprav.

## UTF-8 a overlay guard

Renderer a sync failnou, pokud scaffold, managed artefakty nebo mapping obsahují známé mojibake sekvence. Layout validator failne, pokud watermark nebo branding overlay překrývá pracovní frame.

## Dry-run

Dry-run ověří layout contract, UTF-8, journey, legendu, zóny a plánované create/update operace bez write endpointů a bez změny projektového repozitáře.
