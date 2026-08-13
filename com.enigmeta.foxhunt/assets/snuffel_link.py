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
#   VJ1|HI|<naam>|<shortcode>|<roster csv>|<session>|<shareable csv>|<J/V>
#                                                    broadcast, ~1/s
#   VJ1|SNF|<peer mac>                         broadcast, a few /s for ~3 s
# Identity is the MAC the frame arrived on; names are display only. The
# handshake carries no payload: everything a snuffel yields (food, the
# vonk-geluk creature) is derived locally from the HI roster.
#
# SNF closes the handshake race: each side counts its own CLOSE streak, so
# without it both must complete within the same beacon — the first to finish
# used to go quiet on its payoff screen and starve the other. Now the
# finisher announces "I snuffelled <you>" and the named peer mirrors the
# handshake at once, if its own radio also reads that peer as nearby
# (INVITE_DBM). Both sides pay out from one completed streak.

import random
from creatures import by_id

PROTO = b"VJ1"
CLOSE_DBM = -50  # the consent boundary (findings section 4)
CLOSE_STREAK = 6  # consecutive close readings before the handshake fires
INVITE_DBM = -60  # accept a peer's SNF only if our radio reads them this close
ANNOUNCE_TICKS = 6  # keep resending SNF this many ticks (~3 s): frames drop
CHANNEL = 1  # fixed camp-wide snuffel channel: every badge must agree
_BROADCAST = b"\xff\xff\xff\xff\xff\xff"
_GONE_S = 6  # drop a peer this long after its last beacon


