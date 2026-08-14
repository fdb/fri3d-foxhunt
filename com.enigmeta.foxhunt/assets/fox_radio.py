# fox_radio.py — the screen-facing boundary for the LoRa / ARDF backend.
#
# fox_radio.RADIO is what every screen codes against (see FoxRadio below).
# Two implementations: FakeFoxRadio, which drives the whole UI on desktop
# with no hardware, and LoraFoxRadio, the real thing — hunter side only
# (foxhunt-spec.md §6.2). LoraFoxRadio is a thin adapter: all SX1262 driving,
# the wire format, and the OTC codec live in lora.py; this file only maps
# that link onto the contract below. See lora.py's header for why there is
# no thread anywhere in that path, and FoxRadio.poll() below for why it's
# screens, not this module, that decide when the radio gets serviced.

import lvgl as lv
import random
import time
from collections import deque
from creatures import CREATURES
import lora

# Which beacons are transmitting right now (drives awake/dormant on home) —
# FakeFoxRadio only; LoraFoxRadio answers this from what it has actually
# heard (lora.LINK.active_chars()), since there is no compiled-in list of
# what's deployed on real hardware.
_AWAKE = (0, 1, 2, 12, 17, 19)

# The dBm span the hunt is played over: on top of the box, and the far edge of
# reception. Both mappings below are views of the same measured number.
RSSI_NEAR = -40
RSSI_FAR = -120


def rssi_to_bpm(rssi):
    """Heart rate IS the signal: -40 dBm reads as 215 bpm, -120 as 135.

    A plain offset, no scaling — it puts the whole usable dBm span inside a
    believable pulse and keeps the number monotonic with proximity, so a
    rising heart rate always means you are getting warmer. Unlike level
    below, this stays on the fixed span: bpm is meant to read as an absolute
    "how far into range are you", not a relative "warmer than a moment ago".
    """
    return rssi + 255


# ── 5-LED / mirror level: auto-ranged, ported from lora_rssi_meter.py ───────
#
# A fixed -40..-120 span (the old rssi_to_level) treats every hunt the same,
# but a fox in the open and one behind a wall sit at completely different
# absolute RSSI — so a fixed span either pins one hunt's LEDs at 5 the whole
# way, or never lights them for the other. lora_rssi_meter.py's terminal bar
# solves this by auto-scaling to whatever's actually been heard recently
# (its window_range()/scale()) rather than a fixed span; this is that same
# logic, per fox, driving the 5 LEDs instead of a terminal bar. bpm above is
# deliberately NOT changed to match — it stays the plain, fixed-span reading.
LEVEL_WINDOW_MS = 8000  # shorter than the meter's 20s default: a hunt is
# tens of seconds, not minutes, and an 8s-old sample
# from a different approach shouldn't still be
# setting today's range
RANGE_PAD_DB = 1.0  # same padding as the meter, either side of observed
MIN_SPAN_DB = 4.0  # same floor — never auto-range narrower than this
LEVEL_GAMMA = 2.0  # same power-law default: expands peaks, so the
# last stretch into a fox reads as clearly hotter


def _clamp01(x):
    return max(0.0, min(1.0, x))


class _LevelTracker:
    """One per fox: the sliding window behind its 5-LED level. Direct port
    of lora_rssi_meter.py's window_range() + scale(), swapping wall-clock
    seconds for ticks_ms (no RTC needed) and a terminal bar's width for the
    5 LEDs."""

    def __init__(self):
        self._samples = deque((), 128)  # (ticks_ms, rssi), pruned to the window

    def push(self, rssi):
        now = time.ticks_ms()
        self._samples.append((now, rssi))
        while (
            self._samples
            and time.ticks_diff(now, self._samples[0][0]) > LEVEL_WINDOW_MS
        ):
            self._samples.popleft()

        lo, hi = self._range()
        frac = _clamp01((rssi - lo) / (hi - lo)) ** LEVEL_GAMMA
        return round(frac * 5)

    def _range(self):
        lo = min(r for _, r in self._samples) - RANGE_PAD_DB
        hi = max(r for _, r in self._samples) + RANGE_PAD_DB
        if hi - lo < MIN_SPAN_DB:
            mid = (hi + lo) / 2.0
            lo, hi = mid - MIN_SPAN_DB / 2.0, mid + MIN_SPAN_DB / 2.0
        return lo, hi


