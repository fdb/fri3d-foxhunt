# screen_settings.py — instellingen: geluid, trillen + LED sterkte, and the
# badge/jager ids as plain labels at the bottom.
#
# Geluid mutes the app's buzzer sounds; Trillen is a stored switch waiting
# for a vibration API. Maatje/naam editing lives on the profile screen, and
# LoRa is not optional, so neither appears here.

from mpos import Activity
import ui
import store
import sound
import leds
import registrar

STRIP_BG = 0xEFE7D0
TRACK_OFF = 0xE0D4B4  # switch track when off
ROW_H, ROW_GAP = 26, 4
_ROW_W = 308
# Tap cycles this ladder; the bar's 5 cells (one per LED) show the rung.
# Not linear: perceived brightness is roughly a power law, so each rung about
# doubles the duty — that puts the resolution at the dim end, where it shows.
_LED_STEPS = (0, 5, 15, 30, 60, 100)


def _led_step(pct):
    """Nearest rung — a value stored under an older ladder still lands well."""
    best = 0
    for i, s in enumerate(_LED_STEPS):
        if abs(s - pct) < abs(_LED_STEPS[best] - pct):
            best = i
    return best


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
        s = ui.make_screen(ui.PAPER)
        cfg = store.settings()
        ui.banner(s, "INSTELLINGEN", ui.GREEN)

        self._toggles = {}
        for i, (key, title) in enumerate(
            (("geluid", "Geluid"), ("trillen", "Trillen"))
        ):
            row = ui.panel(s, 6, 32 + i * (ROW_H + ROW_GAP), _ROW_W, ROW_H, bg=ui.CARD)
            ui.label(row, title, 8, 5, ui.INK, ui.font_small())
            self._toggles[key] = _Toggle(row, 262, 3, cfg[key])
            ui.focusable(row, on_click=lambda k=key: self._flip(k))

        # LED sterkte: full power is blinding on the badge, so it's adjustable.
        # A 5-cell bar (the hunt's 5-LED look) beats a slider on a touch screen
        # this small; tapping the row steps through _LED_STEPS and lights the
        # strip at the new level so you can actually judge it.
        self._led = cfg["led"]
        row = ui.panel(s, 6, 32 + 2 * (ROW_H + ROW_GAP), _ROW_W, ROW_H, bg=ui.CARD)
        self._led_cells = ui.seg_bar(
            row, 8, 5, "LED sterkte", _led_step(self._led), ui.TERRA, label_w=196
        )
        ui.focusable(row, on_click=self._cycle_led)

        # ids, labels only: the badge id anchors recovery, the jager id is
        # minted over LoRa during registration ("-" until that happened)
        p = store.profile() or {}
        strip = ui.panel(s, 6, 188, _ROW_W, 22, bg=STRIP_BG)
        ui.label(strip, "BADGE ID", 6, 3, ui.MYSTERY, ui.font_small())
        ui.label(strip, registrar.badge_id(), 72, 3, ui.INK, ui.font_small())
        strip = ui.panel(s, 6, 212, _ROW_W, 22, bg=STRIP_BG)
        ui.label(strip, "JAGER ID", 6, 3, ui.MYSTERY, ui.font_small())
        ui.label(strip, p.get("hunter_id") or "-", 72, 3, ui.INK, ui.font_small())

        self.setContentView(s)

    def onPause(self, screen):
        super().onPause(screen)
        leds.off()  # don't leave the preview burning after leaving the screen

    def _flip(self, key):
        value = not store.settings()[key]
        store.set_setting(key, value)
        # play after the write, so flipping geluid ON is audible immediately
        sound.play("tap")
        self._toggles[key].set(value)

    def _cycle_led(self):
        i = (_led_step(self._led) + 1) % len(_LED_STEPS)
        self._led = _LED_STEPS[i]
        store.set_setting("led", self._led)
        leds.set_brightness(self._led)  # live: no restart to take effect
        sound.play("tap")
        ui.set_segments(self._led_cells, i, ui.TERRA)
        leds.show_level(5)  # preview at the new strength
