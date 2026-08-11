# Vossenjacht — working notes

## Commit discipline
- **Commit after every meaningful, working change** — a fix or feature that builds
  and is verified on the emulator. Don't let verified work pile up uncommitted, and
  don't batch unrelated changes into one giant commit. Each commit should be one
  coherent step with a clear message.

## Run & verify (same source, both targets)
The identical app runs on the Fri3d 2026 badge and the macOS SDL emulator; the
board layer handles the hardware differences.
- **Two MicroPythonOS checkouts exist, and both are load-bearing.** They are not
  copies of each other. `~/MicroPythonOS` is the small prebuilt package
  (`internal_filesystem`, `lvgl_micropython`, `scripts` — no git) that
  `run_on_mac.sh` downloads by itself and treats as `MPOS_DIR`; it holds the
  emulator's save. `~/Source/MicroPythonOS` is the full clone, kept for exactly
  one thing the package lacks — the **mpy-cross** that `deploy_to_badge.sh` and
  `build_mpk.sh` hardcode, which must come from the same checkout as the
  firmware so the bytecode versions match. Deleting the package costs a
  re-download; deleting the clone breaks every badge deploy.
- The app is symlinked into BOTH checkouts' `internal_filesystem/apps/`, so
  both can launch — which is the trap, because their `internal_filesystem/`
  trees are separate. Only the package has `data/com.enigmeta.foxhunt`.
- Run: `scripts/run_on_mac.sh` (add `--lora` for the jager persona). Use it and
  not a bare `run_desktop.sh`: it is the only path that points the save at the
  right persona slot before launching. A run out of `~/Source/MicroPythonOS`
  finds no save and no persona, so it replays onboarding and registers the
  default fake MAC against prod.
- Headless smoke test: run it redirected to a log file and grep the log for
  `Traceback` / `Error`. Home rendering with no traceback means imports + that
  screen build cleanly (other screens build when navigated to).
- Full UI verification: pipe commands into the emulator's stdin REPL to
  simulate taps/drags/focus and capture screenshots — see
  `docs/emulator-testing.md`. Prefer this over "it should work" for any
  change with visible or interactive behaviour.
- **Kill every emulator you start.** The emulator does not exit on stdin EOF,
  and a backgrounded or crashed run leaves it alive for hours. Stale instances
  are not harmless: each one holds the app's data symlink, so the next
  `run_on_mac.sh --lora` swaps the persona under a still-running verzamelaar,
  and a screenshot can come from the wrong process. Two processes per launch —
  the SDL binary and the shell that started it. Do this at the END of every
  task that ran the emulator, not only when a run misbehaves. Two traps, both
  measured rather than guessed:
  - **SIGTERM is often not enough.** A plain `pkill -f lvgl_micropy` regularly
    leaves the binary running with its wrapper already dead. Always verify
    (`pgrep -fl lvgl_micropy_macOS`) and force what survives: `kill -9 <pid>`.
    An emulator whose `ps -o ppid` is **1** is a true orphan — its launcher is
    gone and nothing will ever clean it up.
  - **`pkill -f` is machine-wide and matches whole command lines, so it is not
    safe to fire blindly.** More than one session runs here, and a driver
    script (`docs/emulator-testing.md`, the gcprobe recipes) owns its emulator
    and kills it itself — a blanket pkill destroys an in-flight measurement.
    It also matches any *other* process whose command line merely contains the
    pattern: a monitoring loop watching for `lvgl_micropy` kills itself. Check
    `pgrep -fl` first, kill the PIDs you started, and reach for a pattern only
    when the survivors are confirmed parentless.
- **The emulator's profile is throwaway.** Whatever sits in
  `<MicroPythonOS>/internal_filesystem/prefs/com.enigmeta.foxhunt/config.json` is
  test data — no real account, no real catches. Overwrite it with `{}` to
  replay first-run onboarding, or seed a profile to skip it, without asking.
  Only the badge and the server hold anything worth keeping.
  **The ACCOUNT it registers is not throwaway.** `registrar.badge_id` falls back
  to one fixed fake MAC on desktop, and `BASE_URL` points at prod, so every
  desktop run registers as the same permanent player on the real server. Deleting
  the local config does not touch it: the next onboarding meets its own account
  as "BADGE AL BEKEND", correctly, forever. Clear the server side too —
  `scripts/delete_account.sh --emulator`.
- **The jager half of the game needs a faked antenna.** Desktop has no radio,
  so `registrar.has_lora()` is false and instellingen -> WORD JAGER answers
  "geen antenne gevonden" — a `hunter_id` can never be minted.
  `scripts/run_on_mac.sh --lora` fakes one, through `FOXHUNT_FAKE_LORA` (the
  emulator is the unix MicroPython port, which has `os.getenv`; the badge's
  ESP32 port does not, so these overrides cannot exist on hardware). A normal
  `run_on_mac.sh` launch explicitly clears that internal override: only the
  `--lora` persona may pass the emulator's antenna check.
  It also swaps in a SECOND fake MAC via `FOXHUNT_BADGE_ID`, because `badge_id`
  is the account key: on one MAC the jager and the verzamelaar would be one
  account, and the second registration would meet the first as "BADGE AL
  BEKEND". That second account is exactly as real and permanent as the first —
  `scripts/delete_account.sh --emulator-lora` clears it.
  Each persona also keeps its own LOCAL save: `run_on_mac.sh` makes the app's
  data dir a symlink into a per-persona slot (`com.enigmeta.foxhunt.default` /
  `.lora`) before every launch. Switching persona never touches the other's
  save, and a persona with an empty slot replays onboarding by itself — which
  is how the jager's first run reaches registration. `clear_app_data.sh`
  sweeps the slots too.