class FoxReading:
    # NB: no "found" flag — RSSI can't tell you you've physically reached the
    # box. The player decides when to enter the code. We only report signal.
    def __init__(self, fox_id, rssi, level, link=0, bearing=None):
        self.fox_id = fox_id
        self.rssi = rssi  # dBm, the one measured value — feeds bpm, untouched
        self.level = level  # 0..5 hot/cold, auto-ranged (above) — home's
        # heat bars and other observers still read this
        self.link = link  # 0..5 BEACONs actually received in the trailing
        # link-quality window -> HuntActivity's 5 LEDs
        # (screens_hunt.py); level above still drives
        # everything else that reads .level unchanged
        self.bearing = bearing  # degrees; present but UI ignores it (classic ARDF)


class FoxRadio:
    def __init__(self):
        self._level_trackers = {}  # fox_id -> _LevelTracker

    def _level(self, fox_id, rssi):
        t = self._level_trackers.get(fox_id)
        if t is None:
            t = self._level_trackers[fox_id] = _LevelTracker()
        return t.push(rssi)

    def reset_level(self, fox_id):
        """Drop fox_id's auto-range window. Called from start() so a fresh
        hunt isn't still influenced by the tail of a previous approach, and
        by screens_hunt.HuntActivity whenever link quality drops to 0 --
        a silent fox means the player could be walking around (or away)
        for a while, and the level shouldn't keep reporting wherever the
        window happened to be when the beacons stopped. Public: called from
        outside this module as well as from start() below."""
        self._level_trackers.pop(fox_id, None)

    def active_foxes(self):
        raise NotImplementedError

    def start(self, fox_id):
        """The hunt screen begins (or returns to) hunting fox_id. Part of the
        interface because screen_hunt calls it on every resume: a real radio
        that measures continuously simply ignores it, but leaving it off the
        base class hands the real implementation an AttributeError on the
        hunt screen's first resume."""
        pass

    def bump(self, fox_id, delta):
        """Test hook (emulator keys nudge the signal). No-op on hardware."""
        pass

    def reset(self):
        """Forget everything this radio only believes because of THIS session.

        A no-op for a real radio, and that is the point of it being here: the
        fox network owns which codes are spent, so a real implementation has
        nothing local to drop. Only the fake keeps that state in RAM, where it
        outlives the app — MicroPythonOS re-execs the entrypoint on a relaunch
        but keeps sibling modules in sys.modules, so this singleton survives
        everything short of a power cycle.
        """
        pass

    def poll(self):
        """Pump one round of incoming-message handling. A no-op for a radio
        with nothing to poll (the fake), but for the real one this MUST be
        called from a screen's own tick, before that tick touches any
        widget — see lora.py's module header for why the ordering matters,
        not just the calling. Screens that show live signal (HuntActivity)
        or that are waiting on a network verdict (CodeActivity) call this;
        a screen that only reads cached values on resume doesn't need to."""
        pass

    def reading(self, fox_id):
        raise NotImplementedError

    def peek(self, fox_id):
        """A reading for OBSERVERS — the home row's heat bars — as opposed to
        the hunt loop. A real radio measures either way; the fake advances
        its simulated approach only in reading(), so that merely LOOKING at
        the home screen doesn't walk every fox to level 5."""
        return self.reading(fox_id)

    def submit_code(self, fox_id, code, on_result):
        """Hand a code to the fox network for validation.

        ASYNCHRONOUS BY CONTRACT: the real backend has to ask a server over
        LoRa, so the verdict arrives later, through on_result(result) — never
        as a return value. Callers must be able to survive the wait.

        result is one of:
            "ok"    accepted, the catch counts
            "wrong" no such code for this fox (or the fox was never even
                    heard/reachable -- indistinguishable from a bad code,
                    per spec §5.5)
            "used"  right code, but it was already claimed (codes are one-time)
            "busy"  the fox confirmed the code (PENDING) but the round trip
                    to the central then failed or timed out -- the code was
                    fine, the network wasn't (spec §5.3)
        """
        raise NotImplementedError


# ── 5-LED link quality: real receive counting for LoraFoxRadio (see
# lora.LoRaLink.link_quality), a simulated equivalent here for the fake ────
#
# Distinct from level (above): level asks "how strong is the signal we DID
# get", auto-ranged so it stays readable at any distance. Link quality asks
# a blunter question — "how many of the fox's own ~LQ_PERIOD_MS
# broadcasts actually arrived in the last five of them" — so the LEDs read
# as a literal packet-loss meter: full when every expected message lands,
# fading down over ~1.25s if the fox goes quiet, climbing back the same way
# once it resumes. LoraFoxRadio gets this straight from lora.LINK, which
# counts real BEACONs; FakeFoxRadio has no real packets to count, so
# _FakeLinkSim fabricates the same kind of arrival/drop history at the same
# cadence, driven by the existing walk-toward-the-fox `_strength`.
LINK_DROP_MIN = 0.0  # best-case per-broadcast drop chance, right on top of the fox
LINK_DROP_MAX = 0.65  # worst-case, at the edge of the simulated approach
SILENCE_CHANCE = 0.004  # per simulated broadcast slot, chance the fox
# goes quiet for a while — so the fade/ramp
# behaviour has something to actually show on
# desktop, not just gradually-improving reception
SILENCE_MS = (2000, 6000)  # random length of a simulated silent stretch


