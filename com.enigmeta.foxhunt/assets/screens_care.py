# screens_care.py — everything you do WITH a caught beest, one module.
#
# beast (the hub) -> dossier / feed / school -> games, plus the boekje
# (vriendenboek). Six screens merged into one file for LittleFS block
# economy (see CLAUDE.md, "Size budget"); each section keeps its original
# header, repeated imports between sections are harmless. Section order
# is dependency order, not flow order: the school section builds its
# _GAME_ACT table at module level, so the games section must come first.


# ═════════════════════════ screen_beast ═════════════════════════
# screen_beast.py — BEEST-PAGINA: the hub for a caught creature.
#
# Portrait card with nickname on the left; Band hearts + Energie segment meter
# + found facts on the right; a 3-button action bar (VOER / SPEEL /
# DOSSIER). A finished friend (bond maxed) trades its meters for the
# beste-vriend star and refuses food gently — play stays, free forever.
# Layout follows the design (detail.jsx PxDetail).

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
import pet
from creatures import by_id

# action-bar buttons: (icon, label, kind). Three, all of them doors to
# another screen — the free inline AAI tap that used to sit second is gone:
# it changed no stat and taught nothing, so it was a button that did nothing.
_ACTS = (
    ("food", "VOER", "feed"),
    ("ball", "SPEEL", "spelen"),
    ("book", "DOSSIER", "dossier"),
)
# rarity tag on the portrait card; "norm" gets none. Dark variants of the home
# grid's rarity frame colours (rare=terra, leg=gold), for text on the light card.
_RARITY_TAG = {
    "rare": ("Zeldzaam", ui.TERRA_D),
    "leg": ("Legendarisch", ui.GOLD_D),
}


class BeastActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id)
        self._bubble_timer = None

        s = ui.make_screen(ui.PAPER)
        ui.banner(s, self.c["naam"], ui.GREEN)
        # LV badge (own ref so it updates when band crosses a level)
        self.lvtag = ui.label(
            s, "", 270, 6, ui.CREAM, ui.font_small(), w=44, center=True
        )

        # ── portrait card ───────────────────────────────────────────────
        rare = self.c["rarity"] != "norm"
        card = ui.panel(s, 8, 32, 132, 150, ui.SURFACE_SOFT)
        card.set_style_border_color(ui.hexc(ui.GOLD if rare else ui.GREEN_D), 0)
        sp = art.creature_panel(card, self.c, 5, animate=True)
        sp.align(lv.ALIGN.CENTER, 0, -12)
        tag = _RARITY_TAG.get(self.c["rarity"])
        if tag:
            ui.label(card, tag[0], 0, 112, tag[1], ui.font_small(), w=128, center=True)
        self.bubble = ui.label(card, "", 4, 2, ui.INK, ui.font_small(), w=124)
        strip = ui.box(card, 0, 130, 128, 18, ui.GREEN)
        self.nick = ui.label(
            strip, "", 0, 1, ui.CREAM, ui.font_small(), w=128, center=True
        )

        # ── stats column (rebuilt on every refresh) ─────────────────────
        self.stats = ui.box(s, 150, 34, 164, 148)

        # ── action bar ──────────────────────────────────────────────────
        # the three buttons share the same 307 px the four used to, so the
        # bar still spans the screen instead of leaving a gap where AAI was
        bw = 99
        bar = ui.row(s, 6, 198, 3 * bw + 2 * 5, 36, gap=5)
        for ic, lab, kind in _ACTS:
            b = ui.panel(bar, 0, 0, bw, 36, ui.CARD, border=ui.BORDER_REST)
            art.icon(b, ic, 2).align(lv.ALIGN.TOP_MID, 0, 3)
            ui.label(b, lab, 0, 22, ui.INK, ui.font_small(), w=bw, center=True)
            ui.focusable(b, on_click=lambda k=kind: self._press(k), focus_border=True)

        self.setContentView(s)
        self._refresh()

    def onResume(self, screen):
        super().onResume(screen)
        self._refresh()

    def _refresh(self):
        st = store.beast_state(self.fox_id)
        if st is None:
            return
        self.lvtag.set_text("LV.%d" % pet.level(st["bond"]))
        self.nick.set_text(st.get("bijnaam") or self.c["naam"])
        self.stats.clean()
        g = self.stats
        ui.label(g, "Band", 0, 0, ui.INK, ui.font_small())
        ui.heart_row(g, 0, 16, pet.hearts(st["bond"]), scale=2)
        if pet.finished(st):
            # a beste vriend has no needs — the meters make way for the star
            art.draw_sprite(g, art.STAR, {"g": ui.GOLD}, 2).set_pos(0, 46)
            ui.label(g, "Beste vriend!", 24, 48, ui.GOLD_D, ui.font_label())
            ui.label(g, "speelt altijd mee", 24, 64, ui.TEXT_MUTED, ui.font_small())
        else:
            ui.label(g, "Energie", 0, 44, ui.INK, ui.font_small())
            ui.energy_row(g, 0, 60, pet.energy_segments(st["energy"]), scale=2)
        profile = store.profile() or {}
        self_found = bool(profile.get("hunter_id")) and self.fox_id in store.zelf_ids()
        found_text = "gevonden " + st.get("date", "?")
        found_x = 0
        if profile.get("hunter_id"):
            if self_found:
                art.self_found_badge(g, 2).set_pos(0, 91)
                found_text = "Zelf gevonden " + (
                    store.zelf_date(self.fox_id) or st.get("date", "?")
                )
                found_x = 20
            else:
                found_text = "Gekregen " + st.get("date", "?")
        ui.label(
            g,
            found_text,
            found_x,
            96,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=164 - found_x,
        )
        ui.label(
            g,
            "%s . %dx gezien" % (st.get("place", "?"), st.get("sightings", 1)),
            0,
            112,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=164,
        )

    def _press(self, kind):
        sound.play("tap")
        if kind == "feed":
            st = store.beast_state(self.fox_id)
            if st and pet.finished(st):
                # no refusal screen for a beste vriend — just the fact
                self._flash("hoeft niet meer te eten")
                return
            self.startActivity(
                Intent(activity_class=FeedActivity, extras={"fox_id": self.fox_id})
            )
        elif kind == "spelen":
            # spelen is no longer a free inline tap: it opens the
            # beestenschool, where a session costs energy and earns band
            self.startActivity(
                Intent(activity_class=SchoolActivity, extras={"fox_id": self.fox_id})
            )
        else:  # dossier
            self.startActivity(
                Intent(activity_class=DossierActivity, extras={"fox_id": self.fox_id})
            )

    def _flash(self, text):
        self.bubble.set_text(text)
        if self._bubble_timer:
            self._bubble_timer.delete()
        self._bubble_timer = lv.timer_create(self._clear_bubble, 1100, None)

    def _clear_bubble(self, t):
        t.delete()
        self._bubble_timer = None
        self.bubble.set_text("")

    def onDestroy(self, screen):
        super().onDestroy(screen)
        # The flash timer must not outlive the screen: teardown deletes the
        # bubble, and a surviving timer would set_text on freed memory —
        # flash a message, back-swipe within the 1.1s window, crash.
        if self._bubble_timer:
            self._bubble_timer.delete()
            self._bubble_timer = None


# ═════════════════════════ screen_dossier ═════════════════════════
# screen_dossier.py — DOSSIER: the collection card for a caught creature.
#
# Header (portrait + name + nickname + LV + hearts), a 2-column facts grid, a
# "WEETJE" fun-fact, and a bond-to-next-level progress bar. Static facts come
# from creatures.py; the living bits from the pet state. Layout follows
# the design (detail.jsx PxDossier).

import lvgl as lv
from mpos import Activity
import ui
import art
import store
import pet
from creatures import by_id

_RARITY = {"norm": "gewoon", "rare": "zeldzaam", "leg": "legendarisch"}


class DossierActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        c = by_id(self.fox_id)
        st = store.beast_state(self.fox_id) or pet.default_state("?", "?", 0)
        bond = st["bond"]

        s = ui.make_screen(ui.PAPER)
        ui.banner(s, "Dossier", ui.GREEN, right="#%02d" % (self.fox_id + 1))

        # ── header ───────────────────────────────────────────────────────
        port = ui.panel(s, 8, 32, 64, 64, ui.SURFACE_SOFT)
        art.creature_panel(port, c, 3).align(lv.ALIGN.CENTER, 0, 0)
        ui.label(s, c["naam"], 82, 34, ui.INK, ui.font_title(), w=164)
        ui.label(
            s,
            'bijnaam "%s" . LV.%d' % (st.get("bijnaam") or c["naam"], pet.level(bond)),
            82,
            58,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=210,
        )
        ui.heart_row(s, 82, 76, pet.hearts(bond), scale=2)
        if (store.profile() or {}).get("hunter_id") and self.fox_id in store.zelf_ids():
            # the zelf-gevonden stamp: the hunter visited this one at home
            art.self_found_badge(s, 2).set_pos(198, 70)
            ui.label(s, "zelf gevonden", 216, 77, ui.GOLD_D, ui.font_small())

        # ── facts grid ───────────────────────────────────────────────────
        facts = (
            ("soort", c["soort"]),
            ("biotoop", c["biotoop"]),
            ("zeldzaam", _RARITY.get(c["rarity"], "?")),
            ("1e vangst", st.get("date", "?")),
            ("plek", st.get("place", "?")),
            ("gezien", "%d keer" % st.get("sightings", 1)),
        )
        grid = ui.panel(s, 8, 104, 304, 64, ui.CARD)
        colw = 138
        for i, (k, v) in enumerate(facts):
            cx = 8 + (i % 2) * 150
            cy = 6 + (i // 2) * 18
            ui.label(grid, k, cx, cy, ui.MYSTERY, ui.font_small())
            vl = ui.label(grid, v, cx, cy, ui.INK, ui.font_small(), w=colw)
            vl.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)

        # ── leuk weetje ──────────────────────────────────────────────────
        weet = ui.panel(s, 8, 172, 304, 40, 0xEEF4D6)
        weet.set_style_border_color(ui.hexc(ui.GREEN), 0)
        ui.label(weet, "WEETJE", 8, 4, ui.GREEN_D, ui.font_small())
        ui.label(weet, c["weetje"], 64, 4, ui.INK, ui.font_small(), w=228)

        # ── bond progress to next level ──────────────────────────────────
        lvl = pet.level(bond)
        if lvl >= pet.LEVEL_MAX:
            ui.label(
                s, "max level!", 8, 218, ui.GOLD_D, ui.font_small(), w=304, center=True
            )
        else:
            pct = pet.level_pct(bond)
            ui.label(s, "naar LV.%d" % (lvl + 1), 8, 218, ui.INK, ui.font_small())
            track = ui.box(s, 76, 218, 196, 14, 0xD8C9A4)
            track.set_style_border_width(2, 0)
            track.set_style_border_color(ui.hexc(ui.INK), 0)
            fill = ui.box(track, 0, 0, max(2, int(196 * pct / 100)), 14, ui.GOLD)
            fill.align(lv.ALIGN.LEFT_MID, 0, 0)
            ui.label(
                s, "%d%%" % pct, 276, 218, 0x5E6B44, ui.font_small(), w=40, center=True
            )

        self.setContentView(s)


# ═════════════════════════ screen_feed ═════════════════════════
# screen_feed.py — VOEREN: feed a caught creature a hapje FROM THE VOORRAAD.
#
# A stage with the creature + ENERGIE bar, and a 3-food picker below
# showing what the pantry actually holds. Food is the energy refill — the
# favourite grants extra energie, band comes from spelen. An
# empty jar stays visible ('ga plukken') instead of vanishing. Layout
# follows the design (plukken.jsx PxVoer2).

import lvgl as lv
from mpos import Activity
import ui
import art
import sound
import store
import pet
from creatures import by_id

_FOODS = (("bes", "Bes"), ("noot", "Noot"), ("eikel", "Eikel"))


class FeedActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id)
        self._bubble_timer = None

        s = ui.make_screen(0xDFEEBF)
        ui.banner(s, "Voeren " + self.c["naam"], ui.GREEN)
        self.total_l = ui.label(
            s, "", 240, 8, ui.CREAM, ui.font_small(), w=72, center=True
        )

        # ── stage ────────────────────────────────────────────────────────
        stage = ui.panel(s, 8, 32, 304, 116, ui.SURFACE_TINT)
        sp = art.creature_panel(stage, self.c, 6)
        sp.align(lv.ALIGN.BOTTOM_LEFT, 16, -2)
        self.bubble = ui.label(stage, "", 8, 8, ui.INK, ui.font_label(), w=140)

        # ENERGIE bar, top-right inside the stage
        self.energy_cells = self._bar(stage, 8, "ENERGIE")
        ui.label(
            stage,
            "voer vult energie",
            160,
            30,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=136,
            center=True,
        )

        # ── voorraad picker ─────────────────────────────────────────────
        fw = 97
        picker = ui.row(s, 8, 154, 3 * fw + 2 * ui.GAP_M, 50, gap=ui.GAP_M)
        self.tiles = {}
        for food, lab in _FOODS:
            fav = food == self.c.get("favoriet")
            p = ui.panel(
                picker,
                0,
                0,
                fw,
                50,
                ui.CARD,
                border=(ui.GOLD if fav else ui.BORDER_REST),
            )
            ic = art.icon(p, food, 2)
            ic.set_pos(18, 9)
            cnt = ui.label(p, "", 40, 9, ui.INK, ui.font_title())
            if fav:
                art.draw_sprite(p, art.HEART, {"k": 0x7A1F12, "r": 0xE0463A}, 1).align(
                    lv.ALIGN.TOP_RIGHT, -4, 4
                )
            sub = ui.label(
                p, lab, 0, 32, ui.INK, ui.font_small(), w=fw - 4, center=True
            )
            ui.focusable(p, on_click=lambda f=food: self._feed(f), focus_border=True)
            self.tiles[food] = (p, ic, cnt, sub, lab)

        # ── hint ─────────────────────────────────────────────────────────
        hint = ui.panel(s, 8, 212, 304, 22, ui.CREAM)
        ui.label(
            hint,
            "favoriet = meer energie - band komt van spelen",
            0,
            3,
            ui.INK,
            ui.font_small(),
            w=304,
            center=True,
        )

        self.setContentView(s)
        self._refresh()

    def onResume(self, screen):
        super().onResume(screen)
        self._refresh()

    def _bar(self, parent, y, text):
        ui.label(parent, text, 160, y, ui.INK, ui.font_small())
        cells = []
        for i in range(5):
            c = ui.box(parent, 224 + i * 15, y, 12, 11, ui.DORMANT)
            c.set_style_border_width(ui.BORDER_THIN, 0)
            c.set_style_border_color(ui.hexc(ui.INK), 0)
            cells.append(c)
        return cells

    def _set_bar(self, cells, lit, color):
        for i, c in enumerate(cells):
            c.set_style_bg_color(ui.hexc(color if i < lit else ui.DORMANT), 0)

    def _refresh(self):
        st = store.beast_state(self.fox_id)
        if st is None:
            return
        self._set_bar(self.energy_cells, pet.energy_segments(st["energy"]), ui.GREEN)
        v = store.voorraad()
        self.total_l.set_text("%d voer" % store.voorraad_total())
        for food, (p, ic, cnt, sub, lab) in self.tiles.items():
            n = v.get(food, 0)
            cnt.set_text(str(n))
            p.set_style_bg_color(ui.hexc(ui.CARD if n else ui.DORMANT), 0)
            ic.set_style_opa(lv.OPA.COVER if n else 115, 0)
            sub.set_text(lab if n else "ga plukken")
            sub.set_style_text_color(ui.hexc(ui.INK if n else ui.MYSTERY), 0)

    def _feed(self, food):
        st, ok, msg, is_fav = store.do_feed(self.fox_id, food)
        if st is None:
            return
        sound.play("caught" if is_fav else "tap" if ok else "error")
        self._refresh()
        self._flash(msg)

    def _flash(self, text):
        self.bubble.set_text(text)
        if self._bubble_timer:
            self._bubble_timer.delete()
        self._bubble_timer = lv.timer_create(self._clear, 1100, None)

    def _clear(self, t):
        t.delete()
        self._bubble_timer = None
        self.bubble.set_text("")

    def onDestroy(self, screen):
        super().onDestroy(screen)
        # The flash timer must not outlive the screen: teardown deletes the
        # bubble, and a surviving timer would set_text on freed memory —
        # feed, back-swipe within the 1.1s window, crash.
        if self._bubble_timer:
            self._bubble_timer.delete()
            self._bubble_timer = None


# ═════════════════════════ screen_games ═════════════════════════
# screen_games.py — the beestenschool mini-games: VLIEGEN, VANGEN, DANSEN.
#
# Every game is the same contract: the school gates and launches it with
# {fox_id, kost, fav}; the game pays the energy and banks the band through
# store.do_play the moment the session starts (backing out mid-game costs
# nothing extra and refunds nothing — the creature played, briefly). The end
# card shows the score and the creature's reaction, and offers another round
# only if the energy is really there.
#
# Controls use the badge where it fits: taps for VLIEGEN and VANGEN, the
# four-way joystick for DANSEN. No gesture needs explaining to a seven-year-old.
#
# Every game also hides real hapjes among its ordinary collectables — see
# GameActivity.take_treat. They are the only thing a game hands the player
# beyond a number on an end card, so they are deliberately rare: rare enough
# that finding one is an event, common enough that a long round pays. Each
# game counts its own interval and starts the next one the moment it pays out,
# so playing longer is exactly what earns more.

import gc
import random

import lvgl as lv
from mpos import Activity
import ui
import art
import sound as leds  # LED helpers live in sound.py (merged for block economy)
import sound
import store
import pet
from creatures import by_id

# LVGL redraws the screen on a timer of its own — LV_DEF_REFR_PERIOD, 33 ms —
# and that period has no relation to a game's TICK_MS. The two beat against
# each other: a rendered frame lands between two ticks, repeats the position
# the last frame already showed, and the frame after it moves double. That is
# the hitch you feel several times a second while a game is running, and it is
# nothing to do with background work — measured on VANGEN, the beast's movement
# per RENDERED frame was
#     -4 -4  0 -4  0 -4 -4 -4  0  4  0  4  4  4  0 ...
# and with the refresh period set to the tick it becomes
#     -4 -4 -4 -4 -4 -4  4  4  4  4  4  4  4 -4 -4 ...
# — exactly one step per frame, always. The game still ticks at TICK_MS; only
# the display cadence moves, so no game logic and no difficulty changes. It
# also draws about a fifth less: the refreshes it drops were the ones that had
# nothing new to show.
_LV_REFR_DEFAULT_MS = 33  # LV_DEF_REFR_PERIOD in the firmware's lv_conf.h

