# screen_wipe.py — ALLES WISSEN: hand the badge on, or leave the game.
#
# Reached from instellingen. It ends the account on BOTH sides — the server row
# and everything this badge saved — because ending it on one side alone is not
# a fresh start: badge_id is the MAC and never changes, so a badge that wiped
# only itself would re-register straight into the "deze badge is al bekend"
# fork and be handed every catch back (registrar.adopt, CLAUDE.md).
#
# TYPE THE WORD. A confirm button is not enough protection here. The badge has
# a resistive touchscreen in a pocket at a camp, stray taps are ordinary, and
# this is the one screen in the app where a stray tap costs a week of hunting.
# Typing takes a keyboard, a word and an intent that no pocket produces.
#
# Order of operations, and it is the whole safety design: the SERVER goes first.
# The local wipe is the step nobody can undo, so it only happens once the server
# has confirmed. A server that does not answer leaves the badge exactly as it
# was — which is also why this screen needs no separate "is there wifi" check.

import lvgl as lv
from mpos import Activity
from mpos.ui.keyboard import MposKeyboard
import ui
import store
import sound
import registrar

# What the player has to type. Compared case-insensitively — the OS keyboard
# opens on lowercase and making people find the shift key is friction that
# protects nothing.
CONFIRM_WORD = "DELETE"

FIELD_BG = 0xFFF9EA
PLACEHOLDER = 0xA89A78
BTN_OFF_BG = 0xE6DCC2
BTN_OFF_TX = 0xA2957A
BTN_OFF_BORDER = 0xB3A68A

_FIELD_Y = 128  # resting position (under the prompt)
_FIELD_Y_KB = 30  # hopped up while the keyboard covers the lower half