## Deploying to the badge
`scripts/deploy_to_badge.sh [--start]` pushes the app over USB — ~8s when
nothing changed, ~15-20s for a typical change. Six things it does that are
not obvious, each because copying the files is not enough:
- **It refuses to silently replace another checkout's build.** More than one
  clone of this repo exists, and each clone's script would truthfully report
  "up to date" against its own tree while the developer believes they are
  testing the other one. Every install stamps `#src <dir> <commit> <dirty>`
  into the manifest; a deploy from a different directory than the badge's
  stamp refuses without `--force`, and every run prints both identities.
  A dirty working tree also refuses without `--force`: the settings screen
  shows `version @ commit` from that stamp (`screen_settings._build_info`),
  and a dirty deploy would make that sha a lie ('dev' when running from
  source, `*` after the sha when force-deployed dirty).
- **It ships `.mpy` bytecode, not source.** The badge spends ~2s of every
  cold start compiling 5k lines of Python; the in-tree mpy-cross (same
  checkout as the firmware, so the bytecode versions match) does it once at
  deploy time instead. `-march=xtensawin` so viper modules (`art_fast.py`)
  carry native code; `-O2`, not the OS's `-O3`, because O3's only extra
  saving is the line-number table and badge tracebacks need it. The emulator
  is untouched — its symlink runs the `.py` source directly.
- **It rides mpremote's raw REPL, never the aioREPL controller.** The aioREPL
  (`mpos_controller.py`) echoes every pasted byte back while LVGL starves the
  reader — ~115 B/s measured, and a payload past ~2.5KB stalls its flow
  control and dies on a write timeout. Raw REPL has no echo: the same state
  walk costs 16s through the controller and under 4 directly. The OS keeps
  running across raw-REPL execs (same interpreter — AppManager and
  `sys.modules` included), so the controller's emulator/testing workflow is
  untouched; it is just the wrong transport for deploy traffic. Relatedly:
  the controller's `read_until` must accept CRLF sentinel endings (fixed in
  the MicroPythonOS checkout) — before that, every serial exec silently sat
  out a 30s timeout and *then* returned the right answer, which made deploys
  7 minutes without a single error anywhere.
- **It trusts a shipped manifest instead of re-hashing.** Every install lands
  `.deploy.sha` ("sha16 size path" per line) inside the app dir; the next
  deploy stat-walks the tree and trusts the manifest only if the paths and
  every size match exactly, else falls back to hashing every file
  (~0.28s/file of `open()` overhead). Every way the manifest can lie is
  covered by that check or by placement: a truncated install (size differs),
  a lingering orphan (path extra), a store install (`rmtree` takes the
  manifest with it). Wrong → one slow hash pass, then it self-heals.
  The install itself is verified the same way, on-badge, before success is
  reported: path set + size against the just-pushed manifest, plus a full
  SHA-256 of exactly the files this run copied — because `fs cp` exiting 0
  is a transport claim, not proof the flash holds the bytes (a torn write
  once left a 0-byte `.mpy` behind a clean exit and a count-only "verify").
  On mismatch the badge drops its own manifest and the deploy fails loudly.
- **It copies only what differs, and deletes only what the source dropped.**
  `mpremote fs cp -r` merges, so a delta tree updates exactly the changed
  files; orphans are deleted explicitly (nothing on this path ever deletes
  on its own — a renamed module or stray `__pycache__` stays forever until
  LittleFS is full and installs start truncating). It returns the badge to
  the launcher first, so no live activity holds the code being overwritten.
  Save data is unaffected either way; it lives in `data/com.enigmeta.foxhunt/`,
  not in the app dir.
- **It drops the app's modules from `sys.modules`.** MicroPythonOS evicts only
  the *entrypoint* module between launches (`AppManager.execute_script`), so
  without this a relaunch runs the new `foxhunt.py` against the previous run's
  cached `screen_*` — new caller, stale callee. That mismatch is the exception
  you get from restarting a freshly-deployed app.

Every phase prints `[t+Ns]` elapsed time. Diagnose any slowdown against those
numbers first — the pipeline's costs live where nothing errors (handshakes,
echo, on-badge walks), so a regression is otherwise invisible.

The file count still matters twice over: LittleFS bills a whole 4 KB block per
file, and each file costs ~0.28s whenever the manifest is distrusted and the
hash fallback runs. That is why the 40+ tiny sprite PNGs were folded into one
`assets/sprites.bin` atlas (see Conventions → Artwork) — reclaiming ~96 KB of
blocks on device and shrinking the worst-case hash pass.

End users never touch this path. The app store streams a `.mpk` over WiFi
straight into `AppManager.download_and_install_package`, which unzips it as it
downloads — seconds, not minutes. It `shutil.rmtree`s the app dir first, so a
store install is a clean replace and needs none of the above.

## Talking to the badge over serial (ad-hoc, not deploy)
`deploy_to_badge.sh` owns the raw REPL carefully. Ad-hoc `mpremote` for
measurement wedges the badge easily, and a wedge only clears with a physical
power-cycle. A wedge shows as `could not enter raw repl` or `response:
b'R\x01'`; keep pushing and LittleFS throws `OSError: (-258,
'ESP_ERR_INVALID_ARG')` from `shared_preferences`, which also needs a
power-cycle. `machine.reset()` and `mpremote reset` do not reliably clear
either. Rules:
- **One serial client at a time.** Never run two `mpremote` commands at once.
- **Never poll the badge in a loop.** An `until ... mpremote ...; do` loop opens
  a fresh raw REPL each pass and wedges fast. Wait on-device in one command, or
  wait host-side without touching the port, then run one command.
- **Stop background pollers before the next command.** A `run_in_background` or
  `Monitor` that connects to the badge holds the port; `TaskStop` it first.
- **When wedged, stop and ask for a power-cycle.** Retrying deepens the wedge.
- **A blocking `exec` starves the OS loop, so it cannot start or drive the app.**
  `AppManager.start_app` and `startActivity` run on the asyncio/LVGL loop; an
  `exec` that then calls `time.sleep` blocks that loop, so the app never starts
  and `screens_care` never enters `sys.modules`. Use a blocking self-contained
  script (`fs cp` it, then one `exec "import it"`, all sleeps on-device) ONLY
  for things with no live foreground app: idle-heap rate, a pure function's cost.
