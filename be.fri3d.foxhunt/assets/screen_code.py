# screen_code.py — PIN keypad -> validate -> win / error.
#
# Typing the code is not the end of it: the code goes to the fox network to be
# checked (a real request once the LoRa backend lands, a faked round trip
# today), and only an "ok" reveals the creature. So the screen has three
# states — typing, waiting for the verdict, and showing an error — and the
# keypad is dead while a verdict is in flight.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
from creatures import by_id
from fox_radio import RADIO
from screen_win import WinActivity

# No confirm key: the 4th digit IS the submit, so an OK would only ever fire on
# an unfinished code. "" is the hole that leaves, keeping 0 centred under 8 and
# backspace bottom-right where a keypad puts it.
KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "<"]
CODE_LEN = 4
RED = 0xD6483A  # backspace: the one key that destroys what you typed

# Status line under the panel: one entry per state the player can be in, plus
# one per verdict the radio can hand back (see FoxRadio.submit_code).
STATUS = {
    "idle": ("vul de code in", ui.TEXT_MUTED),
    "checking": ("controleren...", ui.GREEN_D),
    "wrong": ("verkeerde code", ui.TERRA_D),
    "used": ("code al gebruikt", ui.TERRA_D),
}


class CodeActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id)
        self.entry = ""
        self.waiting = False  # a verdict is in flight; the keypad is dead

        s = ui.make_screen(0xDFEEBF)
        ui.banner(s, "VOER DE CODE IN", ui.GREEN)

        kw, kh, kg = 58, 45, 6
        # 3 keys per row; +4px slack so the exact-fit 3rd column never wraps early
        pad = ui.row(s, 6, 34, 3 * kw + 2 * kg + 4, 4 * kh + 3 * kg, gap=kg, wrap=True)
        for k in KEYS:
            if not k:  # the hole where OK used to be: a spacer, not a key
                ui.box(pad, 0, 0, kw, kh, None)
                continue
            b = ui.box(pad, 0, 0, kw, kh, ui.CARD, radius=3)
            b.set_style_border_width(2, 0)
            if k == "<":
                # An icon says "wist een cijfer" where a "<" only says "left",
                # and the red frame sets it apart from the digits at a glance.
                b.set_style_border_color(ui.hexc(RED), 0)
                art.icon(b, "backspace", 2).align(lv.ALIGN.CENTER, 0, 0)
            else:
                b.set_style_border_color(ui.hexc(ui.INK), 0)
                kl = ui.label(b, k, 0, 0, ui.INK, ui.font_title(), w=kw, center=True)
                kl.align(lv.ALIGN.CENTER, 0, 0)
            ui.focusable(b, on_click=lambda kk=k: self.press(kk))
            # LVGL delivers keys to whichever widget has focus, and on this
            # screen that is always one of these — so every key carries the
            # same handler and you can just type the code (desktop only; the
            # badge has no number keys, so it simply never fires there).
            b.add_event_cb(self._on_key, lv.EVENT.KEY, None)

        self.dots = ui.label(
            s, "____", 198, 40, ui.INK, ui.font_title(), w=116, center=True
        )
        # dark scanner panel: the white fill needs a dark ground to read against
        self.rev = ui.box(s, 214, 80, 92, 92, ui.INK, radius=2)
        self.rev.set_style_border_width(2, 0)
        self.rev.set_style_border_color(ui.hexc(ui.TERRA), 0)
        self._sprite = None
        self._draw_reveal()  # starts as a full silhouette
        self.status = ui.label(
            s, "", 198, 178, ui.TEXT_MUTED, ui.font_small(), w=116, center=True
        )
        self._set_status("idle")

        self.setContentView(s)

    def onPause(self, screen):
        super().onPause(screen)
        # A verdict that lands while we're away is dropped (see _on_verdict),
        # so don't leave the keypad locked waiting for one that never applies.
        self.waiting = False
        self._set_status("idle")

    def _set_status(self, state):
        text, colour = STATUS[state]
        self.status.set_text(text)
        self.status.set_style_text_color(ui.hexc(colour), 0)

    def _draw_reveal(self):
        # Progress only: the shape fills in white top-down, a quarter per digit.
        # Never the real art — the creature is only unmasked on the win screen,
        # after the code is entered in full AND validated.
        if self._sprite is not None:
            self._sprite.delete()
        self._sprite = art.creature_panel(
            self.rev,
            self.c,
            4,
            reveal=len(self.entry) / CODE_LEN,
            mask=art.MASK,
            veil=art.GHOST,  # dark panel: the plain silhouette would vanish
        )
        self._sprite.align(lv.ALIGN.CENTER, 0, 0)

    def _on_key(self, e):
        """Type the code on a real keyboard instead of tapping the keys."""
        k = e.get_key()
        if 48 <= k <= 57:  # '0'..'9'
            self.press(chr(k))
        elif k == lv.KEY.BACKSPACE or k == lv.KEY.DEL:
            self.press("<")

    def press(self, k):
        if self.waiting:
            return  # keypad is dead until the network answers
        sound.play("tap")
        if k == "<":
            self.entry = self.entry[:-1]
        elif len(self.entry) < CODE_LEN:
            self.entry += k
        self._set_status("idle")  # typing clears the last error
        self.dots.set_text((self.entry + "____")[:CODE_LEN])
        self._draw_reveal()
        if len(self.entry) == CODE_LEN:
            self._submit()

    def _submit(self):
        """Ask the fox network to validate the code; the verdict arrives later."""
        self.waiting = True
        self._set_status("checking")
        RADIO.submit_code(self.fox_id, self.entry, self._on_verdict)

    def _on_verdict(self, result):
        # The reply can land after the player has already left this screen.
        if not self.has_foreground():
            return
        self.waiting = False
        if result == "ok":
            store.add_caught(self.fox_id)
            # Legendary catches get their fanfare from the win screen itself
            # (celebrate.Fireworks), so it loops in sync with the visuals.
            if self.c["rarity"] != "leg":
                sound.play("caught")
            self.startActivity(
                Intent(activity_class=WinActivity, extras={"fox_id": self.fox_id})
            )
            return
        sound.play("error")
        self._set_status(result)
        self.entry = ""
        self.dots.set_text("____")
        self._draw_reveal()
