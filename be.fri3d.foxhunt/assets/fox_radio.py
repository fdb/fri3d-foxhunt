# fox_radio.py — the STUB boundary for the real LoRa / ARDF backend.
#
# Someone else writes the real direction-finding. We program against this
# interface and ship a FakeFoxRadio that drives the whole UI on desktop.
# When the real radio lands, implement FoxRadio and swap the RADIO singleton.

import lvgl as lv
import random
from creatures import CREATURES

# Which beacons are transmitting right now (drives awake/dormant on home).
_AWAKE = (0, 1, 4, 6, 10, 12)


class FoxReading:
    # NB: no "found" flag — RSSI can't tell you you've physically reached the
    # box. The player decides when to enter the code. We only report signal.
    def __init__(self, fox_id, level, strength, bearing=None):
        self.fox_id = fox_id
        self.level = level  # 0..5 discrete hot/cold -> the 5 LEDs
        self.strength = strength  # 0.0..1.0 continuous   -> bpm
        self.bearing = bearing  # degrees; present but UI ignores it (classic ARDF)


class FoxRadio:
    def active_foxes(self):
        raise NotImplementedError

    def reading(self, fox_id):
        raise NotImplementedError

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
        return FoxReading(fox_id, int(round(s * 5)), s)

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
