# screen_dossier.py — DOSSIER: the collection card for a caught creature.
#
# Header (portrait + name + nickname + LV + hearts), a 2-column facts grid, a
# "WEETJE" fun-fact, and a bond-to-next-level progress bar. Static facts come
# from creatures.py; the living bits from the companion state. Layout follows
# the design (detail.jsx PxDossier).

import lvgl as lv
from mpos import Activity
import ui
import art
import store
import pet
from creatures import by_id

_RARITY = {"norm": "gewoon", "rare": "zeldzaam", "leg": "legendarisch"}


class DossierActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        c = by_id(self.fox_id)
        st = store.beast_state(self.fox_id) or pet.default_state("?", "?", 0)
        bond = st["bond"]

        s = ui.make_screen(ui.PAPER)
        ui.banner(s, "Dossier", ui.GREEN, right="#%02d" % (self.fox_id + 1))

        # ── header ───────────────────────────────────────────────────────
        port = ui.panel(s, 8, 32, 64, 64, ui.SURFACE_SOFT)
        art.creature_panel(port, c, 3).align(lv.ALIGN.CENTER, 0, 0)
        ui.label(s, c["naam"], 82, 34, ui.INK, ui.font_title(), w=164)
        ui.label(
            s,
            'bijnaam "%s" . LV.%d' % (st.get("bijnaam") or c["naam"], pet.level(bond)),
            82,
            58,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=210,
        )
        ui.heart_row(s, 82, 76, pet.hearts(bond), scale=2)

        # ── facts grid ───────────────────────────────────────────────────
        facts = (
            ("soort", c["soort"]),
            ("biotoop", c["biotoop"]),
            ("zeldzaam", _RARITY.get(c["rarity"], "?")),
            ("1e vangst", st.get("date", "?")),
            ("plek", st.get("place", "?")),
            ("gezien", "%d keer" % st.get("sightings", 1)),
        )
        grid = ui.panel(s, 8, 104, 304, 64, ui.CARD)
        colw = 138
        for i, (k, v) in enumerate(facts):
            cx = 8 + (i % 2) * 150
            cy = 6 + (i // 2) * 18
            ui.label(grid, k, cx, cy, ui.MYSTERY, ui.font_small())
            vl = ui.label(grid, v, cx, cy, ui.INK, ui.font_small(), w=colw)
            vl.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)

        # ── leuk weetje ──────────────────────────────────────────────────
        weet = ui.panel(s, 8, 172, 304, 40, 0xEEF4D6)
        weet.set_style_border_color(ui.hexc(ui.GREEN), 0)
        ui.label(weet, "WEETJE", 8, 4, ui.GREEN_D, ui.font_small())
        ui.label(weet, c["weetje"], 64, 4, ui.INK, ui.font_small(), w=228)

        # ── bond progress to next level ──────────────────────────────────
        lvl = pet.level(bond)
        if lvl >= pet.LEVEL_MAX:
            ui.label(
                s, "max level!", 8, 218, ui.GOLD_D, ui.font_small(), w=304, center=True
            )
        else:
            pct = pet.level_pct(bond)
            ui.label(s, "naar LV.%d" % (lvl + 1), 8, 218, ui.INK, ui.font_small())
            track = ui.box(s, 76, 218, 196, 14, 0xD8C9A4)
            track.set_style_border_width(2, 0)
            track.set_style_border_color(ui.hexc(ui.INK), 0)
            fill = ui.box(track, 0, 0, max(2, int(196 * pct / 100)), 14, ui.GOLD)
            fill.align(lv.ALIGN.LEFT_MID, 0, 0)
            ui.label(
                s, "%d%%" % pct, 276, 218, 0x5E6B44, ui.font_small(), w=40, center=True
            )

        self.setContentView(s)
