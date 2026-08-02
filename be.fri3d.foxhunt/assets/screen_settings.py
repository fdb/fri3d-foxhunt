# screen_settings.py — instellingen (design: home.jsx PxSettings).
#
# Geluid mutes the app's buzzer sounds; Helderheid drives the backlight live
# (no-op where there is none); Trillen and LoRa are stored switches waiting
# for their hardware (no vibration API yet, radio is still the stub). Maatje
# and naam re-enter the onboarding screens in edit mode, and HERSTEL asks the
# cloud for a backup through the registrar seam.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
import mascot
import registrar
from registrar import REGISTRAR
from screen_mascot import MascotActivity
from screen_register import RegisterActivity

STRIP_BG = 0xEFE7D0
TRACK_OFF = 0xE0D4B4  # switch track / brightness cell when off
VALUE_TX = 0x8A7D5E  # current value shown next to a chevron row
ROW_H, ROW_GAP = 26, 4
_ROW_W = 308


def apply_brightness(level=None):
    """Push the saved (or given) 1..5 level to the backlight, 20%..100%.
    Desktop and boards without a backlight silently skip it."""
    if level is None:
        level = store.settings()["helderheid"]
    try:
        import mpos.ui

        if mpos.ui.main_display:
            mpos.ui.main_display.set_backlight(level * 20)
    except Exception:
        pass


class _Toggle:
    """The design's 34x16 switch: green track when on, knob slides right."""

    def __init__(self, parent, x, y, on):
        self.track = ui.box(parent, x, y, 34, 16, TRACK_OFF)
        self.track.set_style_border_width(ui.BORDER, 0)
        self.track.set_style_border_color(ui.hexc(ui.INK), 0)
        self.knob = ui.box(self.track, 0, 0, 14, 12, ui.CARD)
        self.knob.set_style_border_width(ui.BORDER_THIN, 0)
        self.knob.set_style_border_color(ui.hexc(ui.INK), 0)
        self.set(on)

    def set(self, on):
        self.track.set_style_bg_color(ui.hexc(ui.GREEN if on else TRACK_OFF), 0)
        self.knob.set_x(16 if on else 0)


class SettingsActivity(Activity):
    def onCreate(self):
        self._fresh = True
        self.screen = ui.make_screen(ui.PAPER)
        self._populate()
        self.setContentView(self.screen)

    def onResume(self, screen):
        super().onResume(screen)
        # Back from a maatje/naam edit: rebuild so the rows show the change.
        if self._fresh:
            self._fresh = False
            return
        self.screen.clean()
        self._populate()

    def _row(self, i, label, on_click=None):
        y = 32 + i * (ROW_H + ROW_GAP)
        row = ui.panel(self.screen, 6, y, _ROW_W, ROW_H, bg=ui.CARD)
        ui.label(row, label, 8, 5, ui.INK, ui.font_small())
        if on_click is not None:
            ui.focusable(row, on_click=on_click)
        return row

    def _populate(self):
        s = self.screen
        cfg = store.settings()
        p = store.profile() or {}
        ui.banner(s, "INSTELLINGEN", ui.GREEN)

        # Geluid / Trillen: plain switches
        row = self._row(0, "Geluid", on_click=lambda: self._flip("geluid"))
        self._t_geluid = _Toggle(row, 262, 3, cfg["geluid"])
        row = self._row(1, "Trillen", on_click=lambda: self._flip("trillen"))
        self._t_trillen = _Toggle(row, 262, 3, cfg["trillen"])

        # Helderheid: 5 cells, tap cycles 1..5 and dims/brightens live
        row = self._row(2, "Helderheid", on_click=self._cycle_brightness)
        self._bri_cells = []
        for i in range(5):
            c = ui.box(row, 224 + i * 15, 5, 12, 12, TRACK_OFF)
            c.set_style_border_width(ui.BORDER, 0)
            c.set_style_border_color(ui.hexc(ui.INK), 0)
            self._bri_cells.append(c)
        self._paint_brightness(cfg["helderheid"])

        # Maatje / Naam: re-enter the onboarding screens in edit mode
        row = self._row(3, "Maatje bewerken", on_click=self._edit_mascot)
        if p:
            mascot.draw(row, p.get("head", "vos"), p.get("accs", []), 1, x=270, y=3)
        art.icon(row, "chev", 2).set_pos(292, 3)

        row = self._row(4, "Naam wijzigen", on_click=self._edit_name)
        nl = ui.label(row, p.get("name", "-"), 180, 5, VALUE_TX, ui.font_small(), w=106)
        nl.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)
        art.icon(row, "chev", 2).set_pos(292, 3)

        # LoRa: hunter id + switch (gates nothing until the radio lands)
        row = self._row(5, "LoRa", on_click=lambda: self._flip("lora"))
        il = ui.label(
            row,
            p.get("hunter_id") or "volgt",
            160,
            5,
            ui.GREEN_D,
            ui.font_small(),
            w=96,
        )
        il.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)
        self._t_lora = _Toggle(row, 262, 3, cfg["lora"])

        # badge strip + HERSTEL (recover this badge's data from the cloud)
        strip = ui.panel(s, 6, 212, _ROW_W, 22, bg=STRIP_BG)
        ui.label(strip, "BADGE", 6, 3, ui.MYSTERY, ui.font_small())
        ui.label(strip, registrar.badge_id(), 52, 3, ui.INK, ui.font_small())
        self._herstel = ui.label(strip, "HERSTEL >", 216, 3, ui.TERRA, ui.font_small())
        ui.focusable(self._herstel, on_click=self._recover)

    # ---- switches ---------------------------------------------------------
    def _flip(self, key):
        value = not store.settings()[key]
        store.set_setting(key, value)
        # play after the write, so flipping geluid ON is audible immediately
        sound.play("tap")
        toggle = {
            "geluid": self._t_geluid,
            "trillen": self._t_trillen,
            "lora": self._t_lora,
        }[key]
        toggle.set(value)

    # ---- brightness -------------------------------------------------------
    def _paint_brightness(self, level):
        for i, c in enumerate(self._bri_cells):
            c.set_style_bg_color(ui.hexc(ui.GOLD if i < level else TRACK_OFF), 0)

    def _cycle_brightness(self):
        sound.play("tap")
        level = store.settings()["helderheid"] % 5 + 1
        store.set_setting("helderheid", level)
        self._paint_brightness(level)
        apply_brightness(level)

    # ---- edit flows -------------------------------------------------------
    def _edit_mascot(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=MascotActivity, extras={"edit": True}))

    def _edit_name(self):
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=RegisterActivity, extras={"edit": True})
        )

    # ---- herstel ----------------------------------------------------------
    def _recover(self):
        sound.play("tap")
        self._herstel.set_text("herstellen...")
        self._herstel.set_style_text_color(ui.hexc(ui.TEXT_MUTED), 0)
        REGISTRAR.recover(registrar.badge_id(), self._on_recover)

    def _on_recover(self, profile):
        if not self.has_foreground():
            return
        if profile:
            store.save_profile(profile)
            sound.play("caught")
            self.screen.clean()
            self._populate()
            self._herstel.set_text("hersteld!")
            self._herstel.set_style_text_color(ui.hexc(ui.GREEN_D), 0)
        else:
            sound.play("error")
            self._herstel.set_text("geen backup")
            self._herstel.set_style_text_color(ui.hexc(ui.TERRA), 0)
