# screen_snuffel.py — SNUFFELEN: nearby players + the VONK payoff.
#
# Layout follows the design (verzamelen.jsx PxSnuffel / PxVonk). Opening the
# screen IS the consent step: the radio leaves camp WiFi and pins the snuffel
# channel (snuffel_link), so the banner honestly says "even geen wifi". The
# idle list doubles as the visible "wil snuffelen" state.
#
# The handshake fires by itself: when a peer holds the CLOSE verdict for a
# full streak (~3 s of -50 dBm or better), both sides celebrate. The payoff
# writes only local, forgiving state — vonken, boekje pages, vonk-geluk —
# never public score (ESP-NOW frames are unauthenticated; see the findings).

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
        self._greeted = set()  # peers already celebrated this visit
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

        bw = 151
        boekje = ui.panel(s, 6, 204, bw, 30, ui.CARD)
        art.icon(boekje, "boek", 2).set_pos(28, 6)
        ui.label(boekje, "BOEKJE", 48, 8, ui.INK, ui.font_label())
        ui.focusable(boekje, on_click=self._boekje)
        code = ui.panel(s, 6 + bw + 6, 204, bw, 30, ui.CARD)
        ui.label(code, "CODE", 0, 8, ui.INK, ui.font_label(), w=bw - 4, center=True)
        ui.focusable(code, on_click=self._code)

        self.setContentView(s)

    def onResume(self, screen):
        super().onResume(screen)
        p = store.profile()
        LINK.set_identity(
            p["name"],
            companion.encode(p["head"], p["accs"], p["bg"]),
            store.caught_ids(),
        )
        LINK.on_gift = self._on_gift
        if not self._handoff:
            LINK.start()
        self._handoff = False
        self.timer = lv.timer_create(self._tick, 500, None)

    def onPause(self, screen):
        super().onPause(screen)
        if self.timer:
            self.timer.delete()
            self.timer = None
        LINK.on_gift = None
        # Pausing INTO the Vonk payoff must keep snuffel mode alive — the
        # gift exchange runs there. Only a real exit restores WiFi.
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
                self._update_row(refs, p)
        if self.empty_l:
            if peers:
                self.empty_l.add_flag(lv.obj.FLAG.HIDDEN)
            else:
                self.empty_l.remove_flag(lv.obj.FLAG.HIDDEN)

        # the handshake: a full CLOSE streak fires the snuffel exactly once
        cp = LINK.close_peer()
        if cp and cp.mac not in self._greeted:
            self._greeted.add(cp.mac)
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
        result = store.record_snuffel(peer.mac, peer.naam, peer.code)
        geluk = store.roll_vonk_geluk(peer.roster) if result["vonk"] else None
        if geluk is not None:
            store.add_caught(geluk, origin="spoor")
        sound.play("legendary" if geluk is not None else "caught")
        self._handoff = True
        self.startActivity(
            Intent(
                activity_class=VonkActivity,
                extras={
                    "mac": peer.mac,
                    "naam": peer.naam,
                    "code": peer.code,
                    "vonk": result["vonk"],
                    "new_friend": result["new_friend"],
                    "dag": result["dag"],
                    "geluk": geluk,
                },
            )
        )

    def _on_gift(self, mac, kind, payload):
        """Incoming GIFT frame while the screen is open (the other side of
        VOER GEVEN / SPOOR DELEN)."""
        p = LINK.peers.get(mac)
        naam = p.naam if p else "iemand"
        if kind == "voer" and payload in store.FOODS:
            store.add_food(payload)
            sound.play("caught")
            self.empty_l.set_text("%s gaf je een %s!" % (naam, payload))
        elif kind == "spoor":
            try:
                cid = int(payload)
            except ValueError:
                return
            c = by_id(cid)
            if c and not store.is_caught(cid):
                store.add_caught(cid, origin="spoor")
                sound.play("legendary")
                self.empty_l.set_text("%s deelde een spoor: de %s!" % (naam, c["naam"]))

    def _boekje(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=BoekjeActivity))

    def _code(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=SnuffelCodeActivity))


