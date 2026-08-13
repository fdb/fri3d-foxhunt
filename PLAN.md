# Vossenjacht — implementatieplan

Fox-hunt badge-app voor Fri3d Camp 2026. Kinderen (6–12) jagen op verstopte
RF-zenders ("beesten") met een directionele antenne, en verzamelen ze in een
Pokédex-achtig boek. UI in het Nederlands, cutesy pixel-art.

Bronnen: `proposal.md` (workshop-abstract), `app.md` (app-brief),
design-handoff van Claude Design (`Foxhunt Schermen.html`).

---

## 1. Waar we nu staan

- **`layout/foxhunt-layout.html`** — de vier schermen, pixel-exact op een
  echte 320×240 grid. Dit is de *bron-of-truth voor de geometrie*: elke maat is
  een geheel getal, niets is fractioneel. Open in een browser, zet "Pixelraster
  8px" aan om te controleren dat alles op de grid valt.
- De rest van dit document is het pad van die layout naar werkende
  MicroPythonOS-software.

**Waarom layout eerst.** Het design-prototype gebruikt CSS `grid`, `1fr`, `46%`,
`scale: 1.9`, `fontSize: 13.5` — een browser rondt die af naar sub-pixels. Een
320×240 framebuffer kan dat niet: elk element moet op een hele pixel landen.
MicroPythonOS tekent met **LVGL**, waar je objecten op absolute pixel-coördinaten
plaatst (`set_pos`, `set_size`). De gesnapte gehele getallen uit de layout-tool
worden dus **letterlijk** je `set_pos`/`set_size`-argumenten. Daarom eerst rekenen,
dan pas porten.

---

## 2. Doel-hardware

| Onderdeel | Detail | Gebruik in de app |
|---|---|---|
| Display | 320×240, 262k kleuren, touch | Alle UI |
| MCU | ESP32-S3, draait **MicroPythonOS** (LVGL) | App-runtime |
| RGB-LED's | strip onderaan (×5 in design) | Warm/koud-meter spiegelt ze |
| D-pad + 4 knoppen | links / rechts | Navigatie (touch-first, knoppen secundair) |
| LoRa-kit | ontvanger + directionele antenne | De eigenlijke jacht (RSSI/richting) |

De "beesten" zijn LoRa-bakens. De badge meet **RSSI** (signaalsterkte) → dat
stuurt zowel de hartslag-snelheid als het aantal brandende LED's/thermo-segmenten.
De directionele antenne geeft *richting* (draaien tot het signaal piekt).

---

## 3. Schermen & navigatie

Vier schermen, één lineaire lus (de "catch loop"):

```
  HOME ──tik beest──▶ HUNT ──signaal gevonden──▶ CODE ──code ok──▶ CAUGHT
   ▲                    │                                              │
   └──────◄ terug ──────┘◄───────────────── VERDER / MIJN BOEK ────────┘
```

| # | Scherm | Functie | Layout-referentie |
|---|---|---|---|
| 1 | **Hoofdscherm** | Pokédex-raster van 12 beesten (wakker=ingekleurd, slapend=silhouet+zz) | `scrHome` |
| 2 | **Jagen** | Silhouet + kloppend hart + bpm + ECG + verticale warm/koud-meter | `scrHunt` |
| 3 | **Code invoeren** | Pincode-toetsenbord + live onthulling van het beest | `scrCode` |
| 4 | **Gevangen!** | Beloning: volledige inkleuring, gouden rand voor legendarisch | `scrCaught` |

---

## 4. Exacte layout (gesnapt op de grid)

Alle coördinaten zijn **logische pixels** in 320×240. Banner = `0,0 → 320×26`.

