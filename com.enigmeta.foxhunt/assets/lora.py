# lora.py — the real radio. Everything that touches the SX1262 or the wire
# format from foxhunt-spec.md lives here; fox_radio.py only adapts LINK to
# the FoxRadio contract every screen already codes against.
#
# HUNTER SIDE ONLY (spec §6.2). This app never plays fox or central: it never
# beacons, never relays FOUND/ACK, and never needs the TDMA slot schedule
# (§4). It does two things over the air —
#   RX continuous: BEACON (§3.1), to read RSSI per creature for the hunt/home
#                  screens, and PROOF/PENDING/FAIL (§3.3, §3.3b), the replies
#                  to a claim.
#   TX briefly:    CODE_ENTRY (§3.2), low power, when the player submits a
#                  code (§5.2 step 1, from our side).
#
# NO RADIO THREAD. main.py's radio_thread proved why not: the SX1262 driver
# holds CS low across a busy-wait and one SPI transaction per byte, and the
# ST7789 display shares the same SPI host (see main.py's header comment and
# sx1262_spi_patch.md). A second Python thread can get a display flush clocked
# into a selected radio mid-transaction. Keeping radio entry on LVGL's thread
# prevents that CPU-side overlap. Display DMA can still outlive the widget call
# that scheduled it, so poll-first ordering and avoiding redundant redraws
# reduce the remaining overlap window; they do not make the shared bus atomic.
#
# The radio is put into continuous receive once, at import time (see LINK.
# start() at the bottom), and stays there. A CODE_ENTRY send leaves RX just
# long enough to clock out ~31 ms of airtime (§7) and returns to it — see
# _transmit().
#
# THERE IS NO INTERNAL POLLING LOOP EITHER. LINK.poll() does one round of
# "is a packet waiting? read it; is the chip healthy? tick the claim" and
# returns — it is meant to be called from a screen's own existing tick
# timer, first thing, before that screen touches any widget. The whole poll
# (and any TX it triggers) therefore returns before that same tick asks LVGL
# for more display work. A second always-on lv.timer would lose even this
# deterministic poll-then-draw ordering, so screens_hunt.py's HuntActivity and
# CodeActivity call LINK.poll() (via RADIO.poll()) from their own ticks instead.
# The first CODE_ENTRY starts from the keypad callback after its final widget
# update; retries run from poll(), before HuntActivity's widget work. Neither
# ordering is an exclusive lock against DMA launched by an earlier flush.

import time
from collections import deque

import lvgl as lv

# ─────────────────────────── radio parameters (spec §7, all nodes fixed) ───
FREQ_MHZ = 869.4625
BW_KHZ = 125.0
SF = 7
CR = 5  # 4/5; the driver takes the denominator, RadioLib convention
SYNC_WORD = 0x12  # expands to 0x1424, RadioLib's private sync word
PREAMBLE = 8
TCXO_V = 3.0  # this board's TCXO (fri3d_2026); the XIAO carrier wants 1.8V
CURRENT_LIMIT = 140.0  # copied from the known-working main.py bring-up; the
# spec's 120 mA (§7) is sized for HP (+14 dBm) TX,
# which this app never does — LP (§7, -9 dBm, the
# SX1262 minimum) is the only power CODE_ENTRY ever
# uses, so 140 mA is harmless headroom, not a risk.
LP_POWER = 4  # dBm; hunter devices only ever transmit at LP (spec §6.2)

RF_SW_PIN = 46  # fri3d_2026: high = Wio module RF-switch gate enabled;
# internal DIO2 selects TX versus RX and stays under driver control
REG_LORA_SYNC_WORD_MSB = 0x0740
PACKET_TYPE_LORA = 0x01
MODE_RX = 5
CHIP_MODES = {2: "STBY_RC", 3: "STBY_XOSC", 4: "FS", 5: "RX", 6: "TX"}

SETTLE_MS = 1000  # let the activity transition finish before touching SPI
# Suggested cadence for whoever calls LINK.poll() from their own tick — tight
# enough to keep up with ~30 ms airtime packets (§3) without demanding it.
# HuntActivity already ticks at this rate for its own reasons (screens_hunt.py).
SUGGESTED_POLL_MS = 250
MODE_CHECK_MS = 1000  # real elapsed time between health checks, not a
# call count — poll() is called at whatever cadence
# each screen's own tick happens to run at
MAX_REJECTS_BEFORE_RESET = 20  # ~0.5 s of unreadable status before re-arming
TX_DEADLINE_MS = 120  # generous vs. 31.0 ms airtime (§3) for TX_DONE to land

