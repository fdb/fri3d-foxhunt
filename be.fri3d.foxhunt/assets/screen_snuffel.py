# screen_snuffel.py — SNUFFELEN: nearby players + the VONK payoff.
#
# Layout follows the design (verzamelen.jsx PxSnuffel / PxVonk). Opening the
# screen IS the consent step: the radio leaves camp WiFi and pins the snuffel
# channel (snuffel_link), so the banner honestly says "even geen wifi". The
# idle list doubles as the visible "wil snuffelen" state.
#
# The handshake fires by itself: when a peer holds the CLOSE verdict for a
# full streak (~3 s of -50 dBm or better), both sides celebrate — the first
# side to complete claims it on the air (SNF) and the other mirrors, so the
# streaks need not line up. There is
# nothing to choose and no buttons on the payoff — food shares itself when
# the pair's cooldown allows (a vonk is a picknick, a repeat inside 4h a
# single hapje at most once an hour; inside the hour the handshake pays
# nothing), and a vonk can spark one of the other player's creatures to
# introduce itself. The same pair can snuffel again after stepping apart.
# Everything written is local, forgiving state — never public score (frames
# are unauthenticated).

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
import companion
from creatures import by_id
from snuffel_link import LINK
from screen_boekje import BoekjeActivity
from screen_beast import BeastActivity

_ROW_TOP_BG = 0xF6E7CD  # the strongest peer's row
_AVATAR_BG = 0xCFE0EA
_VONK_BG = 0x20301C  # the payoff's night sky
_VONK_PANEL = 0x2D3D24
_VONK_TEXT = 0xE8F0D8
_VONK_MUTED = 0x9FB08A
_BAR_H = (6, 10, 14, 18)


def _bars_lit(rssi):
    """dBm -> 0..4 signal bars (same span as the pluk meter)."""
    for i, floor in enumerate((-80, -70, -60, -50)):
        if rssi < floor:
            return i
    return 4


