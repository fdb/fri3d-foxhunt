# screen_welcome.py — onboarding 0: the front door, shown on first launch.
#
# Title art fills the top half (assets/title-screen/), the bottom half offers
# the two ways in: REGISTREER for a fresh badge, "herstel" for a badge that was
# already registered once (a reset badge, or a swapped one). No banner — the
# art is the header — and no back button, per the house rules.
#
# Both routes save the profile before they report "registered" back up, so the
# router underneath (foxhunt.py) opens the book either way when this closes.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
from screen_register import RegisterActivity
from screen_restore import RestoreActivity

_IMG_H = 120  # the title art is authored 320x120 — exactly the top half
_LINK_H = 22
_UNDERLINE_Y = 16


class WelcomeActivity(Activity):
    def onCreate(self):
        s = ui.make_screen(ui.PAPER)
        art.picture(s, art.TITLE_SRC, 0, 0)

        ui.label(
            s,
            "Spoor de beesten van het bos op.",
            0,
            _IMG_H + 12,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=320,
            center=True,
        )

        btn = ui.box(s, ui.PAD, 156, 304, 40, ui.GREEN, radius=ui.RADIUS)
        btn.set_style_border_width(ui.BORDER, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        lbl = ui.label(
            btn, "REGISTREER", 0, 0, ui.CREAM, ui.font_title(), w=300, center=True
        )
        lbl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=self._register)

        # "already have a badge" link: a text button, underlined the way a link
        # is, so it reads as the quieter of the two routes without a second
        # button competing with the CTA.
        link = ui.box(s, ui.PAD, 208, 304, _LINK_H)
        text = ui.label(link, "Herstel mijn account", 0, 0, ui.GREEN_D, ui.font_small())
        # The underline has to match the *text* width, not the box width, and
        # only LVGL knows what the bitmap font measured — so leave the label
        # auto-sized, lay it out, and read the width back instead of counting
        # characters here (which breaks the moment the wording changes).
        link.update_layout()
        tw = text.get_width()
        text.set_x((304 - tw) // 2)
        ui.box(link, (304 - tw) // 2, _UNDERLINE_Y, tw, 2, ui.GREEN)
        ui.focusable(link, on_click=self._restore)

        self.setContentView(s)

    def _register(self):
        sound.play("tap")
        self.startActivityForResult(
            Intent(activity_class=RegisterActivity), self._child_done
        )

    def _restore(self):
        sound.play("tap")
        self.startActivityForResult(
            Intent(activity_class=RestoreActivity), self._child_done
        )

    def _child_done(self, result):
        if result and result.get("result_code") == "registered":
            self.setResult("registered")
            self.finish()
