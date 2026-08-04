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
) | ./scripts/run_desktop.sh be.fri3d.foxhunt > /tmp/run.log 2>&1 &
sleep 30; pkill -f lvgl_micropy   # the emulator never exits on stdin EOF
grep Traceback /tmp/run.log
```

Screenshots are raw RGB565; convert with:

```bash
ffmpeg -vcodec rawvideo -f rawvideo -pix_fmt rgb565le -s 320x240 -i shot.raw shot.png
```

## Useful REPL moves

- **Joystick focus**: there is no key simulation, but
  `import lvgl as lv; g = lv.group_get_default()` then `g.focus_next()` /
  `g.focus_prev()` steps focus order. (Order-based only — the badge's real
  joystick nav is *geometric*, see DESIGN.md.)
- **Test hooks**: app modules stay in `sys.modules` after launch, so fakes
  can be flipped live, e.g.
  `import sys; sys.modules['registrar'].FakeRegistrar.FAIL_BRIDGE = True`.
- **Widget introspection**: `f = g.get_focused()`, then `f.get_state()`,
  `f.get_width()`, `f.get_parent()`, or force styles on it to probe rendering.

## App state

Preferences live at
`<MicroPythonOS>/internal_filesystem/prefs/be.fri3d.foxhunt/config.json`
(NOT `data/` at the repo root, and no longer `internal_filesystem/data/` —
MPOS moved prefs to `prefs/` and keeps `data/` only as the legacy source of a
one-time migration, so seeding the old path silently does nothing). Edit it
between runs to set up scenarios:
delete the `profile` key to re-trigger first-run onboarding, seed a profile
dict to skip it, delete `settings` to reset toggles.

## Reading the log

`Traceback` lines from `lib/mpos/ui/topmenu.py` (`LvReferenceError`) are OS
status-bar noise, not app failures. App-level failures show as tracebacks
with `apps/be.fri3d.foxhunt/...` frames, or an on-screen error dialog logged
from `activity.onCreate`.
