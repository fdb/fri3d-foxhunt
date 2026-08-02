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
    def register(self, name, badge, companion, on_update):
        """Send the profile to the cloud server and the LoRa bridge.

        `companion` is the avatar shortcode (companion.encode) — the server keeps
        it in profile_pic so a restore hands the player back their own maatje.

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

    def restore(self, badge, on_update):
        """Ask the cloud server whether this badge is already registered
        (server/: GET /api/v1/auth/user?badge_id=...).

        ASYNCHRONOUS BY CONTRACT, same as register(); the verdict arrives
        through on_update(status), and today that is the single terminal
        update. status:

            "done" : True on the terminal update
            "found": the server knows this badge
            "name" / "hunter_id": the recovered account (with found)
            "companion": the avatar shortcode the server had, or None — an
                      account registered before shortcodes existed has no
                      profile_pic, and decodes to the default companion
            "error": "E-01" when the server didn't answer, else None
        """
        raise NotImplementedError


class FakeRegistrar(Registrar):
    """Fakes the round trips with one-shot lv timers, like FakeFoxRadio."""

    STEP_MS = 700
    SIMULATE_LORA = True  # desktop has no radio; pretend, so the flow is testable
    FAIL_BRIDGE = False  # flip to walk the E-02 error path
    RESTORE_FOUND = True  # flip to walk the "onbekende badge" restore path
    RESTORE_FAIL = False  # flip to walk the E-01 restore path
    # A recovered companion that is deliberately NOT the default (uil + hoed +
    # sjaal on the third backdrop), so a restore that ignored the shortcode
    # would be obvious on screen instead of quietly plausible.
    RESTORE_COMPANION = "H2A084C3"

    def register(self, name, badge, companion, on_update):
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

    def restore(self, badge, on_update):
        def answer():
            if self.RESTORE_FAIL:
                on_update({"done": True, "found": False, "error": "E-01"})
            elif self.RESTORE_FOUND:
                on_update(
                    {
                        "done": True,
                        "found": True,
                        "name": "Jager",
                        "hunter_id": "JGR-%04d" % random.randrange(10000),
                        "companion": self.RESTORE_COMPANION,
                        "error": None,
                    }
                )
            else:
                on_update({"done": True, "found": False, "error": None})

        t = lv.timer_create(lambda _t: answer(), self.STEP_MS + 500, None)
        t.set_repeat_count(1)


# Shared singleton — the send screen talks to this.
REGISTRAR = FakeRegistrar()
