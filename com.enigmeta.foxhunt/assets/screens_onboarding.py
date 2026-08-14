# screens_onboarding.py — the first-run flow, one module.
#
# welcome -> uitleg -> register -> companion -> reg_send -> starter, plus
# restore (herstel mijn account). Seven screens merged into one file for
# LittleFS block economy (see CLAUDE.md, "Size budget"); each section
# below keeps its original header. Repeated imports between sections are
# harmless (sys.modules lookups). Style constants stay with their screens,
# but a later section must NOT rebind an earlier section's bare name — it
# prefixes its own copy instead (RESTORE_*, STARTER_*), because the module
# namespace is flat and the later binding silently wins at runtime.


# ═════════════════════════ screen_welcome ═════════════════════════
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


# ═════════════════════════ screen_uitleg ═════════════════════════
# screen_uitleg.py — HOE SPEEL JE?: the core loop in three rows, in the
# player's own mode (GAME_DESIGN.md, Roles and navigation).
#
# One screen, two texts: a verzamelaar reads their three verbs and learns
# that jagers bring the new creatures; a jager reads the hunt first and
# learns that verzamelaars hold the food. Shown once when the home screen
# first opens (store flag), and always reachable from instellingen. The
# text changes when the mode does, because it is rebuilt on every open.

import lvgl as lv
from mpos import Activity
import ui
import art
import sound
import store

# (icon, scale, kop, tekst) — icon grids differ (pluk/snuf 16px, ball/ant
# 8px), so the scale normalises every icon to exactly 32px
_VERZAMELAAR = (
    ("pluk", 2, "PLUKKEN", "loop naar een wifi-plek en pluk het eten"),
    ("snuf", 2, "SNUFFELEN", "badge tegen badge - deel een picknick"),
    ("ball", 4, "SPELEN", "voer je beest en speel - zo groeit de band"),
)
_VERZAMELAAR_VOET = "jagers brengen nieuwe beesten het kamp binnen"
_JAGER = (
    ("ant", 4, "JAGEN", "volg het signaal naar de vos - vang het beest"),
    ("pluk", 2, "VERZAMELEN", "pluk eten en snuffel met andere spelers"),
    ("ball", 4, "SPELEN", "voer je beest en speel - zo groeit de band"),
)
_JAGER_VOET = "verzamelaars hebben het eten dat jouw beesten zoeken"


class UitlegActivity(Activity):
    def onCreate(self):
        s = ui.make_screen(ui.PAPER)
        p = store.profile() or {}
        jager = bool(p.get("hunter_id"))
        ui.banner(s, "HOE SPEEL JE?", ui.GREEN)

        rows = _JAGER if jager else _VERZAMELAAR
        for i, (icon, sc, kop, tekst) in enumerate(rows):
            row = ui.panel(s, 8, 32 + i * 44, 304, 40, ui.CARD)
            art.icon(row, icon, sc).align(lv.ALIGN.LEFT_MID, 6, 0)
            ui.label(row, kop, 46, 4, ui.INK, ui.font_label())
            ui.label(row, tekst, 46, 21, ui.TEXT_MUTED, ui.font_small(), w=252)

        voet = ui.panel(s, 8, 166, 304, 24, ui.CREAM)
        ui.label(
            voet,
            _JAGER_VOET if jager else _VERZAMELAAR_VOET,
            0,
            4,
            ui.INK,
            ui.font_small(),
            w=300,
            center=True,
        )

        btn = ui.box(s, 84, 202, 152, 26, ui.GOLD, radius=3)
        btn.set_style_border_width(2, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        bl = ui.label(
            btn, "AAN DE SLAG!", 0, 0, 0x3A2A0C, ui.font_title(), w=152, center=True
        )
        bl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=self._done)

        self.setContentView(s)

    def _done(self):
        sound.play("tap")
        self.finish()


# ═════════════════════════ screen_register ═════════════════════════
# screen_register.py — onboarding 1/3: who are you? Name entry.
#
# First screen of the first-run flow (design: onboarding.jsx / PxRegister).
# The OS keyboard (MposKeyboard) slides over the lower half when the field is
# tapped; the field hops up out of its way and the rest of the chrome hides,
# mirroring the design's "typing" state. VOLGENDE goes to the companion builder.

import lvgl as lv
from mpos import Activity, Intent
from mpos.ui.keyboard import MposKeyboard
import ui
import art
import sound
import store
import registrar

FIELD_BG = 0xFFF9EA
PLACEHOLDER = 0xA89A78
STRIP_BG = 0xEFE7D0
# VOLGENDE before a name exists: washed out on every channel (design 8a).
BTN_OFF_BG = 0xE6DCC2
BTN_OFF_TX = 0xA2957A
BTN_OFF_BORDER = 0xB3A68A
NAME_MAX = 12

