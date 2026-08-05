# screen_reg_send.py — onboarding 3/3: send the profile, then celebrate or
# explain what went wrong.
#
# Three states in one Activity (design: PxRegSending / PxRegDone / PxRegError),
# rebuilt in place with screen.clean() like HomeActivity does. The profile is
# already saved locally before this screen opens; REGISTRAR only syncs it out,
# so a failure costs nothing but a retry ("je profiel is wel bewaard").

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
import companion
import registrar
from creatures import by_id
from registrar import REGISTRAR
from screen_starter import StarterActivity

SEND_BG = 0xDFEEBF
DONE_BG = 0x20301C
DONE_STRIP_BG = 0x14200F
DONE_TEXT = 0xBCD0A4
GOLD_INK = 0x3A2A0C
ERR_BG = 0xF2E3CD
ERR_PANEL = 0xFBE4D6
ERR_NOTE = 0xC2452F
ERR_FOOT_BG = 0xF9F1E2
ERR_FOOT_TX = 0x8A6A4E
NOTE_OK = 0x7D8A60

# note text per step-state; hunter "ok" shows the minted id instead
_NOTES = {
    "cloud": {"busy": "verbinden...", "ok": "opgeslagen", "fail": "geen antwoord"},
    "bridge": {
        "wait": "wacht",
        "busy": "verbinden...",
        "ok": "verbonden",
        "fail": "geen antwoord",
        "skip": "geen antenne",
    },
    "hunter": {
        "wait": "wacht",
        "busy": "munten...",
        "fail": "niet gemunt",
        "skip": "-",
    },
}
_ICONS = {"ok": "st_ok", "fail": "st_bad"}  # everything else: the little clock

_ERRORS = {
    "E-01": (
        "De cloud-server is niet bereikbaar. Je profiel is bewaard op je "
        "badge - probeer straks opnieuw.",
        "server time-out",
    ),
    "E-02": (
        "De bridge is niet bereikbaar. Je profiel is wel bewaard - ga "
        "dichter bij een relais staan en probeer opnieuw.",
        "bridge time-out",
    ),
}

# progress-bar target per completed step
_PCT = {"start": 8, "cloud": 40, "bridge": 72, "done": 100}


