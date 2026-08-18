# Driving the emulator headlessly

The desktop emulator starts a small asyncio REPL on stdin. Piping Python
lines into it turns a normal run into a scripted integration test: simulate
taps, drags and focus moves, and capture screenshots as evidence — no SDL
window interaction needed.

## The recipe

Write a driver script that sleeps through boot (~15 s) and `echo`s REPL
commands, then pipe it into `run_desktop.sh`:

```bash
S=/tmp/shots
( sleep 15
  echo "from mpos.ui.testing import capture_screenshot as shot, simulate_click as click, simulate_drag as drag, wait_for_render as wfr"
  sleep 1
  echo "wfr(); shot('$S/home.raw')"
  sleep 1
  echo "click(160, 120)"        # tap
  sleep 1
  echo "drag(2, 120, 100, 120)" # left-edge swipe = system back
  sleep 1
  echo "wfr(); shot('$S/after.raw')"
  sleep 2
) | ./scripts/run_desktop.sh com.enigmeta.foxhunt > /tmp/run.log 2>&1 &
sleep 30; pkill -f lvgl_micropy   # the emulator never exits on stdin EOF
grep Traceback /tmp/run.log
```

`shot()` asks LVGL for a snapshot of the active screen, so it captures the
320x240 framebuffer itself — never the SDL window, which the Mac backs at 2x
and would hand out at 640x480. The file is raw pixels; PNG at 1:1 is one
ffmpeg call:

```bash
ffmpeg -f rawvideo -pixel_format rgb565le -video_size 320x240 -i shot.raw shot.png
```

RGB565 is the panel's own format, so it is what the badge shows — but it keeps
5/6/5 bits, and a converted PNG is off by a few counts per channel (`0xFFCB45`
comes back as `255,203,66`). For colour-exact evidence, ask for the wide format
and read it as `bgra`, which is how LVGL lays ARGB8888 out in memory:

```
shot('x.raw', color_format=lv.COLOR_FORMAT.ARGB8888)   # 320*240*4 bytes
ffmpeg -f rawvideo -pixel_format bgra -video_size 320x240 -i x.raw x.png
```

`scripts/capture_server_screens.sh` is the same path with one extra step: it
scales to 640x480 with `flags=neighbor`, because the public site wants an exact
2x. Drop that `-vf` to keep 100%.

## Useful REPL moves

- **Joystick focus**: there is no key simulation, but
  `import lvgl as lv; g = lv.group_get_default()` then `g.focus_next()` /
  `g.focus_prev()` steps focus order. (Order-based only — the badge's real
  joystick nav is *geometric*, see DESIGN.md.)
- **Test hooks**: app modules stay in `sys.modules` after launch, so fakes
  can be flipped live, e.g.
  `import sys; sys.modules['registrar'].FakeRegistrar.FAIL_BRIDGE = True`.
  In `--lora` mode, choose a stable nearby-fox scenario with
  `import fox_radio; fox_radio.RADIO.set_active([0, 1, 2, 12])`; pass `[]`
  to exercise the "alles slaapt" state. The default is four active foxes.
- **Widget introspection**: `f = g.get_focused()`, then `f.get_state()`,
  `f.get_width()`, `f.get_parent()`, or force styles on it to probe rendering.
- **Widget lookup**: `get_child(i)` returns properly TYPED wrappers, so a
  recursive walk with `isinstance(c, lv.textarea)` finds any widget — that is
  how a scripted run fills the register screen's name field without the OS
  keyboard. Multi-line helpers don't survive the line-based stdin REPL;
  drop a helper module into `<MicroPythonOS>/internal_filesystem/` and
  `import` it instead (the fs root is on `sys.path`).

## App state

Preferences live under `<MicroPythonOS>/internal_filesystem/` in
`prefs/com.enigmeta.foxhunt/config.json` OR `data/com.enigmeta.foxhunt/config.json`
— which one wins depends on the OS build (the current source checkout loads
`data/`; other builds moved to `prefs/`). Don't guess: the boot log prints
`Loaded preferences from <path>`, and `scripts/clear_app_data.sh` sweeps
both. Edit the winning file between runs to set up scenarios:
delete the `profile` key to re-trigger first-run onboarding, seed a profile
dict to skip it, delete `settings` to reset toggles.

## Measuring a game: `tools/gcprobe.py`

Copy it into `<MicroPythonOS>/internal_filesystem/` and drive it like any
other REPL helper. It answers the two questions a game change has to answer,
and its own header documents the traps in both.

```bash
echo "import gcprobe"
echo "gcprobe.start(25)"                    # 25 ms, NOT the 1 ms default
echo "gcprobe.launch('VangActivity')"       # no screen taps needed
echo "gcprobe.autoplay()"                   # plays the game so a round lasts
sleep 30
echo "gcprobe.report()"                     # B/tick in step(), and the rest
```

- **`start(25)`, not `start()`.** The 1 ms sampler allocates ~10 KB/s of its
  own and doubles an idle reading.
- **`launch()` needs the free-play cheat**, or the round ends on energy:
  put `"debug": {"nooit_moe": true}` in the app's `config.json`. It also
  turns hapjes off (`play_cost` gates both), so a treat-spawn path has to be
  measured another way.
- **Emulator bytes are not badge bytes** — halve anything small, see the
  header. And the desktop has ~11 MB free, so it never shows the collector's
  pause at all; it measures the RATE, the badge measures the interval.
- `pacing()` / `pacing_report()` print per-RENDERED-FRAME movement, which is
  what actually decides whether a game stutters. `check_vlieg()` asserts the
  pooled branch widgets still match the geometry the old per-spawn code drew,
  because a widget pool's failure mode is a ghost and no counter sees one.

## Reading the log

`Traceback` lines from `lib/mpos/ui/topmenu.py` (`LvReferenceError`) are OS
status-bar noise, not app failures. App-level failures show as tracebacks
with `apps/com.enigmeta.foxhunt/...` frames, or an on-screen error dialog logged
from `activity.onCreate`.

An `LvReferenceError` from an app frame is the same noise **when it appears
after the last line your script printed**: killing the emulator tears the
screen down while a game tick is still in flight. Check the line numbers in
the log, not just `grep -c Traceback`.