class _FakeLinkSim:
    """Desktop-only stand-in for lora.LoRaLink's real BEACON bookkeeping:
    walks forward through simulated ~LQ_PERIOD_MS broadcast slots
    (catching up on however many have elapsed since the last call, since
    reading() is polled faster than that), rolling for a drop or an
    occasional silent stretch, and keeps a trailing count the same way
    LoRaLink.link_quality() does."""

    def __init__(self):
        self._times = deque((), 8)
        self._next_slot = time.ticks_ms()
        self._silent_until = 0

    def tick(self, strength):
        now = time.ticks_ms()
        while time.ticks_diff(now, self._next_slot) >= 0:
            if time.ticks_diff(self._next_slot, self._silent_until) >= 0:
                if random.random() < SILENCE_CHANCE:
                    self._silent_until = self._next_slot + random.randint(*SILENCE_MS)
                else:
                    drop = LINK_DROP_MAX - strength * (LINK_DROP_MAX - LINK_DROP_MIN)
                    if random.random() >= drop:
                        self._times.append(self._next_slot)
            self._next_slot = time.ticks_add(self._next_slot, lora.LQ_PERIOD_MS)
        while self._times and time.ticks_diff(now, self._times[0]) > lora.LQ_WINDOW_MS:
            self._times.popleft()
        return min(len(self._times), 5)


class FakeFoxRadio(FoxRadio):
    """Simulates honing in on a fox: strength drifts upward (with noise) the
    longer you 'search', so on desktop the hunt reaches 'found' in a few
    seconds with no hardware. bump() lets a key nudge it warmer/colder."""

    ROUND_TRIP_MS = 500  # what asking the network "costs", faked
    active_cnt = 1

    def __init__(self):
        super().__init__()
        self._strength = {}
        self._used = set()  # burnt one-time codes; the real server owns this
        self._link_sim = {}  # fox_id -> _FakeLinkSim (see class below)

    def reset(self):
        # Both halves are simulation, not a record of play: _strength is where
        # the walk toward a box had got to, and _used stands in for the server
        # that would really be tracking spent codes. Neither may be inherited.
        # A new player after ALLES WISSEN met the previous one's burnt codes as
        # "AL GEBRUIKT" at the fox — the badge changes hands without an app
        # restart, so nothing else was ever going to clear them.
        self._strength = {}
        self._used = set()

    def active_foxes(self):
        ids = {c["id"] for c in CREATURES}
        act = [b for b in _AWAKE if b in ids]
        return act[: self.active_cnt]

    def start(self, fox_id):
        self._strength[fox_id] = 0.12
        self.reset_level(fox_id)
        self._link_sim.pop(fox_id, None)  # fresh hunt, fresh simulated air

    def _link(self, fox_id, strength):
        sim = self._link_sim.get(fox_id)
        if sim is None:
            sim = self._link_sim[fox_id] = _FakeLinkSim()
        return sim.tick(strength)

    def bump(self, fox_id, delta):
        s = self._strength.get(fox_id, 0.12) + delta
        self._strength[fox_id] = max(0.0, min(1.0, s))

    def poll(self):
        self.active_cnt = (self.active_cnt + 1) % 5  # ranges [0-4]

    def reading(self, fox_id):
        s = self._strength.get(fox_id, 0.12)
        s += random.uniform(-0.04, 0.10)  # drift up, with jitter
        s = max(0.0, min(1.0, s))
        self._strength[fox_id] = s
        rssi = int(round(RSSI_FAR + s * (RSSI_NEAR - RSSI_FAR)))
        return FoxReading(
            fox_id, rssi, self._level(fox_id, rssi), link=self._link(fox_id, s)
        )

    def peek(self, fox_id):
        # No drift: reading() simulates walking toward the fox, and the home
        # row samples every awake fox on every resume — through reading(),
        # ~30 visits home pinned all the heat bars at maximum forever. The
        # level tracker still sees this rssi (harmless — same value repeated
        # barely moves an auto-ranged window), just never a NEW one.
        # The link sim, unlike strength, is driven by real elapsed time, not
        # by being looked at — same as a real fox keeps beaconing whether or
        # not a screen is watching — so ticking it here is harmless too.
        s = self._strength.get(fox_id, 0.12)
        rssi = int(round(RSSI_FAR + s * (RSSI_NEAR - RSSI_FAR)))
        return FoxReading(
            fox_id, rssi, self._level(fox_id, rssi), link=self._link(fox_id, s)
        )

    def submit_code(self, fox_id, code, on_result):
        # A one-shot timer stands in for the round trip; the verdict is decided
        # when the "reply" lands, not when the request goes out — same as a
        # server deciding. The real radio swaps this for its LoRa reply
        # handler and the caller never notices.
        t = lv.timer_create(
            lambda _t: on_result(self._verdict(fox_id, code)), self.ROUND_TRIP_MS, None
        )
        t.set_repeat_count(1)  # LVGL deletes it after the single run

    def _verdict(self, fox_id, code):
        # The code has to be THIS fox's code — another box's code is simply
        # wrong here, or you could claim a beast you never walked to.
        for c in CREATURES:
            if c["id"] == fox_id:
                if str(code) != c["code"]:
                    return "wrong"
                if code in self._used:
                    return "used"
                self._used.add(code)  # one-time code: burnt on acceptance
                return "ok"
        return "wrong"