# sx1262.py's SPItransfer() waits for the chip's BUSY pin with a hardcoded
# `timeout=5000` (ms) default -- TWICE per command (its own comment: once
# before CS goes low, once after) -- and nothing in the call chain we use
# (getStatus, getIrqStatus, readRegister, SPIwriteCommand, SPIreadCommand)
# forwards a timeout up to its caller, so there is no legitimate parameter
# to lower it with. We don't own that file (see _patch_busy_timeout, called
# from start()), so this is a monkeypatched INSTANCE override, not a driver
# change. 5000ms is sized to eventually give up on a genuinely dead chip,
# not to stay responsive: BUSY on a healthy SX126x clears in the low single
# digit milliseconds even for the slowest operations (calibration, TCXO
# startup) -- this leaves that generous headroom while cutting how long a
# truly wedged chip takes to be noticed (health_check's chip_mode(), and
# every rx_pending() poll -- measured at 5000-5003ms per call before this
# fix) from seconds down to a fraction of one. Tune upward if a real board
# legitimately needs longer for some command this app happens to exercise.
SPI_BUSY_TIMEOUT_MS = 300
RESET_HOLD_MS = 200
RESET_RELEASE_MS = 200
RECOVERY_RETRY_MS = 200
RECOVERY_ATTEMPTS = 2

# Bit values taken from sx1262.py (kept local rather than importing the
# underscore-prefixed constants — see main.py, same convention).
IRQ_RX_ANY = 0b0000000010 | 0b0000100000 | 0b0001000000  # RX_DONE|HEADER_ERR|CRC_ERR
IRQ_TX_DONE = 0b0000000001
IRQ_TX_ANY = IRQ_TX_DONE | 0b1000000000  # TX_DONE|TIMEOUT
_RX_EMPTY = 0
_RX_READY = 1
_RX_SUSPECT = 2

# CH32 expander config byte (fri3d_2026 only; see main.py):
#   bit 4 = LoRa reset (1 = released)   bit 1 = LCD reset   bit 0 = AUX 3v3
EXPANDER_LORA_HELD = 0x03
EXPANDER_LORA_RUN = 0x13

STALE_MS = 90000  # ~1.7x the biggest example T_CYCLE (52s @ N_SLOTS=4, §4.1).
# A fox this quiet is out of range, off, or orphaned (§4.3.4)
# — not worth showing as "awake" to the player.

LQ_PERIOD_MS = 300  # nominal fox broadcast cadence. Not part of the wire
# format itself, just what the 5-LED "link quality"
# meter (fox_radio.FoxReading.link) counts against.
LQ_WINDOW_MS = 5 * LQ_PERIOD_MS  # trailing window link_quality() scans

# ───────────────────────────── wire format (spec §3) ────────────────────────
TYPE_BEACON = 0x1
TYPE_CODE_ENTRY = 0x2
TYPE_PROOF = 0x3
TYPE_FOUND = 0x4  # fox<->central only; hunter overhears and ignores it
TYPE_ACK = 0x5  # fox<->central only; hunter overhears and ignores it
TYPE_PENDING = 0x6
TYPE_FAIL = 0x7


def _fid_char(fid):
    """CHAR (game creature id) out of a full FID byte (§2.1)."""
    return (fid >> 3) & 0x1F


def _fid_seq(fid):
    """SEQ (slot number) out of a full FID byte (§2.1). 0 = central node."""
    return fid & 0x07


def build_code_entry(fid, hid, otc):
    """§3.2. HID is big-endian on the wire; OTC is the raw byte, never the
    4-digit rendering (§6.4 converts before this is called)."""
    return bytes(
        [TYPE_CODE_ENTRY << 4, fid & 0xFF, (hid >> 8) & 0xFF, hid & 0xFF, otc & 0xFF]
    )


def _parse(msg):
    """A (kind, ...) tuple for the message types the hunter cares about, or
    None for anything malformed or none of our business (FOUND/ACK, or a
    fox/central packet too short to be one of ours)."""
    if len(msg) < 2:
        return None
    kind = (msg[0] >> 4) & 0xF
    if kind == TYPE_BEACON:
        return ("beacon", msg[1])
    if kind in (TYPE_PROOF, TYPE_PENDING, TYPE_FAIL) and len(msg) >= 4:
        fid = msg[1]
        hid = (msg[2] << 8) | msg[3]
        return (kind, fid, hid)
    return None


# ────────────────────── OTC codec (spec §6.4) ───────────────────────────────
# Ported from byte_codec_6_.py (byte_to_code / code_to_byte); only the
# directions the hunter needs. byte_codec_6_.py itself is not part of the
# app — the fox/central side owns generation, this is display-typed-code ->
# wire-byte only, plus the canonical re-encode check §6.4 requires.


def _byte_to_code(byte_val):
    if not 0 <= byte_val <= 255:
        return -1
    b1 = (byte_val >> 5) & 0x7
    b2 = (byte_val >> 2) & 0x7
    b3 = byte_val & 0x7
    checksum = b1 ^ b2 ^ b3
    d1 = b1 + 2
    d2 = b2 + 1
    d3 = b3
    return d1 * 1000 + d2 * 100 + d3 * 10 + checksum