class VonkActivity(Activity):
    """The handshake payoff: VONK! (or a warm hello-again), the boekje page,
    vonk-geluk, and gifts in both directions — spoor one way, hapjes the
    other, no price ever on screen."""

    def onCreate(self):
        x = self.getIntent().extras
        self.mac = x.get("mac")
        self.naam = x.get("naam", "?")
        self.peer_code = x.get("code", "")
        self._note_timer = None
        self.timer = None

        s = ui.make_screen(_VONK_BG)
        self.screen = s
        for sx, sy, sc in (
            (16, 40, 2),
            (286, 36, 1),
            (40, 96, 1),
            (276, 100, 2),
            (150, 30, 1),
        ):
            art.icon(s, "spark", sc).set_pos(sx, sy)

        # the two maatjes, nose to nose
        p = store.profile()
        mine = ui.panel(s, 24, 16, 72, 72, _AVATAR_BG)
        companion.draw(mine, p["head"], p["accs"], 4, x=2, y=2)
        theirs = ui.panel(s, 224, 16, 72, 72, _AVATAR_BG)
        head, accs, bg = companion.decode(self.peer_code)
        companion.draw(theirs, head, accs, 4, x=2, y=2)
        if x.get("vonk"):
            ui.label(s, "VONK!", 100, 30, ui.GOLD, ui.font_title(), w=120, center=True)
        else:
            ui.label(
                s, "HOI WEER!", 100, 24, ui.GOLD, ui.font_title(), w=120, center=True
            )
            ui.label(
                s,
                "al gesnuffeld vandaag",
                100,
                54,
                _VONK_MUTED,
                ui.font_small(),
                w=120,
                center=True,
            )
        ui.label(
            s,
            "%s + %s" % (p["name"], self.naam),
            100,
            70,
            _VONK_TEXT,
            ui.font_small(),
            w=120,
            center=True,
        )

        # vonk-geluk: one of THEIR creatures introduces itself
        geluk = x.get("geluk")
        if geluk is not None:
            c = by_id(geluk)
            gp = ui.panel(s, 8, 100, 304, 64, _VONK_PANEL, border=ui.GOLD)
            art.creature_panel(gp, c, 3, animate=True).set_pos(8, 6)
            ui.label(gp, "VONK-GELUK!", 68, 6, ui.GOLD, ui.font_label())
            ui.label(
                gp,
                "de %s van %s stelt zich voor" % (c["naam"], self.naam),
                68,
                26,
                _VONK_TEXT,
                ui.font_small(),
            )
            ui.label(gp, "nieuw in je boek", 68, 42, _VONK_MUTED, ui.font_small())
            art.icon(gp, "spark", 2).set_pos(276, 20)

        # the boekje line
        strip = ui.box(s, 8, 172, 304, 20, None)
        strip.set_style_border_width(ui.BORDER_THIN, 0)
        strip.set_style_border_color(ui.hexc(ui.GOLD_D), 0)
        art.icon(strip, "boek", 1).set_pos(4, 5)
        self.note = ui.label(
            strip,
            (
                "%s staat nu in je vriendenboekje - %s" % (self.naam, x.get("dag", ""))
                if x.get("new_friend")
                else "%s staat al in je boekje" % self.naam
            ),
            18,
            3,
            _VONK_TEXT,
            ui.font_small(),
        )

        # gifts, both directions
        self.actions = ui.box(s, 8, 200, 304, 34)
        self._build_actions()
        self.setContentView(s)

    def onResume(self, screen):
        super().onResume(screen)
        # keep the exchange alive: this screen ticks the link the snuffel
        # screen handed over, so gifts arrive while the payoff is up
        LINK.on_gift = self._on_gift
        self.timer = lv.timer_create(lambda t: LINK.tick(), 600, None)

    def onPause(self, screen):
        super().onPause(screen)
        if self.timer:
            self.timer.delete()
            self.timer = None
        LINK.on_gift = None

    def _on_gift(self, mac, kind, payload):
        if kind == "voer" and payload in store.FOODS:
            store.add_food(payload)
            sound.play("caught")
            self._flash("%s gaf je een %s!" % (self.naam, payload))
        elif kind == "spoor":
            try:
                cid = int(payload)
            except ValueError:
                return
            c = by_id(cid)
            if c and not store.is_caught(cid):
                store.add_caught(cid, origin="spoor")
                sound.play("legendary")
                self._flash("%s deelde een spoor: de %s!" % (self.naam, c["naam"]))

    # ── the gift row: two buttons <-> pickers, rebuilt in place ─────────
    def _build_actions(self):
        a = self.actions
        a.clean()
        if self.mac.startswith("code:"):
            # a manual meeting has no radio to carry a gift — the vonk and
            # the boekje page are the payoff; hand the hapje over for real
            done = ui.panel(a, 0, 0, 304, 32, ui.GREEN)
            ui.label(done, "KLAAR", 0, 8, ui.CREAM, ui.font_label(), w=300, center=True)
            ui.focusable(done, on_click=lambda: (sound.play("tap"), self.finish()))
            return
        bw = 149
        voer = ui.panel(a, 0, 0, bw, 32, ui.GREEN)
        art.icon(voer, "bes", 1).set_pos(18, 7)
        ui.label(
            voer, "VOER GEVEN", 30, 8, ui.CREAM, ui.font_label(), w=110, center=True
        )
        ui.focusable(voer, on_click=self._pick_voer)
        spoor = ui.panel(a, bw + 6, 0, bw, 32, ui.CARD)
        art.icon(spoor, "spoor", 1).set_pos(18, 8)
        ui.label(
            spoor, "SPOOR DELEN", 30, 8, ui.INK, ui.font_label(), w=110, center=True
        )
        ui.focusable(spoor, on_click=self._pick_spoor)

    def _pick_voer(self):
        sound.play("tap")
        a = self.actions
        a.clean()
        v = store.voorraad()
        x = 0
        for food in store.FOODS:
            tile = ui.panel(a, x, 0, 66, 32, ui.CARD if v[food] else ui.DORMANT)
            art.icon(tile, food, 2).set_pos(6, 6)
            ui.label(tile, str(v[food]), 40, 7, ui.INK, ui.font_label())
            ui.focusable(tile, on_click=lambda f=food: self._give(f), focus_border=True)
            x += 72
        terug = ui.panel(a, 222, 0, 82, 32, ui.CARD)
        ui.label(terug, "TERUG", 0, 8, ui.INK, ui.font_small(), w=78, center=True)
        ui.focusable(terug, on_click=self._terug)

    def _pick_spoor(self):
        sound.play("tap")
        eigen = store.own_find_ids()
        if not eigen:
            sound.play("error")
            self._flash("alleen beesten die je ZELF vond kun je delen")
            return
        a = self.actions
        a.clean()
        strip = ui.row(a, 0, 0, 220, 32, gap=ui.GAP_S)
        strip.add_flag(lv.obj.FLAG.SCROLLABLE)
        strip.set_scroll_dir(lv.DIR.HOR)
        for cid in eigen:
            c = by_id(cid)
            tile = ui.panel(strip, 0, 0, 36, 32, ui.CARD)
            art.creature_panel(tile, c, 2).set_pos(0, 0)
            ui.focusable(tile, on_click=lambda i=cid: self._share(i), focus_border=True)
        terug = ui.panel(a, 226, 0, 78, 32, ui.CARD)
        ui.label(terug, "TERUG", 0, 8, ui.INK, ui.font_small(), w=74, center=True)
        ui.focusable(terug, on_click=self._terug)

    def _terug(self):
        sound.play("tap")
        self._build_actions()

    def _give(self, food):
        if not store.take_food(food):
            sound.play("error")
            self._flash("je %s is op - ga plukken!" % food)
            return
        LINK.send_gift(self.mac, "voer", food)
        sound.play("caught")
        self._flash("je gaf %s een %s!" % (self.naam, food))
        self._build_actions()

    def _share(self, cid):
        c = by_id(cid)
        LINK.send_gift(self.mac, "spoor", str(cid))
        sound.play("caught")
        self._flash("spoor gedeeld: %s kent nu de %s!" % (self.naam, c["naam"]))
        self._build_actions()

    def _flash(self, text):
        self._old_note = self.note.get_text()
        self.note.set_text(text)
        if self._note_timer:
            self._note_timer.delete()
        self._note_timer = lv.timer_create(self._unflash, 1600, None)

    def _unflash(self, t):
        t.delete()
        self._note_timer = None
        self.note.set_text(self._old_note)