class SnuffelActivity(Activity):
    def onCreate(self):
        self.timer = None
        self._rows = {}
        self._shown = []
        self._cooling = set()  # peers who must step away before re-snuffelling
        self._handoff = False  # True while the Vonk payoff sits on top
        s = ui.make_screen(ui.PAPER)
        ui.banner(s, "SNUFFELEN", ui.GREEN, right="even geen wifi")

        hint = ui.panel(s, 6, 32, 308, 18, ui.CREAM)
        art.icon(hint, "snuf", 1).set_pos(4, 0)
        ui.label(
            hint,
            "hou de badges tegen elkaar om te snuffelen",
            24,
            2,
            ui.INK,
            ui.font_small(),
        )

        self.rows_box = ui.box(s, 6, 56, 308, 144)
        self.empty_l = ui.label(
            s,
            "nog niemand in de buurt - wacht even",
            6,
            116,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=308,
            center=True,
        )

        boekje = ui.panel(s, 6, 204, 308, 30, ui.CARD)
        art.icon(boekje, "boek", 2).set_pos(106, 6)
        ui.label(boekje, "BOEKJE", 128, 8, ui.INK, ui.font_label())
        ui.focusable(boekje, on_click=self._boekje)

        self.setContentView(s)

    def onResume(self, screen):
        super().onResume(screen)
        p = store.profile()
        LINK.set_identity(
            p["name"],
            companion.encode(p["head"], p["accs"], p["bg"]),
            store.caught_ids(),
        )
        if not self._handoff:
            LINK.start()
        self._handoff = False
        self.timer = lv.timer_create(self._tick, 500, None)

    def onPause(self, screen):
        super().onPause(screen)
        if self.timer:
            self.timer.delete()
            self.timer = None
        # Pausing INTO the Vonk payoff keeps snuffel mode alive so the
        # return is instant; only a real exit restores WiFi.
        if not self._handoff:
            LINK.stop()

    # ── the peer list ───────────────────────────────────────────────────
    def _tick(self, t):
        if not self.has_foreground():
            return
        LINK.tick()
        peers = LINK.sorted_peers()[:4]
        macs = [p.mac for p in peers]
        if macs != self._shown:
            self._shown = macs
            self._rows = {}
            self.rows_box.clean()
            for i, p in enumerate(peers):
                self._build_row(i, p)
        for p in peers:
            refs = self._rows.get(p.mac)
            if refs:
                try:
                    self._update_row(refs, p)
                except Exception:
                    # Teardown races the timer: during the exit animation
                    # has_foreground() still answers True while the widgets
                    # are already deleted (the OS topmenu logs the same
                    # LvReferenceError in that window). Drop the tick; the
                    # timer dies with onPause a moment later.
                    return
        if self.empty_l:
            if peers:
                self.empty_l.add_flag(lv.obj.FLAG.HIDDEN)
            else:
                self.empty_l.remove_flag(lv.obj.FLAG.HIDDEN)

        # a snuffelled peer re-arms once they step out of CLOSE range —
        # holding two badges together fires exactly one handshake
        for mac in list(self._cooling):
            p = LINK.peers.get(mac)
            if p is None or not p.close:
                self._cooling.discard(mac)

        cp = LINK.close_peer()
        if cp and cp.mac not in self._cooling:
            self._cooling.add(cp.mac)
            self._snuffel(cp)

    def _build_row(self, i, p):
        row = ui.panel(
            self.rows_box, 0, i * 36, 308, 33, _ROW_TOP_BG if i == 0 else ui.CARD
        )
        head, accs, bg = companion.decode(p.code)
        ava = ui.box(row, 3, 1, 26, 26, _AVATAR_BG)
        companion.draw(ava, head, accs, 2, x=-3, y=-3)
        ui.label(row, p.naam, 38, 7, ui.INK, ui.font_label())
        pill = ui.box(row, 196, 7, 62, 15, ui.GREEN)
        pill.set_style_border_width(ui.BORDER_THIN, 0)
        pill.set_style_border_color(ui.hexc(ui.INK), 0)
        ui.label(pill, "DICHTBIJ", 0, 1, ui.CREAM, ui.font_small(), w=58, center=True)
        bars = []
        for b in range(4):
            h = _BAR_H[b]
            bar = ui.box(row, 268 + b * 8, 24 - h, 5, h, ui.DORMANT)
            bar.set_style_border_width(ui.BORDER_THIN, 0)
            bar.set_style_border_color(ui.hexc(ui.INK), 0)
            bars.append(bar)
        self._rows[p.mac] = (pill, bars)

    def _update_row(self, refs, p):
        pill, bars = refs
        if p.close:
            pill.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            pill.add_flag(lv.obj.FLAG.HIDDEN)
        lit = _bars_lit(p.rssi)
        for i, bar in enumerate(bars):
            bar.set_style_bg_color(ui.hexc(ui.GREEN if i < lit else ui.DORMANT), 0)

    # ── the payoff ──────────────────────────────────────────────────────
    def _snuffel(self, peer):
        LINK.claim(peer.mac)  # tell the peer's badge, so both sides pay out
        result = store.record_snuffel(peer.mac, peer.naam, peer.code)
        geluk = (
            store.roll_vonk_geluk(LINK.roster, peer.roster, LINK.encounter_key(peer))
            if result["vonk"]
            else None
        )
        if geluk is not None:
            store.add_caught(geluk, origin="spoor")
        if result["vonk"]:
            # the meeting goes to the server through the outbox — grants a
            # vonk-geluk creature to the durable record so a restore hands
            # it back. Queued only: this mode is OFF camp WiFi by design;
            # sync.flush drains it once the radio is back home.
            store.enqueue_report(
                "snuffel",
                {"peer": peer.mac, "day": result["dag"], "creature_id": geluk},
            )
        sound.play("legendary" if geluk is not None else "caught")
        self._handoff = True
        self.startActivity(
            Intent(
                activity_class=VonkActivity,
                extras={
                    "naam": peer.naam,
                    "code": peer.code,
                    "vonk": result["vonk"],
                    "new_friend": result["new_friend"],
                    "dag": result["dag"],
                    "food": result["food"],
                    "amount": result["amount"],
                    "geluk": geluk,
                },
            )
        )

    def _boekje(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=BoekjeActivity))


