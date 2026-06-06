# screen_beast.py — the companion page for a CAUGHT creature ("boek" entry).
#
# Portrait + mood face on the left, the four living stats on the right, the
# log facts (gevonden op / plaats / waarnemingen) underneath, and three care
# actions along the bottom. pet.py owns the rules; store.py persists.

import lvgl as lv
from mpos import Activity
import ui
import art
import sound
import store
import pet
from creatures import by_id

_BAR_X = 116
_BAR_W = 150
_BAR_Y = (32, 72, 112, 152)

_COLORS = {"bond": ui.GOLD, "mood": ui.GREEN, "energy": ui.GREEN_D, "hunger": ui.TERRA}
_ACTIONS = (("voeden", "VOEDEN", ui.GREEN), ("aaien", "AAIEN", ui.GOLD), ("spelen", "SPELEN", ui.TERRA))


class BeastActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id)
        self.bars = {}          # stat key -> fill box
        self.vals = {}          # stat key -> value label

        s = ui.make_screen(ui.PAPER)
        rare = self.c["rarity"] != "norm"
        ui.banner(s, self.c["naam"], ui.GREEN,
                  right=("legendarisch" if self.c["rarity"] == "leg" else "zeldzaam" if rare else "gewoon"))

        # ── left: portrait + mood face ──────────────────────────────────
        card = ui.box(s, 6, 32, 92, 92, ui.CARD, radius=2)
        card.set_style_border_width(2, 0)
        card.set_style_border_color(ui.hexc(ui.GOLD if rare else ui.GREEN_D), 0)
        sp = art.creature_panel(card, self.c, 5)
        sp.align(lv.ALIGN.CENTER, 0, 0)
        self.face = ui.label(s, "", 6, 126, ui.INK, ui.font_label(), w=92, center=True)

        # ── left: log facts ─────────────────────────────────────────────
        self.lbl_date = ui.label(s, "", 6, 144, 0x5E6B44, ui.font_small(), w=104)
        self.lbl_place = ui.label(s, "", 6, 158, 0x5E6B44, ui.font_small(), w=104)
        self.lbl_seen = ui.label(s, "", 6, 172, 0x5E6B44, ui.font_small(), w=104)

        # ── right: the four living stats ────────────────────────────────
        for i, (key, text) in enumerate(pet.STATS):
            y = _BAR_Y[i]
            self.bars[key] = ui.statbar(s, _BAR_X, y, _BAR_W, text, 0.0, _COLORS[key])
            self.vals[key] = ui.label(s, "", _BAR_X + _BAR_W - 30, y, ui.INK, ui.font_small(), w=30, center=True)

        # ── feedback line + action buttons ──────────────────────────────
        self.msg = ui.label(s, "", 6, 190, ui.GREEN_D, ui.font_small(), w=308, center=True)
        for i, (action, text, color) in enumerate(_ACTIONS):
            b = ui.box(s, 6 + i * 104, 210, 100, 26, color, radius=3)
            b.set_style_border_width(2, 0)
            b.set_style_border_color(ui.hexc(ui.INK), 0)
            bl = ui.label(b, text, 0, 0, ui.CREAM, ui.font_label(), w=100, center=True)
            bl.align(lv.ALIGN.CENTER, 0, 0)
            ui.focusable(b, on_click=lambda a=action: self._act(a))

        self.setContentView(s)
        self._refresh()

    def onResume(self, screen):
        super().onResume(screen)
        self._refresh()         # re-apply time-decay every time you return

    def _refresh(self):
        st = store.beast_state(self.fox_id)
        if st is None:
            return
        # Narrow left column (~104px): keep each fact on one line so it can't
        # wrap and overrun the line below.
        self.lbl_date.set_text(st.get("date", "?"))
        self.lbl_place.set_text(st.get("place", "?"))
        self.lbl_seen.set_text("%dx gezien" % st.get("sightings", 1))
        self._set_values(st, "")

    def _set_values(self, st, msg):
        for key, _ in pet.STATS:
            v = st.get(key, 0)
            self.bars[key].set_width(max(0, int(_BAR_W * v / 100)))
            self.vals[key].set_text(str(v))
        ic, word = pet.face(st)
        self.face.set_text(ic + "  " + word)
        self.msg.set_text(msg)

    def _act(self, action):
        st, ok, msg = store.do_action(self.fox_id, action)
        if st is None:
            return
        sound.play("tap" if ok else "error")
        self._set_values(st, msg)
