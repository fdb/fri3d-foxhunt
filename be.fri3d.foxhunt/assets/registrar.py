# registrar.py — the STUB boundary for the registration transport.
#
# The real thing WiFi-POSTs the profile to the cloud server
# (server/: POST /api/v1/auth/register {badge_id, name}) and asks the LoRa
# bridge to mint a hunter id over the air. Same deal as fox_radio: we program
# against Registrar, ship a FakeRegistrar that drives the whole UI on desktop,
# and swap the REGISTRAR singleton when the backend lands.

import lvgl as lv
import random


def badge_id():
    """The badge's MAC, "A4:CF:..." — machine.unique_id() on the badge, a
    fixed fake on desktop (no machine module) so the UI stays drivable."""
    try:
        import machine

        return ":".join("%02X" % b for b in machine.unique_id())
    except Exception:
        return "A4:CF:12:9B:03:7E"


def has_lora():
    """True when a LoRa radio is configured (antenna installed)."""
    try:
        from mpos import LoRaManager

        return LoRaManager.radioChip is not None
    except Exception:
        return False


class Registrar:
    def register(self, name, badge, on_update):
        """Send the profile to the cloud server and the LoRa bridge.

        ASYNCHRONOUS BY CONTRACT (see FoxRadio.submit_code): progress arrives
        later through on_update(status), never as a return value. status:

            "cloud" / "bridge" / "hunter": "wait"|"busy"|"ok"|"fail"|"skip"
            "hunter_id": the minted id (with hunter ok), else None
            "done": True on the terminal update
            "ok": (with done) the whole registration succeeded
            "error": (with done, not ok) "E-01" cloud down | "E-02" bridge down

        Without a LoRa antenna the bridge/hunter steps report "skip" and the
        cloud save alone counts as success.
        """
        raise NotImplementedError

    def recover(self, badge, on_result):
        """Ask the cloud for the profile saved under this badge id (a player
        getting their data back after a badge reset — HERSTEL in settings).
        Asynchronous like register: on_result(profile_dict) with the stored
        profile, or on_result(None) when the server knows nothing."""
        raise NotImplementedError


class FakeRegistrar(Registrar):
    """Fakes the round trips with one-shot lv timers, like FakeFoxRadio."""

    STEP_MS = 700
    SIMULATE_LORA = True  # desktop has no radio; pretend, so the flow is testable
    FAIL_BRIDGE = False  # flip to walk the E-02 error path
    FAKE_BACKUP = None  # set to a profile dict to walk the HERSTEL success path

    def recover(self, badge, on_result):
        t = lv.timer_create(lambda _t: on_result(self.FAKE_BACKUP), self.STEP_MS, None)
        t.set_repeat_count(1)

    def register(self, name, badge, on_update):
        st = {
            "cloud": "busy",
            "bridge": "wait",
            "hunter": "wait",
            "hunter_id": None,
            "done": False,
            "ok": False,
            "error": None,
        }
        lora = has_lora() or self.SIMULATE_LORA

        def push():
            on_update(dict(st))

        def at(ms, fn):
            t = lv.timer_create(lambda _t: fn(), ms, None)
            t.set_repeat_count(1)

        def cloud_done():
            st["cloud"] = "ok"
            if not lora:
                st["bridge"] = "skip"
                st["hunter"] = "skip"
                st["done"] = st["ok"] = True
                push()
                return
            st["bridge"] = "busy"
            push()
            at(self.STEP_MS + 300, bridge_done)

        def bridge_done():
            if self.FAIL_BRIDGE:
                st["bridge"] = "fail"
                st["hunter"] = "fail"
                st["done"] = True
                st["error"] = "E-02"
                push()
                return
            st["bridge"] = "ok"
            st["hunter"] = "busy"
            push()
            at(self.STEP_MS, mint_done)

        def mint_done():
            st["hunter"] = "ok"
            st["hunter_id"] = "JGR-%04d" % random.randrange(10000)
            st["done"] = st["ok"] = True
            push()

        push()
        at(self.STEP_MS, cloud_done)


# Shared singleton — the send screen talks to this.
REGISTRAR = FakeRegistrar()
