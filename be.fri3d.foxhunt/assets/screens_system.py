# screens_system.py — the hub and the meta screens, one module.
#
# home (the boek + router target), profiel, instellingen, debug and
# ALLES WISSEN. Five screens merged into one file for LittleFS block
# economy (see CLAUDE.md, "Size budget"); each section keeps its
# original header, repeated imports between sections are harmless.


# ═════════════════════════ screen_home ═════════════════════════
# screen_home.py — the book. Profile header, "nu in de buurt" hunt shortcuts,
# and the scrolling boek (design: home.jsx PxHomeNew).
#
# Only ever reached through foxhunt.py's router, so a profile is guaranteed:
# store.profile() is not None here, and the header renders it unconditionally.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import companion
import store
import sound
from creatures import CREATURES
from fox_radio import RADIO
from screens_hunt import HuntActivity
from screens_care import BeastActivity
from screens_hunt import SnuffelActivity
from screens_hunt import PlukActivity
from screens_onboarding import UitlegActivity
from screens_hunt import VisitorActivity
import registrar

_CELL_W, _CELL_H, _GAP = 74, 52, 4  # boek tiles
_HAIR = 0xDCCFA9  # section hairline on paper
_NEAR_BG = 0xF6E7CD  # nearby-card fill
_SEG_OFF = 0xE4D6BC  # unlit heat segment
_RARITY_FRAME = {"rare": ui.TERRA, "leg": ui.GOLD}
_VISITOR_POLL_MS = 30_000


