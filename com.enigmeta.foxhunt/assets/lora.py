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
# NO THREADS. main.py's radio_thread proved why not: the SX1262 driver holds
# CS low across a busy-wait and one SPI transaction per byte, and the ST7789
# display shares the same SPI host (see main.py's header comment and
# sx1262_spi_patch.md). A second thread can get a display flush clocked into
# a selected radio mid-transaction. There is no such window here — this
# module is only ever entered from LVGL timer callbacks, i.e. from inside
# lv_timer_handler() on the one and only thread, interleaved with (never
# concurrent with) the display's own flush timer. That is the whole fix.
#
# The radio is put into continuous receive once, at import time (see LINK.
# start() at the bottom), and stays there. A CODE_ENTRY send leaves RX just
# long enough to clock out ~31 ms of airtime (§7) and returns to it — see
# _transmit().
#
# THERE IS NO INTERNAL POLLING LOOP EITHER. LINK.poll() does one round of
# "is a packet waiting? read it; is the chip healthy? tick the claim" and
# returns — it is meant to be called from a screen's own existing tick
# timer, first thing, before that screen touches any widget. That is what
# actually guarantees no bus conflict: the whole poll (and any TX it
# triggers) runs to completion before the tick goes on to do LVGL work, on
# the same call stack, on the one UI thread. A second always-on lv.timer
# polling independently of the screen timers would still be safe from a
# genuine SPI race (nothing here is concurrent), but it loses the "poll,
# then draw, in that order, every tick" guarantee that makes the ordering
# obviously correct rather than incidentally correct — so screens_hunt.py's
# HuntActivity and CodeActivity call LINK.poll() (via RADIO.poll()) from
# their own ticks instead.

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

RF_SW_PIN = 46  # fri3d_2026: high = receive path enabled
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

