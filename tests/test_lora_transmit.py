"""SX1262 handoff regressions at the driver's destructive TX boundary.

The real 0.17.3 driver uses buffer base 0x00 for both RX and TX, writes the
outgoing bytes before SetTx, and clears every IRQ as part of startTransmit().
This fake intentionally destroys an unread receive when send() starts. A fake
that lets RX survive TX would hide the race these tests are meant to pin down.
"""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"


class FakeTime:
    def __init__(self):
        self.now = 0

    def ticks_ms(self):
        return self.now

    @staticmethod
    def ticks_diff(left, right):
        return left - right

    @staticmethod
    def ticks_add(value, delta):
        return value + delta

    def sleep_ms(self, milliseconds):
        self.now += milliseconds

    def advance(self, milliseconds):
        self.now += milliseconds


def load_lora():
    """Load lora.py without probing host hardware or creating LVGL timers."""
    lvgl = types.ModuleType("lvgl")
    lvgl.timer_create = MagicMock()
    mpos = types.ModuleType("mpos")
    mpos.LoRaManager = types.SimpleNamespace(radioChip=None)
    mpos.DeviceInfo = types.SimpleNamespace(hardware_id="fri3d_2026")

    spec = importlib.util.spec_from_file_location(
        "lora_transmit_under_test", ASSETS / "lora.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"lvgl": lvgl, "mpos": mpos}):
        spec.loader.exec_module(module)
    module.time = FakeTime()
    return module


class HandoffRadio:
    """One RX latch and one shared buffer, matching sx1262.py's semantics."""

    def __init__(self, lora):
        self.lora = lora
        self.time = lora.time
        self.irq = 0
        self.rx_payload = None
        self.inject_after_empty_read = None
        self.unstable_after_inject = False
        self.irq_read_overrides = []
        self.send_advance_ms = 0
        self.send_error = None
        self.sent = []
        self.overwritten = []
        self.events = []
        self.mode = "rx"

    def getIrqStatus(self):
        value = self.irq_read_overrides.pop(0) if self.irq_read_overrides else self.irq
        self.events.append("irq:%04x" % value)
        if value == 0 and self.inject_after_empty_read is not None:
            self.rx_payload = self.inject_after_empty_read
            self.inject_after_empty_read = None
            self.irq = self.lora.IRQ_RX_ANY & 0b0000000010
            if self.unstable_after_inject:
                # The next validation sees RX_DONE once and a mismatching
                # second read once, while the actual latch/payload stay put.
                self.irq_read_overrides = [self.irq, 0]
            self.events.append("inject-rx")
        return value

    def getPacketType(self):
        self.events.append("packet-type")
        return self.lora.PACKET_TYPE_LORA

    def getStatus(self):
        self.events.append("status")
        return self.lora.MODE_RX << 4

    def recv(self):
        self.events.append("recv")
        payload = self.rx_payload
        self.rx_payload = None
        self.irq = 0
        self.mode = "rx"
        return payload, 0

    def getPacketStatus(self):
        self.events.append("packet-status")
        return 80 << 16  # -40 dBm

    def send(self, data):
        self.events.append("send")
        if self.send_error is not None:
            raise self.send_error
        self.sent.append(bytes(data))
        if self.rx_payload is not None:
            self.overwritten.append(self.rx_payload)
            self.rx_payload = None
        # startTransmit() writes TX at 0x00 and clears the old RX IRQ before
        # TX_DONE can become visible.
        self.irq = 0
        self.mode = "tx"
        self.time.advance(self.send_advance_ms)
        self.irq = self.lora.IRQ_TX_DONE

    def clearIrqStatus(self):
        self.events.append("clear-irq")
        self.irq = 0

    def startReceive(self):
        self.events.append("start-rx")
        self.mode = "rx"


class LoRaTransmitTest(unittest.TestCase):
    def setUp(self):
        self.lora = load_lora()
        self.link = self.lora.LoRaLink()
        self.radio = HandoffRadio(self.lora)
        self.link.radio = self.radio
        self.link.available = True
        self.link.ready = True
        self.fid = (3 << 3) | 1
        self.hid = 0x1234
        self.otc = 0x5A

    def _submit_and_make_retry_due(self, results):
        self.link.submit_code(self.fid, self.hid, self.otc, results.append)
        self.assertEqual(len(self.radio.sent), 1)
        self.lora.time.advance(self.lora.T_PEND_INITIAL)
        # Keep this poll focused on RX and the claim. A health check is not
        # part of the race and would only add unrelated fake behavior.
        self.link._last_health_check = self.lora.time.ticks_ms()

    def _proof(self):
        return bytes(
            [
                self.lora.TYPE_PROOF << 4,
                self.fid,
                (self.hid >> 8) & 0xFF,
                self.hid & 0xFF,
                0,
            ]
        )

    def test_retry_drains_proof_arriving_between_poll_check_and_send(self):
        results = []
        self._submit_and_make_retry_due(results)
        event_start = len(self.radio.events)

        # poll() sees zero once; immediately after that read the packet and
        # RX_DONE latch appear, just before _Claim.tick() starts its retry.
        self.radio.inject_after_empty_read = self._proof()
        self.link.poll()

        retry_events = self.radio.events[event_start:]
        self.assertEqual(results, ["ok"])
        self.assertIsNone(self.link._claim)
        self.assertEqual(self.radio.overwritten, [])
        self.assertIn("recv", retry_events)
        self.assertNotIn("send", retry_events)
        self.assertEqual(len(self.radio.sent), 1)
        self.assertEqual(self.radio.mode, "rx")

    def test_unrelated_beacon_is_drained_without_burning_the_retry(self):
        results = []
        self._submit_and_make_retry_due(results)
        event_start = len(self.radio.events)
        beacon_fid = (5 << 3) | 2
        self.radio.inject_after_empty_read = bytes(
            [self.lora.TYPE_BEACON << 4, beacon_fid]
        )

        self.link.poll()

        retry_events = self.radio.events[event_start:]
        self.assertEqual(results, [])
        self.assertEqual(self.link.last_fid(5), beacon_fid)
        self.assertEqual(self.radio.overwritten, [])
        self.assertEqual(len(self.radio.sent), 2)
        self.assertEqual(self.link._claim.attempts, 2)
        self.assertLess(retry_events.index("recv"), retry_events.index("send"))
        self.assertEqual(self.radio.mode, "rx")

    def test_suspect_rx_blocks_tx_without_consuming_an_attempt(self):
        results = []
        self._submit_and_make_retry_due(results)
        proof = self._proof()
        event_start = len(self.radio.events)
        self.radio.inject_after_empty_read = proof
        self.radio.unstable_after_inject = True

        self.link.poll()

        blocked_events = self.radio.events[event_start:]
        self.assertNotIn("send", blocked_events)
        self.assertEqual(self.radio.overwritten, [])
        self.assertEqual(self.radio.rx_payload, proof)
        self.assertEqual(self.link._claim.attempts, 1)

        # The preserved latch is stable on the next poll, so the reply is
        # consumed and resolves the claim without any redundant retry.
        self.link.poll()
        self.assertEqual(results, ["ok"])
        self.assertIsNone(self.link._claim)
        self.assertEqual(len(self.radio.sent), 1)

    def test_suspect_rx_is_not_replaced_by_a_health_check(self):
        proof = self._proof()
        self.radio.rx_payload = proof
        self.radio.irq = self.lora.IRQ_RX_ANY & 0b0000000010
        self.radio.irq_read_overrides = [self.radio.irq, 0]
        self.lora.time.advance(self.lora.MODE_CHECK_MS)

        self.link.poll()

        self.assertNotIn("status", self.radio.events)
        self.assertEqual(self.radio.rx_payload, proof)
        self.assertEqual(self.radio.overwritten, [])

    def test_persistently_suspect_rx_still_has_a_bounded_claim_lifetime(self):
        results = []
        self._submit_and_make_retry_due(results)
        self.link._rx_state = lambda: self.lora._RX_SUSPECT

        self.link._last_health_check = self.lora.time.ticks_ms()
        self.link.poll()
        self.assertEqual(self.link._claim.attempts, 1)
        self.assertEqual(len(self.radio.sent), 1)

        self.lora.time.advance(self.lora.T_TX_DEFER_MAX)
        self.link._last_health_check = self.lora.time.ticks_ms()
        self.link.poll()

        self.assertEqual(results, ["wrong"])
        self.assertIsNone(self.link._claim)
        self.assertEqual(len(self.radio.sent), 1)

    def test_tx_done_deadline_is_anchored_after_slow_send_returns(self):
        self.radio.send_advance_ms = self.lora.TX_DEADLINE_MS + 25

        self.link.submit_code(self.fid, self.hid, self.otc, MagicMock())

        send_index = self.radio.events.index("send")
        self.assertTrue(
            any(
                event.startswith("irq:")
                for event in self.radio.events[send_index + 1 :]
            )
        )
        self.assertEqual(self.radio.events[-1], "start-rx")
        self.assertEqual(self.radio.mode, "rx")
        self.assertEqual(
            self.link._claim.sent_at,
            self.lora.TX_DEADLINE_MS + 25,
        )

    def test_ambiguous_send_failure_conservatively_consumes_an_air_attempt(self):
        self.radio.send_error = RuntimeError("SPI stopped at unknown TX stage")

        self.link.submit_code(self.fid, self.hid, self.otc, MagicMock())

        # send() does not report whether it failed before or after SetTx. The
        # safe bound is therefore to count entry as a possible air attempt;
        # otherwise repeated ambiguous failures could exceed N_CODE_RETRY.
        self.assertEqual(self.link._claim.attempts, 1)
        self.assertIsNone(self.link._claim.tx_deferred_at)
        self.assertEqual(self.radio.sent, [])
        self.assertEqual(self.radio.mode, "rx")


if __name__ == "__main__":
    unittest.main()
