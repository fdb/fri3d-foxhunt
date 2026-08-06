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

        # The whole page scrolls, not a clipped list inside it. An inner
        # scroller only ever had the pixels the fixed panels left over (45px,
        # one row), and every section below it needed a hard-coded y. One flex
        # column under the banner: sections stack, the roster is simply the
        # last and longest of them, and the page grows to fit.
        body = ui.box(s, 0, 26, 320, 214)
        body.add_flag(lv.obj.FLAG.SCROLLABLE)
        # LVGL resolves a scroll from the object the press HIT, and a hit needs
        # CLICKABLE — which ui.box strips. The grids elsewhere get away with it
        # because their cells are focusable and tile the whole area; here most
        # of the page is inert panel, so without this a drag anywhere but on a
        # toggle finds nothing and the page refuses to move.
        body.add_flag(lv.obj.FLAG.CLICKABLE)
        body.set_scroll_dir(lv.DIR.VER)
        body.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        body.set_style_pad_hor(6, 0)
        body.set_style_pad_ver(8, 0)
        body.set_style_pad_row(ui.GAP_M, 0)

        self.code_toggle, self.code_label = self._switch(
            body,
            "TESTCODE 1111",
            "voor elk beest",
            debug_code_enabled(),
            self._toggle_debug_code,
        )

        # pluk on ANY wifi network — for walking-around tests away from the
        # camp: no fri3d-badge hotspots exist yet, every AP becomes a
        # plukplek (identity stays the BSSID, reloads and yields included)
        self.pluk_toggle, self.pluk_label = self._switch(
            body,
            "PLUK OP ELKE WIFI",
            "thuis-testen",
            store.debug_cheat("pluk_any"),
            lambda: self._toggle_cheat("pluk_any", self.pluk_toggle, self.pluk_label),
        )

        # a beestenschool game costs energy, and a tired creature refuses —
        # right, but it makes testing a game a round of feeding first. This
        # zeroes the price (store.play_cost); the reward is untouched.
        self.moe_toggle, self.moe_label = self._switch(
            body,
            "ONVERMOEIBAAR",
            "spelen kost geen energie",
            store.debug_cheat("nooit_moe"),
            lambda: self._toggle_cheat("nooit_moe", self.moe_toggle, self.moe_label),
        )

        visit = ui.panel(body, 0, 0, 308, 34, ui.CARD)
        ui.label(visit, "RANDOM BEZOEK", 8, 3, ui.GREEN_D, ui.font_small())
        self.visit_label = ui.label(
            visit, "na 10 seconden", 8, 17, ui.INK, ui.font_small()
        )
        button = ui.box(visit, 178, 2, 110, 26, ui.GREEN, radius=ui.RADIUS)
        button.set_style_border_width(ui.BORDER, 0)
        button.set_style_border_color(ui.hexc(ui.GREEN_D), 0)
        label = ui.label(
            button, "START", 0, 0, ui.CREAM, ui.font_small(), w=110, center=True
        )
        label.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(button, on_click=self._schedule_visitor, focus_border=True)

        # Uitschrijven is not a debug tool: it is ALLES WISSEN in instellingen,
        # where a player can find it. This only says where, so nobody builds a
        # second one down here.
        account = ui.panel(body, 0, 0, 308, 25, ui.DORMANT, border=ui.BORDER_REST)
        ui.label(account, "ACCOUNT", 8, 7, ui.MYSTERY, ui.font_small())
        ui.label(
            account,
            "uitschrijven: instellingen",
            82,
            7,
            ui.TEXT_MUTED,
            ui.font_small(),
        )

        ui.label(body, "BEESTENBOEK", 0, 0, ui.GREEN_D, ui.font_small())

        caught = set(store.caught_ids())
        for creature in CREATURES:
            cid = creature["id"]
            row = ui.box(body, 0, 0, 308, 42, ui.CARD, radius=ui.RADIUS)
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

        self.setContentView(s)

    def _switch(self, parent, kop, uitleg, enabled, on_click):
        """One debug switch: a 34px titled panel with an ACTIEF / NIET ACTIEF
        toggle on the right. Placed by the body's flex column, so it carries no
        y of its own. Returns (button, label) so the click handler can repaint
        it — LVGL widgets have no __dict__ to hang state on."""
        panel = ui.panel(parent, 0, 0, 308, 34, ui.CARD)
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

    def _toggle_cheat(self, key, button, label):
        # store.debug_cheat, not a setting: settings survive ALLES WISSEN,
        # and an armed cheat must not outlive the player who armed it.
        sound.play("tap")
        enabled = not store.debug_cheat(key)
        store.set_debug_cheat(key, enabled)
        self._paint_toggle(
            button, label, enabled, on_text="ACTIEF", off_text="NIET ACTIEF"
        )

    def _schedule_visitor(self):
        sound.play("tap")
        store.schedule_debug_visitor(10)
        self.visit_label.set_text("komt over 10 sec - ga terug")

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
            # "debug", not the default "vangst": the dossier's lineage must
            # not claim a toggled-on creature was found in the field.
            store.add_caught(cid, origin="debug")
        self._paint_toggle(button, label, not caught)
