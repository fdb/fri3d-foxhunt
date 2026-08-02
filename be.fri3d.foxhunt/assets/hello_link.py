# hello_link.py — the STUB boundary for badge-to-badge radio (the snuffel
# transport, GAME_DESIGN.md "Badge-to-badge radio: the hallo-spike").
#
# Same deal as fox_radio/registrar: screens program against HelloLink, the
# badge gets EspNowHelloLink (ESP-NOW broadcast on the ESP32's own radio —
# the badge IR is receive-only, so badge-to-badge is radio), and desktop gets
# FakeHelloLink, which fakes passers-by so the whole flow runs with no
# hardware. The singleton picks itself: espnow imports on the badge, not in
# the emulator.
#
# The spike carries one frame kind ("hello"); spoor/hapje/speeldate later ride
# the same wire with new kinds.

import lvgl as lv

# ── wire format (pure functions, host-testable) ────────────────────────────
#
#   FXH1|hello|Noor|H2A084C3
#   ^    ^     ^    ^
#   |    |     |    +-- companion shortcode (companion.encode)
#   |    |     +------- player name, sanitised, max NAME_MAX chars
#   |    +------------- frame kind; only "hello" exists today
#   +------------------ magic + wire version
#
# ASCII, pipe-separated: trivially inside ESP-NOW's 250-byte payload, and
# readable in a packet dump — this protocol is *meant* to be reverse-
# engineered by Saturday (see GAME_DESIGN.md, adversarial risks).

MAGIC = "FXH1"
KIND_HELLO = "hello"
NAME_MAX = 24

BROADCAST = b"\xff" * 6
CHANNEL = 6  # agreed channel for badges not on camp WiFi
_POLL_MS = 250  # drain the receive queue at 4 Hz
_BEAT_MS = 2000  # rebroadcast our hello every 2 s while listening


def clean_name(name):
    """A name fit for the wire: no field separator, no newlines, bounded."""
    name = str(name or "").replace("|", " ").replace("\n", " ").strip()
    return name[:NAME_MAX]


def encode_hello(name, shortcode):
    """(name, companion shortcode) -> the hello frame as bytes."""
    return "|".join((MAGIC, KIND_HELLO, clean_name(name), shortcode)).encode()


def decode(frame):
    """Frame bytes -> {"kind", "name", "companion"}, or None for anything that
    isn't ours. Foreign ESP-NOW traffic shares the ether; ignoring it quietly
    is correctness, not politeness."""
    try:
        parts = frame.decode().split("|")
    except (UnicodeError, AttributeError):
        return None
    if len(parts) != 4 or parts[0] != MAGIC:
        return None
    _, kind, name, shortcode = parts
    if kind != KIND_HELLO:
        return None  # future kinds: unknown today, not an error
    return {"kind": kind, "name": name, "companion": shortcode}


# ── the boundary ───────────────────────────────────────────────────────────


class HelloLink:
    """While started, broadcasts our hello on a heartbeat and hands every
    hello heard to on_hello(peer) — peer = {"id", "name", "companion"}, id
    being a stable per-badge key (the sender MAC) for dedup/counting.
    Callbacks arrive on the LVGL timer thread, so screens may touch widgets."""

    transport = "?"  # short label for the UI ("ESP-NOW" / "SIM")

    def start(self, me, on_hello):
        """me = {"name", "companion"}; begin listening + heartbeating."""
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def say_hello(self):
        """Broadcast one hello right now (the ZEG HALLO button)."""
        raise NotImplementedError


