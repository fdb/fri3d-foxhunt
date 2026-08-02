# screen_profile.py — the jagersprofiel (tap your maatje on the home header).
#
# Big maatje portrait, name + ids, score, four stat tiles, and the two edit
# actions that re-enter the onboarding screens in edit mode (design: home.jsx
# PxProfile). Rebuilt on resume so an edit shows the moment you come back.

import lvgl as lv
from mpos import Activity, Intent
import mpos.time
import ui
import art
import pet
import sound
import store
import mascot
from creatures import CREATURES, by_id
from screen_mascot import MascotActivity
from screen_register import RegisterActivity

SCORE_BG = 0xF6E7CD
SCORE_LABEL = 0x8A6A2E
BADGE_TX = 0x5C4F38

# Local, provisional scoring until the cloud server owns it: rarer = more.
_POINTS = {"norm": 100, "rare": 250, "leg": 500}


class ProfileActivity(Activity):
    def onCreate(self):
        self._fresh = True
        self.screen = ui.make_screen(ui.PAPER)
        self._populate()
        self.setContentView(self.screen)

    def onResume(self, screen):
        super().onResume(screen)
        # Coming back from an edit: rebuild in place (never re-setContentView).
        if self._fresh:
            self._fresh = False
            return
        self.screen.clean()
        self._populate()

    def _populate(self):
        s = self.screen
        p = store.profile() or {"name": "Jager", "head": "vos", "accs": [], "bg": 0}
        caught = store.caught_ids()

        ui.banner(s, "JAGERSPROFIEL", ui.GREEN)

        portrait = ui.panel(s, ui.PAD, 32, 108, 108, bg=mascot.BGS[p.get("bg", 0)])
        mascot.draw(portrait, p.get("head", "vos"), p.get("accs", []), 6, x=4, y=4)

        name = ui.label(s, p.get("name", "Jager"), 124, 34, ui.INK, ui.font_title())
        pencil = art.icon(s, "pencil", 2)
        pencil.align_to(name, lv.ALIGN.OUT_RIGHT_MID, 6, 0)
        ui.label(s, p.get("hunter_id") or "JGR volgt", 124, 62, ui.INK, ui.font_small())
        ui.label(s, p.get("badge_id", ""), 124, 78, BADGE_TX, ui.font_small())

        # score: rarity-weighted, local for now (the server will own scoring)
        score = sum(_POINTS.get(by_id(c)["rarity"], 100) for c in caught if by_id(c))
        panel = ui.panel(s, 124, 100, 188, 40, bg=SCORE_BG, border=ui.GOLD)
        art.icon(panel, "spark", 2).set_pos(8, 12)
        ui.label(panel, "SCORE", 26, 12, SCORE_LABEL, ui.font_small())
        sl = ui.label(panel, str(score), 80, 6, ui.INK, ui.font_title(), w=98)
        sl.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)

        # stat tiles
        band = 0
        for cid in caught:
            state = store.beast_state(cid)
            if state:
                band += pet.level(state["bond"])
        since = p.get("since")
        now = mpos.time.epoch_seconds()
        days = 1 + max(0, (now - since) // 86400) if since else 1
        stats = (
            ("%d/%d" % (len(caught), len(CREATURES)), "GEVONDEN", ui.INK),
            (str(band), "BAND", ui.TERRA),
            (str(days), "DAGEN", ui.INK),
            ("0", "GERUILD", ui.GREEN_D),
        )
        tiles = ui.row(s, ui.PAD, 146, 304, 44, gap=5)
        for value, label, colour in stats:
            t = ui.panel(tiles, 0, 0, 72, 44, bg=ui.CARD)
            ui.label(t, value, 0, 4, colour, ui.font_title(), w=68, center=True)
            ui.label(t, label, 0, 28, ui.MYSTERY, ui.font_small(), w=68, center=True)

        # actions: re-enter the onboarding screens in edit mode
        edit_btn = ui.box(s, ui.PAD, 196, 179, 34, ui.GREEN, radius=ui.RADIUS)
        edit_btn.set_style_border_width(ui.BORDER, 0)
        edit_btn.set_style_border_color(ui.hexc(ui.INK), 0)
        el = ui.label(
            edit_btn,
            "MAATJE AANPASSEN",
            0,
            0,
            ui.CREAM,
            ui.font_small(),
            w=175,
            center=True,
        )
        el.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(edit_btn, on_click=self._edit_mascot)

        name_btn = ui.box(s, 193, 196, 119, 34, ui.CARD, radius=ui.RADIUS)
        name_btn.set_style_border_width(ui.BORDER, 0)
        name_btn.set_style_border_color(ui.hexc(ui.INK), 0)
        nl = ui.label(
            name_btn, "NAAM", 0, 0, ui.INK, ui.font_small(), w=115, center=True
        )
        nl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(name_btn, on_click=self._edit_name)

    def _edit_mascot(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=MascotActivity, extras={"edit": True}))

    def _edit_name(self):
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=RegisterActivity, extras={"edit": True})
        )