- **To measure a RUNNING game, a human drives it.** The player opens the game
  through the UI and starts a round; only then does a short, non-blocking probe
  attach — an `lv.timer` sampler (`gcprobe.start`) created by one quick `exec`
  that returns at once and samples in the background, read back later by a second
  quick `exec`. Never a blocking sleep-loop against a live game.
- **When the REPL keeps wedging, skip serial entirely: use an on-screen HUD.**
  Draw the heap stats in a corner behind the debug cheat, deploy, and read the
  numbers off the glass while playing.
- **`gc.mem_free()` and `gc.mem_alloc()` WALK THE WHOLE HEAP** — O(heap size),
  several ms on the badge's multi-MB PSRAM. Sampling either one per game tick
  (or an lv.timer faster than ~1 Hz) is itself a per-frame stall that halves the
  frame rate AND deflates the allocation it is trying to measure. Sample at most
  ~1 Hz. This distorts any probe that reads them in a hot loop; a HUD must
  sample every N ticks, never every tick.

## Frame pacing — why a game stutters
A moving game screen is judged by what the DISPLAY shows per frame, never by
whether the tick fired on time. Both of the stutters found so far are invisible
to "is anything slow?" measurement — no code was slow and nothing blocked.
- **The tick must match the display refresh.** LVGL redraws on its own timer
  (`LV_DEF_REFR_PERIOD`, 33 ms) and 33 has no rhythm in common with a 50 ms
  `TICK_MS`: frames land between ticks, repeat the last position and then move
  double. `GameActivity.onResume` therefore sets the refresh period to its own
  `TICK_MS` and `onPause` hands it back — the period is the display's, not a
  game's. Keep any new animated screen on that rule, and never leave the OS
  running at a game's cadence.
- **Measure the frame, not the tick.** Sample the moving thing at
  `lv.EVENT.REFR_START` and print the per-frame delta. `-4 -4 0 -4 0 -4` is a
  stutter; `-4 -4 -4 -4` is not. A 1 ms `lv.timer` heartbeat is the companion
  test: a gap between beats IS a stall of the whole LVGL thread (render, timer,
  asyncio holding the GIL, gc), and `gc.mem_free()` at each beat tells a gc
  pause apart from the rest. `tools/gcprobe.py` does both — `pacing()` for the
  frame, `start()`/`report()` for the allocation, and its header for the traps
  in each (the sampler is not free, and emulator bytes are not badge bytes).
- **A second-long freeze on a loose ~45 s cycle is the garbage collector.** The
  badge's heap is megabytes of octal PSRAM, so one mark-sweep costs about a
  second, and MicroPython runs one when the heap fills — which is why it lands
  mid-round and never at a fixed point in it. Nothing on the badge runs on that
  cadence: BOTH update services (`com.micropythonos.osupdate`,
  `com.micropythonos.appstore`) check once every **24 h**, connectivity every
  8 s, the status bar between 1 and 15 s. `GameActivity._collect()` therefore
  forces the collect where a game is not animating: before `onCreate` builds
  anything, and — via `_collect_after_render()` — once the game-over card is on
  the glass, so the second is spent while the player reads their score. That
  second one CANNOT be a plain call at the end of `game_over()`: building the
  card only creates widgets, LVGL does not draw until its next refresh, so an
  inline collect holds the card back and the freeze lands between the crash and
  "AUW!". It is a one-shot `lv.timer` at twice the refresh period, cancelled in
  `onPause` and taken inline by `_again()` (a fast NOG EEN KEER would otherwise
  drop it into the new round). Keep new game code allocating as little as
  possible per tick, and keep those collect points.
- **A tick must not CREATE anything.** That is the whole rule, and the two
  halves of it are `screens_care._FP` and `_SpritePool`. Measured with
  `tools/gcprobe.py` (read its header before trusting a number): VANGEN's
  `step()` went 593.5 → 22.0 B/tick and VLIEGEN's 213.4 → 3.5, with the spawn
  tick's peak down from 11 KB to 416 B.
  - **Fixed point, in hundredths.** MicroPython boxes every float on the heap
    (16 B on the badge, 32 on desktop), so `y += vy` is an allocation per
    object per tick. Everything that moves is `px * _FP`; convert once, at the
    `set_x`. Hundredths and not a shift because these numbers were tuned as
    decimals and 1/100 holds all of them exactly — sixteenths already cost the
    sky its 1.6 px cloud (it became 1.625) and would have made 0.9 gravity
    0.875. `// 100` is one machine divide; twenty times a second it is free.
    The unit error does not raise, it just makes something behave: a probe
    comparing hundredths against pixels pinned VANGEN's beast to the wall for
    a whole run and still printed plausible numbers.
  - **Fixed buffers.** `art.sprite_buf` is the pixel work (a 24x24 sprite is
    2.3 KB of bytearray plus a line buffer per row) and `art.canvas_for` is
    the widget. Bake every buffer a round can show in `build()`, then hand a
    pool of canvases around. A pool must be sized as an UPPER BOUND — running
    dry drops a spawn, which is a difficulty change, not a glitch — and its
    failure mode is a ghost widget, so verify it (`gcprobe.check_vlieg`).
  - **Also gone from the tick:** `for o in self.obs[:]`, whose only job was to
    allow removal while iterating. Walk backwards by index instead.
- **Struct-of-arrays is NOT worth it here, though it looks like it should be.**
  `array('i')` in place of the per-item dicts saved 2.6 B/tick, measured.
  MicroPython's dicts and small-int arithmetic already allocate nothing —
  `d["x"] -= 3` is 0 B — so flattening state optimises something that was
  never costing anything, and costs readability. Optimise what gets CREATED.
- **The game is a minority of the allocation, so know the floor before you
  start.** An idle emulator allocates ~11 KB/s with the app on screen and
  nothing playing; VLIEGEN's whole `step()` was ~4 KB/s of that even BEFORE
  this work. Emptying a tick moves the collector's interval by a fraction, and
  it is worth doing because the interval only has to clear the length of a
  round — a threshold, not a proportion. Do not expect it to scale.
