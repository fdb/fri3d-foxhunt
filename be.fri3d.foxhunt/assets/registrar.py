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


def adopt(badge, account, name=None, code=None):
    """Write an account the server handed back into the local store.

    The one place both routes into an existing account agree on what taking it
    over means: the welcome screen's "herstel", and the fork the registration
    flow raises when the badge turns out to be known already.

    `account` is the payload restore() documents — name, hunter_id, companion,
    creatures. `name`/`code` override the first two fields for the player who
    chose to overwrite the account instead of adopting it as it stands.

    The catch list is not optional here. The maatje's accessory unlocks are
    counted off it, so writing the profile alone hands the player an avatar
    wearing things the builder then greys out as unearned.

    Returns how many creatures the badge holds afterwards.
    """
    import store
    import companion

    code = code or account.get("companion")
    head, accs, bg = companion.decode(code)
    store.save_profile(
        {
            "name": name or account.get("name") or "Jager",
            "head": head,
            "accs": accs,
            "bg": bg,
            "badge_id": badge,
            "hunter_id": account.get("hunter_id"),
            "synced": True,
        }
    )
    return len(store.restore_caught(account.get("creatures") or []))


class Registrar:
    def register(self, name, badge, companion, on_update):
        """Send the profile to the cloud server and the LoRa bridge.

        `companion` is the avatar shortcode (companion.encode) — the server keeps
        it in profile_pic so a restore hands the player back their own maatje.

        ASYNCHRONOUS BY CONTRACT (see FoxRadio.submit_code): progress arrives
        later through on_update(status), never as a return value. status:

            "cloud" / "bridge" / "hunter": "wait"|"busy"|"ok"|"fail"|"skip"
            "hunter_id": the minted id (with hunter ok), else None
            "starter": (with done+ok) the startbeest creature id the server
                      granted at registration, or None when the account
                      already had creatures (a re-register instead of a
                      restore) — the reveal screen only opens on a real grant
            "done": True on the terminal update
            "ok": (with done) the whole registration succeeded
            "exists": (with done) THIS BADGE ALREADY HAS AN ACCOUNT. Neither
                      ok nor an error — a fork the player has to settle, so
                      the account payload (see restore(): "name",
                      "hunter_id", "companion", "creatures") rides along and
                      the screen offers adopt() or overwrite().
            "error": (with done, not ok) "E-01" cloud down | "E-02" bridge down

        Without a LoRa antenna the bridge/hunter steps report "skip" and the
        cloud save alone counts as success.
        """
        raise NotImplementedError

    def overwrite(self, name, badge, companion, on_update):
        """Put THIS profile on the account the badge already has (the
        "overschrijf" answer to register()'s "exists"). The account keeps its
        hunter_id and its catches — they are keyed to the badge, and there is
        no second account to move them to — but the name and maatje become the
        ones just built.

        ASYNCHRONOUS BY CONTRACT, like register(). status:

            "done" : True on the terminal update
            "ok"   : the server took it
            "error": "E-01" when it didn't
        """
        raise NotImplementedError

    def delete_account(self, badge, on_update):
        """Wipe this badge's account off the cloud server (server/:
        DELETE /api/v1/auth/user).

        The server leg of ALLES WISSEN, and it goes FIRST — the local wipe is
        the step the player cannot undo, so it may only happen once the server
        has confirmed. A badge that wiped itself while the account lived on
        would re-register straight into the "deze badge is al bekend" fork and
        get every catch handed back, which is the exact thing the wipe is for.

        That ordering is also why there is no separate "is there wifi" check:
        the question is whether the SERVER answered, and this asks it.

        ASYNCHRONOUS BY CONTRACT, like register(). status:

            "done" : True on the terminal update
            "ok"   : the account is gone (or was already gone — the route is
                     idempotent, so a retry after a lost reply still succeeds)
            "error": "E-01" when the server didn't answer or refused
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
    REGISTER_EXISTS = False  # flip to walk the "badge is al bekend" fork
    OVERWRITE_FAIL = False  # flip to walk the E-01 path out of that fork
    DELETE_FAIL = False  # flip to walk the "server antwoordt niet" wipe path
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
            "starter": None,
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
            if self.REGISTER_EXISTS:
                # The server knows this badge already: the same fork the real
                # transport raises on a 409, carrying the same account payload
                # a restore would have handed back.
                st["exists"] = True
                st["name"] = "Jager"
                st["hunter_id"] = "JGR-%04d" % random.randrange(10000)
                st["companion"] = self.RESTORE_COMPANION
                st["creatures"] = list(self.RESTORE_CREATURES)
                st["done"] = True
                push()
                return
            # same pick the real server makes: deterministic per badge
            from creatures import starter_for

            st["starter"] = starter_for(badge)
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

    def overwrite(self, name, badge, companion, on_update):
        ok = not self.OVERWRITE_FAIL
        t = lv.timer_create(
            lambda _t: on_update(
                {"done": True, "ok": ok, "error": None if ok else "E-01"}
            ),
            self.STEP_MS,
            None,
        )
        t.set_repeat_count(1)

    def delete_account(self, badge, on_update):
        ok = not self.DELETE_FAIL
        t = lv.timer_create(
            lambda _t: on_update(
                {"done": True, "ok": ok, "error": None if ok else "E-01"}
            ),
            self.STEP_MS,
            None,
        )
        t.set_repeat_count(1)

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
    """The server keeps hunter_id as the raw HID (spec §2.2, allocated 1-9999);
    every screen shows it as text. Always four digits, so the label is a fixed
    width wherever it is placed. None (no antenna yet) stays None, so the
    profile says "JGR volgt" rather than inventing an id. The number is always
    recoverable from the server when the LoRa layer needs it."""
    return None if n is None else "JGR-%04d" % n


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
            "starter": None,
            "done": False,
            "ok": False,
            "error": None,
        }
        on_update(dict(st))
        TaskManager.create_task(self._register(name, badge, companion, st, on_update))

    async def _account(self, badge):
        """The server's view of an account that already exists, in the shape
        restore() reports. None when the server won't say — we refuse to offer
        the player a choice we cannot back with the real account."""
        status, data = await _json_request("GET", "/api/v1/auth/user?badge_id=" + badge)
        if status != 200 or not data:
            print("registrar: account lookup rejected, HTTP", status)
            return None
        creatures = data.get("creatures") or []
        if not creatures:
            # An account from before the startbeest existed. The server grants
            # one to an EMPTY roster only, so this can neither reroll nor
            # double; it just finishes what registration would have done.
            s, d = await _json_request(
                "POST", "/api/v1/auth/starter", {"badge_id": badge}
            )
            if s == 200 and d and d.get("ok"):
                creatures = [d.get("starter")]
        return {
            "name": data.get("name"),
            "hunter_id": _hunter_label(data.get("hunter_id")),
            # "" is how the server spells "this account never sent one".
            "companion": data.get("profile_pic") or None,
            "creatures": creatures,
        }

    async def _register(self, name, badge, companion, st, on_update):
        body = {"badge_id": badge, "name": name, "profile_pic": companion}
        ok = False
        starter = None
        try:
            status, data = await _json_request("POST", "/api/v1/auth/register", body)
            if status == 201:
                # A fresh account comes back holding its startbeest.
                starter = data.get("starter") if data else None
            elif status == 409:
                # This badge is already in the book, and the badge cannot tell
                # the two ways that happens apart: the same player after a
                # wipe, or a badge that changed hands. They want opposite
                # things, so stop and let the player settle it.
                #
                # This used to PATCH straight through and report success. That
                # overwrote whoever's name was on the account without asking,
                # and — because nothing read the existing row back — left the
                # badge with hunter_id None and an empty catch list while the
                # server still held both.
                account = await self._account(badge)
                if account is not None:
                    st.update(account)
                    st["cloud"] = "ok"
                    st["exists"] = True
                    st["done"] = True
                    on_update(dict(st))
                    return
            ok = status == 201
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
        st["starter"] = starter
        st["done"] = True
        st["ok"] = ok
        st["error"] = None if ok else "E-01"
        on_update(dict(st))

    def overwrite(self, name, badge, companion, on_update):
        TaskManager.create_task(self._overwrite(name, badge, companion, on_update))

    async def _overwrite(self, name, badge, companion, on_update):
        body = {"badge_id": badge, "name": name, "profile_pic": companion}
        status = 0
        try:
            status, _ = await _json_request("PATCH", "/api/v1/auth/user", body)
        except Exception as e:
            print("registrar: overwrite failed:", e)
        ok = status == 200
        if not ok:
            print("registrar: overwrite rejected, HTTP", status)
        on_update({"done": True, "ok": ok, "error": None if ok else "E-01"})

    def delete_account(self, badge, on_update):
        TaskManager.create_task(self._delete_account(badge, on_update))

    async def _delete_account(self, badge, on_update):
        status, data = 0, None
        try:
            status, data = await _json_request(
                "DELETE", "/api/v1/auth/user", {"badge_id": badge}
            )
        except Exception as e:
            print("registrar: delete failed:", e)
        # 404 counts, but only from the ROUTE. The badge is asking for the
        # account to be gone, and a server that never had one has already
        # granted that — an antenna-less badge whose registration failed
        # halfway is the ordinary way to get here, and it must still be able to
        # wipe itself clean. A server too old to have the route answers the
        # same 404 with no JSON at all, and that one is not a grant: it once
        # let a badge wipe itself while the account it asked about lived on,
        # so the next registration met its own row and said "badge al bekend".
        ok = status == 200 or (status == 404 and data is not None)
        if not ok:
            print("registrar: delete rejected, HTTP", status)
        on_update({"done": True, "ok": ok, "error": None if ok else "E-01"})

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
