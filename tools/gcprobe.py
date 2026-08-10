# gcprobe — how a game's tick is measured. Copy into
# <MicroPythonOS>/internal_filesystem/ (the fs root is on sys.path) and drive
# it from the emulator's stdin REPL; see docs/emulator-testing.md.
#
#   import gcprobe
#   gcprobe.start(25); gcprobe.launch('VangActivity'); gcprobe.autoplay()
#   ...                                     # let a round run
#   gcprobe.report()                        # allocation, split step vs rest
#   gcprobe.pacing(); gcprobe.pacing_report()   # per-FRAME movement
#
# Two different questions, and the second is the one that decides whether a
# game feels right:
#
# ALLOCATION. A lv.timer samples gc.mem_alloc() and sums the POSITIVE deltas,
# so it sees every allocation anyone makes. GameActivity._tick is wrapped to
# bill its own share; total - step is everything else (LVGL's refresh, the OS
# status bar, asyncio). A negative delta means memory was freed — LVGL's C
# allocator hands blocks straight back, since lv_conf.h sets
# LV_USE_STDLIB_MALLOC = LV_STDLIB_MPY — so those are counted, not summed.
#   * THE SAMPLER IS NOT FREE. Reading it every 1 ms adds ~10 KB/s of its own
#     and doubles an idle reading; 25 ms is the honest setting. Measured on an
#     idle home screen: 21.2 KB/s at 1 ms, 13.1 at 5, 10.9 at 25.
#   * Emulator bytes are not badge bytes. The desktop is a 64-bit build with
#     32-byte GC blocks and doubles; the badge is 32-bit with 16-byte blocks
#     and single floats. HALVE anything small — a float, a dict, a list. A
#     bytearray costs the same on both.
#   * The desktop heap is ~11 MB free, so the emulator essentially never shows
#     the collector's pause. It tells you the RATE; only the badge tells you
#     the interval.
#
# PACING. What the display shows per frame, which no allocation number can
# see. pacing() samples a thing that moves a fixed amount per tick at
# lv.EVENT.REFR_START: an even run of the same number is right, a zero
# followed by a double is the stutter.
import gc
import sys
import time

import lvgl as lv

_S = {}


def start(hb_ms=1):
    sc = sys.modules.get("screens_care")
    s = _S
    s["total"] = 0
    s["step"] = 0
    s["ticks"] = 0
    s["collects"] = 0
    s["freed"] = 0
    s["prev"] = gc.mem_alloc()
    s["t0"] = time.ticks_ms()
    s["free0"] = gc.mem_free()
    s["minfree"] = s["free0"]

    def sample():
        now = gc.mem_alloc()
        d = now - s["prev"]
        s["prev"] = now
        if d > 0:
            s["total"] += d
        elif d < 0:
            s["collects"] += 1
            s["freed"] -= d
        f = gc.mem_free()
        if f < s["minfree"]:
            s["minfree"] = f

    s["sample"] = sample
    s["hb"] = lv.timer_create(lambda t: sample(), hb_ms, None)
    s["hb_ms"] = hb_ms

    if sc is not None and not hasattr(sc.GameActivity, "_gcprobe_orig"):
        orig = sc.GameActivity._tick

        def tick(self, t):
            sample()
            a = gc.mem_alloc()
            orig(self, t)
            b = gc.mem_alloc()
            if b > a:
                s["step"] += b - a
            s["ticks"] += 1
            sample()

        sc.GameActivity._gcprobe_orig = orig
        sc.GameActivity._tick = tick
        s["patched"] = sc
    print("gcprobe: sampling every %d ms (free at start: %d B)" % (hb_ms, s["free0"]))


def report():
    s = _S
    sec = time.ticks_diff(time.ticks_ms(), s["t0"]) / 1000.0
    tot, st = s["total"], s["step"]
    print("--- gcprobe: %.1f s, %d game ticks ---" % (sec, s["ticks"]))
    print("total allocated : %8d B  = %7.1f KB/s" % (tot, tot / sec / 1024))
    print(
        "  in step()     : %8d B  = %7.1f KB/s  (%.0f%%)"
        % (st, st / sec / 1024, 100 * st / tot if tot else 0)
    )
    print("  everything els: %8d B  = %7.1f KB/s" % (tot - st, (tot - st) / sec / 1024))
    if s["ticks"]:
        print("  per game tick : %8.1f B in step" % (st / s["ticks"]))
    print(
        "collects seen   : %d, freeing %d B; crashes absorbed: %d"
        % (s["collects"], s["freed"], s.get("saved", 0))
    )
    print("free now        : %d B (low water %d)" % (gc.mem_free(), s["minfree"]))
    if tot:
        print(
            "heap runway     : %.0f s until a collect at this rate"
            % (gc.mem_free() / (tot / sec))
        )


def launch(cls_name, fox_id=1):
    """Start a game activity straight from the REPL, no screen taps."""
    from mpos.activity_navigator import ActivityNavigator
    from mpos import Intent

    sc = sys.modules["screens_care"]
    ActivityNavigator.startActivity(
        Intent(
            activity_class=getattr(sc, cls_name),
            extras={"fox_id": fox_id, "kost": 1, "fav": False},
        )
    )