def _code_to_byte(code):
    if not 2100 <= code <= 9877:
        return -1
    d1, d2, d3, d4 = [int(c) for c in str(code)]
    b1, b2, b3 = d1 - 2, d2 - 1, d3
    if not all(0 <= x <= 7 for x in (b1, b2, b3)):
        return -1
    if d4 != (b1 ^ b2 ^ b3):
        return -1
    return (b1 << 5) | (b2 << 2) | b3


def code_to_otc(code):
    """4-digit code as typed -> raw OTC byte, or None if invalid.

    Checks the checksum AND the canonical round-trip: 512 codes pass the
    checksum but only 256 are reachable by encoding a real byte (§6.4), so a
    decode is trusted only if re-encoding it reproduces the same code.
    """
    try:
        code = int(code)
    except (TypeError, ValueError):
        return None
    b = _code_to_byte(code)
    if b < 0:
        return None
    if _byte_to_code(b) != code:
        return None
    return b


# ───────────────────────────── claim state machine (spec §5.2/§5.3) ────────
# Hunter-side half only: we send CODE_ENTRY and wait. The fox->central->fox
# FOUND/ACK exchange (§5.1, §5.4) is entirely someone else's problem; we only
# see its outcome as PENDING, then PROOF or FAIL, or silence.
#
# The FoxRadio contract (fox_radio.py) has four verdicts: "ok", "wrong",
# "used", "busy". The real protocol has no signal for "used" distinct from
# "wrong" — a stale code (already claimed, since rotated) gets exactly the
# same silent ignore as a mistyped one (§6.1, §5.5) — so this never reports
# "used"; that collapses to "wrong", same as a pre-PENDING timeout (the fox
# never confirmed it heard us at all, so a genuinely wrong code and an
# unreachable fox are indistinguishable, per §5.5).
#
# A *post*-PENDING failure is different: the fox already confirmed the code
# was right and proximity was OK, so whatever went wrong happened in the
# FOUND/ACK round trip with the central, not with what the player typed.
# That's "busy", matching §5.3's "on FAIL or timeout -> network busy —
# press to retry", kept apart from "wrong" so the player isn't told their
# correct code was wrong.
T_PEND_INITIAL = 3000  # ms; no PENDING yet on the first send -> start
# repeating CODE_ENTRY (§5.3)
T_CODE_RETRY_INTERVAL = 1000  # ms between repeats after that (§5.3 "1 s intervals")
N_CODE_RETRY = 5  # max CODE_ENTRY attempts before giving up (§5.3)
T_TX_DEFER_MAX = 3000  # ms a continuously suspect RX latch may defer TX;
# enough for transient validation noise to settle without making the claim
# immortal when the status bus remains unreadable
T_VERIFY_HUNTER = 8500  # ms after PENDING to wait for PROOF/FAIL. Spec's
# own §5.2 fox-side T_VERIFY is 12s, so this is
# deliberately shorter than that margin: chosen for
# a snappier UI at the cost of occasionally showing
# "wrong" for a claim that was genuinely still in
# flight and would have succeeded a moment later
# (the late PROOF/FAIL is then silently dropped by
# on_packet's self.done check). Trade accepted.


class _Claim:
    """One in-flight CODE_ENTRY exchange. Exactly one at a time — the keypad
    is dead while waiting (screens_hunt.CodeActivity.waiting) — so LINK holds
    at most one of these, ticked from LINK.poll() (see module header)."""

    def __init__(self, link, fid, hid, otc, on_result):
        self.link = link
        self.fid = fid
        self.hid = hid
        self.otc = otc
        self.on_result = on_result
        self.attempts = 0
        self.pending_seen = False
        self.pending_at = 0
        self.sent_at = time.ticks_ms()
        self.tx_deferred_at = None
        self.done = False
        self._send()

    def _send(self):
        sent_at = self.link._transmit(build_code_entry(self.fid, self.hid, self.otc))
        if sent_at is None:
            if self.tx_deferred_at is None:
                self.tx_deferred_at = time.ticks_ms()
            return
        self.tx_deferred_at = None
        self.attempts += 1
        # Preserve the protocol's send-time retry anchor while allowing a
        # blocked preflight to leave both the deadline and attempt count
        # untouched. The inner TX_DONE deadline is separately anchored
        # after radio.send() returns in _transmit().
        self.sent_at = sent_at

    def on_packet(self, kind, fid, hid):
        if self.done or fid != self.fid or hid != self.hid:
            return
        if kind == TYPE_PENDING:
            self.pending_seen = True
            self.pending_at = time.ticks_ms()
        elif kind == TYPE_PROOF:
            self._finish("ok")
        elif kind == TYPE_FAIL:
            # The fox keeps the OTC valid and would accept an immediate
            # resend (§5.2 step 4), but this UI has no instant-retry
            # affordance -- CodeActivity just clears the entry, so the
            # player's next keypress starts a fresh claim. PENDING was
            # already seen for this claim, so the code itself was fine --
            # this is the central round trip failing, not the player.
            self._finish("busy")

    def tick(self):
        if self.done:
            return
        now = time.ticks_ms()
        if not self.pending_seen:
            if self.tx_deferred_at is not None and (
                time.ticks_diff(now, self.tx_deferred_at) >= T_TX_DEFER_MAX
            ):
                self._finish("wrong")
                return
            timeout = T_PEND_INITIAL if self.attempts == 1 else T_CODE_RETRY_INTERVAL
            if time.ticks_diff(now, self.sent_at) >= timeout:
                if self.attempts >= N_CODE_RETRY:
                    self._finish("wrong")  # never even got PENDING -- give up
                else:
                    self._send()
            return
        if time.ticks_diff(now, self.pending_at) >= T_VERIFY_HUNTER:
            self._finish("busy")  # PENDING but no PROOF/FAIL -- network stalled

    def _finish(self, result):
        self.done = True
        if self.link._claim is self:
            self.link._claim = None
        self.on_result(result)


