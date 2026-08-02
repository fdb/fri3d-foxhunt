# screen_profile.py — the jagersprofiel (tap your companion on the header).
#
# Big companion portrait, name + ids, score, four stat tiles, and the two edit
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
import companion
from creatures import CREATURES, by_id
from screen_companion import CompanionActivity
from screen_hello import HelloActivity
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

        portrait = ui.panel(s, ui.PAD, 32, 108, 108, bg=companion.BGS[p.get("bg", 0)])
        companion.draw(portrait, p.get("head", "vos"), p.get("accs", []), 6, x=4, y=4)

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

        # actions: the two edit re-entries + the snuffeltest (hallo-spike)
        self._action(
            s, ui.PAD, 147, "MAATJE AANPASSEN", ui.GREEN, ui.CREAM, self._edit_companion
        )
        self._action(s, 161, 60, "NAAM", ui.CARD, ui.INK, self._edit_name)
        self._action(s, 227, 85, "SNUFFELEN", ui.GOLD, ui.INK, self._snuffel)

    def _action(self, s, x, w, text, bg, fg, on_click):
        btn = ui.box(s, x, 196, w, 34, bg, radius=ui.RADIUS)
        btn.set_style_border_width(ui.BORDER, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        lbl = ui.label(btn, text, 0, 0, fg, ui.font_small(), w=w - 4, center=True)
        lbl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=on_click)

    def _edit_companion(self):
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=CompanionActivity, extras={"edit": True})
        )

    def _edit_name(self):
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=RegisterActivity, extras={"edit": True})
        )

    def _snuffel(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=HelloActivity))