- **Do not blame background work without measuring it.** `sound.play` is 0 ms
  (the RTTTL player is async), `store` writes are already out of the tick
  (`bank_treats`), home's poll and outbox flush stop on pause, and the OS
  status-bar timers never showed up in a gap.
- **The two targets have opposite render costs, so tune against the right one.**
  The emulator's `sdl_tx_color` uploads the WHOLE texture and presents once per
  invalidated region (costs quantise to ~17 ms — vsync), so it bills the NUMBER
  of scattered movers. The badge renders into a 28800-byte partial buffer and
  DMAs over SPI, so it bills AREA. An emulator win is not automatically a badge
  win.
- **The emulator's LVGL clock runs ~1.79x fast** — a 1000 ms `lv.timer` fires
  after ~560 ms of real time. Every game therefore plays about 1.8x too quick on
  desktop. Judge game FEEL on the badge; the emulator is for correctness.

## Formatting
- `scripts/format.sh` formats all Python (Ruff via `uvx`) and JSON (stdlib
  `json.tool` via `uv`) — both Astral-runner-based, nothing installed into the
  project. `scripts/format.sh --check` reports unformatted files and exits 1 (CI).

## Glossary — terminology
The UI is Dutch and the code is English. The player modes have several accepted,
interchangeable names in discussion: **LoRa mode**, **LoRa players**, **hunters**,
and **jagers** all refer to players using a LoRa antenna; **WiFi mode**, **WiFi
players**, **collectors**, **gatherers**, and **verzamelaars** all refer to players
without LoRa. In code and UI, prefer the canonical terms in the table below so
identifiers and player-facing copy remain consistent.

| Code (English) | UI (Dutch) | What it is |
| --- | --- | --- |
| **companion** | **maatje** | The player's own avatar: a head + stacked accessories + a backdrop, built at registration. `companion.py`, `screen_companion.py`, `CompanionActivity`. |
| **creature** | **beest** | One of the huntable animals in the roster (`creatures.py`). Never a "companion". |
| **fox** | **vos** | A physical LoRa transmitter hidden in the field. The creature is what you *get*; the fox is what you *find*. |
| **hunter** | **jager** | The player, when playing with a LoRa antenna: has a minted `hunter_id` (1-9999), shown as "JGR-0042". |
| **collector** | **verzamelaar** | The player, when playing WiFi-only (no antenna): `hunter_id` is None. The UI shows the mode word where a jager would see their id. |
| **pet state** | — | The per-creature care stats — bond, energy (`pet.py`, `store.beast_state`). Belongs to a creature, never to the companion. |
| **shortcode** | — | The companion serialized for the wire: `H1A003C1` (`companion.encode` / `.decode`). |

Retired words: **mascot** (say companion), **mascotte** (say maatje) — except
as a citation of the original design bundle file `mascotte.jsx`.

## Where things live
Screens are merged into four 1.2-1.7k-line flow modules (see Size budget), so a
filename never names a screen. Find the symbol below and grep for it; don't skim
a whole module. Badge paths are under `com.enigmeta.foxhunt/assets/`.

**Screens** — every one is an `Activity`; the Dutch word is what the UI says.

| Screen / thing the player sees | Module → symbol |
| --- | --- |
| welkom banner, herstel-link | `screens_onboarding` → `WelcomeActivity` |
| uitleg (jager vs verzamelaar) | `screens_onboarding` → `UitlegActivity` |
| naam typen (keyboard) | `screens_onboarding` → `RegisterActivity` |
| maatje bouwen (kop/accessoires/achtergrond) | `screens_onboarding` → `CompanionActivity` |
| inschrijven, "BADGE AL BEKEND" fork, resync | `screens_onboarding` → `RegSendActivity` (`_build_exists`) |
| herstel van de server | `screens_onboarding` → `RestoreActivity` |
| startbeest | `screens_onboarding` → `StarterActivity` |
| home (kaarten, buren, bezoeker-poll) | `screens_system` → `HomeActivity` |
| profiel, score | `screens_system` → `ProfileActivity` |
| instellingen (schakelaars, LED/geluid, WORD JAGER, `version @ commit`) | `screens_system` → `SettingsActivity`, `_Toggle`, `_build_info` |
| debug (5× tik op badge-id) | `screens_system` → `DebugActivity` |
| ALLES WISSEN | `screens_system` → `WipeActivity` |
| beest (stats, acties) | `screens_care` → `BeastActivity` |
| dossier | `screens_care` → `DossierActivity` |
| voeren | `screens_care` → `FeedActivity` |
| school (spel kiezen, favoriet) | `screens_care` → `SchoolActivity`, `GAMES`, `favourite_game` |
| **VLIEGEN** | `screens_care` → `VliegActivity` |
| **VANGEN** | `screens_care` → `VangActivity` |
| **DANSEN** | `screens_care` → `DansActivity` |
| shared game scaffolding (tick loop, scenery, treats, fixed point, widget pool) | `screens_care` → `GameActivity`, `_scenery`, `_FP`, `_SpritePool` |
| boekje (roster-grid) | `screens_care` → `BoekjeActivity` |
| jacht / kompas | `screens_hunt` → `HuntActivity` |
| viercijferige code intypen | `screens_hunt` → `CodeActivity` |
| gevangen! (win + vuurwerk) | `screens_hunt` → `WinActivity` |
| snuffelen (badge↔badge), vonk-payoff | `screens_hunt` → `SnuffelActivity`, `VonkActivity` |
| plukken (wifi-BSSID) | `screens_hunt` → `PlukActivity` |
| bezoeker | `screens_hunt` → `VisitorActivity` |

**Logic, art, radios** — one concern per file.

