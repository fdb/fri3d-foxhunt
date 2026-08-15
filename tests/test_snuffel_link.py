import importlib.util
import sys
import types
import unittest
from pathlib import Path


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"


def load_link():
    creatures = types.ModuleType("creatures")
    creatures.by_id = lambda _cid: None
    spec = importlib.util.spec_from_file_location(
        "snuffel_link_under_test", ASSETS / "snuffel_link.py"
    )
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get("creatures")
    sys.modules["creatures"] = creatures
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            del sys.modules["creatures"]
        else:
            sys.modules["creatures"] = previous
    return module


class SnuffelLinkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_link()

    def receiver(self, rssi=-48):
        link = self.module.EspNowLink.__new__(self.module.EspNowLink)
        self.module.BaseLink.__init__(link)
        link._my_mac = "aa:aa:aa:aa:aa:aa"
        link._rssi_of = lambda _mac: rssi
        return link

    def sender(self):
        class Radio:
            def __init__(self):
                self.sent = []

            def send(self, _destination, payload, _sync):
                self.sent.append(payload)

            def recv(self, _timeout):
                return None, None

        link = self.module.EspNowLink.__new__(self.module.EspNowLink)
        self.module.BaseLink.__init__(link)
        link._now = Radio()
        link._my_mac = "bb:bb:bb:bb:bb:bb"
        link._session = "session-b"
        link.set_identity("Mila", "H01A000C1", [1], [1], False)
        return link

    def test_claim_in_presence_completes_handshake_when_snf_frames_are_lost(self):
        sender = self.sender()
        sender.claim("aa:aa:aa:aa:aa:aa")
        sender.tick()

        # Simulate the observed loss pattern: presence arrives, but the
        # separate unacknowledged SNF broadcast does not.
        presence = next(p for p in sender._now.sent if p.startswith(b"VJ1|HI|"))
        receiver = self.receiver()
        sender_mac = bytes.fromhex("bbbbbbbbbbbb")
        receiver._on_frame(sender_mac, presence)

        self.assertEqual(receiver.close_peer().mac, "bb:bb:bb:bb:bb:bb")

    def test_claim_in_presence_still_requires_the_receiver_to_measure_closeness(self):
        link = self.receiver(rssi=-70)
        sender = bytes.fromhex("bbbbbbbbbbbb")

        link._on_frame(
            sender,
            b"VJ1|HI|Mila|H01A000C1|1|session-b|1|V|aa:aa:aa:aa:aa:aa",
        )

        self.assertIsNone(link.close_peer())

    def test_original_snf_mirror_packet_still_completes_handshake(self):
        link = self.receiver()
        sender = bytes.fromhex("bbbbbbbbbbbb")
        link._on_frame(sender, b"VJ1|HI|Mila|H01A000C1|1|session-b|1|V|")

        link._on_frame(sender, b"VJ1|SNF|aa:aa:aa:aa:aa:aa")

        self.assertEqual(link.close_peer().mac, "bb:bb:bb:bb:bb:bb")


if __name__ == "__main__":
    unittest.main()
