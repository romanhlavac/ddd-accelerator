# Miro scaffolding

## Účel

Scaffold není hotový doménový model ani dekorativní prezentace. Je to deterministická navigační, facilitační a auditní projekce DDDA projektu. Ukazuje metodickou cestu, aktuální gate, pracovní otázky, očekávané evidence a vazbu na Git/YAML.

Miro není autoritou pro gate approval. Stav `passed`, `conditional` nebo `rejected` vzniká pouze explicitním human decision recordem v projektovém Gitu.

## Viditelná struktura boardu

Renderer vytváří:

1. frame **`00 – Navigace, legenda a stav artefaktů`**;
2. samostatný přehled **`01 – DDD Starter journey, gates a iterace`**;
3. osm velkých situačních karet `G1–G8` s čitelným stavem, účelem, pracovním frame a metodickými odkazy;
4. čtyři metodické zóny:
   - Align & Understand,
   - Strategic Architecture,
   - Strategy & Org Design,
   - Tactical Architecture;
5. dopředné přechody a explicitní návratové smyčky;
6. zarovnané pracovní frames s návodem vlevo nahoře;
7. v každém pracovním frame malý vyplněný vektorový vzor očekávaných artefaktů;
8. odkazy na DDDA kuchařku, metodiku a DDD Starter Modelling Process.

Interní ID `control-center` označuje frame **`00 – Navigace, legenda a stav artefaktů`**. V uživatelské komunikaci se používá jeho viditelný název.

## `00 – Navigace, legenda a stav artefaktů`

Frame musí na první pohled ukázat:

- project name a project ID;
- current stage a current gate;
- gate status;
- decision question a decision ownera;
- chybějící nebo sporné evidence;
- doporučené next actions;
- project/source commit a poslední sync;
- pravidlo, že Git/YAML a human gate decision jsou autorita;
- legendu všech pěti gate stavů.

Povinné managed artefakty mají stabilní placement v tomto frame:

```text
project-charter       → control-center
ddda.current-status   → control-center
ddda.next-actions     → control-center
```

## `01 – DDD Starter journey, gates a iterace`

Přehled není dlouhý pás drobných položek. Používá čtyřsloupcové metodické seskupení a velké stage/gate karty. Každá karta obsahuje:

- gate ID, stage a celý textový stav;
- symbol stavu a počet blockerů;
- účel rozhodnutí;
- viditelný název pracovního frame;
- odkaz na kuchařku a metodiku;
- minimálně čtyři situační vektorové prvky odvozené z referenčního DDD Starter boardu.

Přehled zobrazuje sedm dopředných přechodů a nejméně dvě explicitní návratové smyčky. Nesmí působit jako rigidní waterfall.

## Gate states

| Stav | Symbol | Význam |
|---|---:|---|
| `not_ready` | ⛔ | chybí povinné evidence nebo owner |
| `ready_for_review` | ◉ | mechanicky připraveno k lidskému review |
| `conditional` | △ | lidské rozhodnutí s podmínkou, ownerem a termínem; gate není dokončena |
| `rejected` | ✕ | lidské rozhodnutí gate odmítlo |
| `passed` | ✓ | explicitní lidské schválení |

Rozlišení je založeno na symbolu, plném textovém labelu, významu a barvě. Barva je pouze podpůrná. Minimální velikost fontu legendy je součástí layout contractu.

## Workshop frames

Každý pracovní frame obsahuje dva oddělené bloky:

### Návod vlevo nahoře

- účel;
- jak začít;
- očekávané výstupy;
- povinné pracovní oblasti;
- odkaz na DDDA kuchařku;
- odkaz na metodiku DDDA;
- odkaz na DDD Starter reference.

### Mini-vzor v pracovní části

Mini-vzor není klientský model ani hotové řešení. Ukazuje formu a typy artefaktů, se kterými se pracuje, například:

- Align: problém, rozhodnutí, scope a owner;
- Discover: event, command, policy a hotspot;
- Decompose: subdomény, kandidátní hranice a alternativy;
- Strategize: core/supporting/generic a build/buy/SaaS;
- Connect: upstream/downstream, kontrakt a data owner;
- Organize: tým, ownership a interaction mode;
- Define: Bounded Context Canvas, lifecycle, invariant a quality scenario;
- Code: aggregate, event, ADR, C4 a operability.

## Idempotence a zachování ruční práce

Opakovaný render:

- používá stabilní `miro_item_id` z `miro/miro-map.yaml`;
- aktualizuje existující frames a system items;
- nevytváří nový board;
- nemění množinu journey item ID;
- odstraní pouze zastaralé systémové instrukční prvky původního scaffoldu;
- nemaže unmanaged workshopový obsah;
- při běžném syncu nepřepisuje ručně upravený layout managed artefaktu bez explicitního `--include-layout`.

## Dvojí layout validace

### Deklarativní kontrakt

Před zápisem ověřuje YAML:

- minimální rozměry stage karet a pracovních frames;
- minimální fonty;
- zarovnání a mezery mezi frames;
- G1–G8, čtyři metodické zóny a návratové smyčky;
- guide, metodické odkazy a mini-vzor v každém pracovním frame;
- explicitní placement managed artefaktů;
- zákaz blocking overlay definovaného DDDA.

### Remote Miro kontrakt

Po renderu renderer načte skutečné Miro objekty a ověří:

- skutečnou geometrii a pozice frames;
- nepřekrývání pracovních frames;
- osm journey karet a jejich minimální font;
- situační prvky pro všech osm gates;
- pět čitelných gate-state karet;
- top-left umístění workshop guides;
- minimální počet mini-vzorů;
- čtyři zone headers a iterativní přechody.

Výsledek se ukládá jako `remote_layout_status` a `remote_layout_evidence`.

## Developer-team watermark

Velký nápis `Developer team` není prvek renderovaný DDDA a není dostupný jako Miro board item. Je vlastností Miro Developer team prostředí. Pro finální vizuální review se board vytváří v explicitně zvoleném standardním teamu pomocí `-MiroTeamId`; report pak musí uvést `review_team_selection_status: EXPLICIT_TEAM`.

## Acceptance contract

```text
technical_sync_status: PASS
layout_contract_status: PASS
remote_layout_status: PASS
utf8_status: PASS
human_visual_acceptance_status: PENDING
overall_status: PENDING_HUMAN_REVIEW
```

Technický PASS není vizuální ani metodický human PASS. Finální lidské review se provádí nad novým izolovaným boardem a exact SHA.
