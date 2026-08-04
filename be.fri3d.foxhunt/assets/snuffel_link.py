# snuffel_link.py — the snuffelen backend: ESP-NOW presence + handshake.
#
# Ported from the espnow-test experiment (ESP_NOW_FINDINGS.md). Deliberately
# UI-free — no lvgl import — so the whole receive path is drivable from the
# REPL with synthetic packets, the same discipline as registrar.py.
#
# Radio truths baked in here (all measured on two badges):
# - Both badges must share a WiFi channel; a badge on camp WiFi is pinned to
#   its AP's channel and cannot move. So snuffel mode DISCONNECTS (keeping
#   the radio up), pins the fixed camp-wide channel, and restores WiFi on
#   stop(). Both players entering the mode is consent AND physics.
# - RSSI is read by the receiver's own radio, never carried in the payload,
#   so closeness cannot be claimed by a forged frame. It is also noisy and
#   non-monotonic, so the CLOSE verdict must hold over several consecutive
#   beacons before the game acts on it.
# - Frames are unauthenticated: everything here may create LOCAL, forgiving
#   state only. Public score would need the two-sided attestation the
#   findings describe — not built yet.
#
# Wire format (ASCII, pipe-separated, one line, <250 bytes):
#   VJ1|HI|<naam>|<shortcode>|<roster csv>     broadcast, ~1/s
# Identity is the MAC the frame arrived on; names are display only. The
# handshake carries no payload: everything a snuffel yields (food, the
# vonk-geluk creature) is derived locally from the HI roster.

import random

PROTO = b"VJ1"
CLOSE_DBM = -50  # the consent boundary (findings section 4)
CLOSE_STREAK = 6  # consecutive close readings before the handshake fires
CHANNEL = 1  # fixed camp-wide snuffel channel: every badge must agree
_BROADCAST = b"\xff\xff\xff\xff\xff\xff"
_GONE_S = 6  # drop a peer this long after its last beacon


class Peer:
    def __init__(self, mac, naam, code, roster):
        self.mac = mac  # "aa:bb:..." — the identity
        self.naam = naam  # display only
        self.code = code  # companion shortcode
        self.roster = roster  # creature ids they carry (for vonk-geluk)
        self.rssi = -99
        self.age = 0  # ticks since last beacon
        self.streak = 0  # consecutive CLOSE readings

    @property
    def close(self):
        return self.rssi >= CLOSE_DBM


class BaseLink:
    """Shared peer bookkeeping; subclasses supply the radio."""

    def __init__(self):
        self.peers = {}
        self.naam = "?"
        self.code = ""
        self.roster = []

    def set_identity(self, naam, code, roster):
        self.naam = naam or "?"
        self.code = code or ""
        self.roster = list(roster or [])

    def _seen(self, mac, naam, code, roster, rssi):
        p = self.peers.get(mac)
        if p is None:
            p = self.peers[mac] = Peer(mac, naam, code, roster)
        p.naam, p.code, p.roster = naam, code, roster
        p.rssi = rssi
        p.age = 0
        p.streak = p.streak + 1 if p.close else 0

    def _age_out(self, ticks):
        for mac in list(self.peers):
            p = self.peers[mac]
            p.age += 1
            if p.age > ticks:
                del self.peers[mac]

    def sorted_peers(self):
        return sorted(self.peers.values(), key=lambda p: -p.rssi)

    def close_peer(self):
        """The peer the handshake should fire with: CLOSE held for a full
        streak. One at a time — the strongest wins if several qualify."""
        for p in self.sorted_peers():
            if p.streak >= CLOSE_STREAK:
                return p
        return None


class EspNowLink(BaseLink):
    """The real thing. start() applies the verified airdrop-mode recipe from
    the findings (disconnect WITHOUT deactivating, then the channel is
    settable); stop() restores WiFi in all cases."""

    def __init__(self):
        super().__init__()
        import espnow
        import network

        self._sta = network.WLAN(network.STA_IF)
        self._now = espnow.ESPNow()
        self._now.active(True)
        try:
            self._now.add_peer(_BROADCAST)
        except OSError:
            pass  # already registered
        self._network = network

    def start(self):
        try:
            self._sta.active(True)
            self._sta.disconnect()  # NOT active(False): that kills ESP-NOW
            self._sta.config(channel=CHANNEL)
            self._sta.config(pm=self._network.WLAN.PM_NONE)  # no modem sleep
        except Exception as e:
            print("snuffel: start:", e)

    def stop(self):
        self.peers = {}
        try:
            import _thread
            from mpos.net.wifi_service import WifiService

            _thread.start_new_thread(WifiService.auto_connect, ())
        except Exception as e:
            print("snuffel: wifi restore:", e)

    def tick(self):
        try:
            roster = ",".join(str(c) for c in self.roster[:24])
            msg = b"|".join(
                (PROTO, b"HI", self.naam.encode(), self.code.encode(), roster.encode())
            )
            self._now.send(_BROADCAST, msg, False)  # broadcast: never acked
            while True:
                mac, payload = self._now.recv(0)  # drain without blocking
                if mac is None:
                    break
                self._on_frame(mac, payload)
        except Exception as e:
            print("snuffel: tick:", e)
        self._age_out(_GONE_S * 2)  # ~2 ticks/s
        return self.peers

    def _on_frame(self, mac, payload):
        parts = payload.split(b"|")
        if len(parts) < 2 or parts[0] != PROTO or parts[1] != b"HI":
            return  # other ESP-NOW traffic in the field is harmless
        macs = ":".join("%02x" % b for b in mac)
        naam = parts[2].decode() if len(parts) > 2 else "?"
        code = parts[3].decode() if len(parts) > 3 else ""
        roster = []
        if len(parts) > 4 and parts[4]:
            for tok in parts[4].decode().split(","):
                try:
                    roster.append(int(tok))
                except ValueError:
                    pass
        # RSSI comes from OUR radio's peers_table, never from the payload.
        rssi = -99
        try:
            entry = self._now.peers_table.get(mac)
            if entry:
                rssi = entry[0]
        except Exception:
            pass
        self._seen(macs, naam, code, roster, rssi)


class FakeLink(BaseLink):
    """Desktop: Sam walks up to you (ramps into CLOSE, so the handshake
    fires by itself after ~8 s), Nora hovers mid-range, Wout at the edge."""

    _CAST = (
        ("Sam", "H1A003C3", (0, 2, 5), -75, 4.5),  # (start dBm, ramp/tick)
        ("Nora", "H2A103C4", (1, 3), -68, 0.0),
        ("Wout", "H3A200C0", (0,), -78, 0.0),
    )

    def __init__(self):
        super().__init__()
        self._rssi = {}

    def start(self):
        self._rssi = {}

    def stop(self):
        self.peers = {}

    def tick(self):
        for i, (naam, code, roster, base, ramp) in enumerate(self._CAST):
            mac = "fa:ke:%02x:00:00:%02x" % (i, i)
            r = self._rssi.get(mac, float(base)) + ramp + random.uniform(-2.5, 2.5)
            r = max(-90.0, min(-42.0, r))
            self._rssi[mac] = r
            self._seen(mac, naam, code, list(roster), int(r))
        return self.peers


def _make():
    try:
        return EspNowLink()
    except Exception:
        return FakeLink()


# Shared singleton — one radio, however many screens look at it.
LINK = _make()