class SnuffelCodeActivity(Activity):
    """The manual fallback: no radio, no problem — swap names out loud.
    Each player types the other's name; the meeting counts the same (the
    universal baseline the design mandates). No roster travels, so there is
    no vonk-geluk this way — the radio path stays the magic one."""

    def onCreate(self):
        from mpos.ui.keyboard import MposKeyboard

        p = store.profile()
        s = ui.make_screen(ui.PAPER)
        ui.banner(s, "SNUFFELCODE", ui.GREEN)
        card = ui.panel(s, 8, 34, 304, 62, ui.CARD)
        ui.label(
            card,
            "lukt de snuffel niet?",
            0,
            6,
            ui.MYSTERY,
            ui.font_small(),
            w=300,
            center=True,
        )
        ui.label(
            card,
            "jouw code is je naam:",
            0,
            20,
            ui.INK,
            ui.font_small(),
            w=300,
            center=True,
        )
        ui.label(
            card, p["name"], 0, 34, ui.GREEN_D, ui.font_title(), w=300, center=True
        )

        ui.label(s, "typ de naam van je maatje:", 8, 104, ui.INK, ui.font_small())
        ta = lv.textarea(s)
        ta.set_pos(8, 118)
        ta.set_size(304, 30)
        ta.set_one_line(True)
        ta.set_max_length(12)
        ta.set_placeholder_text("tik om te typen")
        self.ta = ta

        self.kb = MposKeyboard(s)
        self.kb.set_textarea(ta)
        self.kb.add_flag(lv.obj.FLAG.HIDDEN)
        ta.add_event_cb(
            lambda e: self.kb.remove_flag(lv.obj.FLAG.HIDDEN), lv.EVENT.CLICKED, None
        )
        self.kb.add_event_cb(self._done, lv.EVENT.READY, None)
        self.kb.add_event_cb(
            lambda e: self.kb.add_flag(lv.obj.FLAG.HIDDEN), lv.EVENT.CANCEL, None
        )
        self.setContentView(s)

    def _done(self, e):
        naam = self.ta.get_text().strip()
        if not naam:
            sound.play("error")
            return
        self.kb.add_flag(lv.obj.FLAG.HIDDEN)
        # identity for a manual meeting: the name, lowercased — the same pair
        # meeting again the same day still only sparks once
        result = store.record_snuffel("code:" + naam.lower(), naam, "")
        sound.play("caught")
        self.startActivity(
            Intent(
                activity_class=VonkActivity,
                extras={
                    "mac": "code:" + naam.lower(),
                    "naam": naam,
                    "code": "",
                    "vonk": result["vonk"],
                    "new_friend": result["new_friend"],
                    "dag": result["dag"],
                    "geluk": None,
                },
            )
        )