_FIELD_Y = 58  # resting position (under the prompt)
_FIELD_Y_KB = 30  # hopped up while the keyboard is open


class RegisterActivity(Activity):
    def onCreate(self):
        # edit mode ("Naam wijzigen" from the profile page): prefill the
        # current name, save on confirm, and skip the rest of the flow.
        extras = self.getIntent().extras or {}
        self.edit = extras.get("edit", False)

        s = ui.make_screen(ui.PAPER)
        if self.edit:
            ui.banner(s, "NAAM WIJZIGEN", ui.GREEN)
        else:
            ui.banner(s, "WELKOM!", ui.GREEN, right="1/3")

        self.prompt = ui.label(
            s,
            "Hoe heet je? Zo kennen andere jagers je.",
            ui.PAD,
            36,
            ui.TEXT_MUTED,
            ui.font_small(),
        )

        # name field: a styled lv.textarea so the OS keyboard can type into it
        ta = lv.textarea(s)
        ta.set_pos(ui.PAD, _FIELD_Y)
        ta.set_size(304, 30)
        ta.set_one_line(True)
        ta.set_max_length(NAME_MAX)
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
        if self.edit:
            ta.set_text((store.profile() or {}).get("name", ""))
        self.ta = ta

        # id strip: badge id (the recovery anchor) + the role this badge can
        # actually play. During first-run there is no minted hunter_id yet, so
        # the antenna probe is what distinguishes a future jager from a
        # verzamelaar.
        strip = ui.panel(s, ui.PAD, 96, 304, 22, bg=STRIP_BG)
        ui.label(strip, "BADGE ID", 6, 3, ui.MYSTERY, ui.font_small())
        ui.label(strip, registrar.badge_id(), 64, 3, ui.INK, ui.font_small())
        ui.box(strip, 170, 2, 2, 14, 0xD8CBAA)
        hunter_id = (store.profile() or {}).get("hunter_id")
        if hunter_id or registrar.has_lora():
            ui.label(strip, "JAGER ID", 180, 3, ui.MYSTERY, ui.font_small())
            art.icon(strip, "ant", 1).set_pos(236, 5)
            hunter = registrar.hunter_label(hunter_id) or "volgt"
            ui.label(strip, hunter, 250, 3, ui.TEXT_MUTED, ui.font_small())
        else:
            ui.label(strip, "VERZAMELAAR", 180, 3, ui.INK, ui.font_small())
        self.strip = strip

        # why we ask: the badge id keeps your catches across a reset
        info = ui.panel(s, ui.PAD, 126, 304, 44, bg=ui.SURFACE_TINT, border=ui.GREEN)
        art.icon(info, "ant", 2).set_pos(8, 12)
        ui.label(
            info,
            "Je badge ID bewaart je vangsten, ook na een reset van je badge.",
            34,
            5,
            ui.INK,
            ui.font_small(),
            w=256,
        )
        self.info = info

        self.btn = ui.box(s, ui.PAD, 198, 304, 34, BTN_OFF_BG, radius=ui.RADIUS)
        self.btn.set_style_border_width(ui.BORDER, 0)
        self.btn_label = ui.label(
            self.btn,
            "OPSLAAN" if self.edit else "VOLGENDE >",
            0,
            0,
            BTN_OFF_TX,
            ui.font_title(),
            w=300,
            center=True,
        )
        self.btn_label.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(self.btn, on_click=self._next)
        self._btn_ready = False
        self._style_btn(False)

        # OS keyboard: hidden until the field is tapped (set_textarea wires
        # the tap); we piggyback our own callbacks to swap the layout state.
        self.kb = MposKeyboard(s)
        self.kb.set_textarea(ta)
        self.kb.add_flag(lv.obj.FLAG.HIDDEN)
        ta.add_event_cb(lambda e: self._kb_open(), lv.EVENT.CLICKED, None)
        self.kb.add_event_cb(self._kb_event, lv.EVENT.READY, None)
        self.kb.add_event_cb(self._kb_event, lv.EVENT.CANCEL, None)

        # textarea set_text (how the keyboard types) fires no event we can
        # trust, so a light poll keeps the VOLGENDE state honest. onResume
        # creates it -- setContentView calls that straight after onCreate.
        self._timer = None

        self.setContentView(s)

    # The poll only makes sense while this screen is the visible one. We stay on
    # the stack under the maatje and registration screens, so left running it
    # would wake every 300ms to re-read a field nobody can reach -- and it is
    # the only thing still holding widget references once those are torn down,
    # which is where the LvReferenceError on shutdown came from.
    #
    # Resume/pause, not start/stop: back_screen() calls only onResume on the
    # screen it uncovers, so pairing with onStart would leave the poll dead
    # after backing out of the maatje screen and freeze VOLGENDE's state.
    def onResume(self, screen):
        super().onResume(screen)
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

    # ---- keyboard open/close: mirror the design's typing layout ----------
    def _kb_open(self):
        for w in (self.prompt, self.strip, self.info, self.btn):
            w.add_flag(lv.obj.FLAG.HIDDEN)
        self.ta.set_y(_FIELD_Y_KB)

    def _kb_event(self, e):
        for w in (self.prompt, self.strip, self.info, self.btn):
            w.remove_flag(lv.obj.FLAG.HIDDEN)
        self.ta.set_y(_FIELD_Y)
        self._refresh_btn()

    # ---- VOLGENDE ---------------------------------------------------------
    def _name(self):
        return self.ta.get_text().strip()

    def _style_btn(self, ready):
        self._btn_ready = ready
        if ready:
            self.btn.set_style_bg_color(ui.hexc(ui.GREEN), 0)
            self.btn.set_style_border_color(ui.hexc(ui.INK), 0)
            self.btn_label.set_style_text_color(ui.hexc(ui.CREAM), 0)
        else:
            self.btn.set_style_bg_color(ui.hexc(BTN_OFF_BG), 0)
            self.btn.set_style_border_color(ui.hexc(BTN_OFF_BORDER), 0)
            self.btn_label.set_style_text_color(ui.hexc(BTN_OFF_TX), 0)

    def _refresh_btn(self):
        ready = bool(self._name())
        if ready != self._btn_ready:
            self._style_btn(ready)

    def _next(self):
        name = self._name()
        if not name:
            sound.play("error")
            return
        sound.play("tap")
        if self.edit:
            store.update_profile(name=name)
            # Same promise as the maatje edit: local first (an edit must stick
            # without WiFi), and the outbox PATCHes the server from the next
            # home resume. The name is the one profile field /scores prints in
            # public, so a rename that never leaves the badge leaves the
            # scoreboard calling the player something they dropped.
            # Enqueue last: it writes through its own preferences instance.
            store.enqueue_report("profile", {"name": name})
            self.finish()
            return
        self.startActivityForResult(
            Intent(activity_class=CompanionActivity, extras={"name": name}),
            self._child_done,
        )

    def _child_done(self, result):
        if result and result.get("result_code") == "registered":
            # Pass the verdict on up: the welcome screen (and the restore
            # screen's "registreer dan maar" route) close on it too.
            self.setResult("registered")
            self.finish()


