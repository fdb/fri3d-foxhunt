# fox_radio.py — the STUB boundary for the real LoRa / ARDF backend.
#
# Someone else writes the real direction-finding. We program against this
# interface and ship a FakeFoxRadio that drives the whole UI on desktop.
# When the real radio lands, implement FoxRadio and swap the RADIO singleton.

import random
from creatures import CREATURES

# Which beacons are transmitting right now (drives awake/dormant on home).
_AWAKE = (0, 1, 3, 4)


class FoxReading:
    def __init__(self, fox_id, level, strength, found, bearing=None):
        self.fox_id = fox_id
        self.level = level          # 0..5 discrete hot/cold -> the 5 LEDs
        self.strength = strength    # 0.0..1.0 continuous   -> bpm
        self.found = found          # close enough -> reveal the code entry
        self.bearing = bearing      # degrees; present but UI ignores it (classic ARDF)


class FoxRadio:
    def active_foxes(self):            raise NotImplementedError
    def reading(self, fox_id):         raise NotImplementedError
    def verify_code(self, fox_id, c):  raise NotImplementedError


class FakeFoxRadio(FoxRadio):
    """Simulates honing in on a fox: strength drifts upward (with noise) the
    longer you 'search', so on desktop the hunt reaches 'found' in a few
    seconds with no hardware. bump() lets a key nudge it warmer/colder."""

    def __init__(self):
        self._strength = {}
        self._found_ticks = {}

    def active_foxes(self):
        ids = {c["id"] for c in CREATURES}
        return [b for b in _AWAKE if b in ids]

    def start(self, fox_id):
        self._strength[fox_id] = 0.12
        self._found_ticks[fox_id] = 0

    def bump(self, fox_id, delta):
        s = self._strength.get(fox_id, 0.12) + delta
        self._strength[fox_id] = max(0.0, min(1.0, s))

    def reading(self, fox_id):
        s = self._strength.get(fox_id, 0.12)
        s += random.uniform(-0.04, 0.10)        # drift up, with jitter
        s = max(0.0, min(1.0, s))
        self._strength[fox_id] = s
        level = int(round(s * 5))
        hot = s >= 0.85
        ticks = self._found_ticks.get(fox_id, 0) + 1 if hot else 0
        self._found_ticks[fox_id] = ticks
        return FoxReading(fox_id, level, s, ticks >= 3)

    def verify_code(self, fox_id, code):
        for c in CREATURES:
            if c["id"] == fox_id:
                return str(code) == c["code"]
        return False


# Shared singleton — all screens talk to the same radio.
RADIO = FakeFoxRadio()