class HomeActivity(Activity):
    def onCreate(self):
        self._fresh = True
        self._visitor_timer = None
        self._visitor_id = None
        self.screen = ui.make_screen(ui.PAPER)
        self._populate()
        self.setContentView(self.screen)
        # First-ever home: one uitleg screen names the loop for this mode.
        # A store flag, not part of onboarding, so restored accounts get it too.
        if not store.flag("uitleg_gezien"):
            store.set_flag("uitleg_gezien")
            self.startActivity(Intent(activity_class=UitlegActivity))

    def onResume(self, screen):
        super().onResume(screen)
        # The profile can vanish under us: instellingen -> ALLES WISSEN erases
        # it. Leave before repopulating — _populate reads the profile as a dict
        # and would fail on None — and the router below (foxhunt.py) opens the
        # welcome screen. Same rule it routes on: the profile IS the verdict.
        if store.profile() is None:
            self.finish()
            return
        # Home is the natural WiFi moment: drain any queued badge→server
        # reports (snuffel/pluk grants, bonded counts). Fire-and-forget — a
        # dead network just leaves the outbox for the next resume.
        registrar.flush()
        self._start_visitor_poll()
        # Refresh caught state in place. Do NOT call setContentView again — it
        # appends a new screen to the stack and leaks the old one (11 canvas
        # buffers!). clean() frees the previous cells before repopulating.
        if self._fresh:  # onCreate built it a moment ago
            self._fresh = False
            return
        self.screen.clean()
        self._populate()

    def onPause(self, screen):
        super().onPause(screen)
        self._stop_visitor_poll()

    def onDestroy(self, screen):
        super().onDestroy(screen)
        self._stop_visitor_poll()

    def _start_visitor_poll(self):
        if self._visitor_timer is None:
            # _populate checks once immediately whenever home is built or
            # resumed. The timer only catches a visitor becoming due while a
            # player leaves home open; visitor timing is measured in hours,
            # so polling the whole preferences file twice a second is wasteful.
            self._visitor_timer = lv.timer_create(
                self._poll_visitor, _VISITOR_POLL_MS, None
            )

    def _stop_visitor_poll(self):
        if self._visitor_timer is not None:
            self._visitor_timer.delete()
            self._visitor_timer = None

    def _poll_visitor(self, _timer):
        pending = store.visitor_pending()
        if pending is not None and self._visitor_id is None:
            self.screen.clean()
            self._populate()

    def _section(self, y, text, color, right=None):
        """Small section header: label + hairline (+ count on the right)."""
        s = self.screen
        ui.label(s, text, 6, y, color, ui.font_small())
        x0 = 6 + len(text) * 7 + 8  # crude r11 width; the hairline just fills
        x1 = 270 if right else 314
        ui.box(s, x0, y + 5, max(4, x1 - x0), 2, _HAIR)
        if right is not None:
            rl = ui.label(s, right, 274, y, ui.MYSTERY, ui.font_small(), w=40)
            rl.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)

    def _populate(self):
        s = self.screen
        p = store.profile()
        awake = set(RADIO.active_foxes())
        caught = set(store.caught_ids())
        jager = bool(p.get("hunter_id"))

        # ── header: your companion (tap -> profile) + settings gear ───────
        # Two SIBLING panels, not one panel with the gear inside: the badge's
        # directional focus navigation is geometric, and a target nested
        # inside another target's rectangle is unreachable by joystick. Side
        # by side, identity and gear are two clean focus stops, each with the
        # standard ring. A jager grows two more stops (snuffel + pluk), so
        # the fox row keeps its whole width and JE BOEK
        # gives up nothing; the verzamelaar gets those verbs as big cards
        # below instead (design: verzamelen.jsx PxHomeJager / PxHomeVerz).
        header_w = 172 if jager else 262
        header = ui.panel(s, 6, 6, header_w, 40, bg=ui.CARD)
        ui.focusable(header, on_click=self._profile)
        # box, not panel: an ink frame here muddles into the sprite's own
        # outlines at 32px — the backdrop swatch alone is enough of an edge.
        portrait = ui.box(header, 4, 2, 32, 32, companion.BGS[p["bg"]])
        # 32px companion in a 28px opening: the art's transparent margin
        # falls off the edges, the face stays centred.
        companion.draw(portrait, p["head"], p["accs"], 2, x=-2, y=-2)
        ui.label(header, p["name"], 46, 0, ui.INK, ui.font_title())
        # Two modes: a jager has a LoRa-minted id ("JGR-0042"), everyone else
        # plays over WiFi as verzamelaar. The subtitle names the mode you're
        # in — never a "coming soon" placeholder.
        sub = p.get("hunter_id") or "Verzamelaar"
        ui.label(header, sub, 46, 24, ui.MYSTERY, ui.font_small())
        if jager:
            self._kop_btn(182, "snuf", self._snuffel)
            self._kop_btn(227, "pluk", self._pluk)
        gear = ui.panel(s, 272, 6, 42, 40, bg=ui.CARD)
        art.icon(gear, "gear", 2).align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(gear, on_click=self._settings)

        if jager:
            self._nearby_row(s, awake, caught)
        else:
            self._op_pad_row(s)

        # ── je boek: every creature, found first (roster order within), scrolls ──
        self._section(
            126, "JE BOEK", ui.MYSTERY, right="%d/%d" % (len(caught), len(CREATURES))
        )
        grid = ui.row(s, 6, 142, 4 * _CELL_W + 3 * _GAP + 2, 92, gap=_GAP, wrap=True)
        grid.add_flag(lv.obj.FLAG.SCROLLABLE)
        grid.set_scroll_dir(lv.DIR.VER)

        # two passes, not sorted(): MicroPython's sort is unstable, and equal
        # keys scramble the roster order the book is supposed to keep
        boek = [c for c in CREATURES if c["id"] in caught]
        boek += [c for c in CREATURES if c["id"] not in caught]
        beste = store.finished_ids()
        for c in boek:
            cid = c["id"]
            is_caught = cid in caught
            # the hunt is jager-only: a verzamelaar's awake tile stays as
            # inert as a sleeping one — a mode you cannot play must not open
            huntable = jager and (cid in awake) and not is_caught

            cell = ui.box(
                grid,
                0,
                0,
                _CELL_W,
                _CELL_H,
                ui.CARD if is_caught else ui.DORMANT,
                radius=2,
            )
            cell.set_style_border_width(ui.BORDER, 0)
            frame = _RARITY_FRAME.get(c["rarity"]) if is_caught else None
            cell.set_style_border_color(ui.hexc(frame or ui.BORDER_REST), 0)

            sp = art.creature_panel(cell, c, 2, silhouette=not is_caught)
            sp.align(lv.ALIGN.TOP_MID, 0, 1)
            if is_caught and c["rarity"] == "leg":
                art.icon(cell, "spark", 1).set_pos(2, 2)
            if cid in beste:
                # beste-vriend star, top-right so it never collides with spark
                art.draw_sprite(cell, art.STAR, {"g": ui.GOLD}, 1).align(
                    lv.ALIGN.TOP_RIGHT, -2, 2
                )
            if is_caught:
                ui.box(cell, 0, 35, _CELL_W - 4, 13, 0xF0E8D4)
            ui.label(
                cell,
                c["naam"] if is_caught else "???",
                0,
                36,
                ui.INK if is_caught else ui.MYSTERY,
                ui.font_small(),
                w=_CELL_W - 4,
                center=True,
            )

            # Every tile is navigable so the grid never goes dead: caught ->
            # creature page, huntable -> the hunt, dormant -> inert.
            if is_caught:
                ui.focusable(
                    cell, on_click=lambda cc=cid: self._open(cc), focus_border=True
                )
            elif huntable:
                ui.focusable(
                    cell, on_click=lambda cc=cid: self._hunt(cc), focus_border=True
                )
            else:
                ui.focusable(cell, focus_border=True)

        # The store refuses to create new normal meetings for a jager, but
        # still returns a visitor that was already waiting before the upgrade.
        self._visitor_id = store.visitor_pending()
        if self._visitor_id is not None:
            self._visitor_popup()

    def _visitor_popup(self):
        pop = ui.panel(self.screen, 8, 178, 304, 54, ui.SURFACE_SOFT, border=ui.GREEN_D)
        art.icon(pop, "bush", 2).set_pos(8, 15)
        ui.label(pop, "GEZOEK!", 56, 9, ui.GREEN_D, ui.font_label())
        ui.label(
            pop,
            "Er ritselt iets bij je kamp...",
            56,
            28,
            ui.INK,
            ui.font_small(),
        )
        btn = ui.panel(pop, 204, 8, 90, 38, ui.GREEN)
        label = ui.label(
            btn, "GA KIJKEN", 0, 0, ui.CREAM, ui.font_label(), w=86, center=True
        )
        label.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=self._visitor)

    def _visitor(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=VisitorActivity))

    def _kop_btn(self, x, icon, on_click):
        """Jager header shortcut: a compact 42px icon panel."""
        s = self.screen
        btn = ui.panel(s, x, 6, 42, 40, bg=ui.CARD)
        art.icon(btn, icon, 1).align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=on_click)

    def _nearby_row(self, s, awake, caught):
        # ── nu in de buurt: every transmitting fox, caught or not ─────────
        self._section(52, "NU IN DE BUURT", ui.TERRA)
        nearby = []
        for c in CREATURES:
            if c["id"] in awake:
                # peek, not reading: the fake radio's reading() advances its
                # simulated approach, and home only wants to LOOK.
                r = RADIO.peek(c["id"])
                heat = max(1, min(3, (r.level * 3 + 4) // 5))
                nearby.append((c, heat))
        # still-huntable first (the row is a hunt shortcut), warmest leading;
        # already-caught ones trail — and stay huntable: re-finding a known
        # creature is zelf vinden (GAME_DESIGN.md), an upgrade, never a dud
        nearby.sort(key=lambda ch: (ch[0]["id"] in caught, -ch[1]))
        if nearby:
            cards = ui.row(s, 6, 68, 308, 52, gap=5)
            for i, (c, heat) in enumerate(nearby[:4]):
                is_caught = c["id"] in caught
                cell = ui.box(cards, 0, 0, 73, 52, _NEAR_BG, radius=ui.RADIUS)
                cell.set_style_border_width(ui.BORDER, 0)
                # warmest card wears gold, the rest the hunt's terra
                cell.set_style_border_color(ui.hexc(ui.GOLD if i == 0 else ui.TERRA), 0)
                spr = art.creature_panel(cell, c, 2, silhouette=not is_caught)
                spr.set_pos(18, 2)
                for d in range(3):
                    seg = ui.box(
                        cell, 20 + d * 10, 40, 8, 5, ui.TERRA if d < heat else _SEG_OFF
                    )
                    seg.set_style_border_width(ui.BORDER_THIN, 0)
                    seg.set_style_border_color(ui.hexc(ui.INK), 0)
                ui.focusable(
                    cell,
                    on_click=lambda cc=c["id"]: self._hunt(cc),
                    focus_border=True,
                )
        else:
            ui.label(
                s,
                "alles slaapt - kom straks terug",
                6,
                86,
                ui.TEXT_MUTED,
                ui.font_small(),
            )

    def _op_pad_row(self, s):
        # ── op pad: the verzamelaar's two verbs, where the (antenna-less,
        # unhuntable) fox row would be. Big cards explain each action without
        # exposing the underlying daily/reload counters.
        self._section(52, "OP PAD", ui.GREEN_D)
        for x, icon, titel, stat, col, fn in (
            (6, "snuf", "SNUFFELEN", "zoek een maatje", 0x8A6A2E, self._snuffel),
            (163, "pluk", "PLUKKEN", "ga op zoek", ui.TEXT_MUTED, self._pluk),
        ):
            card = ui.panel(s, x, 68, 151, 52, ui.CARD, border=ui.TERRA)
            art.icon(card, icon, 2).set_pos(6, 8)
            ui.label(card, titel, 44, 9, ui.INK, ui.font_label())
            ui.label(card, stat, 44, 27, col, ui.font_small())
            ui.focusable(card, on_click=fn)

    def _snuffel(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=SnuffelActivity))

    def _pluk(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=PlukActivity))

    def _hunt(self, cid):
        sound.play("tap")
        self.startActivity(Intent(activity_class=HuntActivity, extras={"fox_id": cid}))

    def _open(self, cid):
        sound.play("tap")
        self.startActivity(Intent(activity_class=BeastActivity, extras={"fox_id": cid}))

    def _profile(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=ProfileActivity))

    def _settings(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=SettingsActivity))