# ═════════════════════════ screen_companion ═════════════════════════
# screen_companion.py — onboarding 2/3: build your companion ("maatje").
#
# Live preview on the left, three tabs on the right (KOP / EXTRA / KLEUR) over
# one shared tile grid (design: mascotte.jsx). Most accessories are locked
# until enough creatures are caught — at registration only bril, strik and
# hoed are available, so the avatar grows with the hunt.
# REGISTREER saves the profile locally and hands off to the send screen.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
import companion
import registrar

LOCKED_BG = 0xE0D6BD
LOCKED_TX = 0x5C4F38
_GRID_X, _GRID_Y, _GRID_W = 128, 62, 184
_TILE_W = 42
# EXTRA needs 11 tiles tall enough for a 32px sprite, which is three rows that
# only fit if they start right under the tabs — hence its own top edge.
_ACC_GRID_Y = 58


class CompanionActivity(Activity):
    def onCreate(self):
        # edit mode ("Maatje aanpassen" from the profile page): prefill from
        # the stored profile and save on confirm instead of registering.
        extras = self.getIntent().extras or {}
        self.edit = extras.get("edit", False)
        p = store.profile() if self.edit else None
        if p:
            self.name = p.get("name", "Jager")
            self.head = p.get("head", "vos")
            self.accs = list(p.get("accs", []))
            self.bg = p.get("bg", 0)
        else:
            self.name = extras.get("name", "Jager")
            self.head = "vos"
            self.accs = []
            self.bg = 0
        self.tab = 0
        self._caught_n = len(store.caught_ids())

        s = ui.make_screen(ui.PAPER)
        self.screen = s
        ui.banner(s, "MAAK JE MAATJE", ui.GREEN, right=None if self.edit else "2/3")

        # live preview: the companion on its backdrop, name plate underneath
        self.preview = ui.panel(s, ui.PAD, 32, 112, 170, bg=companion.BGS[self.bg])
        plate = ui.box(self.preview, 0, 148, 108, 18, ui.GREEN)
        ui.label(plate, self.name, 0, 2, ui.CREAM, ui.font_small(), w=108, center=True)
        self._companion = None
        self._draw_preview()

        # tabs
        self.tabs = []
        tabrow = ui.row(s, _GRID_X, 32, _GRID_W, 24, gap=5)
        for i, t in enumerate(("KOP", "EXTRA", "KLEUR")):
            b = ui.box(tabrow, 0, 0, 58, 24, ui.CARD, radius=ui.RADIUS)
            b.set_style_border_width(ui.BORDER, 0)
            lbl = ui.label(b, t, 0, 3, ui.INK, ui.font_small(), w=54, center=True)
            ui.focusable(b, on_click=lambda ii=i: self._switch_tab(ii))
            self.tabs.append((b, lbl))
        self._style_tabs()

        self._grid = None
        self._hint = None
        self._build_tab()

        btn = ui.box(s, ui.PAD, 208, 304, 26, ui.GREEN, radius=ui.RADIUS)
        btn.set_style_border_width(ui.BORDER, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        ui.label(
            btn,
            "OPSLAAN" if self.edit else "REGISTREER",
            0,
            0,
            ui.CREAM,
            ui.font_title(),
            w=300,
            center=True,
        )
        ui.focusable(btn, on_click=self._register)

        self.setContentView(s)

    # ---- preview ----------------------------------------------------------
    def _draw_preview(self):
        if self._companion is not None:
            self._companion.delete()
        self.preview.set_style_bg_color(ui.hexc(companion.BGS[self.bg]), 0)
        self._companion = companion.draw(
            self.preview, self.head, self.accs, 6, x=6, y=24
        )

    # ---- tabs -------------------------------------------------------------
    def _style_tabs(self):
        for i, (b, lbl) in enumerate(self.tabs):
            on = i == self.tab
            b.set_style_bg_color(ui.hexc(ui.GREEN if on else ui.CARD), 0)
            b.set_style_border_color(ui.hexc(ui.INK), 0)
            lbl.set_style_text_color(ui.hexc(ui.CREAM if on else ui.INK), 0)

    def _switch_tab(self, i):
        if i == self.tab:
            return
        sound.play("tap")
        self.tab = i
        self._style_tabs()
        self._build_tab()

    def _clear_grid(self):
        if self._grid is not None:
            self._grid.delete()
            self._grid = None
        if self._hint is not None:
            self._hint.delete()
            self._hint = None

    def _build_tab(self):
        self._clear_grid()
        if self.tab == 0:
            self._build_heads()
        elif self.tab == 1:
            self._build_accs()
        else:
            self._build_colors()

    # ---- KOP --------------------------------------------------------------
    def _build_heads(self):
        th = 46
        self._grid = ui.row(
            self.screen, _GRID_X, _GRID_Y, _GRID_W, 142, gap=5, wrap=True
        )
        self._grid.add_flag(lv.obj.FLAG.SCROLLABLE)
        self._grid.set_scroll_dir(lv.DIR.VER)
        for h in companion.HEADS:
            on = h["id"] == self.head
            cell = self._tile(th, on)
            # x=3: the cell's 2px border eats into its content box, so the
            # 32px sprite centres in 38, not in _TILE_W.
            art.sprite_img(cell, companion.src(h["id"]), 2, x=3)
            ui.label(
                cell,
                h["naam"],
                0,
                31,
                ui.GREEN_D if on else ui.MYSTERY,
                ui.font_small(),
                w=38,
                center=True,
            )
            ui.focusable(
                cell,
                on_click=lambda hid=h["id"]: self._pick_head(hid),
                focus_border=True,
            )

    def _pick_head(self, hid):
        sound.play("tap")
        self.head = hid
        self._draw_preview()
        self._build_tab()

    # ---- EXTRA ------------------------------------------------------------
    def _build_accs(self):
        th = 46
        self._grid = ui.row(
            self.screen, _GRID_X, _ACC_GRID_Y, _GRID_W, 3 * th + 2 * 5, gap=5, wrap=True
        )
        # "Geen" leads: tapping an accessory toggles it, but taking a whole
        # outfit off wants to be one tap, not five.
        bare = self._tile(th, not self.accs)
        dash = ui.label(bare, "-", 0, 10, ui.MYSTERY, ui.font_small(), w=38)
        dash.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        ui.label(
            bare,
            "Geen",
            0,
            31,
            ui.GREEN_D if not self.accs else ui.MYSTERY,
            ui.font_small(),
            w=38,
            center=True,
        )
        ui.focusable(bare, on_click=self._clear_accs, focus_border=True)

        for a in companion.ACCS:
            on = a["id"] in self.accs
            # Already wearing it beats the threshold: a restored profile can
            # bring back a kroon this badge hasn't re-earned, and a locked
            # tile refuses taps — you'd never get it off again.
            locked = not on and not companion.is_unlocked(a, self._caught_n)
            cell = self._tile(th, on, bg=LOCKED_BG if locked else None)
            spr = art.sprite_img(cell, companion.src(a["id"]), 2, x=3)
            if locked:
                spr.set_style_opa(97, 0)  # ~38%: visible, clearly not yours yet
                self._price(cell, a["unlock"])
            ui.label(
                cell,
                a["naam"],
                0,
                31,
                LOCKED_TX if locked else (ui.GREEN_D if on else ui.MYSTERY),
                ui.font_small(),
                w=38,
                center=True,
            )
            ui.focusable(
                cell,
                on_click=lambda aa=a["id"], ll=locked: self._pick_acc(aa, ll),
                focus_border=True,
            )

    def _price(self, cell, unlock):
        """The padlock and the number of beasts that opens it, as one badge in
        the tile's top-right. It replaces the old blanket "keep playing" hint
        under the grid: with the unlocks spread over the whole hunt, what a
        player wants to know is how far off *this* one is."""
        badge = ui.box(cell, 12, 0, 26, 12, LOCKED_BG, radius=ui.RADIUS)
        art.icon(badge, "lock", 1).set_pos(2, 2)
        ui.label(badge, str(unlock), 11, -1, LOCKED_TX, ui.font_small(), w=14)
        return badge

    def _clear_accs(self):
        sound.play("tap")
        self.accs = []
        self._draw_preview()
        self._build_tab()

    def _pick_acc(self, aid, locked):
        if locked:
            sound.play("error")
            return
        sound.play("tap")
        if aid in self.accs:
            self.accs.remove(aid)
        else:
            self.accs.append(aid)
        self._draw_preview()
        self._build_tab()

    # ---- KLEUR ------------------------------------------------------------
    def _build_colors(self):
        th = 41
        self._grid = ui.row(
            self.screen, _GRID_X, _GRID_Y, _GRID_W, 2 * th + 5, gap=5, wrap=True
        )
        for i, c in enumerate(companion.BGS):
            on = i == self.bg
            cell = self._tile(th, on, bg=c)
            if on:
                dark_swatch = i == len(companion.BGS) - 1
                ic = art.icon(cell, "check_light" if dark_swatch else "check", 2)
                ic.align(lv.ALIGN.CENTER, 0, 0)
            ui.focusable(
                cell, on_click=lambda ii=i: self._pick_bg(ii), focus_border=True
            )
        self._hint = ui.label(
            self.screen,
            "tik of kies met de pijltjes",
            _GRID_X,
            _GRID_Y + 2 * th + 5 + 4,
            ui.TEXT_MUTED,
            ui.font_small(),
        )

    def _pick_bg(self, i):
        sound.play("tap")
        self.bg = i
        self._draw_preview()
        self._build_tab()

    # ---- shared tile ------------------------------------------------------
    def _tile(self, h, selected, bg=None):
        """A grid cell in the quiet-frame-at-rest style of the home grid;
        selection shows as a green frame on a pale green fill."""
        if bg is None:
            bg = ui.SURFACE_SOFT if selected else ui.CARD
        cell = ui.box(self._grid, 0, 0, _TILE_W, h, bg, radius=ui.RADIUS)
        cell.set_style_border_width(ui.BORDER, 0)
        cell.set_style_border_color(
            ui.hexc(ui.GREEN if selected else ui.BORDER_REST), 0
        )
        return cell

    # ---- REGISTREER -------------------------------------------------------
    def _register(self):
        sound.play("tap")
        if self.edit:
            code = companion.encode(self.head, self.accs, self.bg)
            store.update_profile(head=self.head, accs=self.accs, bg=self.bg)
            # Local first: the edit should stick even when the woods have no
            # WiFi. Queue before starting the fire-and-forget drain: failure
            # leaves the report for Home's ordinary resume/retry path.
            store.enqueue_report("profile", {"profile_pic": code})
            registrar.flush()
            self.finish()
            return
        # Save first: whatever the network does, the profile is on the badge.
        store.save_profile(
            {
                "name": self.name,
                "head": self.head,
                "accs": self.accs,
                "bg": self.bg,
                "badge_id": registrar.badge_id(),
                "hunter_id": None,
                "synced": False,
            }
        )
        self.startActivityForResult(
            Intent(activity_class=RegSendActivity), self._child_done
        )

    def _child_done(self, result):
        if result and result.get("result_code") == "registered":
            self.setResult("registered")
            self.finish()


# ═════════════════════════ screen_reg_send ═════════════════════════
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
        self._settled = False  # ...and whether the player answered the fork
        # Opened from instellingen to finish a registration the cloud server
        # never confirmed, instead of from the maatje builder. Same three
        # states and the same fork — the only difference is that the profile
        # here is the player's real one, already lived in, so backing out of
        # the fork must leave it alone.
        self._resync = bool(self.getIntent().extras.get("resync"))
        self.setContentView(self.screen)
        self._start_sending()

    def onDestroy(self, screen):
        super().onDestroy(screen)
        self._stop_bar()
        # The profile was written before the send (screen_companion._register),
        # which is right for a server that is merely down — the player keeps
        # their maatje and retries. It is wrong once the server has said the
        # badge already has an account: that is a question, and leaving without
        # answering it registers nobody. Only adopt/overwrite settle it, so
        # anything else that gets us here takes the half-built profile with it.
        if self._exists is not None and not self._settled and not self._resync:
            store.clear_profile()

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
                note = registrar.hunter_label(st.get("hunter_id")) or ""
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
            registrar.hunter_label(st.get("hunter_id")) or "volgt",
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
        ui.label(
            acct,
            registrar.hunter_label(st.get("hunter_id")) or "volgt",
            140,
            32,
            ui.INK,
            ui.font_small(),
        )
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
        self._settled = True
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
            # NOT the shared register-error screen. That one's LATER button
            # reports "registered" and its text promises the profile is kept —
            # both lies here: the fork is still unsettled, and walking out of
            # an unsettled fork clears the half-built profile (onDestroy). And
            # its checklist would say "Cloud-server: geen antwoord" when the
            # cloud answered fine — the 409 that raised this fork proves it;
            # only the PATCH was refused.
            sound.play("error")
            self._build_overwrite_error(st.get("error") or "E-01")
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
        self._settled = True
        self.p = store.profile() or self.p
        sound.play("caught")
        self._build_done({"hunter_id": self._exists.get("hunter_id"), "bridge": "skip"})

    # ---- state: the overwrite was refused ---------------------------------
    # A dead end inside the fork, so both ways out stay inside it: retry the
    # overwrite, or step back to the question. Deliberately NO "later" — the
    # fork is unsettled, and the only honest way to leave it is the system
    # back gesture, which walks back into onboarding without claiming anyone
    # got registered.
    def _build_overwrite_error(self, code):
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(ERR_BG), 0)
        ui.banner(s, "OVERSCHRIJVEN MISLUKT", ui.TERRA, right=code)

        panel = ui.panel(s, ui.PAD, 48, 304, 68, bg=ERR_PANEL, border=ui.TERRA)
        art.icon(panel, "st_bad", 2).set_pos(8, 24)
        ui.label(
            panel,
            "De server nam de nieuwe naam niet aan. Er is niets veranderd - "
            "het account staat er nog precies zo.",
            34,
            8,
            ui.INK,
            ui.font_small(),
            w=258,
        )

        retry = ui.box(s, ui.PAD, 140, 148, 32, ui.GREEN, radius=ui.RADIUS)
        retry.set_style_border_width(ui.BORDER, 0)
        retry.set_style_border_color(ui.hexc(ui.INK), 0)
        rl = ui.label(
            retry, "OPNIEUW", 0, 0, ui.CREAM, ui.font_title(), w=144, center=True
        )
        rl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(retry, on_click=self._overwrite)

        back = ui.box(s, 164, 140, 148, 32, ui.CARD, radius=ui.RADIUS)
        back.set_style_border_width(ui.BORDER, 0)
        back.set_style_border_color(ui.hexc(ui.INK), 0)
        bl = ui.label(back, "TERUG", 0, 0, ui.INK, ui.font_title(), w=144, center=True)
        bl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(back, on_click=lambda: self._build_exists(self._exists))

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
            # it, VERDER there closes the whole onboarding chain. Clear the
            # id at launch: a player who back-swipes out of the reveal lands
            # here again, and START must then finish the chain instead of
            # replaying a reveal for a beest that is already banked.
            starter = self._starter
            self._starter = None
            self.startActivityForResult(
                Intent(
                    activity_class=StarterActivity,
                    extras={"fox_id": starter},
                ),
                self._starter_done,
            )
            return
        self.setResult("registered")
        self.finish()

    def _starter_done(self, _result):
        self.setResult("registered")
        self.finish()


