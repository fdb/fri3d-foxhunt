# screen_restore.py — "Ik heb al een badge": ask the server whether this badge
# already belongs to a hunter, and adopt that account if it does.
#
# Three states in one Activity, rebuilt in place with screen.clean() the way
# RegSendActivity does it: asking -> found (welcome back) | no-luck (unknown
# badge, or the server didn't answer). The badge id is the whole key — it
# survives a wipe of the badge's filesystem, which is exactly the case this
# screen exists for.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
import mascot
import registrar
from registrar import REGISTRAR
from screen_register import RegisterActivity

ASK_BG = 0xDFEEBF  # same green wash as the send screen: same moment in the flow
STRIP_BG = 0xEFE7D0
ERR_BG = 0xF2E3CD
ERR_PANEL = 0xFBE4D6
ERR_FOOT_BG = 0xF9F1E2
ERR_FOOT_TX = 0x8A6A4E

# no-luck copy, keyed by what went wrong. "unknown" is not an error — the badge
# is simply new — so it gets the softer banner and points at registration.
_NO_LUCK = {
    "unknown": (
        "Deze badge staat nog niet in het boek. Registreer je eerst, dan "
        "onthoudt de server je vangsten.",
        "onbekende badge",
    ),
    "E-01": (
        "De cloud-server is niet bereikbaar. Probeer straks opnieuw, of "
        "registreer nu en synchroniseer later.",
        "server time-out",
    ),
}