| Concern | File |
| --- | --- |
| app entry: onboarding-vs-home routing, launch resync | `foxhunt.py` (`FoxhuntActivity`) |
| ALL persistence — profiel, vangsten, voorraad, vlaggen, outbox, bezoekers, vonk-log, pluk-fase, debug-ontgrendeling | `store.py` |
| care math (bond/energy/hunger, decay, feed, play) — pure, no LVGL | `pet.py` |
| roster: namen, tiers, art-keys, starter | `creatures.py` |
| maatje: shortcode encode/decode, `HEADS`/`ACCS`/`BGS`, `draw` | `companion.py` |
| sprites, atlas, icons, `creature_panel`, animatie | `art.py` (+ generated `atlas.py`, viper blit `art_fast.py`) |
| kleuren, fonts, `box`/`panel`/`row`/`banner`/`seg_bar`, focus | `ui.py` |
| server HTTP, `badge_id`, `has_lora`, `adopt`, `resync`, outbox flush | `registrar.py` |
| geluid **and** LEDs | `sound.py` (call sites do `import sound as leds`) |
| ESP-NOW peer discovery (snuffel transport) | `snuffel_link.py` |
| wifi scan (pluk transport) | `pluk_radio.py` |
| LoRa vos-ontvangst — stub | `fox_radio.py` |
| vuurwerk / stardust animaties | `celebrate.py` |

**Server** (`server/src/`): `routes/auth.ts` = `/api/v1/auth/{register,starter,hunter,user}`;
`routes/player.ts` = `/api/v1/player/{found,snuffel,pluk,visitor}`; `routes/pages.tsx` =
`/`, `/scores`, `/debug/*` (rendered via `components/{Layout,Home,Companion}.tsx`);
`lib/` = badge ports and helpers (`creatures.ts`, `companion.ts`, `companion-art.ts`
generated, `starter.ts`, `events.ts`, `validate.ts`).

**Not where you'd guess:** there is no `sync.py` (in `registrar.py`), no `leds.py`
(in `sound.py`), no `debug_unlock.py` (in `store.py`), no `visitors.py` (logic in
`store.py`, screen in `screens_hunt`), and no per-screen file at all.

## Size budget
The badge's whole user filesystem is a 7 MiB LittleFS partition, and a factory
badge arrives with it nearly full: `roms/` alone holds ~3.8 MB and the OS the
bulk of the rest. This app must fit in the scraps, so its flash footprint is a
budget, not an afterthought. Two costs, and the second is the sneaky one:
- **Payload**: what the bytes weigh. `.mpy` bytecode is the shipped form
  (USB deploy always; the store `.mpk` via `scripts/build_mpk.sh`) — comments
  and docstrings cost nothing on the badge, so never strip them for size.
- **Blocks**: LittleFS bills 4 KB per FILE, so a 250-byte module costs the
  same flash as a 4 KB one. This is why the sprites live in one atlas, and
  why the screens live in four flow modules instead of 24 files:
  `screens_onboarding` (welcome→…→starter + restore), `screens_care`
  (beast/dossier/feed/school/games/boekje), `screens_hunt`
  (hunt/code/win/snuffel/pluk/visitor), `screens_system`
  (home/profiel/instellingen/debug/wipe) — plus the folds of sync→registrar,
  debug_unlock→store and leds→sound (`import sound as leds` at call sites).
**Refactors must keep this shape.** Do not re-split a flow module into
per-screen files, and put a new screen INSIDE the flow module it belongs to —
a new top-level file needs to justify its block. Two traps inside a merged
module: section order is dependency order where module-level tables reference
classes (screens_care: games before school), and repeated imports between
sections are fine — but a bare name shared by two sections is not
(screens_hunt: fox_radio owns `RADIO`, the pluk section says
`pluk_radio.RADIO`). Art stays cheap by construction: the atlas is 8-bit
indexed against one palette, mirrored PNGs are palettized to what the RGB565
panel can show (both enforced by `bake_sprites.sh`). Current shape: 26 files
(20 modules + assets), ~205 KB on flash; compare block counts before and
after when touching the file layout.

## Conventions
- **One SharedPreferences instance, one editor, per write path.** The mpos
  `SharedPreferences` snapshots the whole config file per instance, and
  `Editor.commit()` writes that whole snapshot back. Two instances
  interleaving writes lose the earlier one: `do_feed` once decremented the
  pantry through a fresh instance and then committed beast state through a
  stale one — every feed silently refunded the hapje ("food never runs
  out"). Helpers that write via their own instance (`add_food`,
  `take_food`) may only be called LAST, after every other instance's
  commit; anything else must fold its writes into one editor.
- **`telemetry.py`: nothing to see here.** It is deliberately misnamed. Leave
  it alone — don't rename it, don't "fix" it, don't flag it in reviews.
- **Never touch pins.** Use `mpos.*` managers (`mpos.lights`, `AudioManager`) and
  gate on availability — desktop has no LEDs and no buzzer output, so those calls
  must no-op and fall back (e.g. the on-screen LED mirror).
- **Artwork:** PNGs (with their Aseprite sources) live in `artwork/<folder>/` —
  `animals/` are the huntable creatures (16×16 RGBA), `companions/` the maatje's
  heads and accessories (16×16 RGBA, one PNG per Aseprite layer, filename ==
  the id in `companion.py`), `title-screen/` the 320×120 welcome banner.
  `scripts/bake_sprites.sh` packs every 16px-tall PNG into ONE atlas —
  `assets/sprites.bin` (16×16 frames of 8-bit palette indices, 256 B each,
  against the `PALETTE` in the generated index `assets/atlas.py`; `art.py`
  expands to BGRA on first read and caches) — because on LittleFS forty tiny
  files cost 4 KB and ~0.28s of deploy each; other art (the title banner) is
  mirrored as PNG, palettized to the colours the RGB565 panel can show.
  Sprites keep their artwork-relative path as atlas key (`"animals/vos.png"`).
  Re-run the script after changing artwork; `--check` reports drift (CI). Both
  sides are committed, and everything the script generates belongs to it.
  A creature opts into real art with an `"img"` field in `creatures.py` — the
  bare filename, `art.py` owns the folder; without it, it falls back to the
  procedural placeholder shape.
