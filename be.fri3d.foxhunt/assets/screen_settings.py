# screen_settings.py — instellingen: geluid + LED sterkte, and the
# badge/jager ids as plain labels at the bottom.
#
# Geluid mutes the app's buzzer sounds. Companion/name editing lives on the
# profile screen, and LoRa is not optional, so neither appears here.

import json

import lvgl as lv
from mpos import Activity, Intent
import ui
import store
import sound
import leds
import registrar
from screen_debug import DebugActivity
from screen_wipe import WipeActivity
from screen_uitleg import UitlegActivity
from screen_reg_send import RegSendActivity

TRACK_OFF = 0xE0D4B4  # switch track when off
ROW_H, ROW_GAP = 26, 4
_ROW_W = 308
# Tap cycles this ladder; the bar's 5 cells (one per LED) show the rung.
# Not linear: perceived brightness is roughly a power law, so each rung about
# doubles the duty — that puts the resolution at the dim end, where it shows.
_LED_STEPS = (0, 5, 15, 30, 60, 100)


def _build_info():
    """'0.1.0 @ 66326d8' — version from META-INF, commit from the #src line
    of the deploy stamp. Running from source (the emulator's symlink has no
    .deploy.sha) shows 'dev'; a --force'd dirty deploy carries a '*'."""
    base = __file__.rsplit("/", 2)[0]
    try:
        with open(base + "/META-INF/MANIFEST.JSON") as fh:
            version = json.load(fh).get("version", "?")
    except (OSError, ValueError):
        version = "?"
    commit = "dev"
    try:
        with open(base + "/.deploy.sha") as fh:
            parts = fh.readline().split()
        if parts[:1] == ["#src"] and len(parts) >= 4:
            commit = parts[2] + ("*" if parts[3] == "dirty" else "")
    except OSError:
        pass
    return version + " @ " + commit


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

        row = ui.panel(s, 6, 32, _ROW_W, ROW_H, bg=ui.CARD)
        ui.label(row, "Geluid", 8, 5, ui.INK, ui.font_small())
        self._geluid = _Toggle(row, 262, 3, cfg["geluid"])
        ui.focusable(row, on_click=self._flip_geluid)

        # LED sterkte: full power is blinding on the badge, so it's adjustable.
        # A 5-cell bar (the hunt's 5-LED look) beats a slider on a touch screen
        # this small; tapping the row steps through _LED_STEPS and lights the
        # strip at the new level so you can actually judge it.
        self._led = cfg["led"]
        row = ui.panel(s, 6, 32 + ROW_H + ROW_GAP, _ROW_W, ROW_H, bg=ui.CARD)
        self._led_cells = ui.seg_bar(
            row, 8, 5, "LED sterkte", _led_step(self._led), ui.TERRA, label_w=196
        )
        ui.focusable(row, on_click=self._cycle_led)

        # The way out of the game: hand the badge on, or take your name off the
        # scoreboard. Terra, not green — it is the only row here that destroys
        # anything — and it opens a screen that makes you type the word, so this
        # row itself is safe to sit among the toggles.
        row = ui.panel(s, 6, 32 + 2 * (ROW_H + ROW_GAP), _ROW_W, ROW_H, bg=ui.CARD)
        ui.label(row, "Hoe speel je?", 8, 5, ui.INK, ui.font_small())
        ui.label(
            row, "uitleg", 160, 5, ui.TEXT_MUTED, ui.font_small(), w=140, center=True
        )
        ui.focusable(row, on_click=self._uitleg)

        row = ui.panel(s, 6, 32 + 3 * (ROW_H + ROW_GAP), _ROW_W, ROW_H, bg=ui.CARD)
        ui.label(row, "Alles wissen", 8, 5, ui.TERRA_D, ui.font_small())
        ui.label(
            row,
            "badge + server",
            160,
            5,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=140,
            center=True,
        )
        ui.focusable(row, on_click=self._wipe)

        # ids, labels only: the badge id anchors recovery.
        # No card behind these: subtle text straight on the paper. The boxes
        # stay (transparent) because the badge-id one is also the tap target.
        strip = ui.box(s, 6, 164, _ROW_W, 22, None)
        ui.label(strip, "VERSIE", 6, 3, ui.MYSTERY, ui.font_small())
        ui.label(strip, _build_info(), 72, 3, ui.INK, ui.font_small())
        strip = ui.box(s, 6, 188, _ROW_W, 22, None)
        ui.label(strip, "BADGE ID", 6, 3, ui.MYSTERY, ui.font_small())
        ui.label(strip, registrar.badge_id(), 72, 3, ui.INK, ui.font_small())
        # The badge-id strip doubles as the hidden door: five taps opens the
        # debug tools. Silent on purpose — no tap sound, no focus ring that
        # would advertise the strip as interactive.
        self._id_taps = 0
        strip.add_flag(lv.obj.FLAG.CLICKABLE)
        strip.add_event_cb(lambda e: self._id_tap(), lv.EVENT.CLICKED, None)
        self._s = s
        self._slot = None
        self._slot_kind = None
        self._build_slot()

        self.setContentView(s)

    # The bottom slot: one place, three states that cannot coexist. Order
    # matters. An unconfirmed account outranks WORD JAGER because that button
    # cannot work — /auth/hunter looks the badge up and 404s on an account the
    # server never received — so offering it first would fail for a reason it
    # could not explain. A minted jager id implies both of the others are done.
    def _build_slot(self):
        p = store.profile() or {}
        if p.get("hunter_id"):
            kind = "jager"
        elif not p.get("synced"):
            kind = "cloud"
        else:
            kind = "word"
        self._slot_kind = kind

        if kind == "jager":
            strip = ui.box(self._s, 6, 212, _ROW_W, 22, None)
            ui.label(strip, "JAGER ID", 6, 3, ui.MYSTERY, ui.font_small())
            ui.label(strip, p.get("hunter_id"), 72, 3, ui.INK, ui.font_small())
            self._slot = strip
        elif kind == "cloud":
            # The profile lives on the badge and nowhere else: registration
            # saved it locally, then the server never confirmed. Say so, and
            # make it fixable — the badge retries once per launch on its own
            # (registrar.resync), but a player staring at an empty scoreboard
            # needs to see why, and to be able to ask again on the spot.
            row = ui.panel(self._s, 6, 210, _ROW_W, ROW_H, bg=ui.CARD)
            ui.label(row, "Cloud", 8, 5, ui.TERRA_D, ui.font_small())
            ui.label(
                row,
                "niet bewaard - opnieuw",
                104,
                5,
                ui.TEXT_MUTED,
                ui.font_small(),
                w=196,
                center=True,
            )
            ui.focusable(row, on_click=self._open_resync)
            self._slot = row
        else:
            # WORD JAGER takes the jager-id slot: the upgrade moment lives
            # here (GAME_DESIGN.md, Onboarding) — probe the antenna, then ask
            # the server to mint the id. Jager mode everywhere derives from
            # hunter_id, so the mint IS the enable.
            self._wj_busy = False
            row = ui.panel(self._s, 6, 210, _ROW_W, ROW_H, bg=ui.CARD)
            ui.label(row, "Word jager", 8, 5, ui.GREEN_D, ui.font_small())
            self._wj = ui.label(
                row,
                "check de antenne",
                104,
                5,
                ui.TEXT_MUTED,
                ui.font_small(),
                w=196,
                center=True,
            )
            ui.focusable(row, on_click=self._word_jager)
            self._slot = row

    def onResume(self, screen):
        super().onResume(screen)
        # Back from the wipe screen with no profile left: this screen is showing
        # a badge id and a jager id that belong to nobody. Leave, and let the
        # screens below do the same until the router reaches the welcome screen.
        # The profile IS the verdict — the same rule foxhunt.py routes on.
        if store.profile() is None:
            self.finish()
            return
        # A resync that landed changes which of the three the slot should be —
        # the row that sent them there is now a lie. Rebuild only on a real
        # change, so the ordinary resume does not churn widgets.
        p = store.profile() or {}
        kind = (
            "jager"
            if p.get("hunter_id")
            else ("cloud" if not p.get("synced") else "word")
        )
        if kind != self._slot_kind and self._slot is not None:
            self._slot.delete()
            self._build_slot()

    def onPause(self, screen):
        super().onPause(screen)
        self._id_taps = 0  # a half-finished unlock doesn't survive leaving
        leds.off()  # don't leave the preview burning after leaving the screen

    def _wipe(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=WipeActivity))

    def _uitleg(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=UitlegActivity))

    def _open_resync(self):
        # The send screen, not a bare retry: the server may answer that this
        # badge already has an account, and that fork is a question with two
        # answers only the player can pick between. Everything that can be
        # said about a registration attempt is already said there.
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=RegSendActivity, extras={"resync": True})
        )

    def _word_jager(self):
        if self._wj_busy:
            return
        if not registrar.has_lora():
            # A driver object alone is insufficient: the physical radio must
            # answer the SPI probe. A friendly no leaves the profile unchanged.
            sound.play("error")
            self._wj.set_text("geen antenne gevonden")
            return
        sound.play("tap")
        self._wj_busy = True
        self._wj.set_text("antenne gevonden!...")
        registrar.REGISTRAR.word_jager(registrar.badge_id(), self._wj_done)

    def _wj_done(self, st):
        self._wj_busy = False
        if st.get("ok") and st.get("hunter_id"):
            # Bank the minted id no matter where the player wandered off to —
            # the server has allocated it, and it repeats the same id on a
            # retry, so dropping it here would only desync badge and server.
            store.update_profile(hunter_id=st["hunter_id"])
        if not self.has_foreground():
            # The reply outlived the screen: every widget here is a dangling
            # reference (screen teardown cleans them), so no text, no sound.
            return
        if st.get("ok") and st.get("hunter_id"):
            sound.play("caught")
            self._wj.set_text(st["hunter_id"] + " - veel jachtplezier!")
        else:
            sound.play("error")
            self._wj.set_text("geen verbinding - probeer later")

    def _id_tap(self):
        self._id_taps += 1
        if self._id_taps >= 5:
            self._id_taps = 0
            self.startActivity(Intent(activity_class=DebugActivity))

    def _flip_geluid(self):
        value = not store.settings()["geluid"]
        store.set_setting("geluid", value)
        sound.set_muted(not value)  # live: no restart to take effect
        # play after the write, so flipping geluid ON is audible immediately
        sound.play("tap")
        self._geluid.set(value)

    def _cycle_led(self):
        i = (_led_step(self._led) + 1) % len(_LED_STEPS)
        self._led = _LED_STEPS[i]
        store.set_setting("led", self._led)
        leds.set_brightness(self._led)  # live: no restart to take effect
        sound.play("tap")
        ui.set_segments(self._led_cells, i, ui.TERRA)
        leds.show_level(5)  # preview at the new strength