### Hoofdscherm — Pokédex-raster
- Banner met titel `VOSSENJACHT` + teller `4/12` rechts.
- Raster 4×3, **cel = 74×66**, gap 4, marges links/rechts 6, top 30.
  - kolom-x: `6, 84, 162, 240` · rij-y: `30, 100, 170`
  - (controle: 4·74 + 3·4 + 2·6 = 320 ✓ · 30 + 3·66 + 2·4 = 236, 4px onderaan ✓)
- Per cel: spritezone bovenaan (52px hoog, sprite 16×16 @scale 3 = 48px, gecentreerd),
  naam-strip onderaan (14px). Slapend → silhouet + `zz` rechtsboven + naam `???`.
  Zeldzaam → terra rand-inset, legendarisch → goud rand + sparkle.

### Jagen
- Scan-kaart: `6,34 → 224×172`. Ringen Ø `120/86/54` rond centrum `(112,79)`.
  Silhouet 16×16 @scale 6 = 96px op `(112,79)`. Hart+`96` bpm rechtsboven.
  ECG-strip `6,144 → 212×22` onderin de kaart.
- Thermo-kolom: `x=240`, 5 segmenten **30×16**, gap 4, vanaf y=48. Labels
  `WARM` (boven) / `KOUD` (onder) / `= LEDs`. Spiegelt de fysieke LED-strip.
- Hint-balk: `6,213 → 308×22`, tekst `sneller = dichterbij!`.

### Code invoeren
- Keypad: `6,34 → 186×198`, 3×4 toetsen **58×45**, gap 6.
  Toetsen `1–9, ⌫, 0, ✓` (✓ = groen accent).
  (controle: 3·58 + 2·6 = 186 ✓ · 4·45 + 3·6 = 198 ✓)
- Onthul-kolom: `x=198`, breedte 116. 4 code-bolletjes `20×24` gap 5 (gecentreerd),
  daaronder vul-paneel **92×96** met het beest dat zich "vult" (1/4 per cijfer).

### Gevangen!
- Nacht-bg `#20301c`, sterren (sparkles), spotlight-gloed.
- Gecentreerd: label `★ LEGENDARISCH ★` (y=46), beest-paneel **92×92** met gouden
  dubbele rand (y=66), naam (y=166), ondertitel (y=190), knoppen
  `VERDER` / `MIJN BOEK` (y=210, 78px breed, gap 8).

---

## 5. Beesten-data

Roster van 12 (zie `pixel.jsx` / de layout-tool). Elk beest:

```python
{
    "naam": "Everzwaan",
    "rariteit": "rare",  # norm | rare | leg
    "sh": "bird",  # vorm: fox | owl | deer | bird
    "pal": "cream",  # palet (kleur)
    "code": "7391",  # 4-cijferige code op de fysieke zender
    "beacon_id": 3,  # LoRa-id van het baken
}
```

- **4 herbruikbare 16×16 sprites** (fox/owl/deer/bird) × **8 paletten** = alle 12
  beesten zonder 12 losse afbeeldingen. Recolor = palet-swap (zoals in het design).
- **Status per speler** (opgeslagen, niet in de roster): `gevangen` (bool),
  `wakker` (bool, server/tijd-gestuurd). Legendarisch verschijnt enkel op bepaalde
  momenten.

### Persistentie
MicroPythonOS `Preferences` (key-value). Eén key `gevangen` → lijst van naam/id's.
Het "boek" leest hieruit; vangen voegt toe. Geen netwerk nodig voor de save.

---

## 6. De jacht-mechaniek (RF)

Kern: **RSSI → nabijheid**. De LoRa-ontvanger leest periodiek pakketjes van de
bakens; per baken houden we de recente RSSI bij (gemiddeld over enkele samples
tegen ruis).

```
rssi (dBm)        ─60 ──────── ─90 ──────── ─120
nabijheid          warm                       koud
thermo-segmenten    5    4    3    2    1
LED's (fysiek)      idem (spiegel van thermo)
hartslag-bpm       150  130  110   90   70   (sneller = dichterbij)
```

