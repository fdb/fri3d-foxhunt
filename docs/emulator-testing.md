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
- **Widget lookup**: `get_child(i)` returns properly TYPED wrappers, so a
  recursive walk with `isinstance(c, lv.textarea)` finds any widget — that is
  how a scripted run fills the register screen's name field without the OS
  keyboard. Multi-line helpers don't survive the line-based stdin REPL;
  drop a helper module into `<MicroPythonOS>/internal_filesystem/` and
  `import` it instead (the fs root is on `sys.path`).

## App state

Preferences live under `<MicroPythonOS>/internal_filesystem/` in
`prefs/be.fri3d.foxhunt/config.json` OR `data/be.fri3d.foxhunt/config.json`
— which one wins depends on the OS build (the current source checkout loads
`data/`; other builds moved to `prefs/`). Don't guess: the boot log prints
`Loaded preferences from <path>`, and `scripts/clear_app_data.sh` sweeps
both. Edit the winning file between runs to set up scenarios:
delete the `profile` key to re-trigger first-run onboarding, seed a profile
dict to skip it, delete `settings` to reset toggles.

## Reading the log

`Traceback` lines from `lib/mpos/ui/topmenu.py` (`LvReferenceError`) are OS
status-bar noise, not app failures. App-level failures show as tracebacks
with `apps/be.fri3d.foxhunt/...` frames, or an on-screen error dialog logged
from `activity.onCreate`.