def autoplay():
    """Play the game, so the measurement window is a real round: fly VLIEGEN's
    fox at the next gap, steer VANGEN's beast at whatever lands first, dance
    DANSEN back perfectly.

    Mind the units. This reaches into the activity's own state, and positions
    there are in HUNDREDTHS of a pixel (screens_care._FP) while the widget
    coordinates it compares them against are whole pixels. Getting that wrong
    does not raise: it pinned VANGEN's beast against the left wall for a whole
    measurement run, which read as a plausible set of numbers."""
    from mpos.ui import view

    def drive(_t):
        if not view.screen_stack:
            return
        a = view.screen_stack[-1][0]
        if a is None:
            return
        # One long round beats a string of short ones: rebuilding the screen is
        # not what we are measuring, and driving _again() from a second timer
        # races LVGL's own dispatch (the rebuild deletes widgets the game tick
        # in the same pass still holds). Absorb the crash instead.
        if "saved" not in _S:
            _S["saved"] = 0

            def survive(kop, retry=True):
                _S["saved"] += 1
                if hasattr(a, "_y"):
                    a._y, a._vy = 11000, 0
                elif hasattr(a, "_missed"):
                    a._missed = 0
                else:
                    a.seq, a.state, a._over = [], "new", False

            a.game_over = survive
        if hasattr(a, "_flap"):
            # aim at the gap of the nearest branch pair still ahead, so the
            # autopilot survives the way a player does instead of crashing
            target = 110
            best = 999
            for o in a.obs:
                d = o["x"] - 50
                if -26 < d < best:
                    best, target = d, o["gap"] - 16
            if a._y // 100 > target or not a._flying:
                a._flap()
        elif hasattr(a, "_press") and getattr(a, "seq", None) is not None:
            if a.state == "wait":
                a._press(a.seq[a.inp])  # always the right step: a perfect player
        elif hasattr(a, "_turn") and getattr(a, "items", None):
            low = max(a.items, key=lambda it: it["y"])
            want = low["x"] - 4
            a._dir = 1 if want > a._cx // 100 else -1

    _S["drive"] = lv.timer_create(drive, 50, None)


def stop():
    s = _S
    if s.get("hb"):
        s["hb"].delete()
        s["hb"] = None
    sc = s.get("patched")
    if sc is not None:
        sc.GameActivity._tick = sc.GameActivity._gcprobe_orig
        del sc.GameActivity._gcprobe_orig
        s["patched"] = None


def check_vlieg():
    """Assert the pooled branch pairs still describe the same geometry the
    per-spawn build did: top from 26 to gap-42, bottom from gap+42 to 240, and
    no freed slot left visible. A widget pool's failure mode is a ghost, and a
    ghost is invisible in every number the rest of this file prints."""
    from mpos.ui import view

    a = view.screen_stack[-1][0]
    bad = 0
    for o in a.obs:
        top, bot = a.pairs[o["slot"]]
        g = o["gap"]
        want_t = (o["x"], 26, 26, max(2, g - 42 - 26))
        want_b = (o["x"], g + 42, 26, max(2, 240 - g - 42))
        got_t = (top.get_x(), top.get_y(), top.get_width(), top.get_height())
        got_b = (bot.get_x(), bot.get_y(), bot.get_width(), bot.get_height())
        hidden_t = top.has_flag(lv.obj.FLAG.HIDDEN)
        hidden_b = bot.has_flag(lv.obj.FLAG.HIDDEN)
        ok = got_t == want_t and got_b == want_b and not hidden_t and not hidden_b
        if not ok:
            bad += 1
        print(
            "gap=%d %s top %s want %s | bot %s want %s | hidden %s %s"
            % (
                g,
                "OK " if ok else "BAD",
                got_t,
                want_t,
                got_b,
                want_b,
                hidden_t,
                hidden_b,
            )
        )
    idle = [i for i in a.free_pairs]
    ghosts = [i for i in idle if not a.pairs[i][0].has_flag(lv.obj.FLAG.HIDDEN)]
    print(
        "live=%d bad=%d free=%s visible-but-free=%s" % (len(a.obs), bad, idle, ghosts)
    )


def pacing(n=80):
    """Per-RENDERED-FRAME movement of something that moves a fixed amount per
    tick: VANGEN's beast (4 px) or one of VLIEGEN's branches (3 px). An even
    run of the same number is correct pacing; a 0 followed by a double is the
    stutter CLAUDE.md describes. Allocation numbers cannot see this."""
    from mpos.ui import view

    s = _S
    s["pace"] = []
    s["pace_prev"] = None

    def on_refr(e):
        if len(s["pace"]) >= n:
            return
        a = view.screen_stack[-1][0] if view.screen_stack else None
        if a is None:
            return
        try:
            if hasattr(a, "obs"):
                if not a.obs:
                    return
                v = a.pairs[a.obs[0]["slot"]][0].get_x()
            elif hasattr(a, "beast"):
                v = a.beast.get_x()
            else:
                return
        except Exception:
            return
        if s["pace_prev"] is not None:
            s["pace"].append(v - s["pace_prev"])
        s["pace_prev"] = v

    lv.display_get_default().add_event_cb(on_refr, lv.EVENT.REFR_START, None)


def pacing_report():
    d = _S.get("pace", [])
    print("per-frame delta (%d frames):" % len(d))
    print("  " + " ".join(str(x) for x in d))
    body = [x for x in d if x]
    zeros = sum(1 for x in d if x == 0)
    print(
        "  zero-move frames: %d/%d   distinct nonzero steps: %s"
        % (zeros, len(d), sorted(set(body)))
    )
