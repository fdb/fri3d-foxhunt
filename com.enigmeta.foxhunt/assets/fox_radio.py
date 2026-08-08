# fox_radio.py — the STUB boundary for the real LoRa / ARDF backend.
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
    rising heart rate always means you are getting warmer.
    """
    return rssi + 255


def rssi_to_level(rssi):
    """0..5 discrete hot/cold for the LEDs — the same reading, coarsened."""
    lvl = int(round((rssi - RSSI_FAR) * 5 / (RSSI_NEAR - RSSI_FAR)))
    return max(0, min(5, lvl))


class FoxReading:
    # NB: no "found" flag — RSSI can't tell you you've physically reached the
    # box. The player decides when to enter the code. We only report signal.
    def __init__(self, fox_id, rssi, bearing=None):
        self.fox_id = fox_id
        self.rssi = rssi  # dBm, the one measured value
        self.level = rssi_to_level(rssi)  # 0..5 hot/cold -> the 5 LEDs
        self.bearing = bearing  # degrees; present but UI ignores it (classic ARDF)


class FoxRadio:
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
            "wrong" no such code for this fox
            "used"  right code, but it was already claimed (codes are one-time)
        """
        raise NotImplementedError


class FakeFoxRadio(FoxRadio):
    """Simulates honing in on a fox: strength drifts upward (with noise) the
    longer you 'search', so on desktop the hunt reaches 'found' in a few
    seconds with no hardware. bump() lets a key nudge it warmer/colder."""

    ROUND_TRIP_MS = 500  # what asking the network "costs", faked

    def __init__(self):
        self._strength = {}
        self._used = set()  # burnt one-time codes; the real server owns this

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
        return [b for b in _AWAKE if b in ids]

    def start(self, fox_id):
        self._strength[fox_id] = 0.12

    def bump(self, fox_id, delta):
        s = self._strength.get(fox_id, 0.12) + delta
        self._strength[fox_id] = max(0.0, min(1.0, s))

    def reading(self, fox_id):
        s = self._strength.get(fox_id, 0.12)
        s += random.uniform(-0.04, 0.10)  # drift up, with jitter
        s = max(0.0, min(1.0, s))
        self._strength[fox_id] = s
        return FoxReading(fox_id, int(round(RSSI_FAR + s * (RSSI_NEAR - RSSI_FAR))))

    def peek(self, fox_id):
        # No drift: reading() simulates walking toward the fox, and the home
        # row samples every awake fox on every resume — through reading(),
        # ~30 visits home pinned all the heat bars at maximum forever.
        s = self._strength.get(fox_id, 0.12)
        return FoxReading(fox_id, int(round(RSSI_FAR + s * (RSSI_NEAR - RSSI_FAR))))

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
        pass  # continuous RX already covers every fox at once; nothing to arm

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
        return FoxReading(fox_id, RSSI_FAR if rssi is None else rssi)

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


# Shared singleton — all screens talk to the same radio. LoraFoxRadio is
# used whenever lora.py found a fitted radio chip at import time (see that
# file's LINK.start()); otherwise this falls back to the fake, same as
# desktop always has.
RADIO = LoraFoxRadio() if lora.LINK.available else FakeFoxRadio()