- **Animated creatures:** a sprite that is a SHEET (width N×16, frames left to
  right, like `glitch_vos.png` at 80×16) bakes into N atlas frames
  automatically. Set `"anim": True` on the creature to play them — animation
  runs only where the payoff is honest (win/celebrate screens and the beast
  page pass `animate=True` to `art.creature_panel`); silhouettes, veils and
  grids hold frame 0. Playback is an `lv.anim_t` (`art.animate_sprite`), which
  LVGL kills with the widget — never an `lv.timer`, which would outlive it.
- **Never let LVGL scale a sprite.** Its software transform steps the source
  edge-to-edge in `(dest_w - 1)` increments (`lv_draw_sw_transform.c`), so any
  draw-time scaling — `set_scale`, inner-align STRETCH on a mismatched size —
  renders half-width edge pixels and stray double-width columns even at exact
  integer factors, on badge and desktop alike. `art.sprite_img` pre-scales by
  integer pixel replication instead, so the buffer already matches the widget
  and the transform never runs; keep every sprite on that path.
- **Don't name an asset dir after an imported module** — a folder `creatures/`
  shadows `creatures.py` on import. That's why creature art keys live under
  `animals/` and companion art under `companions/` (plural). The failure is
  silent and confusing: the import succeeds, then the module has no
  attributes.
