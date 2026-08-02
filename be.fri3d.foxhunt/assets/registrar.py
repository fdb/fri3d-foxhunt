# registrar.py — the registration transport.
#
# Two legs, and only one of them is built. HttpRegistrar does the cloud leg
# for real: WiFi + JSON against server/ (Hono on Cloudflare Workers). The
# bridge leg — asking the LoRa bridge to mint a hunter id over the air — has
# no protocol yet, the same way fox_radio is still a stub, so it reports
# "skip": exactly what a badge with no antenna already does, and the server
# has always treated hunter_id as NULL-until-an-antenna-is-attached.
#
# FakeRegistrar stays for offline work and for walking the error paths its
# flags describe. Swap REGISTRAR at the bottom of this file.

import lvgl as lv
import random
from mpos import TaskManager

# The deployed worker (see server/README.md). NO trailing slash — the request
# path is appended verbatim, and "…dev/" + "/api/…" would ask for "//api/…".
# Point it at a wrangler dev instance to work against a local D1:
#   sys.modules["registrar"].BASE_URL = "http://localhost:8787"
BASE_URL = "https://foxhunt.enigmeta.workers.dev"

# Connect timeout. Only guards opening the socket (that is all the aiohttp
# shim takes), which is the part that hangs on a dead network.
CONNECT_TIMEOUT = 10


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
            "creatures": the creature ids the server has for this player
                      (players_creatures), or None when it didn't say. The
                      accessory unlocks are counted off this list, so a
                      restore without it hands back a maatje wearing things
                      the badge then claims are locked.
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
    RESTORE_COMPANION = "H2A014C3"
    # ...and the catch list that earns it: sjaal opens at 8, so eight ids is
    # the smallest recovery consistent with the companion above. Restore them
    # together or the builder greys out a sjaal the player is wearing.
    RESTORE_CREATURES = [0, 1, 2, 3, 4, 5, 6, 7]

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
                        "creatures": list(self.RESTORE_CREATURES),
                        "error": None,
                    }
                )
            else:
                on_update({"done": True, "found": False, "error": None})

        t = lv.timer_create(lambda _t: answer(), self.STEP_MS + 500, None)
        t.set_repeat_count(1)


async def _json_request(method, path, body=None):
    """One JSON round trip against BASE_URL. Returns (status, parsed | None).

    A response with no parseable body is not an error here — a 404 from the
    restore route is a perfectly good answer — so the caller reads the status
    and decides."""
    import aiohttp

    async with aiohttp.ClientSession(BASE_URL) as session:
        async with session.request(
            method, path, json=body, timeout=CONNECT_TIMEOUT
        ) as resp:
            try:
                data = await resp.json()
            except Exception:
                data = None
            return resp.status, data


def _hunter_label(n):
    """The server keeps hunter_id as the 5-bit LoRa address; every screen
    shows it as text. None (no antenna yet) stays None, so the profile says
    "JGR volgt" rather than inventing an id. The number is always recoverable
    from the server when the LoRa layer needs it."""
    return None if n is None else "JGR-%02d" % n


class HttpRegistrar(Registrar):
    """The real transport. Work happens in a TaskManager task, so on_update
    fires on the same loop LVGL runs on — the same place FakeRegistrar's
    timers put it, which is why neither screen needs to care which is live."""

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
        on_update(dict(st))
        TaskManager.create_task(self._register(name, badge, companion, st, on_update))

    async def _register(self, name, badge, companion, st, on_update):
        body = {"badge_id": badge, "name": name, "profile_pic": companion}
        ok = False
        try:
            status, _ = await _json_request("POST", "/api/v1/auth/register", body)
            if status == 409:
                # Already in the book. Not an error: this is what a player who
                # re-registers after a wipe instead of restoring looks like, so
                # adopt the account by updating it rather than refusing them.
                status, _ = await _json_request("PATCH", "/api/v1/auth/user", body)
            ok = status in (200, 201)
            if not ok:
                print("registrar: register rejected, HTTP", status)
        except Exception as e:
            print("registrar: register failed:", e)

        st["cloud"] = "ok" if ok else "fail"
        # The bridge leg is unbuilt (see the module docstring), so it skips
        # rather than pretending. A cloud save alone counts as success — the
        # same rule the flow already applies to an antenna-less badge.
        st["bridge"] = "skip" if ok else "fail"
        st["hunter"] = "skip" if ok else "fail"
        st["done"] = True
        st["ok"] = ok
        st["error"] = None if ok else "E-01"
        on_update(dict(st))

    def restore(self, badge, on_update):
        TaskManager.create_task(self._restore(badge, on_update))

    async def _restore(self, badge, on_update):
        try:
            status, data = await _json_request(
                "GET", "/api/v1/auth/user?badge_id=" + badge
            )
        except Exception as e:
            print("registrar: restore failed:", e)
            on_update({"done": True, "found": False, "error": "E-01"})
            return
        if status == 404:
            # Not an error — the badge is simply new. The screen says so.
            on_update({"done": True, "found": False, "error": None})
            return
        if status != 200 or not data:
            print("registrar: restore rejected, HTTP", status)
            on_update({"done": True, "found": False, "error": "E-01"})
            return
        on_update(
            {
                "done": True,
                "found": True,
                "name": data.get("name"),
                "hunter_id": _hunter_label(data.get("hunter_id")),
                # "" is how the server spells "this account never sent one".
                "companion": data.get("profile_pic") or None,
                "creatures": data.get("creatures") or [],
                "error": None,
            }
        )


# Shared singleton — the send and restore screens talk to this. Swap in
# FakeRegistrar() to work offline or to walk the error paths its flags describe.
REGISTRAR = HttpRegistrar()