class VonkActivity(Activity):
    """The handshake payoff. No buttons and nothing to decide: the picknick
    is already in the voorraad, the geluk creature already in the boek. Tap
    anywhere (or back) to continue; tapping the geluk panel opens the new
    creature's own page, like any boek tile would.
    The link keeps ticking underneath: the badge that finishes first must
    keep beaconing (and resending its SNF claim) while this screen is up,
    or the slower side never completes — that silence WAS the race."""

    def onCreate(self):
        self.timer = None
        x = self.getIntent().extras
        self.naam = x.get("naam", "?")
        self.geluk = x.get("geluk")
        vonk = x.get("vonk")

        s = ui.make_screen(_VONK_BG)
        # tap anywhere = verder (registered on the screen itself, so panels
        # keep their own taps and everything else falls through to this)
        s.add_flag(lv.obj.FLAG.CLICKABLE)
        s.add_event_cb(lambda e: self._done(), lv.EVENT.CLICKED, None)

        for sx, sy, sc in ((16, 44, 2), (286, 40, 1), (150, 10, 1)):
            art.icon(s, "spark", sc).set_pos(sx, sy)

        # the two maatjes, nose to nose
        p = store.profile()
        mine = ui.panel(s, 24, 12, 72, 72, _AVATAR_BG)
        companion.draw(mine, p["head"], p["accs"], 4, x=2, y=2)
        theirs = ui.panel(s, 224, 12, 72, 72, _AVATAR_BG)
        head, accs, bg = companion.decode(x.get("code", ""))
        companion.draw(theirs, head, accs, 4, x=2, y=2)
        if vonk:
            ui.label(s, "VONK!", 100, 26, ui.GOLD, ui.font_title(), w=120, center=True)
        else:
            ui.label(
                s, "HOI WEER!", 100, 20, ui.GOLD, ui.font_title(), w=120, center=True
            )
            ui.label(
                s,
                "al gesnuffeld",
                100,
                50,
                _VONK_MUTED,
                ui.font_small(),
                w=120,
                center=True,
            )
        ui.label(
            s,
            "%s + %s" % (p["name"], self.naam),
            100,
            66,
            _VONK_TEXT,
            ui.font_small(),
            w=120,
            center=True,
        )

        # the picknick: food shares itself when the pair's cooldown allows;
        # a fully cooled-down pair still celebrates, just empty-handed
        amount = x.get("amount", 0)
        fp = ui.panel(s, 8, 94, 304, 46, _VONK_PANEL, border=ui.GOLD_D)
        if amount:
            art.icon(fp, x.get("food", "bes"), 3).set_pos(12, 8)
            ui.label(
                fp,
                "+%d %s" % (amount, x.get("food", "bes")),
                52,
                4,
                _VONK_TEXT,
                ui.font_title(),
            )
            ui.label(
                fp,
                "jullie delen een picknick!" if vonk else "een hapje voor onderweg",
                52,
                28,
                _VONK_MUTED,
                ui.font_small(),
            )
            art.icon(fp, "spark", 1).set_pos(284, 16)
        else:
            ui.label(
                fp,
                "genoeg gedeeld voor nu",
                0,
                8,
                _VONK_TEXT,
                ui.font_label(),
                w=304,
                center=True,
            )
            ui.label(
                fp,
                "kom over een uurtje terug",
                0,
                26,
                _VONK_MUTED,
                ui.font_small(),
                w=304,
                center=True,
            )

        # vonk-geluk: one of THEIR creatures introduces itself
        if self.geluk is not None:
            c = by_id(self.geluk)
            gp = ui.panel(s, 8, 146, 304, 52, _VONK_PANEL, border=ui.GOLD)
            art.creature_panel(gp, c, 3, animate=True).set_pos(6, 0)
            ui.label(gp, "VONK-GELUK!", 62, 4, ui.GOLD, ui.font_label())
            ui.label(
                gp,
                "de %s van %s stelt zich voor" % (c["naam"], self.naam),
                62,
                22,
                _VONK_TEXT,
                ui.font_small(),
            )
            ui.label(
                gp, "nieuw in je boek - tik!", 62, 36, _VONK_MUTED, ui.font_small()
            )
            ui.focusable(gp, on_click=self._open_beest)

        # the boekje line
        strip = ui.box(s, 8, 204, 304, 20, None)
        strip.set_style_border_width(ui.BORDER_THIN, 0)
        strip.set_style_border_color(ui.hexc(ui.GOLD_D), 0)
        art.icon(strip, "boek", 1).set_pos(4, 5)
        ui.label(
            strip,
            (
                "%s staat nu in je vriendenboekje" % self.naam
                if x.get("new_friend")
                else "%s staat al in je boekje" % self.naam
            ),
            18,
            3,
            _VONK_TEXT,
            ui.font_small(),
        )
        ui.label(
            s,
            "tik om verder te gaan",
            0,
            227,
            _VONK_MUTED,
            ui.font_small(),
            w=320,
            center=True,
        )
        self.setContentView(s)

    def onResume(self, screen):
        super().onResume(screen)
        self.timer = lv.timer_create(lambda t: LINK.tick(), 500, None)

    def onPause(self, screen):
        super().onPause(screen)
        if self.timer:
            self.timer.delete()
            self.timer = None

    def _done(self):
        sound.play("tap")
        self.finish()

    def _open_beest(self):
        # straight into the normal creature flow: the geluk beast's page,
        # with VOER / AAI / SPEEL / DOSSIER like any caught creature
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=BeastActivity, extras={"fox_id": self.geluk})
        )