class RegSendActivity(Activity):
    def onCreate(self):
        self.p = store.profile() or {
            "name": "Jager",
            "head": "vos",
            "accs": [],
            "bg": 0,
        }
        self.screen = ui.make_screen(SEND_BG)
        self._bar_timer = None
        self._starter = None  # startbeest id once the server grants one
        self._exists = None  # the account payload, when the badge has one
        self.setContentView(self.screen)
        self._start_sending()

    def onDestroy(self, screen):
        super().onDestroy(screen)
        self._stop_bar()

    def _stop_bar(self):
        if self._bar_timer is not None:
            self._bar_timer.delete()
            self._bar_timer = None

    # ---- shared checklist -------------------------------------------------
    def _checklist(self, y, h, st):
        panel = ui.panel(self.screen, ui.PAD, y, 304, h, bg=ui.CARD)
        rows = (
            ("cloud", "Cloud-server"),
            ("bridge", "LoRa-bridge"),
            ("hunter", "Jager ID"),
        )
        step_h = (h - 16) // 3
        for i, (key, title) in enumerate(rows):
            ry = 6 + i * step_h
            state = st[key]
            art.icon(panel, _ICONS.get(state, "st_wait"), 2).set_pos(8, ry)
            ui.label(
                panel,
                title,
                32,
                ry + 2,
                ui.INK if state in ("ok", "fail", "busy") else ui.MYSTERY,
                ui.font_small(),
            )
            if key == "hunter" and state == "ok":
                note = st.get("hunter_id") or ""
            else:
                note = _NOTES[key].get(state, "")
            nl = ui.label(
                panel,
                note,
                150,
                ry + 2,
                ERR_NOTE
                if state == "fail"
                else (NOTE_OK if state == "ok" else ui.MYSTERY),
                ui.font_small(),
                w=140,
            )
            nl.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)
        return panel

    # ---- state: sending ---------------------------------------------------
    def _start_sending(self):
        self._stop_bar()
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(SEND_BG), 0)
        ui.banner(s, "REGISTREREN...", ui.GREEN)

        card = ui.panel(s, ui.PAD, 40, 56, 56, bg=companion.BGS[self.p["bg"]])
        companion.draw(card, self.p["head"], self.p["accs"], 3, x=2, y=2)
        ui.label(s, self.p["name"], 74, 44, ui.INK, ui.font_title())
        ui.label(s, self.p.get("badge_id", ""), 74, 70, ui.TEXT_MUTED, ui.font_small())

        self._steps = {
            "cloud": "busy",
            "bridge": "wait",
            "hunter": "wait",
            "hunter_id": None,
        }
        self._list = self._checklist(108, 80, self._steps)

        bar = ui.box(s, ui.PAD, 194, 304, 16, ui.DORMANT)
        bar.set_style_border_width(ui.BORDER, 0)
        bar.set_style_border_color(ui.hexc(ui.INK), 0)
        self._fill = ui.box(bar, 0, 0, 2, 12, ui.GREEN)
        self._pct = 0
        self._target = _PCT["start"]
        self._bar_timer = lv.timer_create(lambda t: self._creep(), 100, None)

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

        REGISTRAR.register(
            self.p["name"],
            self.p.get("badge_id", ""),
            companion.encode(self.p["head"], self.p["accs"], self.p["bg"]),
            self._on_update,
        )

    def _creep(self):
        if self._pct < self._target:
            self._pct = min(self._pct + 3, self._target)
            self._fill.set_width(max(2, self._pct * 300 // 100))

    def _on_update(self, st):
        # A verdict that lands after the player backed out is dropped.
        if not self.has_foreground():
            return
        if st["done"]:
            self._stop_bar()
            if st.get("exists"):
                # Neither done nor failed: the badge already has an account,
                # and only the player knows whether it is theirs.
                sound.play("tap")
                self._build_exists(st)
            elif st["ok"]:
                store.update_profile(hunter_id=st["hunter_id"], synced=True)
                self.p = store.profile() or self.p
                # Bank the startbeest right away — the reveal is only
                # theatre, so a player who backs out of it keeps the beest.
                starter = st.get("starter")
                if starter is not None and by_id(starter) is not None:
                    store.add_caught(starter, origin="start")
                    self._starter = starter
                sound.play("caught")
                self._build_done(st)
            else:
                sound.play("error")
                self._build_error(st)
            return
        # progress: refresh the checklist + push the bar along
        self._steps = st
        self._list.delete()
        self._list = self._checklist(108, 80, st)
        if st["bridge"] in ("ok", "busy"):
            self._target = _PCT["cloud"]
        if st["hunter"] in ("ok", "busy"):
            self._target = _PCT["bridge"]

    # ---- state: done ------------------------------------------------------
    def _build_done(self, st):
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(DONE_BG), 0)

        for x, y, sc in (
            (20, 44, 2),
            (286, 38, 3),
            (46, 158, 3),
            (274, 168, 2),
            (120, 62, 2),
        ):
            art.icon(s, "spark", sc).set_pos(x, y)

        ui.label(
            s,
            "+ JE BENT INGESCHREVEN +",
            0,
            30,
            ui.GOLD,
            ui.font_small(),
            w=320,
            center=True,
        )
        card = ui.panel(
            s, 122, 48, 76, 76, bg=companion.BGS[self.p["bg"]], border=ui.GOLD
        )
        companion.draw(card, self.p["head"], self.p["accs"], 4, x=4, y=4)
        ui.label(
            s, self.p["name"], 0, 130, ui.CREAM, ui.font_title(), w=320, center=True
        )

        strip = ui.panel(s, 80, 160, 160, 22, bg=DONE_STRIP_BG, border=ui.GOLD)
        art.icon(strip, "ant", 1).set_pos(6, 6)
        ui.label(strip, "JAGER ID", 20, 3, ui.GOLD, ui.font_small())
        ui.label(
            strip,
            st.get("hunter_id") or "volgt",
            82,
            3,
            ui.CREAM,
            ui.font_small(),
        )

        if st["bridge"] == "ok":
            line = "cloud ok - bridge ok - op jacht!"
        else:
            line = "cloud ok - op jacht!"
        ui.label(s, line, 0, 188, DONE_TEXT, ui.font_small(), w=320, center=True)

        btn = ui.box(s, 100, 206, 120, 28, ui.GOLD, radius=ui.RADIUS)
        btn.set_style_border_width(ui.BORDER, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        lbl = ui.label(
            btn, "START", 0, 0, GOLD_INK, ui.font_title(), w=116, center=True
        )
        lbl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=self._finish_registered)

    # ---- state: the badge already has an account --------------------------
    # The one thing the badge cannot work out on its own. badge_id is the MAC,
    # so "already registered" means this piece of hardware had an account —
    # the same player after a wipe, or a badge that changed hands. Adopting is
    # right for the first, overwriting for the second, and getting it wrong
    # either strands a jager's catches or puts a stranger's name on them. So
    # show them the account and let them say.
    def _build_exists(self, st):
        self._exists = st
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(ui.PAPER), 0)
        ui.banner(s, "BADGE AL BEKEND", ui.GOLD)

        info = ui.panel(s, ui.PAD, 30, 304, 38, bg=ui.SURFACE_TINT, border=ui.GREEN)
        art.icon(info, "ant", 2).set_pos(8, 9)
        ui.label(
            info,
            "Deze badge heeft al een jager. Ben jij dat?",
            34,
            9,
            ui.INK,
            ui.font_small(),
            w=256,
        )

        head, accs, bg = companion.decode(st.get("companion"))
        acct = ui.panel(s, ui.PAD, 74, 304, 74, bg=ui.CARD)
        card = ui.panel(acct, 6, 6, 60, 60, bg=companion.BGS[bg], border=ui.GOLD)
        companion.draw(card, head, accs, 3, x=4, y=4)
        ui.label(acct, st.get("name") or "Jager", 76, 8, ui.INK, ui.font_title())
        ui.label(acct, "JAGER ID", 76, 32, ui.MYSTERY, ui.font_small())
        ui.label(acct, st.get("hunter_id") or "volgt", 140, 32, ui.INK, ui.font_small())
        n = len(st.get("creatures") or [])
        ui.label(
            acct,
            "%d beest%s in het boek" % (n, "" if n == 1 else "en"),
            76,
            50,
            ui.TEXT_MUTED,
            ui.font_small(),
        )

        mine = ui.box(s, ui.PAD, 156, 148, 32, ui.GREEN, radius=ui.RADIUS)
        mine.set_style_border_width(ui.BORDER, 0)
        mine.set_style_border_color(ui.hexc(ui.INK), 0)
        ml = ui.label(
            mine, "DAT BEN IK", 0, 0, ui.CREAM, ui.font_title(), w=144, center=True
        )
        ml.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(mine, on_click=self._adopt_existing)

        new = ui.box(s, 164, 156, 148, 32, ui.CARD, radius=ui.RADIUS)
        new.set_style_border_width(ui.BORDER, 0)
        new.set_style_border_color(ui.hexc(ui.INK), 0)
        nl = ui.label(
            new, "OVERSCHRIJF", 0, 0, ui.INK, ui.font_title(), w=144, center=True
        )
        nl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(new, on_click=self._overwrite)

        ui.label(
            s,
            "DAT BEN IK herstelt dit account. OVERSCHRIJF zet jouw nieuwe naam "
            "en maatje erop; de beesten blijven bij de badge.",
            ui.PAD,
            194,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=304,
        )

    def _adopt_existing(self):
        sound.play("caught")
        registrar.adopt(self.p.get("badge_id", ""), self._exists)
        self.p = store.profile() or self.p
        self._finish_registered()

    def _overwrite(self):
        sound.play("tap")
        self._start_overwriting()

    def _start_overwriting(self):
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(SEND_BG), 0)
        ui.banner(s, "OVERSCHRIJVEN...", ui.GREEN)

        card = ui.panel(s, ui.PAD, 40, 56, 56, bg=companion.BGS[self.p["bg"]])
        companion.draw(card, self.p["head"], self.p["accs"], 3, x=2, y=2)
        ui.label(s, self.p["name"], 74, 44, ui.INK, ui.font_title())
        ui.label(s, self.p.get("badge_id", ""), 74, 70, ui.TEXT_MUTED, ui.font_small())

        row = ui.panel(s, ui.PAD, 108, 304, 30, bg=ui.CARD)
        art.icon(row, "st_wait", 2).set_pos(8, 6)
        ui.label(row, "jouw naam op dit account...", 34, 7, ui.INK, ui.font_small())

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

        REGISTRAR.overwrite(
            self.p["name"],
            self.p.get("badge_id", ""),
            companion.encode(self.p["head"], self.p["accs"], self.p["bg"]),
            self._on_overwrite,
        )

    def _on_overwrite(self, st):
        if not self.has_foreground() or not st["done"]:
            return
        if not st["ok"]:
            sound.play("error")
            self._build_error(
                {
                    "cloud": "fail",
                    "bridge": "fail",
                    "hunter": "fail",
                    "error": st.get("error") or "E-01",
                }
            )
            return
        # The account is this badge's now. Its hunter id and its catches stay:
        # both are keyed to the badge, and there is no second account to move
        # them to — only the name and the maatje change hands.
        registrar.adopt(
            self.p.get("badge_id", ""),
            self._exists,
            name=self.p["name"],
            code=companion.encode(self.p["head"], self.p["accs"], self.p["bg"]),
        )
        self.p = store.profile() or self.p
        sound.play("caught")
        self._build_done({"hunter_id": self._exists.get("hunter_id"), "bridge": "skip"})

    # ---- state: error -----------------------------------------------------
    def _build_error(self, st):
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(ERR_BG), 0)
        code = st.get("error") or "E-01"
        text, detail = _ERRORS[code]
        ui.banner(s, "REGISTRATIE MISLUKT", ui.TERRA, right=code)

        self._checklist(34, 76, st)

        panel = ui.panel(s, ui.PAD, 118, 304, 54, bg=ERR_PANEL, border=ui.TERRA)
        art.icon(panel, "st_bad", 2).set_pos(8, 17)
        ui.label(panel, text, 34, 5, ui.INK, ui.font_small(), w=258)

        retry = ui.box(s, ui.PAD, 178, 148, 32, ui.GREEN, radius=ui.RADIUS)
        retry.set_style_border_width(ui.BORDER, 0)
        retry.set_style_border_color(ui.hexc(ui.INK), 0)
        rl = ui.label(
            retry, "OPNIEUW", 0, 0, ui.CREAM, ui.font_title(), w=144, center=True
        )
        rl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(retry, on_click=self._retry)

        later = ui.box(s, 164, 178, 148, 32, ui.CARD, radius=ui.RADIUS)
        later.set_style_border_width(ui.BORDER, 0)
        later.set_style_border_color(ui.hexc(ui.INK), 0)
        ll = ui.label(later, "LATER", 0, 0, ui.INK, ui.font_title(), w=144, center=True)
        ll.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(later, on_click=self._finish_registered)

        foot = ui.panel(s, ui.PAD, 216, 304, 20, bg=ERR_FOOT_BG)
        badge = self.p.get("badge_id", "")
        ui.label(
            foot,
            "fout %s - %s  badge %s" % (code, detail, badge[-5:]),
            0,
            2,
            ERR_FOOT_TX,
            ui.font_small(),
            w=300,
            center=True,
        )

    def _retry(self):
        sound.play("tap")
        self._start_sending()

    def _finish_registered(self):
        sound.play("tap")
        if self._starter is not None:
            # The reveal rides between "ingeschreven" and home: START opens
            # it, VERDER there closes the whole onboarding chain.
            self.startActivityForResult(
                Intent(
                    activity_class=StarterActivity,
                    extras={"fox_id": self._starter},
                ),
                self._starter_done,
            )
            return
        self.setResult("registered")
        self.finish()

    def _starter_done(self, _result):
        self.setResult("registered")
        self.finish()