class Peer:
    def __init__(self, mac, naam, code, roster, session="", shareable=None, role="V"):
        self.mac = mac  # "aa:bb:..." — the identity
        self.naam = naam  # display only
        self.code = code  # companion shortcode
        self.roster = roster  # creature ids they carry (for vonk-geluk)
        self.shareable = list(roster if shareable is None else shareable)
        self.session = session  # random per visit; couples both geluk rolls
        self.is_hunter = role == "J"
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
        self.shareable = []
        self.is_hunter = False
        self._my_mac = ""
        self._session = ""
        self._announce = None  # [peer mac, ticks left] while resending SNF

    def claim(self, mac):
        """The screen fired the handshake with `mac`: announce it on the air
        for a few seconds so the peer's side fires too."""
        self._announce = [mac, ANNOUNCE_TICKS]

    def set_identity(self, naam, code, roster, shareable=None, is_hunter=False):
        self.naam = naam or "?"
        self.code = code or ""
        self.roster = list(roster or [])
        self.shareable = list(self.roster if shareable is None else shareable)
        self.is_hunter = bool(is_hunter)

    def encounter_key(self, peer):
        """A key both badges derive identically for this snuffel session."""
        ends = [
            "%s@%s" % (self._my_mac, self._session),
            "%s@%s" % (peer.mac, peer.session),
        ]
        ends.sort()
        return "|".join(ends)

    def _seen(
        self,
        mac,
        naam,
        code,
        roster,
        rssi,
        session="",
        shareable=None,
        role="V",
    ):
        # The name is untrusted air bytes bound only by frame size: truncate
        # it here, once, so it can neither overrun the peer row into the
        # DICHTBIJ pill nor bloat the vrienden list it gets persisted into.
        naam = (naam or "?")[:16]
        p = self.peers.get(mac)
        if p is None:
            # Cap the table: a spoofer cycling source MACs would otherwise
            # accumulate ~1200 Peer objects before aging caught up. Real
            # crowds fit; a full table just ignores NEW macs until age-out.
            if len(self.peers) >= 32:
                return
            p = self.peers[mac] = Peer(
                mac, naam, code, roster, session, shareable, role
            )
        p.naam, p.code, p.roster, p.session = naam, code, roster, session
        p.shareable = list(roster if shareable is None else shareable)
        p.is_hunter = role == "J"
        # Smoothed, same filter and same reason as pluk_radio._SMOOTH: raw
        # dBm jitters +-5, and the peer list sorts on this — two peers at
        # comparable range would swap order on most beacons, and every swap
        # makes the screen tear down and rebuild all four companion rows.
        p.rssi = rssi if p.rssi <= -99 else int(p.rssi + (rssi - p.rssi) * 0.5)
        p.age = 0
        p.streak = p.streak + 1 if p.close else 0

    def _age_out(self, ticks):
        for mac in list(self.peers):
            p = self.peers[mac]
            p.age += 1
            if p.age > ticks:
                del self.peers[mac]

    def sorted_peers(self):
        # mac tiebreak: MicroPython's sort is unstable, and equal-strength
        # peers would reshuffle every tick (same rule as pluk_radio._publish).
        return sorted(self.peers.values(), key=lambda p: (-p.rssi, p.mac))

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
            try:
                self._prev_pm = self._sta.config("pm")
            except Exception:
                self._prev_pm = None
            self._sta.config(pm=self._network.WLAN.PM_NONE)  # no modem sleep
            self._my_mac = ":".join("%02x" % b for b in self._sta.config("mac"))
            # getrandbits, NOT randrange(0x100000000): 2**32 exceeds what
            # MicroPython's randrange handles — on this unix build it spins
            # forever (freezing LVGL the moment the snuffel screen opens), and
            # 32-bit ports can't do better.
            self._session = "%08x" % random.getrandbits(32)
        except Exception as e:
            print("snuffel: start:", e)

    def stop(self):
        self.peers = {}
        # Undo what start() changed beyond the association: a stale SNF
        # announce must not broadcast on the first tick of the NEXT session,
        # and modem sleep stays disabled forever unless somebody restores it
        # — pm is a power knob, not a snuffel setting.
        self._announce = None
        prev_pm = getattr(self, "_prev_pm", None)
        if prev_pm is not None:
            try:
                self._sta.config(pm=prev_pm)
            except Exception:
                pass
        try:
            import _thread
            from mpos.net.wifi_service import WifiService

            def _restore():
                # auto_connect aborts silently when another WiFi operation
                # holds the busy flag — e.g. a pluk sweep still finishing
                # after PLUKKEN -> SNUFFELEN. Aborting here meant camp WiFi
                # was never restored, with no retry and nothing on screen.
                # Wait the flag out (an in-flight sweep is ~3 s) first.
                import time

                for _ in range(20):
                    if not WifiService.is_busy():
                        break
                    time.sleep_ms(500)
                WifiService.auto_connect()

            _thread.start_new_thread(_restore, ())
        except Exception as e:
            print("snuffel: wifi restore:", e)

    def tick(self):
        try:
            roster = ",".join(str(c) for c in self.roster[:24])
            shareable = ",".join(str(c) for c in self.shareable[:24])
            msg = b"|".join(
                (
                    PROTO,
                    b"HI",
                    self.naam.encode(),
                    self.code.encode(),
                    roster.encode(),
                    self._session.encode(),
                    shareable.encode(),
                    (b"J" if self.is_hunter else b"V"),
                )
            )
            self._now.send(_BROADCAST, msg, False)  # broadcast: never acked
            if self._announce:
                mac, left = self._announce
                self._now.send(
                    _BROADCAST, b"|".join((PROTO, b"SNF", mac.encode())), False
                )
                self._announce = [mac, left - 1] if left > 1 else None
            while True:
                mac, payload = self._now.recv(0)  # drain without blocking
                if mac is None:
                    break
                try:
                    self._on_frame(mac, payload)
                except Exception:
                    # A malformed frame (the ESP32 port raises UnicodeError
                    # on invalid UTF-8 in .decode()) must cost only itself:
                    # unwinding into the outer handler aborted the WHOLE
                    # drain, so a peer spamming garbage at a few frames/s
                    # held reception to one frame per tick — real peers
                    # never surfaced. Hacker camp: junk frames are the
                    # expected input, not the exotic one.
                    pass
        except Exception as e:
            print("snuffel: tick:", e)
        self._age_out(_GONE_S * 2)  # ~2 ticks/s
        return self.peers

    def _on_frame(self, mac, payload):
        parts = payload.split(b"|")
        if len(parts) < 2 or parts[0] != PROTO:
            return  # other ESP-NOW traffic in the field is harmless
        macs = ":".join("%02x" % b for b in mac)
        if parts[1] == b"SNF":
            # the peer's handshake fired with US: mirror it, even mid-streak.
            # Local forgiving state only, and gated on OUR radio's reading of
            # them (a forged frame cannot claim closeness) — but with margin
            # under CLOSE_DBM, because the two radios never read alike.
            target = parts[2].decode() if len(parts) > 2 else ""
            p = self.peers.get(macs)
            # `target and`: when start() failed, _my_mac is still "" — and a
            # bare "VJ1|SNF" broadcast would then match it and force a
            # handshake with whoever happens to be standing nearby.
            if (
                target
                and target == self._my_mac
                and p
                and self._rssi_of(mac) >= INVITE_DBM
            ):
                p.streak = max(p.streak, CLOSE_STREAK)
            return
        if parts[1] != b"HI":
            return
        naam = parts[2].decode() if len(parts) > 2 else "?"
        code = parts[3].decode() if len(parts) > 3 else ""
        roster = []
        if len(parts) > 4 and parts[4]:
            for tok in parts[4].decode().split(","):
                try:
                    roster.append(int(tok))
                except ValueError:
                    pass
        session = parts[5].decode() if len(parts) > 5 else ""
        shareable = []
        if len(parts) > 6 and parts[6]:
            for tok in parts[6].decode().split(","):
                try:
                    shareable.append(int(tok))
                except ValueError:
                    pass
        elif len(parts) <= 6:
            # Older badges advertised one combined roster without role/self
            # provenance. Base and rare remain safely compatible; legendary
            # must fail closed because its giver cannot be verified locally.
            shareable = [
                cid for cid in roster if by_id(cid) and by_id(cid)["rarity"] != "leg"
            ]
        role = parts[7].decode() if len(parts) > 7 else "V"
        self._seen(
            macs,
            naam,
            code,
            roster,
            self._rssi_of(mac),
            session,
            shareable,
            role,
        )

    def _rssi_of(self, mac):
        # RSSI comes from OUR radio's peers_table, never from the payload.
        try:
            entry = self._now.peers_table.get(mac)
            if entry:
                return entry[0]
        except Exception:
            pass
        return -99