# ═════════════════════════ screen_profile ═════════════════════════
# screen_profile.py — the jagersprofiel (tap your companion on the header).
#
# Big companion portrait, name + ids, score, four stat tiles, and the two edit
# actions that re-enter the onboarding screens in edit mode (design: home.jsx
# PxProfile). Rebuilt on resume so an edit shows the moment you come back.

import lvgl as lv
from mpos import Activity, Intent
import mpos.time
import ui
import art
import sound
import store
import companion
from creatures import CREATURES, by_id
from screens_onboarding import CompanionActivity
from screens_onboarding import RegisterActivity

SCORE_BG = 0xF6E7CD
SCORE_LABEL = 0x8A6A2E
BADGE_TX = 0x5C4F38

# Local, provisional scoring until the cloud server owns it: rarer = more.
_POINTS = {"norm": 100, "rare": 250, "leg": 500}


class ProfileActivity(Activity):
    def onCreate(self):
        self._fresh = True
        self.screen = ui.make_screen(ui.PAPER)
        self._populate()
        self.setContentView(self.screen)

    def onResume(self, screen):
        super().onResume(screen)
        # Coming back from an edit: rebuild in place (never re-setContentView).
        if self._fresh:
            self._fresh = False
            return
        self.screen.clean()
        self._populate()

    def _populate(self):
        s = self.screen
        p = store.profile() or {"name": "Jager", "head": "vos", "accs": [], "bg": 0}
        caught = store.caught_ids()

        ui.banner(s, "PROFIEL", ui.GREEN)

        portrait = ui.panel(s, ui.PAD, 32, 108, 108, bg=companion.BGS[p.get("bg", 0)])
        # animate=True: the one screen big and still enough for the sterren
        # twinkle to read as a reward rather than as a flicker.
        companion.draw(
            portrait, p.get("head", "vos"), p.get("accs", []), 6, x=4, y=4, animate=True
        )

        name = ui.label(s, p.get("name", "Jager"), 124, 34, ui.INK, ui.font_title())
        pencil = art.icon(s, "pencil", 2)
        pencil.align_to(name, lv.ALIGN.OUT_RIGHT_MID, 6, 0)
        ui.label(
            s, p.get("hunter_id") or "Verzamelaar", 124, 62, ui.INK, ui.font_small()
        )
        ui.label(s, p.get("badge_id", ""), 124, 78, BADGE_TX, ui.font_small())

        # score: rarity-weighted, local for now (the server will own scoring)
        score = sum(_POINTS.get(by_id(c)["rarity"], 100) for c in caught if by_id(c))
        panel = ui.panel(s, 124, 100, 188, 40, bg=SCORE_BG, border=ui.GOLD)
        art.icon(panel, "spark", 2).set_pos(8, 12)
        ui.label(panel, "SCORE", 26, 12, SCORE_LABEL, ui.font_small())
        sl = ui.label(panel, str(score), 80, 6, ui.INK, ui.font_title(), w=98)
        sl.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)

        # stat tiles. band_total, not a beast_state loop: beast_state persists
        # its decay pass, so asking per creature cost a whole-config parse and
        # flash write per catch, on every resume of this screen.
        band = store.band_total()
        since = p.get("since")
        now = mpos.time.epoch_seconds()
        days = 1 + max(0, (now - since) // 86400) if since else 1
        stats = (
            ("%d/%d" % (len(caught), len(CREATURES)), "GEVONDEN", ui.INK),
            (str(band), "BAND", ui.TERRA),
            (str(days), "DAGEN", ui.INK),
            ("0", "GERUILD", ui.GREEN_D),
        )
        tiles = ui.row(s, ui.PAD, 146, 304, 44, gap=5)
        for value, label, colour in stats:
            t = ui.panel(tiles, 0, 0, 72, 44, bg=ui.CARD)
            ui.label(t, value, 0, 4, colour, ui.font_title(), w=68, center=True)
            ui.label(t, label, 0, 28, ui.MYSTERY, ui.font_small(), w=68, center=True)

        # actions: re-enter the onboarding screens in edit mode
        edit_btn = ui.box(s, ui.PAD, 196, 179, 34, ui.GREEN, radius=ui.RADIUS)
        edit_btn.set_style_border_width(ui.BORDER, 0)
        edit_btn.set_style_border_color(ui.hexc(ui.INK), 0)
        el = ui.label(
            edit_btn,
            "MAATJE AANPASSEN",
            0,
            0,
            ui.CREAM,
            ui.font_small(),
            w=175,
            center=True,
        )
        el.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(edit_btn, on_click=self._edit_companion)

        name_btn = ui.box(s, 193, 196, 119, 34, ui.CARD, radius=ui.RADIUS)
        name_btn.set_style_border_width(ui.BORDER, 0)
        name_btn.set_style_border_color(ui.hexc(ui.INK), 0)
        nl = ui.label(
            name_btn, "NAAM", 0, 0, ui.INK, ui.font_small(), w=115, center=True
        )
        nl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(name_btn, on_click=self._edit_name)

    def _edit_companion(self):
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=CompanionActivity, extras={"edit": True})
        )

    def _edit_name(self):
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=RegisterActivity, extras={"edit": True})
        )