# ═════════════════════════ screen_restore ═════════════════════════
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
import companion
import registrar
from registrar import REGISTRAR

ASK_BG = 0xDFEEBF  # same green wash as the send screen: same moment in the flow
RESTORE_STRIP_BG = 0xEFE7D0
RESTORE_ERR_BG = 0xF2E3CD
RESTORE_ERR_PANEL = 0xFBE4D6
RESTORE_ERR_FOOT_BG = 0xF9F1E2
RESTORE_ERR_FOOT_TX = 0x8A6A4E

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

        strip = ui.panel(s, ui.PAD, 96, 304, 22, bg=RESTORE_STRIP_BG)
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
        registrar.adopt does the writing; the registration flow's "badge al
        bekend" fork calls the same function, so both routes into an existing
        account recover exactly the same things."""
        self.recovered = registrar.adopt(self.badge, st)

    # ---- state: found -----------------------------------------------------
    def _build_found(self, st):
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(ui.PAPER), 0)
        ui.banner(s, "WELKOM TERUG!", ui.GREEN)

        p = store.profile() or {}
        card = ui.panel(s, 122, 38, 76, 76, bg=companion.BGS[p.get("bg", 0)])
        companion.draw(card, p.get("head", "vos"), p.get("accs", []), 4, x=4, y=4)
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

        strip = ui.panel(s, 80, 148, 160, 22, bg=RESTORE_STRIP_BG)
        art.icon(strip, "ant", 1).set_pos(6, 6)
        ui.label(strip, "JAGER ID", 20, 3, ui.MYSTERY, ui.font_small())
        ui.label(
            strip,
            registrar.hunter_label(st.get("hunter_id")) or "volgt",
            82,
            3,
            ui.INK,
            ui.font_small(),
        )

        ui.label(
            s,
            self._recovered_line(st.get("companion")),
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

    def _recovered_line(self, code):
        """What came back, in one line. The catch count is worth saying out
        loud: it is the number the player's unlocks are counted off, and a
        restore that quietly returned zero would look identical to one that
        worked until they opened the maatje builder."""
        beesten = "1 beest" if self.recovered == 1 else "%d beesten" % self.recovered
        if code and self.recovered:
            return "Je maatje en %s zijn mee hersteld." % beesten
        if code:
            return "Je maatje is mee hersteld."
        if self.recovered:
            return "%s hersteld - je maatje kies je opnieuw." % beesten
        return "Je maatje kies je opnieuw in je profiel."

    # ---- state: no luck ---------------------------------------------------
    def _build_no_luck(self, code):
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(RESTORE_ERR_BG), 0)
        text, detail = _NO_LUCK[code]
        unknown = code == "unknown"
        if unknown:
            ui.banner(s, "NIEUWE BADGE", ui.GREEN)
        else:
            ui.banner(s, "HERSTEL MISLUKT", ui.TERRA, right=code)

        panel = ui.panel(s, ui.PAD, 44, 304, 60, bg=RESTORE_ERR_PANEL, border=ui.TERRA)
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

        foot = ui.panel(s, ui.PAD, 216, 304, 20, bg=RESTORE_ERR_FOOT_BG)
        ui.label(
            foot,
            "%s - badge %s" % (detail, self.badge[-5:]),
            0,
            2,
            RESTORE_ERR_FOOT_TX,
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


# ═════════════════════════ screen_starter ═════════════════════════
# screen_starter.py — the startbeest reveal, onboarding's payoff moment.
#
# Registration minted one base-tier creature server-side (deterministic per
# badge — GAME_DESIGN.md, "The startbeest"); reg_send has already stored it
# locally before opening this. States rebuilt in place (the reg_send
# pattern): a veiled silhouette first — "er wacht iemand op je" — then the
# reveal, framed the way the design asks: the creature chose YOU. The calm
# card copies the win screen's geometry, so the two payoffs rhyme.
#
# The reveal flows into a GUIDED FIRST FEEDING — the whole tutorial is this
# one taught tap (GAME_DESIGN.md, "The first gatherer experience"): the
# pantry was pre-seeded, the player picks a hapje, the beest eats. Real
# mechanics, not a mock — store.do_feed spends the pantry and pays energie.

import lvgl as lv
from mpos import Activity
import ui
import art
import sound
import store
from creatures import by_id

BG = 0x20301C
TEXT_SOFT = 0xBCD0A4
STARTER_GOLD_INK = 0x3A2A0C


class StarterActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id) or by_id(0)
        self.screen = ui.make_screen(BG)
        self.setContentView(self.screen)
        self._build_mystery()

    # ---- shared chrome ----------------------------------------------------
    def _card(self, s, silhouette):
        panel = ui.box(s, 114, 36, 92, 92, ui.SURFACE_SOFT, radius=2)
        panel.set_style_border_width(3, 0)
        border = ui.GREEN_D if silhouette else ui.GOLD
        panel.set_style_border_color(ui.hexc(border), 0)
        sp = art.creature_panel(
            panel, self.c, 5, silhouette=silhouette, animate=not silhouette
        )
        sp.align(lv.ALIGN.CENTER, 0, 0)
        return panel

    def _button(self, s, text, cb):
        # same margins as the win screen: room under it for the focus halo
        btn = ui.box(s, 84, 202, 152, 26, ui.GOLD, radius=3)
        btn.set_style_border_width(2, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        bl = ui.label(
            btn, text, 0, 0, STARTER_GOLD_INK, ui.font_title(), w=152, center=True
        )
        bl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=cb)

    # ---- state: mystery ---------------------------------------------------
    def _build_mystery(self):
        s = self.screen
        s.clean()
        ui.label(s, "SSST...", 0, 10, ui.GOLD, ui.font_title(), w=320, center=True)
        self._card(s, silhouette=True)
        ui.label(
            s,
            "Er wacht iemand op je!",
            0,
            140,
            ui.CREAM,
            ui.font_title(),
            w=320,
            center=True,
        )
        ui.label(
            s,
            "Een beest uit het bos is je gevolgd...",
            0,
            166,
            TEXT_SOFT,
            ui.font_small(),
            w=320,
            center=True,
        )
        self._button(s, "WIE IS DAT?", self._reveal)

    # ---- state: reveal ----------------------------------------------------
    def _reveal(self):
        s = self.screen
        s.clean()
        sound.play("caught")
        # sparks flank the card, clear of the 136-180 text band
        for x, y, sc in (
            (20, 44, 2),
            (286, 38, 3),
            (40, 90, 3),
            (270, 96, 2),
        ):
            art.icon(s, "spark", sc).set_pos(x, y)
        ui.label(
            s,
            "+ JOUW STARTBEEST +",
            0,
            10,
            ui.GOLD,
            ui.font_small(),
            w=320,
            center=True,
        )
        self._card(s, silhouette=False)
        ui.label(
            s,
            "%s heeft jou gekozen!" % self.c["naam"],
            0,
            140,
            ui.CREAM,
            ui.font_title(),
            w=320,
            center=True,
        )
        ui.label(
            s,
            "Zorg er goed voor - geef het hapjes en speel!",
            0,
            166,
            TEXT_SOFT,
            ui.font_small(),
            w=320,
            center=True,
        )
        # "GEEF EEN HAPJE" is 166px in font_title() and wraps to two clipped
        # lines in the 152px button; the short form fits like every other one.
        self._button(s, "GEEF HAPJE", self._build_feed)

    # ---- state: the guided first feeding ----------------------------------
    def _build_feed(self):
        s = self.screen
        s.clean()
        sound.play("tap")
        ui.label(
            s, "+ EERSTE HAPJE +", 0, 10, ui.GOLD, ui.font_small(), w=320, center=True
        )
        self._card(s, silhouette=False)
        ui.label(
            s,
            "Waar heeft %s zin in?" % self.c["naam"],
            0,
            136,
            ui.CREAM,
            ui.font_label(),
            w=320,
            center=True,
        )
        v = store.voorraad()
        fw = 92
        row = ui.row(s, 14, 158, 3 * fw + 2 * 8, 38, gap=8)
        for food, lab in (("bes", "Bes"), ("noot", "Noot"), ("eikel", "Eikel")):
            fav = food == self.c.get("favoriet")
            p = ui.panel(
                row, 0, 0, fw, 38, ui.CARD, border=(ui.GOLD if fav else ui.BORDER_REST)
            )
            art.icon(p, food, 2).set_pos(8, 10)
            ui.label(
                p, "%s x%d" % (lab, v.get(food, 0)), 32, 12, ui.INK, ui.font_small()
            )
            ui.focusable(
                p, on_click=lambda f=food: self._first_feed(f), focus_border=True
            )

    def _first_feed(self, food):
        st, ok, msg, is_fav = store.do_feed(self.fox_id, food)
        sound.play("caught" if is_fav else "tap" if ok else "error")
        self._build_fed(ok, msg, is_fav)

    def _build_fed(self, ok, msg, is_fav):
        s = self.screen
        s.clean()
        for x, y, sc in ((24, 46, 2), (282, 44, 2)):
            art.icon(s, "spark", sc).set_pos(x, y)
        ui.label(
            s, "+ SMAKELIJK +", 0, 10, ui.GOLD, ui.font_small(), w=320, center=True
        )
        self._card(s, silhouette=False)
        kop = "%s %s" % (self.c["naam"], "smikkelt!" if ok else "zit al vol!")
        ui.label(s, kop, 0, 138, ui.CREAM, ui.font_title(), w=320, center=True)
        if ok:
            ui.label(
                s,
                msg,
                0,
                162,
                ui.GOLD if is_fav else TEXT_SOFT,
                ui.font_small(),
                w=320,
                center=True,
            )
        ui.label(
            s,
            "hapjes vind je met plukken - band groeit door spelen",
            0,
            180,
            TEXT_SOFT,
            ui.font_small(),
            w=320,
            center=True,
        )
        self._button(s, "VERDER", self._done)

    def _done(self):
        sound.play("tap")
        self.setResult("done")
        self.finish()
