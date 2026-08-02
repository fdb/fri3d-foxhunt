# screen_register.py — onboarding 1/3: who are you? Name entry.
#
# First screen of the first-run flow (design: onboarding.jsx / PxRegister).
# The OS keyboard (MposKeyboard) slides over the lower half when the field is
# tapped; the field hops up out of its way and the rest of the chrome hides,
# mirroring the design's "typing" state. VOLGENDE goes to the mascot builder.

import lvgl as lv
from mpos import Activity, Intent
from mpos.ui.keyboard import MposKeyboard
import ui
import art
import sound
import store
import registrar
from screen_mascot import MascotActivity

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
            ui.banner(s, "WELKOM, JAGER!", ui.GREEN, right="1/3")

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

        # id strip: badge id (the recovery anchor) + hunter id (still to come)
        strip = ui.panel(s, ui.PAD, 96, 304, 22, bg=STRIP_BG)
        ui.label(strip, "BADGE ID", 6, 3, ui.MYSTERY, ui.font_small())
        ui.label(strip, registrar.badge_id(), 64, 3, ui.INK, ui.font_small())
        ui.box(strip, 170, 2, 2, 14, 0xD8CBAA)
        ui.label(strip, "JAGER ID", 180, 3, ui.MYSTERY, ui.font_small())
        art.icon(strip, "ant", 1).set_pos(236, 5)
        hunter = (store.profile() or {}).get("hunter_id") or "volgt"
        ui.label(strip, hunter, 250, 3, ui.TEXT_MUTED, ui.font_small())
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
        # trust, so a light poll keeps the VOLGENDE state honest.
        self._timer = lv.timer_create(lambda t: self._refresh_btn(), 300, None)

        self.setContentView(s)

    def onDestroy(self, screen):
        super().onDestroy(screen)
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
            self.finish()
            return
        self.startActivityForResult(
            Intent(activity_class=MascotActivity, extras={"name": name}),
            self._child_done,
        )

    def _child_done(self, result):
        if result and result.get("result_code") == "registered":
            self.finish()
