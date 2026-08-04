# screen_debug.py — hidden test tools, unlocked from the code keypad.

import lvgl as lv
from mpos import Activity
import art
import sound
import store
import ui
from creatures import CREATURES
from debug_unlock import (
    DEBUG_CODE,
    debug_code_enabled,
    disable_debug_code,
    enable_debug_code,
)


class DebugActivity(Activity):
    def onCreate(self):
        s = ui.make_screen(ui.PAPER)
        ui.banner(s, "DEBUG", ui.TERRA, right=DEBUG_CODE)

        self.code_toggle, self.code_label = self._switch(
            s,
            34,
            "TESTCODE 1111",
            "voor elk beest",
            debug_code_enabled(),
            self._toggle_debug_code,
        )

        # pluk on ANY wifi network — for walking-around tests away from the
        # camp: no fri3d-badge hotspots exist yet, every AP becomes a
        # plukplek (identity stays the BSSID, reloads and yields included)
        self.pluk_toggle, self.pluk_label = self._switch(
            s,
            72,
            "PLUK OP ELKE WIFI",
            "thuis-testen",
            bool(store.settings().get("pluk_any")),
            lambda: self._toggle_setting("pluk_any", self.pluk_toggle, self.pluk_label),
        )

        # a beestenschool game costs energy, and a tired creature refuses —
        # right, but it makes testing a game a round of feeding first. This
        # zeroes the price (store.play_cost); the reward is untouched.
        self.moe_toggle, self.moe_label = self._switch(
            s,
            110,
            "ONVERMOEIBAAR",
            "spelen kost geen energie",
            bool(store.settings().get("nooit_moe")),
            lambda: self._toggle_setting("nooit_moe", self.moe_toggle, self.moe_label),
        )

        ui.label(s, "BEESTENBOEK", 8, 145, ui.GREEN_D, ui.font_small())
        self.roster = ui.panel(s, 6, 160, 308, 45, ui.SURFACE_SOFT)
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

    def _switch(self, s, y, kop, uitleg, enabled, on_click):
        """One debug switch: a 34px titled panel with an ACTIEF / NIET ACTIEF
        toggle on the right. Returns (button, label) so the click handler can
        repaint it — LVGL widgets have no __dict__ to hang state on."""
        panel = ui.panel(s, 6, y, 308, 34, ui.CARD)
        ui.label(panel, kop, 8, 3, ui.TERRA_D, ui.font_small())
        ui.label(panel, uitleg, 8, 17, ui.INK, ui.font_small())
        button = ui.box(panel, 178, 2, 110, 26, ui.DORMANT, radius=ui.RADIUS)
        button.set_style_border_width(ui.BORDER, 0)
        label = ui.label(button, "", 0, 0, ui.INK, ui.font_small(), w=110, center=True)
        label.align(lv.ALIGN.CENTER, 0, 0)
        self._paint_toggle(
            button, label, enabled, on_text="ACTIEF", off_text="NIET ACTIEF"
        )
        ui.focusable(button, on_click=on_click, focus_border=True)
        return button, label

    def _paint_toggle(
        self, button, label, enabled, on_text="GEVANGEN", off_text="NIET GEV."
    ):
        button.set_style_bg_color(ui.hexc(ui.GREEN if enabled else ui.DORMANT), 0)
        button.set_style_border_color(
            ui.hexc(ui.GREEN_D if enabled else ui.BORDER_REST), 0
        )
        label.set_text(on_text if enabled else off_text)
        label.set_style_text_color(ui.hexc(ui.CREAM if enabled else ui.INK), 0)

    def _toggle_setting(self, key, button, label):
        sound.play("tap")
        enabled = not store.settings().get(key)
        store.set_setting(key, enabled)
        self._paint_toggle(
            button, label, enabled, on_text="ACTIEF", off_text="NIET ACTIEF"
        )

    def _toggle_debug_code(self):
        sound.play("tap")
        enabled = debug_code_enabled()
        if enabled:
            disable_debug_code()
        else:
            enable_debug_code()
        self._paint_toggle(
            self.code_toggle,
            self.code_label,
            not enabled,
            on_text="ACTIEF",
            off_text="NIET ACTIEF",
        )

    def _toggle(self, cid, button, label):
        sound.play("tap")
        caught = store.is_caught(cid)
        if caught:
            store.remove_caught(cid)
        else:
            store.add_caught(cid)
        self._paint_toggle(button, label, not caught)
