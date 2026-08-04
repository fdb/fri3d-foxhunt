# pluk_radio.py — the plukken backend: passive scan for `fri3d-badge` APs.
#
# The badge only LISTENS: no beacon hardware exists for the game, no frames
# are sent. The terrain's hotspots all broadcast the same SSID, so a spot's
# identity is its BSSID — which also means anyone can run their own hotspot
# and harvest from it. Deliberate: food is local state, so that is a fair
# hack, not an exploit (GAME_DESIGN.md, Plukken).
#
# Same seam pattern as fox_radio.py: a real WifiPlukRadio where the hardware
# cooperates, a FakePlukRadio that drives the whole UI on desktop.

import random

SSID = "fri3d-badge"
PLUK_LEVEL = 4  # harvestable at meter level >= 4 (about -55 dBm)


def _level(rssi):
    """dBm -> the 5-segment hot/cold meter. -85 is the edge of usable,
    -45 is standing next to it — same span the snuffel bars use."""
    return max(0, min(5, int((rssi + 85) / 8 + 0.5)))


class PlukReading:
    def __init__(self, bssid, rssi):
        self.bssid = bssid  # "aa:bb:cc:dd:ee:ff" — the spot's identity
        self.rssi = rssi
        self.level = _level(rssi)


def yield_for(bssid, date):
    """What a spot gives today: deterministic in (BSSID, day), so every spot
    re-deals daily and rescanning can never reroll a harvest. 1-3 hapjes."""
    h = 0
    for ch in bssid + date:
        h = (h * 31 + ord(ch)) & 0xFFFF
    foods = ("bes", "noot", "eikel")
    out = {f: 0 for f in foods}
    primary = foods[h % 3]
    out[primary] = 1 + (h >> 4) % 2
    second = foods[(h >> 2) % 3]
    if second != primary and (h >> 6) % 2:
        out[second] = 1
    return out


class WifiPlukRadio:
    """Scan the real STA interface. A scan can fail transiently (radio busy,
    mid-association); we return the last good result rather than raising —
    the plukscherm polls, so a hiccup just skips a beat."""

    def __init__(self, wlan):
        self._wlan = wlan
        self._last = []

    def scan(self):
        try:
            if not self._wlan.active():
                self._wlan.active(True)
            found = []
            for net in self._wlan.scan():
                # (ssid, bssid, channel, RSSI, security, hidden)
                if net[0] == SSID.encode():
                    mac = ":".join("%02x" % b for b in net[1])
                    found.append(PlukReading(mac, net[3]))
            found.sort(key=lambda r: -r.rssi)
            self._last = found
        except Exception:
            pass
        return self._last


class FakePlukRadio:
    """Two fake spots on desktop: one you 'walk toward' (drifts warmer, like
    FakeFoxRadio), one that stays at the edge of range. bump() lets a REPL
    nudge the walk."""

    def __init__(self):
        self._near = -82.0  # the spot being walked toward

    def bump(self, delta_dbm):
        self._near = max(-90.0, min(-40.0, self._near + delta_dbm))

    def scan(self):
        self._near = min(-42.0, self._near + random.uniform(-1.0, 3.5))
        far = -80 + random.uniform(-4, 4)
        return [
            PlukReading("fa:ke:00:00:00:01", int(self._near)),
            PlukReading("fa:ke:00:00:00:02", int(far)),
        ]


def _make():
    try:
        import network

        return WifiPlukRadio(network.WLAN(network.STA_IF))
    except Exception:
        return FakePlukRadio()


# Shared singleton — the pluk screen and the home stat talk to the same radio.
RADIO = _make()