# ═════════════════════════ screen_settings ═════════════════════════
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
import sound as leds  # LED helpers live in sound.py (merged for block economy)
import registrar
from screens_onboarding import UitlegActivity
from screens_onboarding import RegSendActivity

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


# ═════════════════════════ screen_debug ═════════════════════════
# screen_debug.py — hidden test tools, unlocked from the code keypad.

import lvgl as lv
from mpos import Activity
import art
import sound
import store
import ui
from creatures import CREATURES
from store import (
    DEBUG_CODE,
    debug_code_enabled,
    disable_debug_code,
    enable_debug_code,
)


class DebugActivity(Activity):
    def onCreate(self):
        s = ui.make_screen(ui.PAPER)
        ui.banner(s, "DEBUG", ui.TERRA, right=DEBUG_CODE)

        # The whole page scrolls, not a clipped list inside it. An inner
        # scroller only ever had the pixels the fixed panels left over (45px,
        # one row), and every section below it needed a hard-coded y. One flex
        # column under the banner: sections stack, the roster is simply the
        # last and longest of them, and the page grows to fit.
        body = ui.box(s, 0, 26, 320, 214)
        body.add_flag(lv.obj.FLAG.SCROLLABLE)
        # LVGL resolves a scroll from the object the press HIT, and a hit needs
        # CLICKABLE — which ui.box strips. The grids elsewhere get away with it
        # because their cells are focusable and tile the whole area; here most
        # of the page is inert panel, so without this a drag anywhere but on a
        # toggle finds nothing and the page refuses to move.
        body.add_flag(lv.obj.FLAG.CLICKABLE)
        body.set_scroll_dir(lv.DIR.VER)
        body.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        body.set_style_pad_hor(6, 0)
        body.set_style_pad_ver(8, 0)
        body.set_style_pad_row(ui.GAP_M, 0)

        self.code_toggle, self.code_label = self._switch(
            body,
            "TESTCODE 1111",
            "voor elk beest",
            debug_code_enabled(),
            self._toggle_debug_code,
        )

        # pluk on ANY wifi network — for walking-around tests away from the
        # camp: no fri3d-badge hotspots exist yet, every AP becomes a
        # plukplek (identity stays the BSSID, reloads and yields included)
        self.pluk_toggle, self.pluk_label = self._switch(
            body,
            "PLUK OP ELKE WIFI",
            "thuis-testen",
            store.debug_cheat("pluk_any"),
            lambda: self._toggle_cheat("pluk_any", self.pluk_toggle, self.pluk_label),
        )

        # a beestenschool game costs energy, and a tired creature refuses —
        # right, but it makes testing a game a round of feeding first. This
        # zeroes the price (store.play_cost); the reward is untouched.
        self.moe_toggle, self.moe_label = self._switch(
            body,
            "ONVERMOEIBAAR",
            "spelen kost geen energie",
            store.debug_cheat("nooit_moe"),
            lambda: self._toggle_cheat("nooit_moe", self.moe_toggle, self.moe_label),
        )

        visit = ui.panel(body, 0, 0, 308, 34, ui.CARD)
        ui.label(visit, "RANDOM BEZOEK", 8, 3, ui.GREEN_D, ui.font_small())
        self.visit_label = ui.label(
            visit, "na 10 seconden", 8, 17, ui.INK, ui.font_small()
        )
        button = ui.box(visit, 178, 2, 110, 26, ui.GREEN, radius=ui.RADIUS)
        button.set_style_border_width(ui.BORDER, 0)
        button.set_style_border_color(ui.hexc(ui.GREEN_D), 0)
        label = ui.label(
            button, "START", 0, 0, ui.CREAM, ui.font_small(), w=110, center=True
        )
        label.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(button, on_click=self._schedule_visitor, focus_border=True)

        # Uitschrijven is not a debug tool: it is ALLES WISSEN in instellingen,
        # where a player can find it. This only says where, so nobody builds a
        # second one down here.
        account = ui.panel(body, 0, 0, 308, 25, ui.DORMANT, border=ui.BORDER_REST)
        ui.label(account, "ACCOUNT", 8, 7, ui.MYSTERY, ui.font_small())
        ui.label(
            account,
            "uitschrijven: instellingen",
            82,
            7,
            ui.TEXT_MUTED,
            ui.font_small(),
        )

        ui.label(body, "BEESTENBOEK", 0, 0, ui.GREEN_D, ui.font_small())

        caught = set(store.caught_ids())
        for creature in CREATURES:
            cid = creature["id"]
            row = ui.box(body, 0, 0, 308, 42, ui.CARD, radius=ui.RADIUS)
            row.set_style_border_width(ui.BORDER_THIN, 0)
            row.set_style_border_color(ui.hexc(ui.BORDER_REST), 0)

            sprite = art.creature_panel(row, creature, 2)
            sprite.align(lv.ALIGN.LEFT_MID, 6, 0)
            ui.label(row, creature["naam"], 45, 14, ui.INK, ui.font_small(), w=130)

            toggle = ui.box(row, 178, 7, 110, 28, ui.DORMANT, radius=ui.RADIUS)
            toggle.set_style_border_width(ui.BORDER, 0)
            toggle.set_style_border_color(ui.hexc(ui.BORDER_REST), 0)
            state = ui.label(
                toggle,
                "",
                0,
                0,
                ui.INK,
                ui.font_small(),
                w=110,
                center=True,
            )
            state.align(lv.ALIGN.CENTER, 0, 0)
            self._paint_toggle(toggle, state, cid in caught)
            ui.focusable(
                toggle,
                on_click=lambda cc=cid, bb=toggle, ll=state: self._toggle(cc, bb, ll),
                focus_border=True,
            )

        self.setContentView(s)

    def _switch(self, parent, kop, uitleg, enabled, on_click):
        """One debug switch: a 34px titled panel with an ACTIEF / NIET ACTIEF
        toggle on the right. Placed by the body's flex column, so it carries no
        y of its own. Returns (button, label) so the click handler can repaint
        it — LVGL widgets have no __dict__ to hang state on."""
        panel = ui.panel(parent, 0, 0, 308, 34, ui.CARD)
        ui.label(panel, kop, 8, 3, ui.TERRA_D, ui.font_small())
        ui.label(panel, uitleg, 8, 17, ui.INK, ui.font_small())
        button = ui.box(panel, 178, 2, 110, 26, ui.DORMANT, radius=ui.RADIUS)
        button.set_style_border_width(ui.BORDER, 0)
        label = ui.label(button, "", 0, 0, ui.INK, ui.font_small(), w=110, center=True)
        label.align(lv.ALIGN.CENTER, 0, 0)
        self._paint_toggle(
            button, label, enabled, on_text="ACTIEF", off_text="NIET ACTIEF"
        )
        ui.focusable(button, on_click=on_click, focus_border=True)
        return button, label

    def _paint_toggle(
        self, button, label, enabled, on_text="GEVANGEN", off_text="NIET GEV."
    ):
        button.set_style_bg_color(ui.hexc(ui.GREEN if enabled else ui.DORMANT), 0)
        button.set_style_border_color(
            ui.hexc(ui.GREEN_D if enabled else ui.BORDER_REST), 0
        )
        label.set_text(on_text if enabled else off_text)
        label.set_style_text_color(ui.hexc(ui.CREAM if enabled else ui.INK), 0)

    def _toggle_cheat(self, key, button, label):
        # store.debug_cheat, not a setting: settings survive ALLES WISSEN,
        # and an armed cheat must not outlive the player who armed it.
        sound.play("tap")
        enabled = not store.debug_cheat(key)
        store.set_debug_cheat(key, enabled)
        self._paint_toggle(
            button, label, enabled, on_text="ACTIEF", off_text="NIET ACTIEF"
        )

    def _schedule_visitor(self):
        sound.play("tap")
        store.schedule_debug_visitor(10)
        self.visit_label.set_text("komt over 10 sec - ga terug")

    def _toggle_debug_code(self):
        sound.play("tap")
        enabled = debug_code_enabled()
        if enabled:
            disable_debug_code()
        else:
            enable_debug_code()
        self._paint_toggle(
            self.code_toggle,
            self.code_label,
            not enabled,
            on_text="ACTIEF",
            off_text="NIET ACTIEF",
        )

    def _toggle(self, cid, button, label):
        sound.play("tap")
        caught = store.is_caught(cid)
        if caught:
            store.remove_caught(cid)
        else:
            # "debug", not the default "vangst": the dossier's lineage must
            # not claim a toggled-on creature was found in the field.
            store.add_caught(cid, origin="debug")
        self._paint_toggle(button, label, not caught)


# ═════════════════════════ screen_wipe ═════════════════════════
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
