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
#
# THE SCAN NEVER RUNS ON THE UI THREAD. `wlan.scan()` is
# `esp_wifi_scan_start(&config, block=1)` — it sweeps every channel and does
# not return for 2-4 s. Called from the plukscherm's lv.timer it starved
# LVGL of input completely: no tap, no back-swipe, not even a raw REPL. The
# port releases the GIL around that call (network_wlan.c), so a worker
# thread scans while LVGL keeps drawing. `scan()` is therefore a cheap
# getter: it hands back the last published readings and makes sure a worker
# is alive.

import random
import time

SSID = "fri3d-badge"
_SSID_B = SSID.encode()
PLUK_LEVEL = 4  # harvestable at meter level >= 4 (about -55 dBm)

_MAX_SPOTS = 12  # keep the strongest few; a city block can show 40+
_SCAN_GAP_MS = 1500  # breather between sweeps. A sweep itself blocks the
# radio ~2.9 s; back-to-back sweeps pin the high-priority WiFi task at ~90%
# duty and starve everything below it — measurably the USB serial console,
# and it buys a hot/cold meter nothing. ~4.5 s per reading is plenty for a
# walking pace.
_IDLE_EXIT_MS = 5000  # worker retires once the screen stops asking
_STALE_MS = 20000  # nothing scanned this long -> report nothing, not a lie
_SMOOTH = 0.5  # per-BSSID RSSI smoothing: raw dBm jitters +-5 and would
# flicker the meter across the PLUK! threshold


def _level(rssi):
    """dBm -> the 5-segment hot/cold meter. -85 is the edge of usable,
    -45 is standing next to it — same span the snuffel bars use."""
    return max(0, min(5, int((rssi + 85) / 8 + 0.5)))


class PlukReading:
    def __init__(self, bssid, rssi, ssid=SSID):
        self.bssid = bssid  # "aa:bb:cc:dd:ee:ff" — the spot's identity
        self.rssi = rssi
        self.level = _level(rssi)
        self.ssid = ssid  # display only; differs from SSID in any-wifi debug