class FakeLink(BaseLink):
    """Desktop: Sam walks up to you (ramps into CLOSE, so the handshake
    fires by itself after ~8 s), Nora hovers mid-range, Wout at the edge."""

    _CAST = (
        ("Sam", "H01A003C3", (0, 2, 5, 16), -75, 4.5, "J"),
        ("Nora", "H02A103C4", (1, 3), -68, 0.0, "V"),
        ("Wout", "H3A200C0", (0,), -78, 0.0, "J"),
    )

    def __init__(self):
        super().__init__()
        self._rssi = {}

    def start(self):
        self._rssi = {}
        self._my_mac = "fa:ke:ff:00:00:ff"
        # getrandbits, same reason as EspNowLink.start.
        self._session = "%08x" % random.getrandbits(32)

    def stop(self):
        self.peers = {}

    def tick(self):
        for i, (naam, code, roster, base, ramp, role) in enumerate(self._CAST):
            mac = "fa:ke:%02x:00:00:%02x" % (i, i)
            r = self._rssi.get(mac, float(base)) + ramp + random.uniform(-2.5, 2.5)
            r = max(-90.0, min(-42.0, r))
            self._rssi[mac] = r
            self._seen(
                mac,
                naam,
                code,
                list(roster),
                int(r),
                "cast-%02x" % i,
                list(roster),
                role,
            )
        return self.peers


def _make():
    try:
        return EspNowLink()
    except Exception:
        return FakeLink()


# Shared singleton — one radio, however many screens look at it.
LINK = _make()