- **Mapping** is één functie `rssi_to_level(dbm) -> 0..5` + `level_to_bpm(level)`.
  Kalibreer de drempels in het veld (afhankelijk van antenne/terrein).
- **Richting**: directionele antenne → draaien tot RSSI piekt. Geen kompas in de
  UI nodig; de stijgende/dalende meter is de feedback.
- Voor ontwikkeling zonder hardware: een **simulator** die `rssi` afleidt uit een
  nep-afstand, zodat alle schermen testbaar zijn op de desktop/emulator.

---

## 7. MicroPythonOS-implementatie

App-structuur (Android-achtig model):

```
com.enigmeta.foxhunt/
├── MANIFEST.JSON               # name, fullname, version, activities[]
├── assets/
│   ├── foxhunt.py         # Activity-subclass, onCreate() → setContentView
│   ├── screens.py              # 4 schermen, bouwt LVGL-objecten op de coords van §4
│   ├── sprites.py              # SH-shapes, PALS-paletten, roster
│   ├── pixel.py                # sprite → lv.canvas (pixel-blit met palet)
│   └── hunt.py                 # RSSI-lezen, mapping, simulator
└── icon_64x64.png
```

- **UI**: elk scherm = een `lv.obj()` root; kinderen met absolute `set_pos(x,y)` /
  `set_size(w,h)` uit §4. `Activity.onCreate()` → `self.setContentView(screen)`.
- **Sprites**: `lv.canvas` met een buffer; teken elke 16×16-cel pixel-voor-pixel
  met de palet-kleur, schaal via een grotere canvas (nearest-neighbour) of door
  per "pixel" een `rect` van N×N te tekenen. Eén `draw_sprite(canvas, shape, pal,
  scale, silhouette)`-helper dekt alle schermen.
- **Touch**: LVGL-events op de keypad-knoppen en de beest-cellen. Hardware-knoppen
  via `InputManager` als secundaire navigatie (optioneel voor v1).
- **Animatie**: hart-`pxbeat` en ECG-scroll via een LVGL-timer; bpm = `f(rssi)`.

---

## 8. Milestones

1. **Layout vastleggen** ✅ — `layout/foxhunt-layout.html`, gesnapt op de grid.
2. **Sprite-pipeline** — `draw_sprite` in MicroPython/LVGL; render het roster op één
   testscherm. *Verify:* alle 12 beesten herkenbaar, scherp, op de juiste plek.
3. **Statische schermen** — de vier schermen exact volgens §4 (nog zonder logica).
   *Verify:* side-by-side met de HTML-layout, pixel-identiek.
4. **Navigatie + state** — de catch-lus, `Preferences`-save, boek-teller. *Verify:*
   beest tikken → jagen → code → gevangen → terug; vangst blijft na herstart.
5. **RF-integratie** — LoRa-RSSI → thermo/LED's/hartslag, met simulator-fallback.
   *Verify:* meter loopt mee met afstand in het veld; code op zender ontgrendelt.
6. **Polish** — legendarisch-timing, geluid/LED-feedback bij vangst, rand-cases
   (alles gevangen, geen signaal).

---

## 9. Open punten (bevestigen)

- **LED-aantal**: design gaat uit van **5** segmenten. Klopt dat met de fysieke
  strip op de 2026-badge? (Pas `total` in de thermo aan indien anders.)
- **Codebron**: staat de 4-cijferige code fysiek op de zender (sticker) of wordt
  hij over LoRa meegestuurd? Bepaalt of we hem moeten valideren tegen de roster of
  tegen een ontvangen waarde.
- **Wakker/slapend & legendarisch-timing**: lokaal (klok op de badge) of centraal
  aangestuurd? v1 kan prima met een vaste set + tijdvensters op de badge zelf.
- **Sprites**: 4 herbruikbare vormen (huidige aanpak) of 12 unieke 16×16-sprites
  voor de finale look? Eerste is sneller; tweede is mooier.