# Fixed point: every game keeps anything that MOVES in hundredths of a pixel,
# `_FP` to the pixel, and its speeds with it.
#
# MicroPython boxes every float on the heap — a 16-byte GC block on the badge,
# 32 on the desktop — so `y += vy` is an allocation per moving object per tick,
# and garbage is exactly what buys the collector's second-long pause (see
# _collect). A small int allocates nothing at all. Measured over both games,
# the floats were ~350 B of the ~600 B a VANGEN tick used to cost.
#
# Hundredths, not a power-of-two shift, and that choice has already been made
# the other way once: VLIEGEN's sky first went to sixteenths and had to round a
# 1.6 px cloud to 1.625. Every number these games were tuned with is a decimal
# a human typed — 0.9 gravity, a -6.5 flap, 4.0 px of run, 0.08 of ramp — and
# 1/100 holds all of them exactly. `// 100` is one machine divide; against
# twenty ticks a second it is not measurable, and the arithmetic staying
# readable as the numbers the designer chose is worth more.
#
# Screen coordinates stay whole pixels. Convert once, at the set_x / set_y.
_FP = 100


def _collect():
    """Take the garbage collector's pause where it cannot hurt.

    The badge's heap lives in octal PSRAM and is megabytes wide, so a mark-sweep
    over it costs about a SECOND — and MicroPython runs one whenever the heap
    fills, which during a round means in mid-flight. That is the second-long
    freeze every ~45 s: not a timer, not an updater (both update services check
    once every 24 h), just a constant allocation rate meeting a fixed heap.
    Measured: the OS alone allocates ~8 KB/s, VLIEGEN ~21 KB/s, VANGEN ~50 KB/s.

    So collect deliberately, at the two moments a game is not animating
    anything — the same two `bank_treats()` already trusts with a flash write.
    A round then starts with the whole heap in front of it and the automatic
    collect never comes due while the player is flying. The pause is not
    removed, it is moved: out of the middle of a jump and onto a screen the
    player is reading (see `_collect_after_render`) or a screen change the OS
    is making anyway (`onCreate`, before anything is built)."""
    gc.collect()


def _set_refr_period(ms):
    """Best effort. display.get_refr_timer() is plain LVGL 9, but the app runs
    on badge firmware older than this checkout (same reason sound.py sticks to
    the oldest mpos.lights calls) — a build without it just keeps its own
    cadence and the game plays exactly as it did before."""
    try:
        lv.display_get_default().get_refr_timer().set_period(ms)
    except Exception:
        pass