- **Fonts** are 1-bit bitmap fonts in `assets/fonts/*.bin`, loaded with
  `lv.binfont_create`. Edit the source `.bdf` in `tools/bitmap_fonts/` (editor)
  and re-bake the deployed `.bin` with `scripts/bake_fonts.sh`
  (`--check` reports drift) — see `docs/fonts.md`. Coverage is ASCII 32–126
  ONLY: no `► ✓ · — é`. Substitute ASCII (`>`, `-`, "wel") or draw a pixel
  icon in `art.ICONS` (that's what the checkmark/cross/antenna icons are).
- **Back navigation** is the system left-edge swipe / Esc / joystick — apps don't
  draw their own back button.
- **LVGL native widgets have no `__dict__`** — you can't set Python attributes on
  them; keep per-widget state in the Activity.

## Cloud server
Base URL: **https://foxhunt.enigmeta.workers.dev/** — the badge's `registrar.py`
talks to `/api/v1/auth/*` there.

- **Test against a local worker, not prod.** `cd server && npm run dev` (plus
  `npm run db:init:local` once), then point the app at it from the emulator
  REPL before touching a screen:
  `import sys; sys.modules["registrar"].BASE_URL = "http://localhost:8787"`.
  The transport is drivable straight from the REPL, no UI needed —
  `sys.modules["registrar"].REGISTRAR.restore(badge, print)`.
- **`wrangler deploy` ships code, never schema.** `schema.sql` is all `CREATE
  TABLE IF NOT EXISTS`, so it cannot add a column to a database that already
  holds players — that is what `server/migrations/` is for, and each one is a
  separate `wrangler d1 execute foxhunt --remote --file=...`. Deploying code
  that reads a column prod lacks does not fail at deploy time: every query
  touching it throws at request time, so `/scores` and every `/auth` route
  return 500 while `/debug/players` still looks fine. The badge reads that as
  "geen antwoord" and blames the network. Ship the migration FIRST — it is
  additive, so it is safe against the old code — then deploy.
- Only the **cloud** leg of `register()` is real. The bridge/hunter legs report
  `"skip"` because no LoRa bridge protocol exists yet (`fox_radio.py` is a stub
  too); a cloud save alone counts as success, which is the rule the flow
  already applied to an antenna-less badge.

- **LoRa finds never flow badge → server.** That is an auth decision, not an
  unfinished wire: `POST /api/v1/player/found` is held by the LoRa bridge
  behind a `BRIDGE_KEY`. A badge that could claim its own fox finds could claim
  all of them. Badge-originated collection grants are narrower and explicitly
  not hunts: `/player/snuffel` reports a meeting, and `/player/pluk` reports a
  seeded BSSID/camp-phase encounter. Both are deduplicated, carry no
  zelf-gevonden provenance or hunter score, and enter `players_creatures` only
  so `GET /auth/user` can restore permanent progress.
- The badge writes what is its own to claim — name, `profile_pic` (companion
  shortcode), `hunter_id`, care summaries, meetings and pluk encounters. Only
  the bridge may attest that a fox was physically found.
- **A second registration on a known badge is a question, not a policy.**
  `badge_id` is the MAC, so a 409 from `/register` means this *hardware* already
  has an account: the same player after a wipe, or a badge that changed hands.
  Those want opposite things and the badge cannot tell them apart, so the flow
  stops and shows the account it found (`screen_reg_send._build_exists`) — DAT
  BEN IK adopts it, OVERSCHRIJF PATCHes the new name and maatje onto it. Either
  answer keeps the `hunter_id` and the catch list: both are keyed to the badge,
  and there is no second account to move them to. `registrar.adopt` does the
  writing for both, and for the welcome screen's "herstel" — one definition of
  what recovery means. Do not restore the silent PATCH this replaced: it renamed
  a stranger's account without asking, and because nothing read the existing row
  back it left the badge with `hunter_id = None` and an empty roster while the
  server still held both, under a screen that said "je bent ingeschreven".
- **`profile["synced"]` is a promise, and something must keep it.** Registration
  saves the profile locally BEFORE the send, so a server that is down cannot
  cost the player the maatje they just built — the error screen says "probeer
  straks opnieuw" and means it. But `REGISTRAR.register` has one call site,
  inside onboarding, and `foxhunt.py` routes on `store.profile() is None`
  alone: once a profile exists, synced or not, onboarding is unreachable
  forever. An unconfirmed badge then looks completely normal while the game has
  never heard of it — off the scoreboard, no startbeest, WORD JAGER answering
  404 (`/auth/hunter` looks the badge up), nothing to restore.
  Two things keep the promise, and both must stay:
  - `registrar.resync()`, fired once per launch from `FoxhuntActivity.onCreate`.
    It settles only the answer that needs no human: 201 syncs and banks the
    startbeest, a dead server does nothing and retries next launch, and **409
    also does nothing** — that is the exists fork, a question with two answers,
    and answering it needs the screen.
  - The instellingen bottom slot, which shows `Cloud / niet bewaard - opnieuw`
    and opens `RegSendActivity` with `extras={"resync": True}`. That slot holds
    three mutually exclusive states and the order matters: an unconfirmed
    account outranks WORD JAGER, because WORD JAGER cannot work until the
    account exists. In resync mode the screen must NOT clear the profile when
    the player walks out of the fork — that rule is for onboarding, where
    walking away registers nobody; here the profile is real and already lived in.
- **ALLES WISSEN is the only real way to start over, and it is soft.** The 409
  fork above is why: a badge that wiped only itself re-registers straight into
  it and gets every catch handed back, so instellingen -> ALLES WISSEN
  (`screen_wipe.py`) ends the account on both sides. Four rules hold it up.
  - **The server goes first.** `registrar.delete_account` runs before
    `store.reset_all`, because the local wipe is the step nobody can undo. A
    server that doesn't answer must leave the badge untouched and say so — that
    is also why the screen has no separate wifi check, and why a 404 counts as
    success (the badge asked for the account to be gone) **only when it carries
    a JSON body**. A worker deployed before this route existed answers the same
    404 with Hono's plain-text not-found, and that is not a grant: it once let a
    badge wipe itself while the account it asked about lived on, so the next
    registration met its own row and showed "badge al bekend" instead of
    starting over. Deploy the server before trusting a wipe.
  - **`DELETE /api/v1/auth/user` is a soft delete** — `dt_deleted` stamped, row
    kept. Every player-facing read filters it out (restore, PATCH, `/found`,
    `/scores`); `/debug/players` keeps it tagged GEWIST so an organiser can undo
    by clearing the column. Registering again **revives that row**: `/register`
    therefore reads before it inserts, because `badge_id` is UNIQUE across
    deleted rows and an INSERT can only ever report a conflict. Do not make it
    a hard delete: the API is unauthenticated by house style, a vandalised name
    is repairable and a destroyed catch list is not.
  - **It is not erasure.** `game_events` is append-only and the projections are
    rebuilt from it, so `player_registered` still carries the name. Say that
    plainly rather than implying otherwise.
  - **`store.reset_all` is an allowlist** — `Editor` has no `remove(key)`, so it
    wipes everything and writes back `_KEEP_ON_RESET`. Keep it that way: a new
    store key is then wiped by default instead of surviving into the next
    player's badge. Only `settings` stays.

  `scripts/test_server_wipe.sh` walks the whole lifecycle; the properties live in
  four different routes' WHERE clauses, so test it end to end, not route by route.

  `scripts/delete_account.sh` does the same wipe from a laptop, for the accounts
  ALLES WISSEN cannot reach: a badge already wiped locally, a dead badge, an
  emulator profile that was thrown away. It calls the SAME route rather than
  writing `dt_deleted` itself — a second definition of deleting would drift from
  the first, and this one already carries the soft delete, the `game_events`
  entry and the idempotency. Run it with no argument to list accounts.

- **`hunter_id` is a `uint16`, allocated 1-9999.** The LoRa spec (§2.2) makes
  HID a big-endian `uint16` — `HID_hi`, `HID_lo`, 1-65535, 0 reserved — and
  everything that carries the field honours all of it: the server validator
  accepts 1-65535 (`lib/validate.ts`), and anything parsing the air reads a
  full `uint16`. Our allocator (`POST /auth/hunter`) deliberately mints only
  the bottom 1-9999: a camp brings hundreds of badges, so four digits is ~16x
  headroom, and a fixed-width id keeps "JGR-0042" the same size on every
  screen that prints it (home, profiel, instellingen, registratie).
  - **The badge profile stores the raw number, never the label.** Screens
    format it at the last moment with `registrar.hunter_label`; the LoRa layer
    packs the same number into `HID_hi`/`HID_lo`. `store.profile()` tolerates
    the label string older builds saved, parsing it back to the number on read.
  Do NOT copy the 0-31 that `fox_id` uses. That range is not a hunter range: it
  is `CHAR`, the 5 MSB of the FID byte (§2.1) — the creature's character code,
  which is why 0-31 is exactly right for `fox_id` and was a bug for `hunter_id`.
  Never accept `0`: the spec reserves it, and every screen falls back through
  `hunter_label(hunter_id) or "Verzamelaar"`, so a falsy id silently renders a
  jager as a collector.
- **Debug catches must never score.** Creatures "attained" through the debug
  screen (opened by tapping the badge id five times in settings) — the 1111
  test code, the roster toggles — land only in the badge's local store. The
  no-badge-writes rule above already guarantees they can't reach the
  scoreboard, but treat it as a requirement, not a happy accident: any future
  debug or test path must stay local-only and never produce a server-side
  catch.

## Server pages
`/` is the public one-pager (`components/Home.tsx`): what the game is, both
play tracks, screenshots. It renders through `<Layout bare>` — same `<head>`,
no green banner, no width cap, because it brings its own full-bleed sections.
The scoreboard lives at `/scores` and keeps the badge-flavoured `<Layout>`.

Its screenshots in `static/screens/` are 640×480 — an exact 2× of the badge's
320×240 screen — so they stay pixel-crisp at 320 or 640 CSS px, and
`image-rendering: pixelated` covers the sizes in between.

**The roster is a spoiler; the public site must not hold it.** Every creature
ships as a flat `#86ad64` silhouette — the title banner's own green, alpha kept,
colour discarded — under `static/art/silhouettes/NN.png`. Numbered, not named: a
filename in view-source gives the roster away exactly as well as a picture
does. The Vos is no exception: it may be the favicon, but one full-colour
animal in a parade of shapes reads as a rendering fault, not as a hint. The
favicon and the nav brand keep their own copy at `static/vos.png`.
Never copy `artwork/animals/` into `server/static/` again. Body copy is Nunito;
Pixelify Sans is for headings and the badge-mirroring UI (tables, buttons,
tags) only — it is unreadable at paragraph length.

**Card labels are the badge's own icons, never emoji.** An emoji is somebody
else's drawing in the middle of a hand-pixelled page, and it dates the whole
band as decoration. `scripts/bake_server_icons.sh` bakes the `ICONS` grids out
of `art.py` into `src/lib/icon-art.ts` as SVG run geometry, drawn by
`<Icon name>`; `--check` reports drift (CI), and `WANTED` in the script lists
what the site asks for. SVG, not PNG like the companion layers, because an
`ICONS` entry has no file behind it — the grid IS the source — and rects stay
square at any card size. Two rules that are easy to get wrong: pick the icon
that reads standing ALONE (`ant` is the badge's antenna and is correct beside
the words "antenne gevonden", but in a bare tile it reads as a gold X, which is
why the jager card wears `spoor`), and keep `shape-rendering: crispEdges` —
without it the seam between two neighbouring runs antialiases into a hairline
down the middle of the art. `In het kort` takes neither: it is a sequence, so
its cards are numbered with a CSS counter (`.cards-steps`), in terra rather
than the gold chip `.steps` uses, so two orders on one page do not read as one
list.

**The scoreboard says HOW MANY, never WHICH.** `/scores` is public, so it shows
each player's maatje, their catch count and when they last scored — and no
creature name, id or picture. It also shows their name, which is why taking
that name off it is one of the two reasons ALLES WISSEN exists: `fetchScores`
filters `dt_deleted IS NULL`. `fetchScores` is written so it cannot leak one:
it counts `players_creatures` and never selects a `creature_id`. The names
belong to the badge that earned them and to `/debug/players/:id`.

One column carries the score, headed **Beesten**, holding a bar and `6/22`. It
used to be two — a "Vossen" bar beside a "Beesten" number — which read as two
different scores for one thing. The denominator is `CREATURES.length`, not a
constant, and the bar is continuous rather than segmented like the badge's
stat rows: 22 segments is more than an eye can count, so the bar carries the
feeling and the fraction carries the number. In code that count is
`creatures_found` — a **fox** is the transmitter you find, a **creature** is
what you get, and this counts the latter (Glossary).

## Server debug routes
`server/` (Hono on Cloudflare Workers + D1) exposes read-only inspection pages
under `/debug/*` — `/debug/log` for the event log, `/debug/players` for the
player list, `/debug/players/:id` for one player (maatje, account fields, catch
list with names, and the events that wrote them). Conventions for adding
another one:
- **One handler, two representations.** Query D1 once, then
  `if (c.req.header("Accept")?.includes("application/json")) return c.json(...)`
  before falling through to the HTML render. Curl gets JSON, the browser gets a
  page — no separate `/api` twin.
- **Render through `<Layout>`** with a Dutch `title` and a `right` count badge
  (`` `${results.length} spelers` ``), and use the shared table markup:
  `class="muted"` for secondary columns, `<code>` for ids/hashes, and a
  `colspan` `class="empty"` row for the no-rows case.
- **Timestamps** go through the `shortTime` / `fullTime` helpers in
  `pages.tsx` — logs and lists show `YYYY-MM-DD HH:MM:SS`, the scoreboard just
  `HH:MM`. Never dump the raw ISO string in HTML; JSON keeps it verbatim.
- Debug pages are unauthenticated and unpolled — no HTMX refresh unless the page
  is meant to be left open (the scoreboard is the only one that is).
- **Roster names live in the worker, never in `static/`.** `lib/creatures.ts`
  carries id → naam → tier so a debug page can say "Eend" instead of "7"; it is
  a port of `creatures.py`, names and tiers only. The spoiler rule above is
  about what the *public* site hands out, and a debug route nobody links is not
  that — but the art stays out of `static/` either way.
- **The maatje renders from the shortcode**, through `lib/companion.ts` (a port
  of `companion.py`: HEADS, ACCS, BGS and `decode`) and `<Companion>`, which
  stacks one `<img>` per layer exactly as `companion.draw()` stacks LVGL
  layers. Three things must stay in sync with the badge or the same shortcode
  draws two different maatjes: head order, ACCS order (it is both the bit
  positions *and* the draw order, append-only), and the BGS palette.
  The layer PNGs are inlined as data URIs by `scripts/bake_server_art.sh` into
  `lib/companion-art.ts` — not copied into `static/`, because a `konijn.png` in
  view-source leaks a roster name, and because an avatar is up to eleven layers
  and a list draws one per row. All fifteen are 2.7 KB. Re-run the script after
  changing `artwork/companions/`; `--check` reports drift. It is in
  `.prettierignore`: prettier would wrap the data URIs and the script owns the
  file's shape.
- **Sprite sizes must stay integer multiples of 16.** `image-rendering:
  pixelated` only keeps pixels square at whole scale factors. `.maatje` carries
  no border or padding — the backdrop is its own edge — and anything added
  later must sit OUTSIDE the box (`box-sizing: content-box`), because the
  global `border-box` takes it out of the art instead: a 2px frame turns a 96px
  avatar into a 5.75x scale. Same rule as the badge's "never let LVGL scale a
  sprite", same reason.

## Layout source of truth
`layout/foxhunt-layout.html` is the pixel-exact 320×240 spec — it owns
sizes, gaps and colours; keep them in sync. *How* the app expresses them is in
`DESIGN.md`: repeated elements use LVGL flex via `ui.row(...)` (positions are
computed, not transcribed); only one-off panels keep absolute coords. Colours
and spacing are tokens in `ui.py`, applied through shared `lv.style_t` objects —
read `DESIGN.md` before adding a screen.