def _hunter_id():
    """HID for CODE_ENTRY (spec §2.2): 1-9999, minted at registration and
    stored on the profile. Imported lazily — store reaches back into the
    radio module indirectly through other screens, and this keeps that path
    acyclic (same trick registrar.py uses for its own `import store`)."""
    import store

    p = store.profile()
    return None if p is None else p.get("hunter_id")


class LoraFoxRadio(FoxRadio):
    """The real thing, hunter side only. Every method here just reads
    lora.LINK's cache or hands it work — see lora.py for the SX1262 driving,
    the wire format, and the CODE_ENTRY retry/timeout state machine."""

    def active_foxes(self):
        ids = {c["id"] for c in CREATURES}
        return sorted(c for c in lora.LINK.active_chars() if c in ids)

    def start(self, fox_id):
        self.reset_level(fox_id)  # continuous RX already runs; just a fresh window

    def poll(self):
        lora.LINK.poll()

    def reading(self, fox_id):
        return self._reading(fox_id)

    def peek(self, fox_id):
        # There's only one live RSSI value either way — reading() doesn't
        # simulate a walk here, it's a real measurement — so peek() and
        # reading() are the same call. Unlike FakeFoxRadio, looking at the
        # home screen can't accidentally walk anything toward "found".
        return self._reading(fox_id)

    def _reading(self, fox_id):
        rssi = lora.LINK.last_rssi(fox_id)
        if rssi is None:
            rssi = RSSI_FAR
        link = lora.LINK.link_quality(fox_id)
        return FoxReading(fox_id, rssi, self._level(fox_id, rssi), link=link)

    def submit_code(self, fox_id, code, on_result):
        otc = lora.code_to_otc(code)
        if otc is None:
            lora.defer(1, lambda: on_result("wrong"))
            return

        hid = _hunter_id()
        if hid is None:
            # No minted hunter_id — e.g. a verzamelaar (WiFi-only) somehow
            # reached the keypad, or registration hasn't landed yet. Nothing
            # to prove a claim with.
            lora.defer(1, lambda: on_result("wrong"))
            return

        fid = lora.LINK.last_fid(fox_id)
        if fid is None or not lora.LINK.ready:
            # Never heard this fox beacon (or the radio isn't up yet) — we
            # don't know its SEQ (§2.1) and can't address a CODE_ENTRY at it.
            # A hunter standing close enough to read a code off its display
            # will have heard it beacon too, outside its own deaf TX burst
            # (§4.4), so this is effectively the "walk closer" case.
            lora.defer(1, lambda: on_result("wrong"))
            return

        lora.LINK.submit_code(fid, hid, otc, on_result)


# Shared singleton — all screens talk to the same radio. Simulation is a
# desktop development tool, never a badge fallback: a Fri3d badge whose radio
# is absent or temporarily unresponsive must remain quiet, not invent nearby
# foxes, RSSI, packets, or successful codes. LoraFoxRadio reads LINK live, so a
# later WORD JAGER recovery immediately becomes usable without replacing this
# singleton.
RADIO = LoraFoxRadio() if lora.LINK.is_fri3d else FakeFoxRadio()