class RestoreActivity(Activity):
    def onCreate(self):
        self.badge = registrar.badge_id()
        self.screen = ui.make_screen(ASK_BG)
        self.setContentView(self.screen)
        self._start_asking()

    # ---- state: asking ----------------------------------------------------
    def _start_asking(self):
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(ASK_BG), 0)
        ui.banner(s, "HERSTELLEN...", ui.GREEN)

        info = ui.panel(s, ui.PAD, 40, 304, 44, bg=ui.SURFACE_TINT, border=ui.GREEN)
        art.icon(info, "ant", 2).set_pos(8, 12)
        ui.label(
            info,
            "We vragen de server of deze badge al een jager heeft.",
            34,
            5,
            ui.INK,
            ui.font_small(),
            w=256,
        )

        strip = ui.panel(s, ui.PAD, 96, 304, 22, bg=STRIP_BG)
        ui.label(strip, "BADGE ID", 6, 3, ui.MYSTERY, ui.font_small())
        ui.label(strip, self.badge, 64, 3, ui.INK, ui.font_small())

        row = ui.panel(s, ui.PAD, 130, 304, 30, bg=ui.CARD)
        art.icon(row, "st_wait", 2).set_pos(8, 6)
        ui.label(row, "verbinden...", 34, 7, ui.INK, ui.font_small())

        ui.label(
            s,
            "even geduld - (B) annuleer",
            0,
            218,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=320,
            center=True,
        )

        REGISTRAR.restore(self.badge, self._on_update)

    def _on_update(self, st):
        # A verdict that lands after the player backed out is dropped.
        if not self.has_foreground():
            return
        if not st.get("done"):
            return
        if st.get("found"):
            sound.play("caught")
            self._adopt(st)
            self._build_found(st)
        else:
            sound.play("error")
            self._build_no_luck(st.get("error") or "unknown")

    def _adopt(self, st):
        """Save the recovered account locally, straight away — same reasoning
        as the send screen: whatever happens next, the badge has the profile.
        The maatje comes back as a shortcode (mascot.decode), so the player
        gets their own avatar rather than a default fox; an account from
        before shortcodes has none and falls back to the default."""
        head, accs, bg = mascot.decode(st.get("maatje"))
        store.save_profile(
            {
                "name": st.get("name") or "Jager",
                "head": head,
                "accs": accs,
                "bg": bg,
                "badge_id": self.badge,
                "hunter_id": st.get("hunter_id"),
                "synced": True,
            }
        )

    # ---- state: found -----------------------------------------------------
    def _build_found(self, st):
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(ui.PAPER), 0)
        ui.banner(s, "WELKOM TERUG!", ui.GREEN)

        p = store.profile() or {}
        card = ui.panel(s, 122, 38, 76, 76, bg=mascot.BGS[p.get("bg", 0)])
        mascot.draw(card, p.get("head", "vos"), p.get("accs", []), 4, x=4, y=4)
        ui.label(
            s,
            p.get("name", "Jager"),
            0,
            120,
            ui.INK,
            ui.font_title(),
            w=320,
            center=True,
        )

        strip = ui.panel(s, 80, 148, 160, 22, bg=STRIP_BG)
        art.icon(strip, "ant", 1).set_pos(6, 6)
        ui.label(strip, "JAGER ID", 20, 3, ui.MYSTERY, ui.font_small())
        ui.label(strip, st.get("hunter_id") or "volgt", 82, 3, ui.INK, ui.font_small())

        ui.label(
            s,
            "Je maatje is mee hersteld."
            if st.get("maatje")
            else "Je maatje kies je opnieuw in je profiel.",
            0,
            178,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=320,
            center=True,
        )

        btn = ui.box(s, 100, 200, 120, 32, ui.GREEN, radius=ui.RADIUS)
        btn.set_style_border_width(ui.BORDER, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        lbl = ui.label(
            btn, "START", 0, 0, ui.CREAM, ui.font_title(), w=116, center=True
        )
        lbl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=self._finish_registered)

    # ---- state: no luck ---------------------------------------------------
    def _build_no_luck(self, code):
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(ERR_BG), 0)
        text, detail = _NO_LUCK[code]
        unknown = code == "unknown"
        if unknown:
            ui.banner(s, "NIEUWE BADGE", ui.GREEN)
        else:
            ui.banner(s, "HERSTEL MISLUKT", ui.TERRA, right=code)

        panel = ui.panel(s, ui.PAD, 44, 304, 60, bg=ERR_PANEL, border=ui.TERRA)
        art.icon(panel, "st_bad" if not unknown else "st_wait", 2).set_pos(8, 20)
        ui.label(panel, text, 34, 5, ui.INK, ui.font_small(), w=258)

        first = ui.box(s, ui.PAD, 124, 148, 32, ui.GREEN, radius=ui.RADIUS)
        first.set_style_border_width(ui.BORDER, 0)
        first.set_style_border_color(ui.hexc(ui.INK), 0)
        fl = ui.label(
            first,
            "REGISTREER" if unknown else "OPNIEUW",
            0,
            0,
            ui.CREAM,
            ui.font_title(),
            w=144,
            center=True,
        )
        fl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(first, on_click=self._register if unknown else self._retry)

        back = ui.box(s, 164, 124, 148, 32, ui.CARD, radius=ui.RADIUS)
        back.set_style_border_width(ui.BORDER, 0)
        back.set_style_border_color(ui.hexc(ui.INK), 0)
        bl = ui.label(back, "TERUG", 0, 0, ui.INK, ui.font_title(), w=144, center=True)
        bl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(back, on_click=self._back)

        foot = ui.panel(s, ui.PAD, 216, 304, 20, bg=ERR_FOOT_BG)
        ui.label(
            foot,
            "%s - badge %s" % (detail, self.badge[-5:]),
            0,
            2,
            ERR_FOOT_TX,
            ui.font_small(),
            w=300,
            center=True,
        )

    # ---- actions ----------------------------------------------------------
    def _retry(self):
        sound.play("tap")
        self._start_asking()

    def _register(self):
        sound.play("tap")
        self.startActivityForResult(
            Intent(activity_class=RegisterActivity), self._child_done
        )

    def _child_done(self, result):
        if result and result.get("result_code") == "registered":
            self._finish_registered()

    def _back(self):
        sound.play("tap")
        self.finish()

    def _finish_registered(self):
        sound.play("tap")
        self.setResult("registered")
        self.finish()
