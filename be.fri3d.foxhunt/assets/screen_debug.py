# screen_debug.py — hidden test tools, unlocked from the code keypad.

import lvgl as lv
from mpos import Activity
import sound
import store
import ui
from creatures import CREATURES, by_id

DEBUG_CODE = "1111"


def _debug_creature():
    for creature in CREATURES:
        if creature["code"] == DEBUG_CODE:
            return creature
    return None


class DebugActivity(Activity):
    def onCreate(self):
        self.creature = _debug_creature()

        s = ui.make_screen(ui.PAPER)
        ui.banner(s, "DEBUG", ui.TERRA, right="TEST")

        add_panel = ui.panel(s, 6, 34, 308, 54, ui.CARD)
        ui.label(add_panel, "VASTE VANGST", 8, 5, ui.TERRA_D, ui.font_small())
        name = self.creature["naam"] if self.creature else "onbekend"
        ui.label(
            add_panel,
            "%s  -  code %s" % (name, DEBUG_CODE),
            8,
            25,
            ui.INK,
            ui.font_small(),
        )
        self.add_button = ui.box(add_panel, 202, 8, 96, 34, ui.GREEN, radius=3)
        self.add_button.set_style_border_width(ui.BORDER, 0)
        self.add_button.set_style_border_color(ui.hexc(ui.INK), 0)
        self.add_label = ui.label(
            self.add_button,
            "VANG 1111",
            0,
            0,
            ui.CREAM,
            ui.font_label(),
            w=96,
            center=True,
        )
        self.add_label.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(self.add_button, on_click=self._add)

        ui.label(s, "GEVONDEN BEESTEN", 8, 94, ui.GREEN_D, ui.font_small())
        self.caught_list = ui.panel(s, 6, 108, 308, 74, ui.SURFACE_SOFT)
        self.caught_list.add_flag(lv.obj.FLAG.SCROLLABLE)
        self.caught_list.set_scroll_dir(lv.DIR.VER)
        self.caught_list.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        self.caught_list.set_style_pad_all(4, 0)
        self.caught_list.set_style_pad_row(ui.GAP_S, 0)

        account = ui.panel(s, 6, 190, 308, 42, ui.DORMANT, border=ui.BORDER_REST)
        ui.label(account, "ACCOUNT", 8, 5, ui.MYSTERY, ui.font_small())
        ui.label(
            account,
            "registreren / uitschrijven: binnenkort",
            8,
            22,
            ui.TEXT_MUTED,
            ui.font_small(),
        )

        self._refresh()
        self.setContentView(s)

    def _refresh(self):
        self.caught_list.clean()
        caught = store.caught_ids()
        if not caught:
            ui.label(
                self.caught_list,
                "nog geen beesten gevonden",
                0,
                0,
                ui.TEXT_MUTED,
                ui.font_small(),
                w=294,
                center=True,
            )
            return

        for cid in caught:
            creature = by_id(cid)
            if creature is None:
                continue
            row = ui.box(self.caught_list, 0, 0, 294, 30, ui.CARD, radius=ui.RADIUS)
            row.set_style_border_width(ui.BORDER_THIN, 0)
            row.set_style_border_color(ui.hexc(ui.BORDER_REST), 0)
            ui.label(row, creature["naam"], 7, 8, ui.INK, ui.font_small(), w=188)
            remove = ui.box(row, 204, 3, 84, 24, ui.TERRA, radius=ui.RADIUS)
            remove.set_style_border_width(ui.BORDER, 0)
            remove.set_style_border_color(ui.hexc(ui.INK), 0)
            label = ui.label(
                remove,
                "VERWIJDER",
                0,
                0,
                ui.CREAM,
                ui.font_small(),
                w=84,
                center=True,
            )
            label.align(lv.ALIGN.CENTER, 0, 0)
            ui.focusable(remove, on_click=lambda cc=cid: self._remove(cc))

    def _add(self):
        sound.play("tap")
        if self.creature is None:
            sound.play("error")
            return
        store.add_caught(self.creature["id"])
        self.add_label.set_text("GEVANGEN")
        self._refresh()

    def _remove(self, cid):
        sound.play("tap")
        store.remove_caught(cid)
        if self.creature and cid == self.creature["id"]:
            self.add_label.set_text("VANG 1111")
        self._refresh()
