# Foxhunt 🦊

A "fox hunting" (ARDF) game for the **Fri3d Camp 2026 badge**. Kids hunt hidden
LoRa beacons ("beasts") with a directional antenna and collect them in a
Pokédex-style book. Dutch UI, cutesy pixel-art. Runs on the badge
(ESP32-S3 / MicroPythonOS / LVGL) **and** on the macOS SDL emulator from the
same source.

## Layout

```
be.fri3d.foxhunt/      # the MicroPythonOS app (the thing that ships)
  META-INF/MANIFEST.JSON
  assets/                    # all the Python; assets/ is on sys.path at runtime
    foxhunt.py          # entry: HomeActivity (the "boek" grid)
    screen_hunt.py           # classic ARDF: silhouette + heart/bpm + 5 LEDs
    screen_code.py           # PIN keypad + reveal
    screen_win.py            # "Gevangen!" payoff -> back to home
    creatures.py             # roster data (no LVGL)
    art.py                   # placeholder pixel sprites (the art swap point)
    ui.py                    # colours, fonts, positioned-widget builders, focus
    fox_radio.py             # FoxRadio interface + FakeFoxRadio sim (LoRa stub)
    leds.py                  # 5 NeoPixels hot/cold (no-op on desktop)
    sound.py                 # buzzer RTTTL jingles (no-op on desktop)
    store.py                 # caught-set persistence (SharedPreferences)
  res/mipmap-mdpi/icon_64x64.png
layout/foxhunt-layout.html   # pixel-exact 320x240 layout spec (source of truth)
PLAN.md                           # architecture + decisions
proposal.md / app.md              # original workshop brief
```

## Run on the desktop emulator

The app is symlinked into a local MicroPythonOS checkout's `apps/`. From that
checkout:

```bash
cd /Users/fdb/Source/MicroPythonOS
./scripts/run_desktop.sh be.fri3d.foxhunt
```

Mouse = touch · arrow keys = focus nav · Esc = back. The hunt "warms up" on its
own (FakeFoxRadio) until it auto-advances to the code screen. Codes are in
`creatures.py` (e.g. Everzwaan = `7391`).

## Same source, both targets

The app never touches a pin. The MicroPythonOS **board layer**
(`board/fri3d_2026.py` on the badge, `board/linux.py` on desktop) sets up the
320×240 display, input, LEDs and audio. Hardware that only exists on the badge
(`mpos.lights`, the buzzer audio output) is gated: we call it, check the return,
and fall back (on-screen LED mirror, silent audio) on desktop.

## Status / next

- ✅ Full catch loop: home → hunt → code → win, with persistence.
- ⏳ Pixel font (Pixelify Sans, baked via `lv_font_conv`) — built-in Montserrat for now.
- ⏳ Real creature art (PNGs) — procedural placeholders for now.
- ⏳ Hunt-screen polish (scrolling ECG, scale-pulse heartbeat).