def yield_for(bssid, phase):
    """What a spot gives this camp phase: deterministic in (BSSID, phase), so
    every spot re-deals at 15:00 and rescanning cannot reroll it. 1-3 hapjes."""
    h = 0
    for ch in bssid + phase:
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
    """Scan the real STA interface, on a worker thread (see module header).

    A scan can fail transiently (radio busy, mid-association); we keep the
    last good result rather than raising — the plukscherm polls, so a hiccup
    just skips a beat. After _STALE_MS with no success we publish nothing,
    so a wedged radio reads as "geen plukplek" instead of a frozen meter.

    any_ssid is the debug switch (instellingen -> debug): accept EVERY named
    network instead of only `fri3d-badge`, so plukken is walkable anywhere
    there's WiFi — home, office — before the camp exists. Identity stays
    the BSSID, so reloads and daily yields work exactly as at camp.

    Hidden networks are never a plukplek, in either mode: the firmware asks
    for them (`config.show_hidden = true`) and reports them with an empty
    SSID, and its `hidden` tuple field is hardcoded False — so the empty
    name is the only honest signal. A spot you cannot name is not a place.
    """

    def __init__(self, wlan):
        self._wlan = wlan
        self._last = []
        self._smooth = {}  # bssid -> smoothed dBm, pruned to what's in view
        self._ok_ms = 0  # ticks_ms of the last successful scan
        self._asked_ms = 0  # ticks_ms of the last scan() call
        self._worker = False
        self._lock = None
        self.any_ssid = False
        try:
            import _thread

            self._thread = _thread
            self._lock = _thread.allocate_lock()
        except ImportError:
            self._thread = None

    # ── the UI side: cheap, never touches the radio ─────────────────────
    def scan(self):
        self._asked_ms = time.ticks_ms()
        self._pump()
        if time.ticks_diff(self._asked_ms, self._ok_ms) > _STALE_MS:
            return []
        return self._last

    def stop(self):
        """Retire the worker now. The plukscherm calls this on pause because
        a channel-hopping scan would wreck snuffelen, which pins the radio to
        one channel — leaving the worker to time out is too slow for that.
        ticks_add, not plain subtraction: ticks_ms() lives in a wrapping range
        and a bare negative is not a valid tick value, so ticks_diff on it
        returns nonsense and the worker would never see the signal."""
        self._asked_ms = time.ticks_add(time.ticks_ms(), -(_IDLE_EXIT_MS + 1))

    # ── the radio side ──────────────────────────────────────────────────
    def _pump(self):
        """Make sure exactly one worker is scanning. Without threads (some
        desktop builds) fall back to scanning inline — slow, but the screen
        still works."""
        if self._thread is None:
            self._scan_once()
            return
        with self._lock:
            if self._worker:
                return
            self._worker = True
        try:
            from mpos import TaskManager

            self._thread.stack_size(TaskManager.good_stack_size())
            self._thread.start_new_thread(self._run, ())
        except Exception as e:
            print("pluk: worker:", e)
            with self._lock:
                self._worker = False

    def _run(self):
        try:
            while time.ticks_diff(time.ticks_ms(), self._asked_ms) < _IDLE_EXIT_MS:
                self._scan_once()
                time.sleep_ms(_SCAN_GAP_MS)
        finally:
            with self._lock:
                self._worker = False

    def _scan_once(self):
        """One blocking sweep, guarded by the OS-wide WiFi busy flag so we
        never race auto_connect or the wifi app into a failed scan."""
        svc = None
        try:
            from mpos.net.wifi_service import WifiService

            svc = WifiService
        except Exception:
            pass
        if svc is not None:
            if svc.is_busy():
                return
            svc.wifi_busy = True
        try:
            if not self._wlan.active():
                self._wlan.active(True)
            nets = self._wlan.scan()
        except Exception:
            return
        finally:
            if svc is not None:
                svc.wifi_busy = False
        self._publish(nets)

    def _publish(self, nets):
        smooth, names = {}, {}
        for net in nets:
            ssid = net[0]
            if not ssid:
                continue  # hidden AP: no name, no plukplek
            if not self.any_ssid and ssid != _SSID_B:
                continue
            mac = ":".join("%02x" % b for b in net[1])
            prev = self._smooth.get(mac)
            smooth[mac] = net[3] if prev is None else prev + (net[3] - prev) * _SMOOTH
            try:
                names[mac] = ssid.decode()
            except Exception:
                names[mac] = "?"
        out = [PlukReading(m, int(r), names[m]) for m, r in smooth.items()]
        # sort on (rssi, bssid): MicroPython's sort is unstable, and a field
        # full of same-strength networks would otherwise reshuffle the lead
        # spot every sweep
        out.sort(key=lambda r: (-r.rssi, r.bssid))
        self._smooth = smooth
        self._last = out[:_MAX_SPOTS]
        self._ok_ms = time.ticks_ms()


class FakePlukRadio:
    """Two fake spots on desktop: one you 'walk toward' (drifts warmer, like
    FakeFoxRadio), one that stays at the edge of range. bump() lets a REPL
    nudge the walk."""

    def __init__(self):
        self._near = -82.0  # the spot being walked toward
        self.any_ssid = False  # accepted, ignored: the fake is always fake

    def bump(self, delta_dbm):
        self._near = max(-90.0, min(-40.0, self._near + delta_dbm))

    def stop(self):
        pass

    def scan(self):
        self._near = min(-42.0, self._near + random.uniform(-1.0, 3.5))
        far = -80 + random.uniform(-4, 4)
        return [
            PlukReading("fa:ce:00:00:00:01", int(self._near)),
            PlukReading("fa:ce:00:00:00:02", int(far)),
        ]


def _make():
    try:
        import network

        return WifiPlukRadio(network.WLAN(network.STA_IF))
    except Exception:
        return FakePlukRadio()


# Shared singleton — the pluk screen and the home stat talk to the same radio.
RADIO = _make()