# Bit values taken from sx1262.py (kept local rather than importing the
# underscore-prefixed constants — see main.py, same convention).
IRQ_RX_ANY = 0b0000000010 | 0b0000100000 | 0b0001000000  # RX_DONE|HEADER_ERR|CRC_ERR
IRQ_TX_DONE = 0b0000000001
IRQ_TX_ANY = IRQ_TX_DONE | 0b1000000000  # TX_DONE|TIMEOUT

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
        self.sent_at = 0
        self.done = False
        self._send()

    def _send(self):
        self.attempts += 1
        self.sent_at = time.ticks_ms()
        self.link._transmit(build_code_entry(self.fid, self.hid, self.otc))

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
        """Called once, at import (see bottom of file) -- "the start of the
        app" for every practical purpose, since fox_radio is the first thing
        any screen touches the radio through."""
        try:
            from mpos import LoRaManager, DeviceInfo
        except Exception as e:
            print("lora: mpos.LoRaManager unavailable (%r) -- desktop?" % e)
            return

        self.radio = LoRaManager.radioChip
        if self.radio is None:
            print("lora: no LoRa radio fitted (LoRaManager.radioChip is None)")
            return
        self._patch_busy_timeout()  # before ANY SPI traffic -- see constant above

        # MicroPythonOS constructs a driver object even when the antenna kit
        # is absent. Prove an SX1262 answers before treating that object as a
        # fitted radio: an open bus reads 0xFF on a badge without the radio
        # daughterboard, and recovery attempts against it needlessly pulse the
        # expander before falling back. This is the same read-only
        # presence probe registrar.has_lora() uses; 0 and 1 are the chip's
        # valid GFSK and LoRa packet-type replies.
        try:
            packet_type = self.radio.getPacketType()
        except Exception as e:
            print("lora: radio presence probe failed:", repr(e))
            return
        if packet_type not in (0, 1):
            print("lora: no responding SX1262 (packet type %r)" % packet_type)
            return
        self.available = True

        self.is_fri3d = DeviceInfo.hardware_id == "fri3d_2026"
        if self.is_fri3d:
            try:
                from machine import Pin

                self.rf_sw = Pin(RF_SW_PIN, Pin.OUT)
                self.rf_sw.value(1)
            except Exception as e:
                print("lora: could not drive RF switch pin:", repr(e))

        # Deferred, not blocking: configuring the radio while LVGL is still
        # animating the screen transition puts 40 MHz display traffic on the
        # shared bus mid-SPI-transaction (see module header). A one-shot
        # lv.timer costs nothing and needs no thread.
        t = lv.timer_create(lambda _t: self.bring_up(), SETTLE_MS, None)
        t.set_repeat_count(1)

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

    def bring_up(self, allow_hard_reset=True):
        detail = "not attempted"
        for attempt in range(3):
            try:
                self.configure()
            except Exception as e:
                detail = "configure raised: %r" % e
                print("lora: attempt %d %s" % (attempt + 1, detail))
                if allow_hard_reset and self.hard_reset():
                    detail += " (after hard reset)"
                time.sleep_ms(200)
                continue

            ok, detail = self.verify()
            print("lora: verify:", detail)
            if ok:
                self.ready = True
                self._last_health_check = time.ticks_ms()
                return True
            if allow_hard_reset:
                self.hard_reset()
            time.sleep_ms(200)

        print("lora: radio setup failed after 3 attempts:", detail)
        self.ready = False
        return False

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
            # begin() ends with setDio2AsRfSwitch(True); this board drives
            # the RF switch itself (RF_SW_PIN), not via DIO2.
            self.radio.setDio2AsRfSwitch(False)
            if self.rf_sw is not None:
                self.rf_sw.value(1)

    def hard_reset(self):
        """Pulse the SX1262 reset via the CH32 expander -- fri3d_2026 has no
        ESP32-side reset pin (see main.py). The only way to un-wedge the
        radio on this board."""
        try:
            import mpos

            expander = getattr(mpos, "io_expander", None)
        except Exception:
            expander = None
        if expander is None:
            print("lora: no io_expander, cannot hard reset")
            return False
        try:
            expander.config = EXPANDER_LORA_HELD
            time.sleep_ms(20)
            expander.config = EXPANDER_LORA_RUN
            time.sleep_ms(50)
            self._resets += 1
            print("lora: pulsed LoRa reset via expander (reset #%d)" % self._resets)
            return True
        except Exception as e:
            print("lora: hard reset failed:", repr(e))
            return False

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
            print("lora: radio not responding (BUSY stuck?), hard resetting")
            self.hard_reset()
            return self.bring_up(allow_hard_reset=False)

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
    # to touch LVGL. That ordering, not anything below, is what keeps this
    # off the display's bus at the wrong moment.

    def poll(self):
        if not self.ready:
            return
        try:
            if self.rx_pending():
                self.read_packet()
            elif (
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
        irq = self.radio.getIrqStatus()
        if not (irq & IRQ_RX_ANY):
            self._consecutive_rejects = 0
            return False

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
            return False

        self._consecutive_rejects = 0
        return True

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
        §7), then return to it. Runs inline from poll()/_Claim -- always the
        same call stack, so there is nothing else on this SPI bus to race."""
        if not self.ready:
            return
        try:
            self.radio.send(bytes(data))  # non-blocking: queues the TX and
            # returns once the BUSY line clears -- that covers issuing the
            # command, not the transmission, so poll IRQ for the real done.
            deadline = time.ticks_add(time.ticks_ms(), TX_DEADLINE_MS)
            while time.ticks_diff(deadline, time.ticks_ms()) > 0:
                if self.radio.getIrqStatus() & IRQ_TX_ANY:
                    break
                time.sleep_ms(2)
            self.radio.clearIrqStatus()
            self.radio.startReceive()  # back to continuous RX
        except Exception as e:
            print("lora: transmit failed:", repr(e))
            self.soft_recover()

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
# mode at the start of the app". On desktop (no LoRaManager / no radio
# fitted) start() just leaves `available` False and fox_radio.py falls back
# to FakeFoxRadio, same as it always has.
LINK = LoRaLink()
LINK.start()
