# screen_debug.py — hidden test tools, unlocked from the code keypad.

import lvgl as lv
from mpos import Activity
import art
import sound
import store
import ui
from creatures import CREATURES
from debug_unlock import DEBUG_CODE, enable_debug_code


class DebugActivity(Activity):
    def onCreate(self):
        # Debug mode lasts for this app session. Once unlocked, 1111 catches
        # whichever creature the player is currently hunting.
        enable_debug_code()

        s = ui.make_screen(ui.PAPER)
        ui.banner(s, "DEBUG", ui.TERRA, right=DEBUG_CODE)

        code_panel = ui.panel(s, 6, 34, 308, 42, ui.CARD)
        ui.label(code_panel, "TESTCODE ACTIEF", 8, 5, ui.TERRA_D, ui.font_small())
        ui.label(
            code_panel,
            "elk beest vang je nu met code %s" % DEBUG_CODE,
            8,
            22,
            ui.INK,
            ui.font_small(),
        )

        ui.label(s, "BEESTENBOEK", 8, 84, ui.GREEN_D, ui.font_small())
        self.roster = ui.panel(s, 6, 98, 308, 101, ui.SURFACE_SOFT)
        self.roster.add_flag(lv.obj.FLAG.SCROLLABLE)
        self.roster.set_scroll_dir(lv.DIR.VER)
        self.roster.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        self.roster.set_style_pad_all(4, 0)
        self.roster.set_style_pad_row(ui.GAP_S, 0)

        caught = set(store.caught_ids())
        for creature in CREATURES:
            cid = creature["id"]
            row = ui.box(self.roster, 0, 0, 294, 42, ui.CARD, radius=ui.RADIUS)
            row.set_style_border_width(ui.BORDER_THIN, 0)
            row.set_style_border_color(ui.hexc(ui.BORDER_REST), 0)

            sprite = art.creature_panel(row, creature, 2)
            sprite.align(lv.ALIGN.LEFT_MID, 6, 0)
            ui.label(row, creature["naam"], 45, 14, ui.INK, ui.font_small(), w=130)

            toggle = ui.box(row, 178, 7, 110, 28, ui.DORMANT, radius=ui.RADIUS)
            toggle.set_style_border_width(ui.BORDER, 0)
            toggle.set_style_border_color(ui.hexc(ui.BORDER_REST), 0)
            state = ui.label(
                toggle,
                "",
                0,
                0,
                ui.INK,
                ui.font_small(),
                w=110,
                center=True,
            )
            state.align(lv.ALIGN.CENTER, 0, 0)
            self._paint_toggle(toggle, state, cid in caught)
            ui.focusable(
                toggle,
                on_click=lambda cc=cid, bb=toggle, ll=state: self._toggle(cc, bb, ll),
                focus_border=True,
            )

        account = ui.panel(s, 6, 207, 308, 25, ui.DORMANT, border=ui.BORDER_REST)
        ui.label(account, "ACCOUNT", 8, 7, ui.MYSTERY, ui.font_small())
        ui.label(
            account,
            "registreren / uitschrijven: binnenkort",
            82,
            7,
            ui.TEXT_MUTED,
            ui.font_small(),
        )

        self.setContentView(s)

    def _paint_toggle(self, button, label, caught):
        button.set_style_bg_color(ui.hexc(ui.GREEN if caught else ui.DORMANT), 0)
        button.set_style_border_color(
            ui.hexc(ui.GREEN_D if caught else ui.BORDER_REST), 0
        )
        label.set_text("GEVANGEN" if caught else "NIET GEV.")
        label.set_style_text_color(ui.hexc(ui.CREAM if caught else ui.INK), 0)

    def _toggle(self, cid, button, label):
        sound.play("tap")
        caught = store.is_caught(cid)
        if caught:
            store.remove_caught(cid)
        else:
            store.add_caught(cid)
        self._paint_toggle(button, label, not caught)
