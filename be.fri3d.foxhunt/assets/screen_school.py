# screen_school.py — BEESTENSCHOOL: pick a game, spend energy, earn band.
#
# Layout follows the design (plukken.jsx PxSchool / PxSchoolMoe). Spelen is
# the bond leg of the economy chain: the tired state is the playful rate
# limit ("eerst een hapje?"), never a punishment. The actual mini-games are
# the next slice — picking one runs the play session (energy down, band up)
# through store.do_play, which is exactly the seam a real game will report
# its result through.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
import pet
from creatures import by_id
from screen_feed import FeedActivity

# (icon, naam, energy cost in segments, subtitle)
GAMES = (
    ("vlieg", "VLIEGEN", 2, "ontwijk de takken"),
    ("doolhof", "DOOLHOF", 1, "kantel de badge"),
    ("simon", "SIMON", 1, "volg de LEDs"),
)


def favourite_game(cid):
    """Each creature favours one game, stably, without a roster field —
    flying beasts don't exist as data, so the id decides. A favourite grants
    extra band (pet.play) and wears the gold frame."""
    return GAMES[cid % len(GAMES)][0]


class SchoolActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id)
        self._fresh = True
        self._flash_timer = None
        self._flash_msg = None
        self.screen = ui.make_screen(ui.PAPER)
        self._populate()
        self.setContentView(self.screen)

    def onResume(self, screen):
        super().onResume(screen)
        if self._fresh:
            self._fresh = False
            return
        self._rebuild()

    def _rebuild(self):
        if self._flash_timer:
            self._flash_timer.delete()
            self._flash_timer = None
        self.screen.clean()
        self._populate()

    def _populate(self):
        s = self.screen
        st = store.beast_state(self.fox_id)
        if st is None:
            return
        # gate on exact energy points, not display segments: segments() may
        # round 35 up to 2 cells while pet.play still refuses a 40-point game
        energie = st["energy"]
        segs = pet.segments(energie)
        cheapest = min(g[2] for g in GAMES)
        moe = energie < cheapest * pet.SEG
        naam = st.get("bijnaam") or self.c["naam"]
        fav = favourite_game(self.fox_id)

        ui.banner(s, "BEESTENSCHOOL", ui.GREEN, right="energie %d/5" % segs)

        # transient top bubble: the refusal when moe, the payoff after a game
        note = self._flash_msg or (
            "%s is moe - eerst een hapje?" % naam if moe else None
        )
        if note:
            bub = ui.panel(s, 8, 30, 304, 24, ui.CREAM)
            ui.label(bub, note, 0, 3, ui.INK, ui.font_label(), w=300, center=True)
        self._flash_msg = None

        # creature column
        top = 58 if note else 34
        stage = ui.panel(s, 8, top, 96, 112 - (top - 34), ui.SURFACE_SOFT)
        sp = art.creature_panel(stage, self.c, 4, animate=not moe)
        sp.align(lv.ALIGN.BOTTOM_MID, 0, -4)
        if moe:
            sp.set_style_opa(180, 0)
        ui.label(s, naam, 8, 152, ui.INK, ui.font_label())
        ui.label(s, "ENERGIE", 8, 170, ui.MYSTERY, ui.font_small())
        for i in range(5):
            cell = ui.box(
                s,
                8 + i * 17,
                184,
                14,
                12,
                (ui.TERRA if moe else ui.GREEN) if i < segs else ui.DORMANT,
            )
            cell.set_style_border_width(ui.BORDER_THIN, 0)
            cell.set_style_border_color(ui.hexc(ui.INK), 0)
        ui.label(
            s,
            "te weinig energie" if moe else "spelen geeft band",
            8,
            202,
            ui.MYSTERY,
            ui.font_small(),
            w=96,
        )

        # game tiles
        tile_h = 40 if note else 52
        y = top
        for icon, gnaam, kost, sub in GAMES:
            kan = not moe and energie >= kost * pet.SEG
            is_fav = icon == fav
            tile = ui.panel(
                s,
                112,
                y,
                200,
                tile_h,
                ui.CARD if kan else ui.DORMANT,
                border=(ui.GOLD if (is_fav and kan) else ui.BORDER_REST),
                bw=ui.BORDER,
            )
            ic = art.icon(tile, icon, 3)
            ic.set_pos(6, (tile_h - 24) // 2 - 2)
            if not kan:
                ic.set_style_opa(115, 0)
            ui.label(tile, gnaam, 38, 5, ui.INK if kan else ui.MYSTERY, ui.font_label())
            if is_fav:
                art.icon(tile, "spark", 1).set_pos(96, 7)
                ui.label(tile, "favoriet", 106, 6, ui.GOLD_D, ui.font_small())
            ui.label(tile, sub, 38, tile_h - 18, ui.MYSTERY, ui.font_small())
            ui.label(
                tile,
                "-%d" % kost,
                150,
                4,
                ui.TERRA if kan else ui.MYSTERY,
                ui.font_label(),
                w=44,
                center=True,
            )
            ui.label(
                tile, "energie", 150, 20, ui.MYSTERY, ui.font_small(), w=44, center=True
            )
            if kan:
                ui.focusable(
                    tile,
                    on_click=lambda g=icon, k=kost, f=is_fav: self._play(g, k, f),
                    focus_border=True,
                )
            else:
                ui.focusable(tile, focus_border=True)  # navigable, inert
            y += tile_h + ui.GAP_M

        # bottom right: the way out of moe, or the standing hint
        if moe:
            btn = ui.panel(s, 112, 208, 200, 26, ui.GREEN)
            ui.label(
                btn, "EERST VOEREN", 0, 5, ui.CREAM, ui.font_label(), w=196, center=True
            )
            ui.focusable(btn, on_click=self._feed)
        else:
            hint = ui.panel(s, 112, 208, 200, 26, ui.CREAM)
            ui.label(
                hint,
                "kies een spel",
                0,
                5,
                ui.INK,
                ui.font_small(),
                w=196,
                center=True,
            )

    def _play(self, game, kost, is_fav):
        # The mini-game itself is the next slice; the session's economy —
        # energy spent, band earned, the refusal — is already real.
        st, ok, msg = store.do_play(self.fox_id, kost, is_fav)
        if st is None:
            return
        sound.play("caught" if ok and is_fav else "tap" if ok else "error")
        naam = st.get("bijnaam") or self.c["naam"]
        self._flash_msg = "%s: %s" % (naam, msg)
        self._rebuild()

    def _feed(self):
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=FeedActivity, extras={"fox_id": self.fox_id})
        )