class GameActivity(Activity):
    """Shared scaffolding: banner + score, the play-session economy, the
    game-over card with NOG EEN KEER / TERUG. Subclasses implement build()
    and step()."""

    TITLE = "?"
    BG = ui.PAPER
    TICK_MS = 50

    def onCreate(self):
        # Before anything is built: the whole heap in front of the round.
        _collect()
        x = self.getIntent().extras
        self.fox_id = x.get("fox_id", 0)
        self.kost = x.get("kost", 1)
        self.fav = x.get("fav", False)
        self.c = by_id(self.fox_id)
        self.timer = None
        self._gc_timer = None
        self._over = False
        self._grabbed = False
        self._wired_keys = False
        self._wired_tap = False
        self.score = 0
        st, ok, self.pet_msg = store.do_play(self.fox_id, self.kost, self.fav)
        self.naam = (st or {}).get("bijnaam") or self.c["naam"]
        # Hapjes spawn only in a session that COST energy. pet.play already
        # rules that a beste vriend plays free and earns no band — "or free
        # play becomes the infinite farming route" — but the mid-game hapjes
        # sat outside that rule: bond a creature to 100, tap NOG EEN KEER
        # forever, and DANSEN paid out roughly four hapjes per five rounds
        # with none of plukken's reload limits. Energy is the rate limit on
        # every reward, hapjes included. (The debug free-play switch rides
        # the same gate, so it stops farming food too.)
        self.treats = store.play_cost(self.kost, st) > 0
        self._pocket = []  # hapjes caught this round, banked by bank_treats()
        self.screen = ui.make_screen(self.BG)
        self._build_chrome()
        self.build(self.screen)
        self.setContentView(self.screen)
        if not ok:
            # the school gates on energy, but state may have decayed between
            # screens — refuse gracefully instead of playing on credit
            self.game_over(self.pet_msg, retry=False)

    def _build_chrome(self):
        ui.banner(self.screen, self.TITLE, ui.GREEN)
        self.right_l = ui.label(
            self.screen, "", 240, 8, ui.CREAM, ui.font_small(), w=72, center=True
        )
        # The hapje toast lives in the banner, between the title and the score:
        # the one strip of screen no game draws in, so it never covers play.
        self.toast_l = ui.label(
            self.screen, "", 104, 8, ui.CREAM, ui.font_small(), w=132, center=True
        )
        self._toast_t = 0
        self._bonus = 0  # score earned by hapjes, on top of what a game counts
        self.set_score(0)

    def set_score(self, n):
        self.score = n
        self.right_l.set_text("score %d" % n)

    def onResume(self, screen):
        super().onResume(screen)
        self.timer = lv.timer_create(self._tick, self.TICK_MS, None)
        _set_refr_period(self.TICK_MS)

    def onPause(self, screen):
        super().onPause(screen)
        if self.timer:
            self.timer.delete()
            self.timer = None
        if self._gc_timer:  # walked out before it fired; onCreate will collect
            self._gc_timer.delete()
            self._gc_timer = None
        # The refresh period is the display's, not ours: hand it back or the
        # whole OS keeps whichever game's cadence was on screen last.
        _set_refr_period(_LV_REFR_DEFAULT_MS)
        leds.off()
        self.bank_treats()

    def _collect_after_render(self):
        """Take the collector's second while the player is READING the card.

        Collecting inline froze the badge for about a second between the crash
        and the "AUW!" — the one moment the player is waiting to be told what
        happened, so it read as the game hanging on the hit. Moving the call to
        the end of game_over() would not have helped either: building the card
        only creates widgets, and LVGL does not draw until its next refresh, so
        an inline collect still holds the card back.

        Hence a one-shot timer. onResume locked the refresh period to TICK_MS,
        so twice that is certainly at least one refresh: the card is on the
        glass before the pause starts, and the pause lands in the seconds the
        player spends reading their score. Walking out first (TERUG, or the
        back swipe) cancels it in onPause — the next round's onCreate collects
        anyway, so nothing is lost by skipping it."""
        if self._gc_timer is None:
            self._gc_timer = lv.timer_create(self._do_collect, self.TICK_MS * 2, None)
            self._gc_timer.set_repeat_count(1)

    def _do_collect(self, _t):
        # LVGL deletes a one-shot timer once it has run, so drop our handle
        # BEFORE collecting: onPause must not delete it a second time.
        self._gc_timer = None
        _collect()

    def _tick(self, t):
        if self.has_foreground() and not self._over:
            if self._toast_t:
                self._toast_t -= 1
                if not self._toast_t:
                    self.toast_l.set_text("")
            self.step()

    def take_treat(self, food=None):
        """Collect a hapje found mid-game: pocket it, say so, score it.

        Pocketed, not banked. Writing it straight through cost a full
        config.json rewrite to flash INSIDE the 50 ms tick, and the player felt
        the game stop for it — the one hitch in a round that is otherwise
        smooth. So a round's catches ride in `_pocket` and `bank_treats()`
        commits them all in one write, from game_over() and onPause(): the two
        moments the game is not animating anything. Walking out mid-round still
        keeps them (onPause is guaranteed on finish and on any activity pushed
        on top); only a power cut mid-round now loses them, which is the trade.

        `food` is the hapje actually on screen and caught (each game stores it
        on the falling item): naming the toast with a fresh pick would show
        different fruit from the icon the player just grabbed."""
        if food is None:
            food = random.choice(store.FOODS)
        self._pocket.append(food)
        sound.play("caught")
        self.toast_l.set_text("+1 %s!" % food)
        self._toast_t = max(8, 2000 // self.TICK_MS)
        self._bonus += 1
        self.set_score(self.score + 1)

    def bank_treats(self):
        """Commit the pocket. `store.add_foods` writes through its OWN
        SharedPreferences instance, so it may only run where nothing else holds
        an editor — true at both call sites: the play session was committed
        back in onCreate and no game keeps a pending write."""
        if self._pocket:
            store.add_foods(self._pocket)
            self._pocket = []

    # ── input, wired once per activity ──────────────────────────────────
    # NOG EEN KEER rebuilds the round on the SAME screen object, and clean()
    # deletes the children while leaving the screen's own event callbacks
    # alone. Wiring them again in build() therefore STACKS a second copy on
    # every retry, and that is not cosmetic: one tap flipped VANGEN's beast
    # twice (so it never turned), and one joystick tilt played a DANSEN step
    # twice — which spent the right answer and then failed the next one, so
    # every round after the first died on its first correct move.
    # The handlers are bound methods reading live activity state, so one
    # registration covers every round the activity ever plays.
    def grab_keys(self, s, on_key):
        """Give the playfield itself the joystick/keyboard focus.

        The board pushes a key to whatever the default group has focused, so a
        game that wants to be steered has to BE that object. Added bare, never
        through ui.focusable() — a gold halo around the whole screen is exactly
        the wrong feedback. DANSEN also grabs the playfield because each stick
        direction is a dance move, not focus navigation.
        The group membership IS released in game_over(), so unlike the
        callback it has to be taken again every round."""
        if not self._wired_keys:
            s.add_event_cb(on_key, lv.EVENT.KEY, None)
            self._wired_keys = True
        g = lv.group_get_default()
        if g:
            g.add_obj(s)
            lv.group_focus_obj(s)
            self._grabbed = True

    def tap_to(self, s, fn):
        """Make the whole playfield tappable, once (see grab_keys)."""
        if self._wired_tap:
            return
        s.add_flag(lv.obj.FLAG.CLICKABLE)
        s.add_event_cb(lambda e: fn(), lv.EVENT.CLICKED, None)
        self._wired_tap = True

    # ── the end card ────────────────────────────────────────────────────
    def game_over(self, kop, retry=True):
        self._over = True
        leds.off()
        self.bank_treats()  # the round is done animating — the write is free here
        # Hand the joystick back BEFORE the card exists: with nothing focused,
        # the group focuses the first button the card registers. Keep the grab
        # and NOG EEN KEER / TERUG are unreachable without the touchscreen.
        if self._grabbed:
            lv.group_remove_obj(self.screen)
            self._grabbed = False
        card = ui.panel(self.screen, 30, 46, 260, 138, ui.CARD)
        ui.label(card, kop, 0, 8, ui.TERRA, ui.font_title(), w=256, center=True)
        ui.label(
            card,
            "score: %d" % self.score,
            0,
            40,
            ui.INK,
            ui.font_label(),
            w=256,
            center=True,
        )
        ui.label(
            card,
            "%s: %s" % (self.naam, self.pet_msg),
            0,
            60,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=256,
            center=True,
        )
        self.note_l = ui.label(
            card, "", 0, 76, ui.TERRA_D, ui.font_small(), w=256, center=True
        )
        bw = 122
        again = ui.panel(card, 4, 96, bw, 30, ui.GREEN if retry else ui.DORMANT)
        ui.label(
            again,
            "NOG EEN KEER",
            0,
            7,
            ui.CREAM if retry else ui.MYSTERY,
            ui.font_label(),
            w=bw - 4,
            center=True,
        )
        if retry:
            ui.focusable(again, on_click=self._again)
        terug = ui.panel(card, 4 + bw + 6, 96, bw, 30, ui.CARD)
        ui.label(terug, "TERUG", 0, 7, ui.INK, ui.font_label(), w=bw - 4, center=True)
        ui.focusable(terug, on_click=self._terug)
        # Card complete. Arm the collect for just after it is drawn, so NOG EEN
        # KEER rebuilds on a clean heap without paying for it again.
        self._collect_after_render()

    def _again(self):
        st = store.beast_state(self.fox_id)
        if st is None or st["energy"] < store.play_cost(self.kost, st) * pet.SEG:
            sound.play("error")
            self.note_l.set_text("te moe - eerst een hapje!")
            return
        sound.play("tap")
        # A tap inside game_over's ~100 ms arming window would otherwise leave
        # that collect to land in the middle of the new round — the exact thing
        # all of this exists to prevent. Take it here instead: the screen is
        # about to be rebuilt anyway, so the pause costs nothing visible.
        if self._gc_timer:
            self._gc_timer.delete()
            self._gc_timer = None
            _collect()
        st, ok, self.pet_msg = store.do_play(self.fox_id, self.kost, self.fav)
        self.treats = store.play_cost(self.kost, st) > 0  # same gate as onCreate
        self._over = False
        self.screen.clean()
        self._build_chrome()
        self.build(self.screen)

    def _terug(self):
        sound.play("tap")
        self.finish()


# ── scenery ──────────────────────────────────────────────────────────────
# Backdrops are built before the player and before any obstacle, so LVGL's
# creation order alone keeps them behind everything — no z-index juggling.
def _scenery(parent, rows, pal, scale, x, y):
    """One backdrop sprite. Scenery must never be tappable: the whole game
    screen carries the tap-to-flap / tap-to-turn handler, and a clickable
    child eats the event before it reaches the screen (same reason ui.box
    drops the flag)."""
    w = art.draw_sprite(parent, rows, pal, scale)
    w.set_pos(x, y)
    w.remove_flag(lv.obj.FLAG.CLICKABLE)
    return w


class _SpritePool:
    """A fixed set of canvases that take turns being whatever is on screen.

    The N64 rule, and the one that matters most here: nothing a round needs is
    allocated while the round is running. Every buffer the pool can ever show
    is baked once in build(), every widget is created once, and a spawn is
    then three calls that allocate nothing — point a canvas at a buffer, place
    it, unhide it. Before this, VANGEN built a fresh 24x24x4 bytearray per
    falling ring and deleted it on the catch: 763 B of garbage per tick with
    11 KB spikes on the spawn tick, which is both what fills the heap and what
    makes that one frame late.

    `bufs` maps a key (ring metal, food name) to art.sprite_buf's
    (bytearray, w, h). Sizes may differ between keys; set_buffer takes the new
    one. The pool holds every buffer, so a canvas whose buffer was swapped
    still has it rooted (art.canvas_for only anchors the one it was born with).

    Sizing is the caller's job and must be an upper bound on how many can be on
    screen at once: take() returning None means the game silently drops a
    spawn, which is a difficulty change, not a rendering glitch."""

    def __init__(self, parent, bufs, n):
        self.bufs = bufs
        buf, w, h = next(iter(bufs.values()))
        self.w = []
        for _ in range(n):
            c = art.canvas_for(parent, buf, w, h)
            c.add_flag(lv.obj.FLAG.HIDDEN)
            c.remove_flag(lv.obj.FLAG.CLICKABLE)  # taps belong to the playfield
            self.w.append(c)
        self.free = list(range(n))

    def take(self, key, x, y):
        """Show `key` at (x, y). Returns (slot, widget), or None if all out."""
        if not self.free:
            return None
        slot = self.free.pop()
        c = self.w[slot]
        buf, w, h = self.bufs[key]
        c.set_size(w, h)
        c.set_buffer(buf, w, h, lv.COLOR_FORMAT.ARGB8888)
        c.set_pos(x, y)
        c.remove_flag(lv.obj.FLAG.HIDDEN)
        return slot, c

    def give(self, slot):
        self.w[slot].add_flag(lv.obj.FLAG.HIDDEN)
        self.free.append(slot)


# ════ VLIEGEN — flappy: tik om te fladderen, ontwijk de takken ═══════════
_BRANCH = 0x8A5F2C
_GAP = 84  # opening between branch pair
_BIRD_X = 50

# Parallax layers: (grid, palette, scale, hundredth-px per tick). Depth is
# signalled on three channels at once — far clouds are smaller, paler and
# slower — because speed alone is barely legible on a 320px screen. The
# branches scroll at 3 px, so even the fastest cloud stays visibly behind the
# play field.
# Cloud x and speed are in hundredths (see _FP). This sky went to sixteenths
# first and had to round its 1.6 px layer to 1.625; at 1/100 it is 160, exactly
# the number the parallax was tuned with.
# THREE layers, not five. Every moving widget costs a per-frame LVGL draw
# descriptor off the MicroPython heap, and the badge's partial-buffer renderer
# pays that several times per frame — the sky was ~100 KB/s of the allocation
# that fills the heap and buys the ~400 ms collect (see _collect). One layer per
# depth channel keeps the parallax reading (small/pale/slow, mid, big/bright/
# fast) while cutting the sky's mover count from five to three.
_SKY = (
    (art.PUFF, {"w": 0xE7F0CE, "s": 0xDCE8BC}, 2, 50),
    (art.CLOUD, {"w": 0xECF2D6, "s": 0xDFE9C2}, 2, 100),
    (art.CLOUD, {"w": 0xFFF7E6, "s": 0xEDF3D8}, 3, 160),
)
_SKY_TOP = 32  # clear of the 26px banner, which is drawn before the clouds
_SKY_BOT = 148

# The fox's flight, in hundredths per tick. These three ARE the game feel and
# were tuned by hand as decimals; 1/100 holds all of them exactly.
_GRAVITY = 90  # 0.9 px/tick added per tick
_FLAP = -650  # 6.5 px/tick upward
_VY_MAX = 800  # 8 px/tick terminal fall
_BRANCH_DX = 3  # px per tick, whole from the start

# Collision leniency, the oldest trick in the platformer book: the fox's box is
# 32x32 but the art doesn't fill it — ears, tail and paws leave transparent
# margin — so an honest box-vs-box test kills you for a hit that never looked
# like one. The player's hitbox shrinks by _GRACE on every side. It costs
# nothing when you were clearly going to crash and saves you when you weren't.
# The screen edges deliberately stay strict: there the sprite leaving the frame
# IS the visible signal, and a forgiving box would just clip the fox off-screen.
_GRACE = 5

# Branch pairs between hapjes. The hapje hangs in the middle of the gap, so it
# costs no detour — flying the centre line instead of scraping past a branch is
# the whole skill of this game, and this pays for it.
_VLIEG_TREAT = (10, 21)
_TREAT_PX = 16  # a food icon at scale 2
# A branch pair spawns every 46 ticks and crosses the 350 px to its deletion
# point in 117, so four pairs can share the screen; five is the pool with room.
# Two hapjes can never be in the air at once (they are at least ten pairs
# apart) but the pool costs two small canvases, and a pool that runs dry drops
# a spawn silently.
_MAX_OBS = 5
_MAX_TREATS = 2


class VliegActivity(GameActivity):
    TITLE = "VLIEGEN"
    BG = 0xCFE2AD
    TICK_MS = 50

    def build(self, s):
        self.tap_to(s, self._flap)
        self.grab_keys(s, self._key)
        self.clouds = []
        for i, (rows, pal, scale, sp) in enumerate(_SKY):
            # seeded apart rather than at random, so a fresh round never starts
            # with every cloud stacked in one corner
            x = (i * 67 + random.randrange(0, 40)) % 320
            y = random.randrange(_SKY_TOP, _SKY_BOT)
            w = _scenery(s, rows, pal, scale, x, y)
            self.clouds.append(
                {
                    "w": w,
                    "x": x * _FP,
                    "px": (len(rows[0]) * scale) * _FP,
                    "sp": sp,
                    "ix": x,
                }
            )
        self.bird = art.creature_panel(s, self.c, 2, flip_x=True)
        self._y = 110 * _FP
        self._vy = 0
        # The round starts on the first tap, not on the first tick. Gravity,
        # the branches and the collision test all wait; only the sky keeps
        # drifting, so the held frame still looks alive. Without this a player
        # who is still reading the hint has already fallen out of the sky.
        self._flying = False
        self.bird.set_pos(_BIRD_X, self._y // _FP)
        # Branch pairs and hapjes are pooled the same way VANGEN's falling
        # items are: the widgets exist for the whole round and a spawn only
        # moves and unhides them. Two lv.obj per pair plus a canvas per hapje,
        # created and deleted every 46 ticks, was the rest of this game's
        # garbage once the sky and the fox stopped allocating.
        self.obs = []  # {"slot", "x", "gap", "passed", "treat"}
        self.pairs = []
        for _ in range(_MAX_OBS):
            top = self._branch(s, 26, 2, lv.BORDER_SIDE.BOTTOM)
            bot = self._branch(s, 26, 2, lv.BORDER_SIDE.TOP)
            top.add_flag(lv.obj.FLAG.HIDDEN)
            bot.add_flag(lv.obj.FLAG.HIDDEN)
            self.pairs.append((top, bot))
        self.free_pairs = list(range(_MAX_OBS))
        bufs = {}
        for f in store.FOODS:
            bufs[f] = art.icon_buf(f, 2)
        self.treat_pool = _SpritePool(s, bufs, _MAX_TREATS)
        self._spawn_t = 10
        self._treat_in = random.randrange(*_VLIEG_TREAT)

    def _flap(self):
        if not self._over:
            self._flying = True
            self._vy = _FLAP

    def _key(self, e):
        """Every "go" key flaps: joystick up and A on the badge, up / enter /
        space on the emulator keyboard. 0x20 is the space bar arriving as plain
        ASCII — the SDL keyboard passes printable keys straight through, and
        lv.KEY has no name for it."""
        if e.get_key() in (lv.KEY.UP, lv.KEY.ENTER, 0x20):
            self._flap()

    def _branch(self, s, y, h, cap):
        """One branch. Built five pairs at a time in build() and then reshaped
        per spawn (set_y + set_height), never created inside the round."""
        b = ui.box(s, 320, y, 26, max(2, h), _BRANCH)
        b.set_style_border_width(ui.BORDER, 0)
        b.set_style_border_color(ui.hexc(ui.INK), 0)
        # The end facing the gap keeps its ink cap — that edge is the thing the
        # player has to fly past, and it needs to be crisp. The other end runs
        # off the screen, where a cap would print a hard line across the branch
        # and make it read as a short plank floating there. `cap` says which.
        b.set_style_border_side(lv.BORDER_SIDE.LEFT | lv.BORDER_SIDE.RIGHT | cap, 0)
        return b

    def _drift(self):
        """Scroll the parallax sky. The int-x guard matters: the slowest layer
        advances half a pixel per tick, so half its set_x calls would be a
        no-move that still costs LVGL an invalidate + redraw."""
        for c in self.clouds:
            c["x"] -= c["sp"]
            if c["x"] < -c["px"]:
                c["x"] = (320 + random.randrange(0, 48)) * _FP
                c["w"].set_y(random.randrange(_SKY_TOP, _SKY_BOT))
            x = c["x"] // _FP
            if x != c["ix"]:
                c["ix"] = x
                c["w"].set_x(x)

    def step(self):
        self._drift()
        if not self._flying:
            return
        vy = self._vy + _GRAVITY
        if vy > _VY_MAX:
            vy = _VY_MAX
        self._vy = vy
        yf = self._y + vy
        self._y = yf
        y = yf // _FP
        if y < 26 or y > 240 - 32:
            sound.play("error")
            self.game_over("AUW!")
            return
        self.bird.set_pos(_BIRD_X, y)

        self._spawn_t -= 1
        if self._spawn_t <= 0 and self.free_pairs:
            self._spawn_t = 46
            gap_y = random.randrange(92, 178)
            slot = self.free_pairs.pop()
            top, bot = self.pairs[slot]
            top.set_pos(320, 26)
            top.set_height(max(2, gap_y - _GAP // 2 - 26))
            top.remove_flag(lv.obj.FLAG.HIDDEN)
            bot.set_pos(320, gap_y + _GAP // 2)
            bot.set_height(max(2, 240 - gap_y - _GAP // 2))
            bot.remove_flag(lv.obj.FLAG.HIDDEN)
            self.obs.append(
                {
                    "slot": slot,
                    # A branch scrolls exactly 3 px per tick, so its x is a
                    # plain pixel count: the fox needs hundredths because its
                    # motion is fractional, a branch never does.
                    "x": 320,
                    "gap": gap_y,
                    "passed": False,
                    "treat": None,
                }
            )
            self._treat_in -= 1
            if self._treat_in <= 0 and self.treats:
                self._treat_in = random.randrange(*_VLIEG_TREAT)
                _f = random.choice(store.FOODS)
                got = self.treat_pool.take(_f, 325, gap_y - _TREAT_PX // 2)
                if got is not None:
                    self.obs[-1]["treat"] = got[0]
                    self.obs[-1]["treat_food"] = _f
        # Backwards by index, so no per-tick copy of the list (see VANGEN).
        obs = self.obs
        for i in range(len(obs) - 1, -1, -1):
            o = obs[i]
            x = o["x"] - _BRANCH_DX
            o["x"] = x
            top, bot = self.pairs[o["slot"]]
            top.set_x(x)
            bot.set_x(x)
            t = o["treat"]
            if t is not None:
                self.treat_pool.w[t].set_x(x + 5)
                # The hapje's own box against the fox's forgiving one. It sits
                # inside the gap, so this can only ever fire on a pass the
                # branch test below is going to allow anyway.
                ty = o["gap"] - _TREAT_PX // 2
                if (
                    x + 5 < _BIRD_X + 32 - _GRACE
                    and x + 5 + _TREAT_PX > _BIRD_X + _GRACE
                    and ty < y + 32 - _GRACE
                    and ty + _TREAT_PX > y + _GRACE
                ):
                    self.treat_pool.give(t)
                    o["treat"] = None
                    self.take_treat(o.pop("treat_food", None))
            if not o["passed"] and x + 26 < _BIRD_X:
                o["passed"] = True
                self.set_score(self.score + 1)
            if x < -30:
                top.add_flag(lv.obj.FLAG.HIDDEN)
                bot.add_flag(lv.obj.FLAG.HIDDEN)
                self.free_pairs.append(o["slot"])
                if o["treat"] is not None:
                    self.treat_pool.give(o["treat"])
                obs.pop(i)
                continue
            # collision: the fox's hitbox (its 32x32 box inset by _GRACE, so
            # x 55..77) vs the branch column outside the gap
            if x < _BIRD_X + 32 - _GRACE and x + 26 > _BIRD_X + _GRACE:
                if (
                    y + _GRACE < o["gap"] - _GAP // 2
                    or y + 32 - _GRACE > o["gap"] + _GAP // 2
                ):
                    sound.play("error")
                    self.game_over("AUW!")
                    return


# ════ VANGEN — het beest draaft heen en weer, tik om te keren ════════════
# The backdrop is a camp field in two planes. Nothing here moves: the beast
# runs along a fixed line, so a scrolling backdrop would only claim a motion
# that isn't happening. Depth comes from the horizon instead — the ground band
# starts where the far treeline stands, and the near row is drawn bigger and
# greener on top of it.
_FIELD = 0xD3E5AE  # far field, a shade under the screen's own bg
_GROUND = 0xC3D897  # near ground; its top edge IS the horizon line
_HORIZON = 198
_FAR = {"c": 0xBAD48F, "t": 0xC4B489}
_NEAR = {"c": 0x9CBE6C, "t": 0xA68E63}
_CANVAS = {"a": 0xE7D49B, "b": 0xBFA469}
# (grid, palette, scale, x, baseline) — y is derived so every tree stands ON
# its line instead of being hand-placed and floating a pixel.
_FIELD_ART = (
    (art.PINE, _FAR, 2, 26, _HORIZON),
    (art.TREE, _FAR, 2, 100, _HORIZON),
    (art.PINE, _FAR, 2, 176, _HORIZON),
    (art.TREE, _FAR, 2, 250, _HORIZON),
)
_CAMP_ART = (
    (art.TREE, _NEAR, 3, 2, 226),
    (art.TENT, _CANVAS, 3, 104, 226),
    (art.PINE, _NEAR, 3, 286, 226),
)

# The playfield, named — the spawner does reachability maths off these numbers,
# so a hand-tuned literal moving out from under it would silently make the game
# unfair again.
#
# The beast's x, a falling item's y and its vy are in hundredths (see _FP);
# every number below is exact at that scale (4.0 -> 400, 2.5 -> 250, 0.08 -> 8).
_RUN_PX = 4  # beast px per tick; it never stops, it only turns
_CX_MIN_PX, _CX_MAX_PX = 6, 282  # how far the beast can run
_CX_START_PX = 144  # where it stands when the round starts
_RUN = _RUN_PX * _FP  # the same three in hundredths, so the tick never converts
_CX_MIN, _CX_MAX = _CX_MIN_PX * _FP, _CX_MAX_PX * _FP
_CX_START = _CX_START_PX * _FP
_BEAST_Y = 196  # top of the beast: where a falling item is caught
_ITEM_PX = 24  # an 8x8 icon at scale 3 — ring and hapje are the same size
_DROP_Y = 30  # where an item appears
_CATCH_Y = _BEAST_Y - _ITEM_PX  # item y at which its bottom meets the beast
_GONE_Y = 232  # past here the item is missed
# the two the fall maths needs in hundredths, so the tick never converts
_DROP_YF = _DROP_Y * _FP
_CATCH_YF = _CATCH_Y * _FP
# The catch window: cx may be anywhere in (item.x - 32, item.x + 24), so the
# beast aims at item.x - _AIM and a target cx wants an item at cx + _AIM.
_AIM = 4

# What falls, and what it is worth. Rings are the rain; a hapje is the event.
# Metal is the only variation, so worth has to follow the eye: brons 1, zilver
# 2, goud 3, and rarer the higher it pays.
_RING_ODDS = (70, 22, 8)
# Drops between hapjes. The round ends on the third miss, so a fixed "every
# 50th" would hand the good players everything and the young ones nothing; the
# interval is redrawn each time instead, and it is short enough that an ordinary
# round still meets one.
_VANG_TREAT = (30, 61)

# How many items can share the sky. The spawner runs every max(16, 30 - caught)
# ticks and an item lives (_GONE_Y - _DROP_Y) / vy of them, so the busiest the
# air ever gets is about three and a half; six is the pool with headroom, and
# headroom is not optional — a pool that runs dry drops a spawn, which the
# player reads as the game going easy on them.
_MAX_ITEMS = 6
_HEART_LIT = {"k": 0x7A1F12, "r": 0xE0463A}
_HEART_DIM = {"k": 0xB0A07E, "r": 0xECE0C2}


def _ring_kind():
    r = random.randrange(sum(_RING_ODDS))
    for i, w in enumerate(_RING_ODDS):
        if r < w:
            return i
        r -= w
    return 0


class VangActivity(GameActivity):
    TITLE = "VANGEN"
    BG = 0xDFEEBF
    TICK_MS = 50

    def build(self, s):
        self.tap_to(s, self._turn)
        self.grab_keys(s, self._key)
        ui.box(s, 0, _HORIZON - 22, 320, 240 - _HORIZON + 22, _FIELD)
        for rows, pal, scale, x, base in _FIELD_ART:
            _scenery(s, rows, pal, scale, x, base - len(rows) * scale)
        ui.box(s, 0, _HORIZON, 320, 240 - _HORIZON, _GROUND)
        for rows, pal, scale, x, base in _CAMP_ART:
            _scenery(s, rows, pal, scale, x, base - len(rows) * scale)
        self.beast = art.creature_panel(s, self.c, 2)
        self._cx = _CX_START  # hundredths of a pixel — see _FP
        self._dir = 1
        self.beast.set_pos(_CX_START_PX, _BEAST_Y)
        self.items = []  # {"w", "slot", "x", "y", "vy", "worth"}
        self._spawn_t = 10
        self._missed = 0
        # Difficulty rides the number of CATCHES, never the score: a gold ring
        # is worth three and would otherwise ramp the game three times as fast
        # as the player is actually playing it.
        self._caught = 0
        self._treat_in = random.randrange(*_VANG_TREAT)
        # Everything that can fall, baked once. Three ring metals plus one per
        # hapje: seven small buffers built here instead of one per spawn thrown
        # away a second later.
        bufs = {}
        for k in range(3):
            bufs[k] = art.sprite_buf(art.RING, art.RING_PALS[k], 3)
        for f in store.FOODS:
            bufs[f] = art.icon_buf(f, 3)
        self.pool = _SpritePool(s, bufs, _MAX_ITEMS)
        self.hearts_box = ui.box(s, 8, 30, 66, 18)
        # The hearts are three widgets for the whole round, swapped between two
        # baked palettes. _hearts() used to clean the box and draw three fresh
        # sprites on every miss — three buffers plus three widgets, at the one
        # moment the player is already being told bad news.
        self._heart_buf = (
            art.sprite_buf(art.HEART, _HEART_LIT, 2),
            art.sprite_buf(art.HEART, _HEART_DIM, 2),
        )
        buf, hw, hh = self._heart_buf[0]
        self.heart_w = []
        for i in range(3):
            c = art.canvas_for(self.hearts_box, buf, hw, hh)
            c.set_pos(i * 22, 0)
            c.remove_flag(lv.obj.FLAG.CLICKABLE)
            self.heart_w.append(c)
        self._hearts()

    def _hearts(self):
        lit, dim = self._heart_buf
        for i, c in enumerate(self.heart_w):
            buf, w, h = lit if i < 3 - self._missed else dim
            # set_buffer re-points the canvas's OWN dsc struct, so LVGL's image
            # cache sees the same src pointer for lit and dim; it drops the
            # cache itself, and the invalidate makes the repaint explicit.
            c.set_buffer(buf, w, h, lv.COLOR_FORMAT.ARGB8888)
            c.invalidate()

    def _turn(self):
        if not self._over:
            self._dir = -self._dir

    def _key(self, e):
        """Joystick left/right steer the beast. Both controls set the same
        _dir, so tapping and steering agree: a tap flips the direction, the
        stick names it outright."""
        if self._over:
            return
        k = e.get_key()
        if k == lv.KEY.LEFT:
            self._dir = -1
        elif k == lv.KEY.RIGHT:
            self._dir = 1

    def _due(self, it):
        """Ticks until `it` is catchable — its place in the queue the player
        has to work through, in order. Whole ticks: the item only ever moves on
        one, and the caller clamps the negative case to zero anyway."""
        return (_CATCH_YF - it["y"]) // it["vy"]

    def _drop_x(self, vy):
        """Where an item falling at `vy` may appear: only somewhere the beast
        can still run to, given everything already in the air.

        The beast moves a fixed _RUN per tick and cannot stop, so its range is
        just speed times time — but time from WHERE. Measuring from where it
        stands now is not enough: two or three items are usually falling at
        once, and a player who is off collecting the one that lands first has
        no way back for a second that was only reachable from a standstill.
        That is the version of this game that felt unfair.

        So the window chains: it hangs off the last item already due, and is
        as wide as the run the beast can make between that catch and this one.
        Serving them in the order they land is then always possible, which is
        the order a player plays in anyway. With an empty sky there is nothing
        to chain to and the beast's own position anchors it.

        The fall is measured to the FIRST catchable tick, not the last, so a
        drop at the very edge of the window still arrives with a little slack
        rather than demanding a frame-perfect turn.

        Whole ticks and whole pixels throughout — vy is hundredths, everything
        else here is a screen coordinate. Rounding costs the window at most the
        4 px of one tick's run, well inside the slack the paragraph above
        deliberately leaves."""
        fall = (_CATCH_YF - _DROP_YF) // vy
        if self.items:
            last = max(self.items, key=self._due)
            due = self._due(last)
            anchor, slack = last["x"] - _AIM, fall - (due if due > 0 else 0)
        else:
            anchor, slack = self._cx // _FP, fall
        reach = (slack if slack > 0 else 0) * _RUN_PX
        lo = max(_CX_MIN_PX, anchor - reach) + _AIM
        hi = min(_CX_MAX_PX, anchor + reach) + _AIM
        return random.randrange(lo, hi + 1)

    def step(self):
        cxf = self._cx + _RUN * self._dir
        if cxf < _CX_MIN:
            cxf, self._dir = _CX_MIN, 1
        elif cxf > _CX_MAX:
            cxf, self._dir = _CX_MAX, -1
        self._cx = cxf
        cx = cxf // _FP
        self.beast.set_x(cx)

        self._spawn_t -= 1
        if self._spawn_t <= 0:
            self._spawn_t = max(16, 30 - self._caught)
            vy = min(600, 250 + self._caught * 8)  # hundredth-px per tick
            self._treat_in -= 1
            if self._treat_in <= 0 and self.treats:
                # worth 0 marks the hapje: it pays a pantry item, not points
                self._treat_in = random.randrange(*_VANG_TREAT)
                _f = random.choice(store.FOODS)
                key, worth = _f, 0
            else:
                kind = _ring_kind()
                key, worth, _f = kind, kind + 1, None
            x = self._drop_x(vy)
            got = self.pool.take(key, x, _DROP_Y)
            if got is not None:
                slot, w = got
                self.items.append(
                    {
                        "w": w,
                        "slot": slot,
                        "x": x,
                        "y": _DROP_YF,
                        "vy": vy,
                        "worth": worth,
                        "food": _f,
                    }
                )
        # Backwards by index: `self.items[:]` copied the list every tick just to
        # be able to remove from it while iterating, and a copy is an
        # allocation. Walking down never visits a moved element.
        items = self.items
        for i in range(len(items) - 1, -1, -1):
            it = items[i]
            y = it["y"] + it["vy"]
            it["y"] = y
            ypx = y // _FP
            it["w"].set_y(ypx)
            if (
                ypx + _ITEM_PX >= _BEAST_Y
                and it["x"] + _ITEM_PX > cx
                and it["x"] < cx + 32
            ):
                self.pool.give(it["slot"])
                items.pop(i)
                self._caught += 1
                if it["worth"]:
                    sound.play("tap")
                    self.set_score(self.score + it["worth"])
                else:
                    self.take_treat(it["food"])
            elif ypx > _GONE_Y:
                self.pool.give(it["slot"])
                items.pop(i)
                self._missed += 1
                self._hearts()
                sound.play("error")
                if self._missed >= 3:
                    self.game_over("OEPS!")
                    return


# ════ DANSEN — het beest doet pasjes voor, de speler doet ze na ══════════
# (dx, dy, colour), in joystick-direction order. The same index drives
# movement, sound and LEDs, so every cue agrees.
_DANCE_MOVES = (
    (-64, 0, 0xF08A7A),
    (0, -52, 0xF6D88A),
    (0, 52, 0x9ACE7A),
    (64, 0, 0xB8C8D6),
)
_DANCE_X = 136
_DANCE_Y = 104
_DANCE_LEAD_TICKS = 10  # one second to get ready before the first move
_DANCE_STEP_TICKS = 10  # one second per move: 600 ms posed, 400 ms centred
_WIN_ROUNDS = 8
# 1 in N player turns puts a hapje on one of the four tiles. It is seeded when
# the player's turn STARTS, never during the demo — the beast walking over it
# while showing the steps would read as eating it. If this round's steps never
# visit that tile it simply stays for the next one, so a seeded hapje is always
# eventually reachable, and a new one is only drawn once this one is taken.
#
# 20, not 5: the seed rolls once per turn and a full game is 8 turns, so 1-in-5
# paid a hapje most rounds — DANSEN out-earned VLIEGEN (whose typical round
# ends before its first hapje even scrolls in) several times over, and the
# easiest game was the best forage. 1-in-20 lands a full game around the same
# expected payout as a decent VLIEGEN run: a treat is a nice surprise, not the
# reason to pick this game.
_DANCE_TREAT_ODDS = 20


class DansActivity(GameActivity):
    TITLE = "DANSEN"
    TICK_MS = 100

    def build(self, s):
        self.grab_keys(s, self._key)
        stage = ui.panel(s, 20, 32, 280, 190, ui.SURFACE_SOFT)
        # A quiet tiled floor makes the creature's four moves easy to read
        # without turning them back into Simon buttons.
        for row in range(3):
            for col in range(3):
                ui.box(
                    stage,
                    24 + col * 76,
                    20 + row * 54,
                    72,
                    50,
                    0xE8DFC8 if (row + col) % 2 else 0xF2EAD7,
                )
        self.hint_l = ui.label(
            stage,
            "kijk naar de pasjes",
            0,
            5,
            ui.MYSTERY,
            ui.font_small(),
            w=276,
            center=True,
        )
        self.beast = art.creature_panel(s, self.c, 3, animate=True)
        self.beast.set_pos(_DANCE_X, _DANCE_Y)
        self.seq = []
        self.state = "new"
        self.t = 0
        self.show_i = 0
        self.inp = 0
        self._dim_t = 0
        self.treat = None
        self.treat_i = None
        self.treat_food = None

    def _seed_treat(self):
        if not self.treats or self.treat is not None:
            return
        if random.randrange(_DANCE_TREAT_ODDS):
            return
        self.treat_i = random.randrange(4)
        dx, dy, _ = _DANCE_MOVES[self.treat_i]
        self.treat_food = random.choice(store.FOODS)
        self.treat = art.icon(self.screen, self.treat_food, 2)
        self.treat.set_pos(_DANCE_X + dx + 16, _DANCE_Y + dy + 16)
        self.beast.move_foreground()  # the beast steps ON the hapje, not under it

    def _pose(self, i=None):
        if i is None:
            self.beast.set_pos(_DANCE_X, _DANCE_Y)
            leds.off()
            return
        dx, dy, colour = _DANCE_MOVES[i]
        self.beast.set_pos(_DANCE_X + dx, _DANCE_Y + dy)
        try:
            rgb = ((colour >> 16) & 0xFF, (colour >> 8) & 0xFF, colour & 0xFF)
            leds.write([rgb] * 5)
        except Exception:
            pass

    def _key(self, e):
        keys = {
            lv.KEY.LEFT: 0,
            lv.KEY.UP: 1,
            lv.KEY.DOWN: 2,
            lv.KEY.RIGHT: 3,
        }
        i = keys.get(e.get_key())
        if i is not None:
            # The badge repeats a held joystick direction after 400 ms. A
            # dance step is one deliberate tilt, so consume nothing else from
            # this input device until the stick has physically returned to
            # neutral. This also stops a direction held during the demo from
            # leaking into the player's turn.
            indev = lv.indev_active()
            if indev:
                indev.wait_release()
            self._press(i)

    def step(self):
        if self._dim_t:
            self._dim_t -= 1
            if self._dim_t == 0:
                self._pose()
        if self.state == "new":
            self.seq.append(random.randrange(4))
            self.show_i = 0
            self.t = 0
            self.state = "lead"
            self.hint_l.set_text("kijk naar de pasjes")
        elif self.state == "lead":
            self.t += 1
            if self.t >= _DANCE_LEAD_TICKS:
                self.state = "show"
                self.t = 0
        elif self.state == "show":
            ph = self.t % _DANCE_STEP_TICKS
            if ph == 0:
                self._pose(self.seq[self.show_i])
                sound.play("sim%d" % self.seq[self.show_i])
            elif ph == 6:
                self._pose()
            elif ph == _DANCE_STEP_TICKS - 1:
                self.show_i += 1
                if self.show_i >= len(self.seq):
                    self.state = "wait"
                    self.inp = 0
                    self._seed_treat()
                    self.hint_l.set_text("doe ze na met de stick!")
            self.t += 1
        elif self.state == "pause":
            self.t += 1
            if self.t >= 8:
                self.state = "new"

    def _press(self, i):
        if self._over or self.state != "wait":
            return
        self._pose(i)
        self._dim_t = 2
        sound.play("sim%d" % i)
        if i != self.seq[self.inp]:
            sound.play("error")
            self.game_over("OEPS!")
            return
        if self.treat is not None and i == self.treat_i:
            self.treat.delete()
            self.treat = None
            self.treat_i = None
            self.take_treat(self.treat_food)
            self.treat_food = None
        self.inp += 1
        if self.inp >= len(self.seq):
            self.set_score(len(self.seq) + self._bonus)
            if len(self.seq) >= _WIN_ROUNDS:
                sound.play("caught")
                self.game_over("SUPER!")
                return
            self.state = "pause"
            self.t = 0


# ═════════════════════════ screen_school ═════════════════════════
# screen_school.py — BEESTENSCHOOL: pick a game, spend energy, earn band.
#
# Layout follows the design (plukken.jsx PxSchool / PxSchoolMoe). Spelen is
# the bond leg of the economy chain: the tired state is the playful rate
# limit ("eerst een hapje?"), never a punishment. Picking a game launches
# the real mini-game (screen_games); the game itself pays the energy and
# banks the band through store.do_play when the session starts.
#
# The design's third tile was DOOLHOF (tilt maze), but the IMU has no
# spike yet — VANGEN (tap to turn, catch the falling rings) takes its
# slot until it does.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
import pet
from creatures import by_id

# (game id, icon, naam, energy cost in segments, subtitle)
GAMES = (
    ("vlieg", "vlieg", "VLIEGEN", 2, "ontwijk de takken"),
    ("vang", "ring", "VANGEN", 1, "vang de ringen"),
    ("dans", "dans", "DANSEN", 1, "doe de pasjes na"),
)
_GAME_ACT = {"vlieg": VliegActivity, "vang": VangActivity, "dans": DansActivity}


def favourite_game(cid):
    """Each creature favours one game, stably, without a roster field —
    flying beasts don't exist as data, so the id decides. A favourite grants
    extra band (pet.play) and wears the gold frame."""
    return GAMES[cid % len(GAMES)][0]


class SchoolActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id)
        self._fresh = True
        self.screen = ui.make_screen(ui.PAPER)
        self._populate()
        self.setContentView(self.screen)

    def onResume(self, screen):
        super().onResume(screen)
        if self._fresh:
            self._fresh = False
            return
        self._rebuild()

    def _rebuild(self):
        self.screen.clean()
        self._populate()

    def _populate(self):
        s = self.screen
        st = store.beast_state(self.fox_id)
        if st is None:
            return
        # Show complete spendable units so one lit cell always pays for a
        # one-energy game. Affordability still gates on exact energy points.
        energie = st["energy"]
        segs = pet.energy_segments(energie)
        cheapest = min(g[3] for g in GAMES)
        moe = energie < store.play_cost(cheapest, st) * pet.SEG
        naam = st.get("bijnaam") or self.c["naam"]
        fav = favourite_game(self.fox_id)

        ui.banner(s, "BEESTENSCHOOL", ui.GREEN, right="energie %d/5" % segs)

        # the playful refusal, when moe
        note = "%s is moe - eerst een hapje?" % naam if moe else None
        if note:
            bub = ui.panel(s, 8, 30, 304, 24, ui.CREAM)
            ui.label(bub, note, 0, 3, ui.INK, ui.font_label(), w=300, center=True)

        # creature column
        top = 58 if note else 34
        stage = ui.panel(s, 8, top, 96, 112 - (top - 34), ui.SURFACE_SOFT)
        sp = art.creature_panel(stage, self.c, 4, animate=not moe)
        sp.align(lv.ALIGN.BOTTOM_MID, 0, -4)
        if moe:
            sp.set_style_opa(180, 0)
        ui.label(s, naam, 8, 152, ui.INK, ui.font_label())
        ui.label(s, "ENERGIE", 8, 170, ui.MYSTERY, ui.font_small())
        for i in range(5):
            cell = ui.box(
                s,
                8 + i * 17,
                184,
                14,
                12,
                (ui.TERRA if moe else ui.GREEN) if i < segs else ui.DORMANT,
            )
            cell.set_style_border_width(ui.BORDER_THIN, 0)
            cell.set_style_border_color(ui.hexc(ui.INK), 0)
        ui.label(
            s,
            "te weinig energie" if moe else "spelen geeft band",
            8,
            202,
            ui.MYSTERY,
            ui.font_small(),
            w=96,
        )

        # game tiles
        tile_h = 40 if note else 52
        y = top
        for gid, icon, gnaam, kost, sub in GAMES:
            echte_kost = store.play_cost(kost, st)
            kan = not moe and energie >= echte_kost * pet.SEG
            is_fav = gid == fav
            tile = ui.panel(
                s,
                112,
                y,
                200,
                tile_h,
                ui.CARD if kan else ui.DORMANT,
                border=(ui.GOLD if (is_fav and kan) else ui.BORDER_REST),
                bw=ui.BORDER,
            )
            ic = art.icon(tile, icon, 3)
            ic.set_pos(6, (tile_h - 24) // 2 - 2)
            if not kan:
                ic.set_style_opa(115, 0)
            ui.label(tile, gnaam, 38, 5, ui.INK if kan else ui.MYSTERY, ui.font_label())
            if is_fav:
                art.icon(tile, "spark", 1).set_pos(96, 7)
                ui.label(tile, "favoriet", 106, 6, ui.GOLD_D, ui.font_small())
            ui.label(tile, sub, 38, tile_h - 18, ui.MYSTERY, ui.font_small())
            ui.label(
                tile,
                "gratis" if echte_kost == 0 else "-%d" % echte_kost,
                150,
                4,
                ui.TERRA if kan else ui.MYSTERY,
                ui.font_label(),
                w=44,
                center=True,
            )
            ui.label(
                tile,
                "energie" if echte_kost else "spelen",
                150,
                20,
                ui.MYSTERY,
                ui.font_small(),
                w=44,
                center=True,
            )
            if kan:
                ui.focusable(
                    tile,
                    on_click=lambda g=gid, k=kost, f=is_fav: self._play(g, k, f),
                    focus_border=True,
                )
            else:
                ui.focusable(tile, focus_border=True)  # navigable, inert
            y += tile_h + ui.GAP_M

        # bottom right: the way out of moe, or the standing hint
        if moe:
            btn = ui.panel(s, 112, 208, 200, 26, ui.GREEN)
            ui.label(
                btn, "EERST VOEREN", 0, 5, ui.CREAM, ui.font_label(), w=196, center=True
            )
            ui.focusable(btn, on_click=self._feed)
        else:
            hint = ui.panel(s, 112, 208, 200, 26, ui.CREAM)
            ui.label(
                hint,
                "kies een spel",
                0,
                5,
                ui.INK,
                ui.font_small(),
                w=196,
                center=True,
            )

    def _play(self, game, kost, is_fav):
        # launch the real game; it pays the energy and banks the band
        # (store.do_play) itself, and shows the score + reaction on its end
        # card. Returning here rebuilds, so the meters are already fresh.
        sound.play("tap")
        self.startActivity(
            Intent(
                activity_class=_GAME_ACT[game],
                extras={"fox_id": self.fox_id, "kost": kost, "fav": is_fav},
            )
        )

    def _feed(self):
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=FeedActivity, extras={"fox_id": self.fox_id})
        )


# ═════════════════════════ screen_boekje ═════════════════════════
# screen_boekje.py — VRIENDENBOEKJE: one page per first-ever meeting.
#
# The permanent layer under the daily vonk: never decays, grows all weekend.
# Every kid knows the friend-book ritual — meetings as memories, never as
# "collecting people". Layout follows the design (verzamelen.jsx PxBoekje /
# PxBoekjeLeeg).

import lvgl as lv
from mpos import Activity
import ui
import art
import sound
import store
import companion

_AVATAR_BG = 0xCFE0EA
_CELL_W, _CELL_H, _CELL_GAP = 99, 60, 5
_MAAND = (
    "jan",
    "feb",
    "mrt",
    "apr",
    "mei",
    "jun",
    "jul",
    "aug",
    "sep",
    "okt",
    "nov",
    "dec",
)


def _dag_label(dag):
    """'2026-08-04' -> '4 aug' — the full ISO date doesn't fit the card and
    the year is always this year anyway."""
    try:
        _, m, d = dag.split("-")
        return "%d %s" % (int(d), _MAAND[int(m) - 1])
    except (ValueError, IndexError):
        return dag


class BoekjeActivity(Activity):
    def onCreate(self):
        vrienden = store.vrienden()
        s = ui.make_screen(ui.PAPER)
        n = len(vrienden)
        ui.banner(
            s,
            "VRIENDENBOEKJE",
            ui.GREEN,
            right="%d %s" % (n, "maatje" if n == 1 else "maatjes"),
        )
        if vrienden:
            self._grid(s, vrienden)
        else:
            self._empty(s)
        self.setContentView(s)

    def _grid(self, s, vrienden):
        grid = ui.row(
            s, 6, 34, 3 * _CELL_W + 2 * _CELL_GAP + 2, 200, gap=_CELL_GAP, wrap=True
        )
        grid.add_flag(lv.obj.FLAG.SCROLLABLE)
        grid.set_scroll_dir(lv.DIR.VER)
        for f in vrienden:
            card = ui.panel(grid, 0, 0, _CELL_W, _CELL_H, ui.CARD)
            head, accs, bg = companion.decode(f.get("code", ""))
            ava = ui.box(card, 3, 7, 40, 40, companion.BGS[bg])
            # 48px companion in a 40px opening: transparent margin falls off
            # the edges, the face stays centred (same crop as the home header)
            companion.draw(ava, head, accs, 3, x=-4, y=-4)
            ui.label(card, f.get("naam", "?"), 49, 12, ui.INK, ui.font_label())
            ui.label(
                card, _dag_label(f.get("dag", "")), 49, 30, ui.MYSTERY, ui.font_small()
            )
            ui.focusable(card, focus_border=True)  # navigable, inert

    def _empty(self, s):
        p = ui.panel(s, 20, 48, 280, 140, ui.CARD)
        art.icon(p, "spark", 2).set_pos(16, 14)
        art.icon(p, "spark", 2).set_pos(248, 26)
        art.icon(p, "boek", 5).align(lv.ALIGN.TOP_MID, 0, 14)
        ui.label(
            p, "Nog niemand ontmoet", 0, 66, ui.INK, ui.font_title(), w=276, center=True
        )
        ui.label(
            p,
            "elke nieuwe snuffel geeft je",
            0,
            96,
            ui.MYSTERY,
            ui.font_small(),
            w=276,
            center=True,
        )
        ui.label(
            p,
            "een pagina in dit boekje",
            0,
            110,
            ui.MYSTERY,
            ui.font_small(),
            w=276,
            center=True,
        )
        btn = ui.panel(s, 20, 200, 280, 32, ui.GREEN)
        art.icon(btn, "snuf", 1).set_pos(70, 6)
        ui.label(
            btn, "GA SNUFFELEN", 0, 8, ui.CREAM, ui.font_label(), w=276, center=True
        )
        ui.focusable(btn, on_click=self._terug)

    def _terug(self):
        # the boekje is only reachable from the snuffelscherm, so back IS
        # "ga snuffelen" — no circular import needed
        sound.play("tap")
        self.finish()