def defer(ms, fn):
    """Call fn() once, ms from now, off an lv.timer -- never synchronously.
    Used for verdicts LINK can resolve immediately (bad code, no radio),
    which still owe callers the same asynchronous contract as a real claim."""
    t = lv.timer_create(lambda _t: fn(), max(ms, 1), None)
    t.set_repeat_count(1)


# ───────────────────────────────── the link ─────────────────────────────────
class LoRaLink:
    def __init__(self):
        self.radio = None
        self.rf_sw = None
        self.is_fri3d = False
        self.available = False  # a radio chip is fitted at all
        self.ready = False  # configured, verified, in continuous RX
        self._bring_up_scheduled = False
        self._recovery_active = False
        self._recovery_attempt = 0
        self._recovery_limit = 0
        self._reset_done = False
        self._status = "waiting"
        self._status_detail = "controle wordt gestart"

        self._last_health_check = 0
        self._consecutive_rejects = 0
        self._rejects = 0
        self._errors = 0
        self._stalls = 0
        self._resets = 0

        self._last_fid = {}  # char -> last full FID byte seen in a BEACON
        self._last_reading = {}  # char -> (rssi, ticks_ms) of that BEACON
        self._recv_times = {}  # char -> deque of ticks_ms for every BEACON
        # actually heard, pruned to LQ_WINDOW_MS.
        # Kept separate from _last_reading above,
        # which only remembers the single newest
        # sample -- link_quality() needs the whole
        # trailing set so it can literally count them.
        self._claim = None  # the one in-flight CODE_ENTRY, or None

    # ------------------------------------------------------------ lifecycle

    def start(self):
        """Discover the shared chip and schedule its first full bring-up."""
        try:
            from mpos import LoRaManager, DeviceInfo
        except Exception as e:
            print("lora: mpos.LoRaManager unavailable (%r) -- desktop?" % e)
            return

        self.is_fri3d = DeviceInfo.hardware_id == "fri3d_2026"
        self.radio = LoRaManager.radioChip
        if self.radio is None:
            print("lora: no LoRa radio fitted (LoRaManager.radioChip is None)")
            self._set_status("missing", "geen radioverbinding")
            return
        self._patch_busy_timeout()  # before ANY SPI traffic -- see constant above

        if self._packet_type() is not None:
            self._mark_available()
            self._set_status("starting", "instellingen laden")
            self._schedule_bring_up(lambda: self.request_recovery(False))
        else:
            # MicroPythonOS constructs this driver even when no daughterboard
            # is fitted. Do not pulse the shared CH32 expander merely because
            # the read-only presence probe found an open bus: on some cold
            # boots that can restart the badge. WORD JAGER remains the explicit
            # recovery path for a fitted but wedged SX1262.
            print("lora: no responding SX1262; waiting for explicit recovery")
            self._set_status("missing", "geen radioverbinding")

    def _packet_type(self):
        """A valid SX1262 packet type, or None for an unreadable/open bus."""
        try:
            packet_type = self.radio.getPacketType()
        except Exception as e:
            print("lora: radio presence probe failed:", repr(e))
            return None
        return packet_type if packet_type in (0, 1) else None

    def ensure_available(self):
        """Wake and re-probe an unreliable Fri3d SX1262.

        MicroPythonOS constructs the driver even when the daughterboard is
        absent, so the object existing proves nothing. Conversely, one failed
        SPI read does not prove absence: the fitted SX1262 can be wedged or
        still held in reset. A player explicitly choosing WORD JAGER therefore
        gets one bounded hardware reset. The reset must be followed by
        `begin()` -- a reset-only probe was measured still returning
        0xFF/0x00 on the badge. Only a failed full initialization counts as
        absent.

        This is intentionally callable again from WORD JAGER. A radio that was
        unavailable during the app import gets another honest recovery chance
        when the player explicitly asks for it.
        """
        if self.ready:
            return True
        if self.radio is None:
            return False
        if self._recovery_active:
            return False

        if self.available:
            self.request_recovery(False)
            return False

        if self._packet_type() is not None:
            self._mark_available()
            self._schedule_bring_up(lambda: self.request_recovery(False))
            return False
        if self.is_fri3d:
            self.request_recovery(True)
        return False

    def fitted(self):
        """Passive: does a radio look fitted right now? Never resets.

        The query half of ensure_available(), for screens that only DISPLAY
        the role (the register strip's JAGER/VERZAMELAAR). It reads state and
        at most one SPI register; it never pulses the shared CH32 expander,
        which on some cold boots restarts the whole badge. A fitted but
        wedged radio answers False here until WORD JAGER recovers it.
        """
        if self.ready or self.available:
            return True
        if self.radio is None:
            return False
        return self._packet_type() is not None

    def notice(self):
        """Friendly, compact radio state for the home screen.

        None means normal nearby-creature UI may be shown. The second line is
        deliberately useful when somebody photographs a failing badge in the
        field, without exposing driver names or exception text to a player.
        """
        if self.ready or not self.is_fri3d:
            return None
        title = {
            "waiting": "Wachten op LoRa",
            "resetting": "LoRa-chip resetten...",
            "starting": "LoRa starten...",
            "failed": "LoRa reageert niet",
            "missing": "Geen LoRa-chip aangesloten",
        }.get(self._status, "Wachten op LoRa")
        return (title, self._status_detail)

    def _set_status(self, status, detail):
        self._status = status
        self._status_detail = detail

    def _mark_available(self):
        self.available = True

        if self.is_fri3d:
            try:
                from machine import Pin

                if self.rf_sw is None:
                    self.rf_sw = Pin(RF_SW_PIN, Pin.OUT)
                self.rf_sw.value(1)
            except Exception as e:
                print("lora: could not drive RF switch pin:", repr(e))

    def _schedule_bring_up(self, fn):
        if not self._bring_up_scheduled:
            # Deferred, not blocking: configuring the radio while LVGL is
            # still animating the screen transition puts 40 MHz display
            # traffic on the shared bus mid-SPI-transaction (module header).
            self._bring_up_scheduled = True

            def _bring_up(_t):
                self._bring_up_scheduled = False
                fn()

            t = lv.timer_create(_bring_up, SETTLE_MS, None)
            t.set_repeat_count(1)

    def _later(self, ms, fn):
        t = lv.timer_create(lambda _t: fn(), max(1, ms), None)
        t.set_repeat_count(1)

    def request_recovery(self, reset_first=True):
        """Start one finite, timer-driven recovery and return immediately.

        Reset hold/release and retry delays used to be sleep_ms calls inside
        LVGL's callback. Keeping those phases on one-shot timers preserves the
        single-threaded shared-SPI guarantee while letting LVGL draw status and
        accept input between every phase. SPItransfer itself is separately
        bounded by SPI_BUSY_TIMEOUT_MS.
        """
        if self.radio is None or self._recovery_active:
            return False
        self.ready = False
        self._recovery_active = True
        self._recovery_attempt = 0
        self._reset_done = False
        if reset_first:
            self._begin_reset()
        else:
            # A chip which answered the probe gets one ordinary begin(). If
            # verification fails, _attempt_setup escalates to a full reset.
            self._recovery_limit = 1
            self._later(1, self._attempt_setup)
        return True

    def _expander(self):
        try:
            import mpos

            return getattr(mpos, "io_expander", None)
        except Exception:
            return None

    def _begin_reset(self):
        expander = self._expander()
        if expander is None:
            self._finish_recovery("reset niet beschikbaar")
            return
        self._set_status("resetting", "reset %d · even geduld" % (self._resets + 1))
        try:
            expander.config = EXPANDER_LORA_HELD
        except Exception as e:
            print("lora: reset assert failed:", repr(e))
            self._finish_recovery("reset lukt niet")
            return
        self._later(RESET_HOLD_MS, lambda: self._release_reset(expander))

    def _release_reset(self, expander):
        try:
            expander.config = EXPANDER_LORA_RUN
        except Exception as e:
            print("lora: reset release failed:", repr(e))
            self._finish_recovery("reset lukt niet")
            return
        self._later(RESET_RELEASE_MS, lambda: self._check_reset(expander))

    def _check_reset(self, expander):
        try:
            released = expander.config[0]
        except Exception as e:
            print("lora: reset readback failed:", repr(e))
            released = False
        if not released:
            self._finish_recovery("reset blijft actief")
            return
        self._resets += 1
        self._reset_done = True
        self._recovery_attempt = 0
        self._recovery_limit = RECOVERY_ATTEMPTS
        self._mark_available()  # configure() needs the board RF switch set
        print("lora: pulsed LoRa reset via expander (reset #%d)" % self._resets)
        self._later(1, self._attempt_setup)

    def _attempt_setup(self):
        self._recovery_attempt += 1
        self._set_status(
            "starting",
            "poging %d van %d · %d reset"
            % (self._recovery_attempt, self._recovery_limit, self._resets),
        )
        detail = "not attempted"
        try:
            self.configure()
            ok, detail = self.verify()
        except Exception as e:
            ok = False
            detail = "configure raised: %r" % e
        print("lora: setup attempt %d: %s" % (self._recovery_attempt, detail))
        if ok:
            self.available = True
            self.ready = True
            self._recovery_active = False
            self._last_health_check = time.ticks_ms()
            self._set_status("ready", "LoRa is klaar")
            return
        if self._recovery_attempt < self._recovery_limit:
            self._later(RECOVERY_RETRY_MS, self._attempt_setup)
            return
        if self.is_fri3d and not self._reset_done:
            self._begin_reset()
            return
        self._finish_recovery(self._friendly_failure(detail))

    def _friendly_failure(self, detail):
        if "DEAD" in detail or "raised" in detail or "sync=ffff" in detail.lower():
            return "geen antwoord · %d pogingen · %d reset" % (
                self._recovery_attempt,
                self._resets,
            )
        if "devErr=0x0000" not in detail:
            reason = "chip meldt een fout"
        elif "sync=1424" not in detail:
            reason = "instellingen niet goed"
        else:
            reason = "ontvangst start niet"
        return "%s · %d pogingen · %d reset" % (
            reason,
            self._recovery_attempt,
            self._resets,
        )

    def _finish_recovery(self, detail):
        self.available = False
        self.ready = False
        self._recovery_active = False
        self._set_status("failed", detail)
        print("lora: no responding SX1262 after restart and initialization")

    def _patch_busy_timeout(self):
        """Rebind sx1262.py's SPItransfer() BUSY-wait timeout down to
        SPI_BUSY_TIMEOUT_MS (see that constant for why) -- on this radio
        INSTANCE only, since sx1262.py itself isn't ours to edit.

        `orig` is grabbed while SPItransfer is still resolved through the
        class, so it comes back as a normal bound method (self already
        curried in). Assigning the wrapper onto self.radio.SPItransfer
        afterward puts a plain function in the INSTANCE's __dict__, which
        shadows the class method without going through the descriptor
        protocol -- so every internal self.SPItransfer(...) call inside
        sx1262.py (SPIreadCommand, SPIwriteCommand, readRegister) finds the
        instance attribute first and calls it as a plain function, no
        implicit self, which is exactly why the wrapper below doesn't take
        one either -- its parameter list has to match SPItransfer's own,
        self excluded.
        """
        try:
            orig = self.radio.SPItransfer
        except AttributeError:
            print("lora: SPItransfer not found, busy-timeout patch skipped")
            return

        def _fast_transfer(
            cmd,
            cmdLen,
            write,
            dataOut,
            dataIn,
            numBytes,
            waitForBusy,
            timeout=SPI_BUSY_TIMEOUT_MS,
        ):
            return orig(
                cmd, cmdLen, write, dataOut, dataIn, numBytes, waitForBusy, timeout
            )

        self.radio.SPItransfer = _fast_transfer

    def configure(self):
        self.radio.begin(
            freq=FREQ_MHZ,
            bw=BW_KHZ,
            sf=SF,
            cr=CR,
            syncWord=SYNC_WORD,
            preambleLength=PREAMBLE,
            implicit=False,
            crcOn=True,
            tcxoVoltage=TCXO_V,
            useRegulatorLDO=False,
            blocking=True,
            currentLimit=CURRENT_LIMIT,
            power=LP_POWER,
        )
        # No callback: drops straight into continuous receive (setRx
        # 0xFFFFFF) with DIO1 action cleared. We poll from LINK.poll(), never IRQ.
        self.radio.setBlockingCallback(False)

        if self.is_fri3d:
            # begin() ends with setDio2AsRfSwitch(True). Preserve it: the Wio
            # module keeps DIO2 internal and uses it to select TX (high) versus
            # RX (low). GPIO46 is the separate external gate, held high for
            # both directions while foxhunt owns the radio.
            if self.rf_sw is not None:
                self.rf_sw.value(1)

    def chip_mode(self):
        """None means the radio isn't answering -- getStatus() swallows SPI
        failures and returns 0x00, which is not a real mode."""
        status = self.radio.getStatus()
        if status in (0x00, 0xFF):
            return None
        return (status >> 4) & 0x07

    def verify(self):
        try:
            deverr = self.radio.getDeviceErrors()
            mode = self.chip_mode()
            sync = bytearray(2)
            self.radio.readRegister(REG_LORA_SYNC_WORD_MSB, memoryview(sync), 2)
        except Exception as e:
            return False, "readback raised: %r" % e

        detail = "mode=%s sync=%02x%02x devErr=0x%04x" % (
            "DEAD" if mode is None else CHIP_MODES.get(mode, mode),
            sync[0],
            sync[1],
            deverr,
        )
        ok = mode == MODE_RX and sync[0] == 0x14 and sync[1] == 0x24 and deverr == 0
        return ok, detail

    def health_check(self):
        """False means the radio is gone for good and polling should stop."""
        mode = self.chip_mode()
        if mode == MODE_RX:
            return True

        if mode is None:
            print("lora: radio not responding; scheduling a reset")
            self.request_recovery(True)
            return False

        self._stalls += 1
        print(
            "lora: found chip in %s, re-arming (stall #%d)"
            % (CHIP_MODES.get(mode, mode), self._stalls)
        )
        try:
            self.radio.startReceive()
        except Exception as e:
            print("lora: re-arm failed:", repr(e))
            return False
        return True

    # ---------------------------------------------------------------- poll
    #
    # No internal timer calls this — see module header. It is meant to be
    # the first thing a screen's own tick does, before any widget update, so
    # every SPI transaction this triggers (a read, or a health-check re-arm,
    # or a claim's CODE_ENTRY retry) finishes before that same tick goes on
    # to touch LVGL. That ordering narrows the asynchronous display-DMA overlap
    # window; it is not an exclusive bus lock (see module header).

    def poll(self):
        if not self.ready:
            return
        try:
            rx_state = self._rx_state()
            if rx_state == _RX_READY:
                self.read_packet()
            elif rx_state == _RX_EMPTY and (
                time.ticks_diff(time.ticks_ms(), self._last_health_check)
                >= MODE_CHECK_MS
            ):
                self._last_health_check = time.ticks_ms()
                if not self.health_check():
                    self.ready = False
        except Exception as e:
            print("lora: poll error:", repr(e))
            self.soft_recover()

        if self._claim is not None:
            self._claim.tick()

    def rx_pending(self):
        """True if a packet is really waiting. A corrupted read can set
        RX_DONE spuriously or garble the packet type, so a suspicious read is
        retried rather than acted on (see main.py). The IRQ stays latched
        through a rejection -- a real packet is never dropped, just picked
        up on a later poll."""
        return self._rx_state() == _RX_READY

    def _rx_state(self):
        """Classify the receive latch without conflating suspect with empty.

        _RX_SUSPECT deliberately preserves the IRQ and payload for another
        read. A transmitter must treat it as occupied: sx1262.py's send()
        would otherwise erase the packet this validation chose to keep.
        """
        irq = self.radio.getIrqStatus()
        if not (irq & IRQ_RX_ANY):
            self._consecutive_rejects = 0
            return _RX_EMPTY

        if (
            self.radio.getIrqStatus() != irq
            or self.radio.getPacketType() != PACKET_TYPE_LORA
        ):
            self._rejects += 1
            self._consecutive_rejects += 1
            if self._consecutive_rejects >= MAX_REJECTS_BEFORE_RESET:
                print(
                    "lora: %d consecutive unreadable status reads, re-arming"
                    % self._consecutive_rejects
                )
                self._consecutive_rejects = 0
                self.soft_recover()
            return _RX_SUSPECT

        self._consecutive_rejects = 0
        return _RX_READY

    def read_packet(self):
        try:
            msg, err = self.radio.recv()  # reads the buffer, re-arms RX
            if err != 0 or not msg:
                return
            # One GetPacketStatus read for RSSI: byte 0 is RssiPkt, half-dBm.
            status = self.radio.getPacketStatus()
            rssi = -((status >> 16) & 0xFF) / 2.0
            self._handle(msg, rssi)
        except Exception as e:
            self._errors += 1
            print("lora: read error:", repr(e))
            self.soft_recover()

    def _handle(self, msg, rssi):
        parsed = _parse(msg)
        if parsed is None:
            return  # malformed, or FOUND/ACK (fox<->central, not ours)
        if parsed[0] == "beacon":
            fid = parsed[1]
            if _fid_seq(fid) == 0:
                return  # central's own beacon (§3.1) -- not a creature, and
                # this app has no TDMA role to sync it against (§4)
            char = _fid_char(fid)
            now = time.ticks_ms()
            self._last_fid[char] = fid
            self._last_reading[char] = (rssi, now)
            times = self._recv_times.setdefault(char, deque((), 8))
            times.append(now)
            while times and time.ticks_diff(now, times[0]) > LQ_WINDOW_MS:
                times.popleft()
            return
        kind, fid, hid = parsed
        if self._claim is not None:
            self._claim.on_packet(kind, fid, hid)

    def soft_recover(self):
        try:
            self.radio.clearIrqStatus()
            self.radio.startReceive()
        except Exception as e:
            print("lora: soft recover failed:", repr(e))

    # ------------------------------------------------------------------ tx

    def _transmit(self, data):
        """Leave continuous RX just long enough to clock out one packet (LP,
        §7), then return to it. Runs inline from poll()/_Claim on the LVGL
        thread, so another Python radio call cannot interleave with it."""
        if not self.ready:
            return None
        attempted_at = None
        sent_at = None
        try:
            # Close the gap between poll()'s first IRQ read and a due claim
            # retry. sx1262.py writes TX at the same 0x00 buffer base as RX and
            # clears all IRQs inside send(), so an unread frame must be drained
            # before entering the driver. A matching PENDING/PROOF/FAIL makes
            # this retry redundant; an unrelated BEACON does not, so continue
            # on to send it rather than silently burning an attempt.
            claim = self._claim
            rx_state = self._rx_state()
            if rx_state == _RX_SUSPECT:
                return None
            if rx_state == _RX_READY:
                self.read_packet()
                if claim is not None and (claim.done or claim.pending_seen):
                    return None
            # The public driver call can raise before or after SetTx; it does
            # not expose that stage. Count any entered send() conservatively
            # as an air attempt so an ambiguous failure cannot exceed the
            # protocol's N_CODE_RETRY maximum.
            attempted_at = time.ticks_ms()
            self.radio.send(bytes(data))  # non-blocking: queues the TX and
            # returns once the BUSY line clears -- that covers issuing the
            # command, not the transmission, so poll IRQ for the real done.
            sent_at = time.ticks_ms()
            deadline = time.ticks_add(time.ticks_ms(), TX_DEADLINE_MS)
            while time.ticks_diff(deadline, time.ticks_ms()) > 0:
                if self.radio.getIrqStatus() & IRQ_TX_ANY:
                    break
                time.sleep_ms(2)
            self.radio.clearIrqStatus()
            self.radio.startReceive()  # back to continuous RX
            return sent_at
        except Exception as e:
            print("lora: transmit failed:", repr(e))
            self.soft_recover()
            return sent_at if sent_at is not None else attempted_at

    # --------------------------------------------------------------- reads

    def last_rssi(self, char):
        """Most recent BEACON RSSI for this creature, or None if we've never
        heard one or it's gone stale (§4.3.4-ish, from the hunter's view)."""
        r = self._last_reading.get(char)
        if r is None:
            return None
        rssi, seen = r
        if time.ticks_diff(time.ticks_ms(), seen) > STALE_MS:
            return None
        return rssi

    def last_fid(self, char):
        """Full FID byte last seen for this creature (has the real SEQ, see
        §2.1), or None if we've never heard it beacon. Kept even once stale
        -- SEQ doesn't change on its own, and it's the only way we can ever
        address a CODE_ENTRY at this fox."""
        fid = self._last_fid.get(char)
        return fid

    def link_quality(self, char):
        """How many BEACONs we've actually heard from this creature in the
        trailing LQ_WINDOW_MS (5 slots of its ~LQ_PERIOD_MS cadence)
        -- the 5-LED "link quality" meter's source value (screens_hunt.py).

        A plain sliding window, not a decay filter: each LQ_PERIOD_MS
        that passes without a fresh BEACON ages the oldest timestamp out of
        the window on its own, so the count -- and therefore the LEDs --
        fades from 5 down to 0 over the span the fox was actually silent
        for, and climbs back the same way once it resumes. No separate
        ramp/decay logic needed."""
        times = self._recv_times.get(char)
        if not times:
            return 0
        now = time.ticks_ms()
        while times and time.ticks_diff(now, times[0]) > LQ_WINDOW_MS:
            times.popleft()
        return min(len(times), 5)

    def active_chars(self):
        """Creatures heard beaconing recently -- this hunter's only source
        of "awake", since there is no compiled-in deployment list (§6.2)."""
        now = time.ticks_ms()
        return [
            c
            for c, (_, seen) in self._last_reading.items()
            if time.ticks_diff(now, seen) <= STALE_MS
        ]

    # ------------------------------------------------------------- claims

    def submit_code(self, fid, hid, otc, on_result):
        if self._claim is not None:
            self._claim = None  # superseded; its own on_result never fires
        self._claim = _Claim(self, fid, hid, otc, on_result)


# Shared singleton, started immediately: "set the LoRa in continuous receive
# mode at the start of the app". Desktop has no Fri3d hardware and uses the
# explicit simulator in fox_radio.py. A badge with no responding daughterboard
# stays on the real, quiet adapter -- it must never invent LoRa traffic.
LINK = LoRaLink()
LINK.start()