class WipeActivity(Activity):
    def onCreate(self):
        s = ui.make_screen(ui.PAPER)
        ui.banner(s, "ALLES WISSEN", ui.TERRA)

        # Name what is lost, in the words the player knows them by. "Profiel"
        # would be true and useless: nobody weighs losing a profiel, everybody
        # weighs losing their beesten.
        self.warn = ui.panel(s, ui.PAD, 32, 304, 76, bg=ui.CARD, border=ui.TERRA)
        ui.label(
            self.warn,
            "Weg van deze badge EN van de server:",
            8,
            4,
            ui.TERRA_D,
            ui.font_small(),
            w=288,
        )
        ui.label(
            self.warn,
            "je naam, je maatje, al je beesten,\n"
            "je vrienden en je voorraad.\n"
            "Je plek op het scorebord.",
            8,
            19,
            ui.INK,
            ui.font_small(),
            w=288,
        )
        ui.label(
            self.warn,
            "Dit kan niet ongedaan gemaakt worden.",
            8,
            58,
            ui.TERRA_D,
            ui.font_small(),
            w=288,
        )

        self.prompt = ui.label(
            s,
            "Typ " + CONFIRM_WORD + " om te bevestigen.",
            ui.PAD,
            113,
            ui.TEXT_MUTED,
            ui.font_small(),
        )

        # Same field + OS keyboard pairing as the name entry (screen_register):
        # a styled lv.textarea is the only thing MposKeyboard can type into.
        ta = lv.textarea(s)
        ta.set_pos(ui.PAD, _FIELD_Y)
        ta.set_size(304, 30)
        ta.set_one_line(True)
        ta.set_max_length(len(CONFIRM_WORD))
        ta.set_placeholder_text("tik om te typen")
        ta.set_style_bg_color(ui.hexc(FIELD_BG), 0)
        ta.set_style_border_width(ui.BORDER, 0)
        ta.set_style_border_color(ui.hexc(ui.INK), 0)
        ta.set_style_radius(ui.RADIUS, 0)
        ta.set_style_pad_hor(6, 0)
        ta.set_style_pad_ver(1, 0)
        ta.set_style_text_color(ui.hexc(ui.INK), 0)
        f = ui.font_title()
        if f is not None:
            ta.set_style_text_font(f, 0)
        try:
            ta.set_style_text_color(ui.hexc(PLACEHOLDER), lv.PART.TEXTAREA_PLACEHOLDER)
        except AttributeError:
            pass
        self.ta = ta

        self.btn = ui.box(s, ui.PAD, 166, 304, 34, BTN_OFF_BG, radius=ui.RADIUS)
        self.btn.set_style_border_width(ui.BORDER, 0)
        self.btn_label = ui.label(
            self.btn, "WIS ALLES", 0, 0, BTN_OFF_TX, ui.font_title(), w=300, center=True
        )
        self.btn_label.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(self.btn, on_click=self._wipe)
        self._btn_ready = False
        self._busy = False
        self._style_btn(False)

        self.status = ui.label(
            s,
            "Veeg vanaf de linkerrand om te stoppen.",
            ui.PAD,
            210,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=304,
            center=True,
        )

        self.kb = MposKeyboard(s)
        self.kb.set_textarea(ta)
        self.kb.add_flag(lv.obj.FLAG.HIDDEN)
        ta.add_event_cb(lambda e: self._kb_open(), lv.EVENT.CLICKED, None)
        self.kb.add_event_cb(self._kb_event, lv.EVENT.READY, None)
        self.kb.add_event_cb(self._kb_event, lv.EVENT.CANCEL, None)

        # The keyboard types with set_text, which fires no event worth trusting
        # (screen_register hit the same wall), so a light poll keeps the button
        # honest. onResume starts it — setContentView calls that straight after.
        self._timer = None

        self.setContentView(s)

    def onResume(self, screen):
        super().onResume(screen)
        self._start_poll()

    def _start_poll(self):
        if self._timer is None:
            self._timer = lv.timer_create(lambda t: self._refresh_btn(), 300, None)

    def onPause(self, screen):
        super().onPause(screen)
        self._stop_poll()

    def onDestroy(self, screen):
        super().onDestroy(screen)
        self._stop_poll()

    def _stop_poll(self):
        if self._timer is not None:
            self._timer.delete()
            self._timer = None

    # ---- keyboard open/close ----------------------------------------------
    def _kb_open(self):
        for w in (self.warn, self.prompt, self.btn, self.status):
            w.add_flag(lv.obj.FLAG.HIDDEN)
        self.ta.set_y(_FIELD_Y_KB)

    def _kb_event(self, e):
        for w in (self.warn, self.prompt, self.btn, self.status):
            w.remove_flag(lv.obj.FLAG.HIDDEN)
        self.ta.set_y(_FIELD_Y)
        self._refresh_btn()

    # ---- the button --------------------------------------------------------
    def _confirmed(self):
        return self.ta.get_text().strip().upper() == CONFIRM_WORD

    def _style_btn(self, ready):
        self._btn_ready = ready
        if ready:
            self.btn.set_style_bg_color(ui.hexc(ui.TERRA), 0)
            self.btn.set_style_border_color(ui.hexc(ui.INK), 0)
            self.btn_label.set_style_text_color(ui.hexc(ui.CREAM), 0)
        else:
            self.btn.set_style_bg_color(ui.hexc(BTN_OFF_BG), 0)
            self.btn.set_style_border_color(ui.hexc(BTN_OFF_BORDER), 0)
            self.btn_label.set_style_text_color(ui.hexc(BTN_OFF_TX), 0)

    def _refresh_btn(self):
        if self._busy:
            return
        ready = self._confirmed()
        if ready != self._btn_ready:
            self._style_btn(ready)

    # ---- doing it ----------------------------------------------------------
    def _wipe(self):
        if self._busy or not self._confirmed():
            sound.play("error")
            return
        sound.play("tap")
        self._busy = True
        self._stop_poll()  # nothing may repaint the button while it runs
        self._style_btn(False)
        self.btn_label.set_text("WISSEN...")
        self.status.set_text("De server wordt bijgewerkt.")
        self.status.set_style_text_color(ui.hexc(ui.TEXT_MUTED), 0)
        registrar.REGISTRAR.delete_account(registrar.badge_id(), self._on_delete)

    def _on_delete(self, st):
        if not st.get("done"):
            return
        if not st.get("ok"):
            if not self.has_foreground():
                # The player walked out mid-wait and this screen is destroyed:
                # every widget below is a dangling reference, and nothing was
                # wiped on either side. Silently drop the verdict.
                return
            # Nothing has been touched yet, on either side. Say so — a player
            # who thinks the wipe half-happened will go looking for damage.
            sound.play("error")
            self._busy = False
            self.btn_label.set_text("WIS ALLES")
            self.status.set_text(
                "Geen verbinding met de server (%s). Niets is gewist."
                % (st.get("error") or "E-01")
            )
            self.status.set_style_text_color(ui.hexc(ui.TERRA_D), 0)
            self._start_poll()  # so the button can arm again for a retry
            return
        # The server is done; the badge follows — even if the player wandered
        # off mid-wait. They typed the word and pressed the button, and the
        # server row is already gone: keeping the local profile would leave the
        # badge living on a deleted account. From here the profile is gone,
        # which is the signal every screen below reads on the way out: settings
        # and the boek finish themselves, and the router (foxhunt.py) shows the
        # welcome screen again.
        store.reset_all()
        # finish() pops the TOP of the screen stack unconditionally, which is
        # only this screen while it still has the foreground — a late verdict
        # must not close whatever the player is looking at now.
        if self.has_foreground():
            self.finish()
