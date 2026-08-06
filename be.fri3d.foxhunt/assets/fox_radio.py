# fox_radio.py — the STUB boundary for the real LoRa / ARDF backend.
#
# Someone else writes the real direction-finding. We program against this
# interface and ship a FakeFoxRadio that drives the whole UI on desktop.
# When the real radio lands, implement FoxRadio and swap the RADIO singleton.

import lvgl as lv
import random
from creatures import CREATURES

# Which beacons are transmitting right now (drives awake/dormant on home).
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


# Shared singleton — all screens talk to the same radio.
RADIO = FakeFoxRadio()
