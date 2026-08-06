# screen_visitor.py — random visitor: meet the silhouette, then welcome the
# base-tier creature into the book. The schedule and pending visitor live in
# store.py; this screen only presents and claims one durable pending meeting.

import lvgl as lv
from mpos import Activity
import art
import sound
import store
import ui
from creatures import by_id

_BG = 0x2D492B
_GROUND = 0x405E35
_TEXT_SOFT = 0xC7DDAE

_TENT = (
    ".......kk.......",
    "......kaak......",
    ".....kaaaak.....",
    "....kaa..aak....",
    "...kaa....aak...",
    "..kaa......aak..",
    ".kaaaaaaaaaaaak.",
    "kaaaaaaaaaaaaaak",
    "kkkkkkkkkkkkkkkk",
)
_TENT_PAL = {"k": ui.INK, "a": ui.TERRA}


class VisitorActivity(Activity):
    def onCreate(self):
        self.fox_id = store.visitor_pending()
        self.c = by_id(self.fox_id) if self.fox_id is not None else None
        if self.c is None or self.c["rarity"] != "norm":
            self.finish()
            return
        self.screen = ui.make_screen(_BG)
        self.setContentView(self.screen)
        self._build_meeting()

    def _button(self, text, on_click):
        btn = ui.panel(self.screen, 8, 198, 304, 34, ui.GREEN)
        label = ui.label(btn, text, 0, 0, ui.CREAM, ui.font_title(), w=300, center=True)
        label.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=on_click)

    def _build_meeting(self):
        s = self.screen
        s.clean()
        ui.label(
            s,
            "ER ZIT IETS IN DE STRUIKEN...",
            10,
            10,
            ui.CREAM,
            ui.font_title(),
            w=300,
        )
        ui.label(
            s,
            "Het lijkt op jou te wachten.",
            10,
            43,
            _TEXT_SOFT,
            ui.font_small(),
        )
        note = ui.box(s, 10, 62, 158, 22, 0x263F25, radius=ui.RADIUS)
        art.icon(note, "leaf", 1).set_pos(8, 7)
        ui.label(note, "het heeft geen haast", 25, 5, _TEXT_SOFT, ui.font_small())

        # Campsite at dusk: the player's tent on the left, paw prints leading
        # to the waiting silhouette on the right, hidden behind the shrub.
        ui.box(s, 0, 164, 320, 30, _GROUND)
        art.draw_sprite(s, _TENT, _TENT_PAL, 2).set_pos(18, 130)
        for x, y in ((118, 174), (150, 160)):
            art.icon(s, "spoor", 1).set_pos(x, y)
        creature = art.creature_panel(s, self.c, 5, silhouette=True)
        creature.set_pos(220, 92)
        art.icon(s, "bush", 5).set_pos(202, 122)
        for x, y in ((58, 34), (252, 24), (284, 82)):
            art.icon(s, "leaf", 1).set_pos(x, y)
        self._button("ZEG HALLO", self._reveal)

    def _reveal(self):
        cid = store.claim_visitor()
        if cid is None:
            sound.play("error")
            self.finish()
            return
        sound.play("caught")
        self._build_reveal()

    def _build_reveal(self):
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(0xCFE2AD), 0)
        ui.banner(s, "NIEUW BEZOEK", ui.GREEN)
        tier = ui.panel(s, 273, 5, 38, 17, ui.GREEN, border=ui.GREEN_D)
        ui.label(tier, "basis", 0, 3, ui.CREAM, ui.font_small(), w=34, center=True)

        card = ui.panel(s, 8, 32, 304, 120, ui.SURFACE_SOFT)
        art.icon(card, "leaf", 1).set_pos(12, 12)
        art.icon(card, "leaf", 1).set_pos(246, 78)
        art.icon(card, "bush", 2).set_pos(8, 78)
        speech = ui.panel(card, 62, 10, 48, 24, ui.CARD)
        ui.label(speech, "Prrr.", 7, 5, ui.INK, ui.font_small())
        sprite = art.creature_panel(card, self.c, 5, animate=True)
        sprite.set_pos(102, 34)
        ui.label(
            card,
            "%s WIL\nBLIJVEN!" % self.c["naam"].upper(),
            174,
            24,
            ui.GREEN_D,
            ui.font_title(),
            w=120,
            center=True,
        )

        info = ui.panel(s, 8, 158, 304, 32, ui.SURFACE_SOFT)
        art.icon(info, "boek", 1).set_pos(8, 9)
        ui.label(
            info,
            "%s - toegevoegd aan je boek!" % self.c["naam"],
            30,
            9,
            ui.INK,
            ui.font_small(),
            w=264,
        )
        self._button("VERDER", self._finish)

    def _finish(self):
        sound.play("tap")
        self.finish()