class EspNowHelloLink(HelloLink):
    """The badge: ESP-NOW broadcast. Symmetric — every badge just shouts and
    listens; no AP/client roles, no pairing.

    SPIKE-LEVEL RADIO OWNERSHIP: we activate the STA interface ourselves and
    restore it on stop. If MicroPythonOS grows a WiFi manager that owns the
    interface, route through it instead — same rule as pins."""

    transport = "ESP-NOW"

    def __init__(self):
        # Import here so the module-level factory can catch the desktop case.
        import network
        import espnow

        self._network = network
        self._espnow = espnow
        self._e = None
        self._sta_was_active = False
        self._frame = b""
        self._on_hello = None
        self._poll = None
        self._beat = None

    def start(self, me, on_hello):
        self.stop()
        self._frame = encode_hello(me.get("name"), me.get("companion", ""))
        self._on_hello = on_hello

        sta = self._network.WLAN(self._network.STA_IF)
        self._sta_was_active = sta.active()
        sta.active(True)
        if not sta.isconnected():
            # Unassociated badges meet on the agreed channel; an associated
            # badge sits wherever camp WiFi put it (the spike's field question).
            try:
                sta.config(channel=CHANNEL)
            except OSError:
                pass

        self._e = self._espnow.ESPNow()
        self._e.active(True)
        self._e.add_peer(BROADCAST)

        self._poll = lv.timer_create(lambda _t: self._drain(), _POLL_MS, None)
        self._beat = lv.timer_create(lambda _t: self.say_hello(), _BEAT_MS, None)
        self.say_hello()

    def stop(self):
        for t in (self._poll, self._beat):
            if t:
                t.delete()
        self._poll = self._beat = None
        if self._e:
            try:
                self._e.active(False)
            except OSError:
                pass
            self._e = None
        if not self._sta_was_active:
            # We switched the radio on; switch it back off. A radio that was
            # already up (camp WiFi) is someone else's and stays untouched.
            try:
                self._network.WLAN(self._network.STA_IF).active(False)
            except OSError:
                pass
        self._on_hello = None

    def say_hello(self):
        if not self._e:
            return
        try:
            self._e.send(BROADCAST, self._frame, False)
        except OSError:
            pass  # a dropped hello is fine; the heartbeat retries in 2 s

    def _drain(self):
        # recv(0) returns (None, None) when the queue is empty — drain it all
        # so a burst of badges doesn't back up at 4 Hz.
        while self._e:
            mac, msg = self._e.recv(0)
            if not msg:
                return
            hello = decode(msg)
            if hello and self._on_hello:
                peer_id = ":".join("%02X" % b for b in mac)
                self._on_hello(
                    {
                        "id": peer_id,
                        "name": hello["name"],
                        "companion": hello["companion"],
                    }
                )


class FakeHelloLink(HelloLink):
    """Desktop: no radio, so a small cast of fake passers-by stands in.

    simulate_hello() injects the next cast member — wired to the H key on the
    snuffeltest screen, and callable from the stdin REPL:
        import hello_link; hello_link.LINK.simulate_hello()
    say_hello() also gets one simulated answer after a beat (someone heard
    you), so the button demonstrates the whole loop unprompted. The cast
    cycles, so repeats exercise the heard-count path."""

    transport = "SIM"
    ANSWER_MS = 600
    CAST = (
        ("Noor", "H2A084C3"),
        ("Sam", "H1A011C4"),
        ("Lotte", "H4A140C2"),
        ("Ilias", "H5A020C6"),
    )

    def __init__(self):
        self._on_hello = None
        self._next = 0

    def start(self, me, on_hello):
        self._on_hello = on_hello

    def stop(self):
        self._on_hello = None

    def say_hello(self):
        t = lv.timer_create(lambda _t: self.simulate_hello(), self.ANSWER_MS, None)
        t.set_repeat_count(1)

    def simulate_hello(self):
        if not self._on_hello:
            return
        name, shortcode = self.CAST[self._next % len(self.CAST)]
        self._next += 1
        # Same path as the real link: through the wire format and back, so a
        # frame the badge couldn't parse can't sneak through the emulator.
        hello = decode(encode_hello(name, shortcode))
        self._on_hello(
            {
                "id": "SIM:%s" % name,
                "name": hello["name"],
                "companion": hello["companion"],
            }
        )


def _make_link():
    try:
        return EspNowHelloLink()
    except ImportError:
        return FakeHelloLink()


# Shared singleton — the snuffeltest screen talks to this.
LINK = _make_link()
