# screens_hunt.py — finding creatures in the field, one module.
#
# hunt (LoRa heat) -> code -> win, plus snuffel (badge meetings), pluk
# (WiFi harvest) and the random visitor. Six screens merged into one
# file for LittleFS block economy (see CLAUDE.md, "Size budget"); each
# section keeps its original header, repeated imports are harmless.
# NOTE: two radios live here — fox_radio RADIO (hunt/code) keeps the
# bare name, the pluk section calls pluk_radio.RADIO explicitly.


# ═════════════════════════ screen_hunt ═════════════════════════
# screen_hunt.py — classic ARDF. Silhouette + heart/bpm + 5-LED hot/cold.
#
# A timer polls the (faked) radio; the RSSI it reports IS the heart rate
# (rssi + 255) and also drives the LEDs (warmer = closer).
# There is NO automatic "found": RSSI can't tell you you've physically reached
# the box. The player walks up, reads the code off the device, and taps
# "VOER DE CODE IN" themselves.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound as leds  # LED helpers live in sound.py (merged for block economy)
import sound
from creatures import by_id
from fox_radio import RADIO, rssi_to_bpm


class HuntActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id)
        self.timer = None
        self._beat = False
        self._mirror_level = None  # last drawn LED-mirror level; None = never

        s = ui.make_screen(0xCFE2AD)
        rarity = self.c["rarity"]
        tag = {"leg": "legende", "rare": "zeldzaam"}.get(rarity, "gewoon")
        # The hunt is the mystery — you only learn WHICH beast it is once you've
        # entered its code. Only the rarity is teased, as a difficulty cue.
        ui.banner(s, "?????", ui.TERRA, right=tag)

        # scan card with the silhouette + heartbeat
        card = ui.box(s, 6, 30, 308, 120, ui.SURFACE_SOFT, radius=2)
        card.set_style_border_width(2, 0)
        card.set_style_border_color(ui.hexc(ui.TERRA), 0)
        self.sil = art.creature_panel(card, self.c, 6, silhouette=True)
        self.sil.align(lv.ALIGN.CENTER, 0, -2)
        self.heart = art.draw_sprite(card, art.HEART, {"k": 0x7A1F12, "r": 0xE0463A}, 3)
        self.heart.align(lv.ALIGN.TOP_RIGHT, -54, 8)
        self.bpm = ui.label(card, "--", 258, 8, ui.TERRA, ui.font_title(), w=46)

        ui.label(
            s,
            "draai rond om te zoeken",
            6,
            154,
            ui.INK,
            ui.font_small(),
            w=308,
            center=True,
        )

        # 5-LED mirror (emulator + redundant on-badge): cells 52x16, gap 5
        self.mirror = []
        for i in range(5):
            seg = ui.box(s, 20 + i * 57, 172, 52, 16, 0x222222, radius=2)
            seg.set_style_border_width(2, 0)
            seg.set_style_border_color(ui.hexc(ui.INK), 0)
            self.mirror.append(seg)
        ui.label(s, "koud", 20, 186, ui.GREEN_D, ui.font_small())
        ui.label(s, "warm", 252, 186, ui.TERRA, ui.font_small(), w=42, center=True)

        # player-driven: tap when you've physically found the box & read its code.
        # y=204 leaves screen margin for the focused button's 4px gold halo.
        btn = ui.box(s, 6, 204, 308, 26, ui.GREEN, radius=3)
        btn.set_style_border_width(2, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        bl = ui.label(
            btn, "VOER DE CODE IN", 0, 0, ui.CREAM, ui.font_label(), w=308, center=True
        )
        bl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=self._enter_code)

        self.setContentView(s)

    def onResume(self, screen):
        super().onResume(screen)
        RADIO.start(self.fox_id)  # restart cold on every entry / return
        self.timer = lv.timer_create(self._tick, 250, None)

    def onPause(self, screen):
        super().onPause(screen)
        if self.timer:
            self.timer.delete()
            self.timer = None
        leds.off()

    def _tick(self, t):
        if not self.has_foreground():
            return
        r = RADIO.reading(self.fox_id)
        self.bpm.set_text(str(rssi_to_bpm(r.rssi)))

        # heartbeat: nudge the heart up/down each tick so it visibly throbs
        self._beat = not self._beat
        self.heart.align(lv.ALIGN.TOP_RIGHT, -54, 6 if self._beat else 10)

        leds.show_level(r.level)  # physical LEDs (badge)
        # Restyle the mirror only when the level moved: every set_style call
        # invalidates its cell, and at 4 Hz an unchanged level would redraw
        # all five for nothing (same guard discipline as VliegActivity._drift).
        if r.level != self._mirror_level:
            self._mirror_level = r.level
            cols = leds.colors_for_level(r.level)
            for i, seg in enumerate(self.mirror):
                rr, gg, bb = cols[i]
                seg.set_style_bg_color(ui.hexc((rr << 16) | (gg << 8) | bb), 0)

    def _enter_code(self):
        if self.timer:
            self.timer.delete()
            self.timer = None
        leds.off()
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=CodeActivity, extras={"fox_id": self.fox_id})
        )


# ═════════════════════════ screen_code ═════════════════════════
# screen_code.py — PIN keypad -> validate -> win / error.
#
# Typing the code is not the end of it: the code goes to the fox network to be
# checked (a real request once the LoRa backend lands, a faked round trip
# today), and only an "ok" reveals the creature. So the screen has three
# states — typing, waiting for the verdict, and showing an error — and the
# keypad is dead while a verdict is in flight.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
from creatures import by_id
from fox_radio import RADIO
from store import accepts_debug_code

# No confirm key: the 4th digit IS the submit, so an OK would only ever fire on
# an unfinished code. "" is the hole that leaves, keeping 0 centred under 8 and
# backspace bottom-right where a keypad puts it.
KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "<"]
CODE_LEN = 4
RED = 0xD6483A  # backspace: the one key that destroys what you typed

# Status line under the panel: one entry per state the player can be in, plus
# one per verdict the radio can hand back (see FoxRadio.submit_code).
STATUS = {
    "idle": ("vul de code in", ui.TEXT_MUTED),
    "checking": ("controleren...", ui.GREEN_D),
    "wrong": ("verkeerde code", ui.TERRA_D),
    "used": ("code al gebruikt", ui.TERRA_D),
}


class CodeActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.c = by_id(self.fox_id)
        self.entry = ""
        self.waiting = False  # a verdict is in flight; the keypad is dead

        s = ui.make_screen(0xDFEEBF)
        ui.banner(s, "VOER DE CODE IN", ui.GREEN)

        kw, kh, kg = 58, 45, 6
        # 3 keys per row; +4px slack so the exact-fit 3rd column never wraps early
        pad = ui.row(s, 6, 34, 3 * kw + 2 * kg + 4, 4 * kh + 3 * kg, gap=kg, wrap=True)
        for k in KEYS:
            if not k:  # the hole where OK used to be: a spacer, not a key
                ui.box(pad, 0, 0, kw, kh, None)
                continue
            b = ui.box(pad, 0, 0, kw, kh, ui.CARD, radius=3)
            b.set_style_border_width(2, 0)
            if k == "<":
                # An icon says "wis de code" where a "<" only says "left",
                # and the red frame sets it apart from the digits at a glance.
                b.set_style_border_color(ui.hexc(RED), 0)
                art.icon(b, "backspace", 2).align(lv.ALIGN.CENTER, 0, 0)
            else:
                b.set_style_border_color(ui.hexc(ui.INK), 0)
                kl = ui.label(b, k, 0, 0, ui.INK, ui.font_title(), w=kw, center=True)
                kl.align(lv.ALIGN.CENTER, 0, 0)
            ui.focusable(b, on_click=lambda kk=k: self.press(kk))
            # LVGL delivers keys to whichever widget has focus, and on this
            # screen that is always one of these — so every key carries the
            # same handler and you can just type the code (desktop only; the
            # badge has no number keys, so it simply never fires there).
            b.add_event_cb(self._on_key, lv.EVENT.KEY, None)

        self.dots = ui.label(
            s, "____", 198, 40, ui.INK, ui.font_title(), w=116, center=True
        )
        # dark scanner panel: the white fill needs a dark ground to read against
        self.rev = ui.box(s, 214, 80, 92, 92, ui.INK, radius=2)
        self.rev.set_style_border_width(2, 0)
        self.rev.set_style_border_color(ui.hexc(ui.TERRA), 0)
        self._sprite = None
        self._draw_reveal()  # starts as a full silhouette
        self.status = ui.label(
            s, "", 198, 178, ui.TEXT_MUTED, ui.font_small(), w=116, center=True
        )
        self._set_status("idle")

        self.setContentView(s)

    def onPause(self, screen):
        super().onPause(screen)
        # A verdict that lands while we're away still banks the catch (see
        # _on_verdict) — only its theatre is dropped. Don't leave the keypad
        # locked waiting for a reply whose screen side already happened.
        self.waiting = False
        self._set_status("idle")

    def onResume(self, screen):
        super().onResume(screen)
        # State may have moved while we were away: a verdict that landed
        # mid-pause cleared the entry without touching widgets (it cannot know
        # whether they still exist). Redraw from the one source of truth.
        self.dots.set_text((self.entry + "____")[:CODE_LEN])
        self._draw_reveal()

    def _set_status(self, state):
        text, colour = STATUS[state]
        self.status.set_text(text)
        self.status.set_style_text_color(ui.hexc(colour), 0)

    def _draw_reveal(self):
        # Progress only: the shape fills in white top-down, a quarter per digit.
        # Never the real art — the creature is only unmasked on the win screen,
        # after the code is entered in full AND validated.
        if self._sprite is not None:
            self._sprite.delete()
        self._sprite = art.creature_panel(
            self.rev,
            self.c,
            4,
            reveal=len(self.entry) / CODE_LEN,
            mask=art.MASK,
            veil=art.GHOST,  # dark panel: the plain silhouette would vanish
        )
        self._sprite.align(lv.ALIGN.CENTER, 0, 0)

    def _on_key(self, e):
        """Type the code on a real keyboard instead of tapping the keys."""
        k = e.get_key()
        if 48 <= k <= 57:  # '0'..'9'
            self.press(chr(k))
        elif k == lv.KEY.BACKSPACE or k == lv.KEY.DEL:
            self.press("<")

    def press(self, k):
        if self.waiting:
            return  # keypad is dead until the network answers
        sound.play("tap")
        if k == "<":
            self.entry = ""
        elif len(self.entry) < CODE_LEN:
            self.entry += k
        self._set_status("idle")  # typing clears the last error
        self.dots.set_text((self.entry + "____")[:CODE_LEN])
        self._draw_reveal()
        if len(self.entry) == CODE_LEN:
            self._submit()

    def _submit(self):
        """Ask the fox network to validate the code; the verdict arrives later."""
        if accepts_debug_code(self.entry):
            self._on_verdict("ok")
            return
        self.waiting = True
        self._set_status("checking")
        RADIO.submit_code(self.fox_id, self.entry, self._on_verdict)

    def _on_verdict(self, result):
        self.waiting = False
        if result == "ok":
            # Bank the catch FIRST, foreground or not. The code is one-time
            # and the network burnt it the moment it said ok — a player who
            # stepped out during the round trip must not lose the beest to a
            # verdict nobody was looking at (retyping would only get "used").
            pakket = None
            if store.is_caught(self.fox_id):
                # zelf gevonden: re-finding a known creature is an upgrade,
                # not a dud (GAME_DESIGN.md) — sightings, stamp and pakket
                # instead of a re-add that would change nothing
                pakket = store.zelf_gevonden(self.fox_id)
            else:
                store.add_caught(self.fox_id)
            # The keypad resets NOW, not on return: coming back from the win
            # screen must land on an empty code, not a full one whose next
            # tap re-submits it and answers "code al gebruikt".
            self.entry = ""
            if not self.has_foreground():
                # The screen (and possibly its widgets) is gone; the catch is
                # safe above, only the theatre is skipped.
                return
            self.dots.set_text("____")
            self._draw_reveal()
            self._set_status("idle")
            # Legendary catches get their fanfare from the win screen itself
            # (celebrate.Fireworks), so it loops in sync with the visuals —
            # including on a re-find.
            if self.c["rarity"] != "leg":
                sound.play("caught")
            extras = {"fox_id": self.fox_id}
            if pakket is not None:
                extras["pakket"] = pakket
            self.startActivity(Intent(activity_class=WinActivity, extras=extras))
            return
        # wrong/used: pure feedback, nothing to bank — a late one just drops.
        if not self.has_foreground():
            return
        sound.play("error")
        self._set_status(result)
        self.entry = ""
        self.dots.set_text("____")
        self._draw_reveal()


# ═════════════════════════ screen_win ═════════════════════════
# screen_win.py — the "Gevangen!" payoff. One button: back to Home.
#
# The fuss scales with the rarity. Base: a calm card, jingle from the code
# screen. Rare: the same card plus celebrate.Stardust — twinkling stars, a
# gold glint, a soft LED breathe. Legendary: the full maximalist fireworks
# (celebrate.Fireworks): rainbow halo, confetti, flashing title, bouncing
# beast, looping fanfare and a rainbow LED chase.
#
# A `pakket` extra makes normal and rare catches the calmer ZELF GEVONDEN
# variant (GAME_DESIGN.md). A legendary remains legendary on every encounter;
# its fireworks carry the verzorgingspakket summary instead of the book line.

import lvgl as lv
import mpos.ui
from mpos import Activity
import ui
import art
from creatures import by_id
from celebrate import Fireworks, Stardust


class WinActivity(Activity):
    def onCreate(self):
        self.fox_id = self.getIntent().extras.get("fox_id", 0)
        self.pakket = self.getIntent().extras.get("pakket")  # zelf gevonden
        c = by_id(self.fox_id)
        leg = c["rarity"] == "leg"
        self.fx = None

        s = ui.make_screen(0x140A2E if leg else 0x20301C)
        if leg:
            detail = None
            if self.pakket:
                regel = "  ".join(
                    "+%d %s" % (n, f) for f, n in sorted(self.pakket.items())
                )
                detail = "zelf gevonden - pakket: " + regel
            self.fx = Fireworks(s, c, detail=detail)
            self._verder_button(s, ui.GOLD, ui.INK)
        else:
            panel = self._calm_card(s, c)
            if c["rarity"] != "norm":
                self.fx = Stardust(s, panel)

        self.setContentView(s)

    def _calm_card(self, s, c):
        panel = ui.box(s, 114, 36, 92, 92, ui.SURFACE_SOFT, radius=2)
        panel.set_style_border_width(3, 0)
        panel.set_style_border_color(ui.hexc(ui.GOLD if self.pakket else ui.GREEN_D), 0)
        sp = art.creature_panel(panel, c, 5, animate=True)
        sp.align(lv.ALIGN.CENTER, 0, 0)

        ui.label(s, c["naam"], 0, 136, ui.CREAM, ui.font_title(), w=320, center=True)
        if self.pakket:
            ui.label(
                s,
                "zelf gevonden - blij je weer te zien!",
                0,
                162,
                0xBCD0A4,
                ui.font_small(),
                w=320,
                center=True,
            )
            regel = "  ".join("+%d %s" % (n, f) for f, n in sorted(self.pakket.items()))
            ui.label(
                s,
                "verzorgingspakket: " + regel,
                0,
                180,
                ui.GOLD,
                ui.font_small(),
                w=320,
                center=True,
            )
        else:
            ui.label(
                s,
                "toegevoegd aan je boek!",
                0,
                162,
                0xBCD0A4,
                ui.font_small(),
                w=320,
                center=True,
            )
        self._verder_button(s, ui.GOLD, ui.INK)
        return panel

    def _verder_button(self, s, bg, border):
        # y=202, not flush at the bottom: the focused button wears a 4px gold
        # halo outside its box, so it needs real screen margin under it.
        btn = ui.box(s, 100, 202, 120, 26, bg, radius=3)
        btn.set_style_border_width(2, 0)
        btn.set_style_border_color(ui.hexc(border), 0)
        bl = ui.label(
            btn, "VERDER", 0, 0, 0x3A2A0C, ui.font_title(), w=120, center=True
        )
        bl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=self.go_home)

    def onResume(self, screen):
        super().onResume(screen)
        if self.fx:
            self.fx.start()

    def onPause(self, screen):
        super().onPause(screen)
        if self.fx:
            self.fx.stop()

    def go_home(self):
        # Stack is home -> hunt -> code -> win; pop the three to land on home.
        for _ in range(3):
            mpos.ui.back_screen()


# ═════════════════════════ screen_snuffel ═════════════════════════
# screen_snuffel.py — SNUFFELEN: nearby players + the VONK payoff.
#
# Layout follows the design (verzamelen.jsx PxSnuffel / PxVonk). Opening the
# screen IS the consent step: the radio leaves camp WiFi and pins the snuffel
# channel (snuffel_link), so the banner honestly says "even geen wifi". The
# idle list doubles as the visible "wil snuffelen" state.
#
# The handshake fires by itself: when a peer holds the CLOSE verdict for a
# full streak (~3 s of -50 dBm or better), both sides celebrate — the first
# side to complete claims it on the air (SNF) and the other mirrors, so the
# streaks need not line up. There is
# nothing to choose and no buttons on the payoff — food shares itself when
# the pair's cooldown allows (a vonk is a picknick, a repeat inside 4h a
# single hapje at most once an hour; inside the hour the handshake pays
# nothing), and a vonk can spark one of the other player's creatures to
# introduce itself. The same pair can snuffel again after stepping apart.
# Everything written is local, forgiving state — never public score (frames
# are unauthenticated).

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
import companion
from creatures import by_id
from snuffel_link import LINK
from screens_care import BoekjeActivity
from screens_care import BeastActivity

_ROW_TOP_BG = 0xF6E7CD  # the strongest peer's row
_AVATAR_BG = 0xCFE0EA
_VONK_BG = 0x20301C  # the payoff's night sky
_VONK_PANEL = 0x2D3D24
_VONK_TEXT = 0xE8F0D8
_VONK_MUTED = 0x9FB08A
_BAR_H = (6, 10, 14, 18)


def _bars_lit(rssi):
    """dBm -> 0..4 signal bars (same span as the pluk meter)."""
    for i, floor in enumerate((-80, -70, -60, -50)):
        if rssi < floor:
            return i
    return 4


class SnuffelActivity(Activity):
    def onCreate(self):
        self.timer = None
        self._rows = {}
        self._shown = []
        self._cooling = set()  # peers who must step away before re-snuffelling
        self._handoff = False  # True while the Vonk payoff sits on top
        s = ui.make_screen(ui.PAPER)
        ui.banner(s, "SNUFFELEN", ui.GREEN, right="even geen wifi")

        hint = ui.panel(s, 6, 32, 308, 18, ui.CREAM)
        art.icon(hint, "snuf", 1).set_pos(4, 0)
        ui.label(
            hint,
            "hou de badges tegen elkaar om te snuffelen",
            24,
            2,
            ui.INK,
            ui.font_small(),
        )

        self.rows_box = ui.box(s, 6, 56, 308, 144)
        self.empty_l = ui.label(
            s,
            "nog niemand in de buurt - wacht even",
            6,
            116,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=308,
            center=True,
        )

        boekje = ui.panel(s, 6, 204, 308, 30, ui.CARD)
        art.icon(boekje, "boek", 2).set_pos(106, 6)
        ui.label(boekje, "BOEKJE", 128, 8, ui.INK, ui.font_label())
        ui.focusable(boekje, on_click=self._boekje)

        self.setContentView(s)

    def onResume(self, screen):
        super().onResume(screen)
        p = store.profile()
        LINK.set_identity(
            p["name"],
            companion.encode(p["head"], p["accs"], p["bg"]),
            store.caught_ids(),
        )
        if not self._handoff:
            LINK.start()
        self._handoff = False
        self.timer = lv.timer_create(self._tick, 500, None)

    def onPause(self, screen):
        super().onPause(screen)
        if self.timer:
            self.timer.delete()
            self.timer = None
        # Pausing INTO the Vonk payoff keeps snuffel mode alive so the
        # return is instant; only a real exit restores WiFi.
        if not self._handoff:
            LINK.stop()

    # ── the peer list ───────────────────────────────────────────────────
    def _tick(self, t):
        if not self.has_foreground():
            return
        LINK.tick()
        peers = LINK.sorted_peers()[:4]
        macs = [p.mac for p in peers]
        if macs != self._shown:
            self._shown = macs
            self._rows = {}
            self.rows_box.clean()
            for i, p in enumerate(peers):
                self._build_row(i, p)
        for p in peers:
            refs = self._rows.get(p.mac)
            if refs:
                try:
                    self._update_row(refs, p)
                except Exception:
                    # Teardown races the timer: during the exit animation
                    # has_foreground() still answers True while the widgets
                    # are already deleted (the OS topmenu logs the same
                    # LvReferenceError in that window). Drop the tick; the
                    # timer dies with onPause a moment later.
                    return
        if self.empty_l:
            if peers:
                self.empty_l.add_flag(lv.obj.FLAG.HIDDEN)
            else:
                self.empty_l.remove_flag(lv.obj.FLAG.HIDDEN)

        # a snuffelled peer re-arms once they step out of CLOSE range —
        # holding two badges together fires exactly one handshake
        for mac in list(self._cooling):
            p = LINK.peers.get(mac)
            if p is None or not p.close:
                self._cooling.discard(mac)

        cp = LINK.close_peer()
        if cp and cp.mac not in self._cooling:
            self._cooling.add(cp.mac)
            self._snuffel(cp)

    def _build_row(self, i, p):
        row = ui.panel(
            self.rows_box, 0, i * 36, 308, 33, _ROW_TOP_BG if i == 0 else ui.CARD
        )
        head, accs, bg = companion.decode(p.code)
        ava = ui.box(row, 3, 1, 26, 26, _AVATAR_BG)
        companion.draw(ava, head, accs, 2, x=-3, y=-3)
        ui.label(row, p.naam, 38, 7, ui.INK, ui.font_label())
        pill = ui.box(row, 196, 7, 62, 15, ui.GREEN)
        pill.set_style_border_width(ui.BORDER_THIN, 0)
        pill.set_style_border_color(ui.hexc(ui.INK), 0)
        ui.label(pill, "DICHTBIJ", 0, 1, ui.CREAM, ui.font_small(), w=58, center=True)
        bars = []
        for b in range(4):
            h = _BAR_H[b]
            bar = ui.box(row, 268 + b * 8, 24 - h, 5, h, ui.DORMANT)
            bar.set_style_border_width(ui.BORDER_THIN, 0)
            bar.set_style_border_color(ui.hexc(ui.INK), 0)
            bars.append(bar)
        self._rows[p.mac] = (pill, bars)

    def _update_row(self, refs, p):
        pill, bars = refs
        if p.close:
            pill.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            pill.add_flag(lv.obj.FLAG.HIDDEN)
        lit = _bars_lit(p.rssi)
        for i, bar in enumerate(bars):
            bar.set_style_bg_color(ui.hexc(ui.GREEN if i < lit else ui.DORMANT), 0)

    # ── the payoff ──────────────────────────────────────────────────────
    def _snuffel(self, peer):
        LINK.claim(peer.mac)  # tell the peer's badge, so both sides pay out
        result = store.record_snuffel(peer.mac, peer.naam, peer.code)
        geluk = (
            store.roll_vonk_geluk(LINK.roster, peer.roster, LINK.encounter_key(peer))
            if result["vonk"]
            else None
        )
        if geluk is not None:
            store.add_caught(geluk, origin="spoor")
        if result["vonk"]:
            # the meeting goes to the server through the outbox — grants a
            # vonk-geluk creature to the durable record so a restore hands
            # it back. Queued only: this mode is OFF camp WiFi by design;
            # registrar.flush drains it once the radio is back home.
            store.enqueue_report(
                "snuffel",
                {"peer": peer.mac, "day": result["dag"], "creature_id": geluk},
            )
        sound.play("legendary" if geluk is not None else "caught")
        self._handoff = True
        self.startActivity(
            Intent(
                activity_class=VonkActivity,
                extras={
                    "naam": peer.naam,
                    "code": peer.code,
                    "vonk": result["vonk"],
                    "new_friend": result["new_friend"],
                    "dag": result["dag"],
                    "food": result["food"],
                    "amount": result["amount"],
                    "geluk": geluk,
                },
            )
        )

    def _boekje(self):
        sound.play("tap")
        self.startActivity(Intent(activity_class=BoekjeActivity))


class VonkActivity(Activity):
    """The handshake payoff. No buttons and nothing to decide: the picknick
    is already in the voorraad, the geluk creature already in the boek. Tap
    anywhere (or back) to continue; tapping the geluk panel opens the new
    creature's own page, like any boek tile would.
    The link keeps ticking underneath: the badge that finishes first must
    keep beaconing (and resending its SNF claim) while this screen is up,
    or the slower side never completes — that silence WAS the race."""

    def onCreate(self):
        self.timer = None
        x = self.getIntent().extras
        self.naam = x.get("naam", "?")
        self.geluk = x.get("geluk")
        vonk = x.get("vonk")

        s = ui.make_screen(_VONK_BG)
        # tap anywhere = verder (registered on the screen itself, so panels
        # keep their own taps and everything else falls through to this)
        s.add_flag(lv.obj.FLAG.CLICKABLE)
        s.add_event_cb(lambda e: self._done(), lv.EVENT.CLICKED, None)

        for sx, sy, sc in ((16, 44, 2), (286, 40, 1), (150, 10, 1)):
            art.icon(s, "spark", sc).set_pos(sx, sy)

        # the two maatjes, nose to nose
        p = store.profile()
        mine = ui.panel(s, 24, 12, 72, 72, _AVATAR_BG)
        companion.draw(mine, p["head"], p["accs"], 4, x=2, y=2)
        theirs = ui.panel(s, 224, 12, 72, 72, _AVATAR_BG)
        head, accs, bg = companion.decode(x.get("code", ""))
        companion.draw(theirs, head, accs, 4, x=2, y=2)
        if vonk:
            ui.label(s, "VONK!", 100, 26, ui.GOLD, ui.font_title(), w=120, center=True)
        else:
            ui.label(
                s, "HOI WEER!", 100, 20, ui.GOLD, ui.font_title(), w=120, center=True
            )
            ui.label(
                s,
                "al gesnuffeld",
                100,
                50,
                _VONK_MUTED,
                ui.font_small(),
                w=120,
                center=True,
            )
        ui.label(
            s,
            "%s + %s" % (p["name"], self.naam),
            100,
            66,
            _VONK_TEXT,
            ui.font_small(),
            w=120,
            center=True,
        )

        # the picknick: food shares itself when the pair's cooldown allows;
        # a fully cooled-down pair still celebrates, just empty-handed
        amount = x.get("amount", 0)
        fp = ui.panel(s, 8, 94, 304, 46, _VONK_PANEL, border=ui.GOLD_D)
        if amount:
            art.icon(fp, x.get("food", "bes"), 3).set_pos(12, 8)
            ui.label(
                fp,
                "+%d %s" % (amount, x.get("food", "bes")),
                52,
                4,
                _VONK_TEXT,
                ui.font_title(),
            )
            ui.label(
                fp,
                "jullie delen een picknick!" if vonk else "een hapje voor onderweg",
                52,
                28,
                _VONK_MUTED,
                ui.font_small(),
            )
            art.icon(fp, "spark", 1).set_pos(284, 16)
        else:
            ui.label(
                fp,
                "genoeg gedeeld voor nu",
                0,
                8,
                _VONK_TEXT,
                ui.font_label(),
                w=304,
                center=True,
            )
            ui.label(
                fp,
                "kom over een uurtje terug",
                0,
                26,
                _VONK_MUTED,
                ui.font_small(),
                w=304,
                center=True,
            )

        # vonk-geluk: one of THEIR creatures introduces itself
        if self.geluk is not None:
            c = by_id(self.geluk)
            gp = ui.panel(s, 8, 146, 304, 52, _VONK_PANEL, border=ui.GOLD)
            art.creature_panel(gp, c, 3, animate=True).set_pos(6, 0)
            ui.label(gp, "VONK-GELUK!", 62, 4, ui.GOLD, ui.font_label())
            ui.label(
                gp,
                "de %s van %s stelt zich voor" % (c["naam"], self.naam),
                62,
                22,
                _VONK_TEXT,
                ui.font_small(),
            )
            ui.label(
                gp, "nieuw in je boek - tik!", 62, 36, _VONK_MUTED, ui.font_small()
            )
            ui.focusable(gp, on_click=self._open_beest)

        # the boekje line
        strip = ui.box(s, 8, 204, 304, 20, None)
        strip.set_style_border_width(ui.BORDER_THIN, 0)
        strip.set_style_border_color(ui.hexc(ui.GOLD_D), 0)
        art.icon(strip, "boek", 1).set_pos(4, 5)
        ui.label(
            strip,
            (
                "%s staat nu in je vriendenboekje" % self.naam
                if x.get("new_friend")
                else "%s staat al in je boekje" % self.naam
            ),
            18,
            3,
            _VONK_TEXT,
            ui.font_small(),
        )
        ui.label(
            s,
            "tik om verder te gaan",
            0,
            227,
            _VONK_MUTED,
            ui.font_small(),
            w=320,
            center=True,
        )
        self.setContentView(s)

    def onResume(self, screen):
        super().onResume(screen)
        self.timer = lv.timer_create(lambda t: LINK.tick(), 500, None)

    def onPause(self, screen):
        super().onPause(screen)
        if self.timer:
            self.timer.delete()
            self.timer = None

    def _done(self):
        sound.play("tap")
        self.finish()

    def _open_beest(self):
        # straight into the normal creature flow: the geluk beast's page,
        # with VOER / AAI / SPEEL / DOSSIER like any caught creature
        sound.play("tap")
        self.startActivity(
            Intent(activity_class=BeastActivity, extras={"fox_id": self.geluk})
        )


# ═════════════════════════ screen_pluk ═════════════════════════
# screen_pluk.py — PLUKKEN: wifi hot/cold naar een fri3d-badge hotspot, en de
# oogst-payoff. Layout follows the design (plukken.jsx PxPluk / PxOogst).
#
# One activity, two phases (zoek / oogst) swapped with screen.clean() —
# same in-place rebuild pattern as HomeActivity.onResume, so no stacked
# screens and no leaked canvases. The meter speaks the hunt's language:
# 5 segments, koud onderaan, warm bovenaan, mirrored on the physical LEDs.

import lvgl as lv
from mpos import Activity
import ui
import art
import sound as leds  # LED helpers live in sound.py (merged for block economy)
import sound
import store
import pluk_radio
from creatures import by_id

_BG_ZOEK = 0xCFE2AD
_BG_OOGST = 0xDFEEBF
_RING = 0x9DB37A  # ring outline: the design's translucent green, flattened
_SSID_INK = 0x8A9A6A
# a rival spot must beat the one we're homing on by this much before the
# meter switches to it — without it, a field of equally-strong networks
# swaps target every sweep and the hot/cold meter is unreadable
_STICKY_DBM = 6


class PlukActivity(Activity):
    def onCreate(self):
        self.timer = None
        self._armed = False
        self._target = None
        self._harvest = None
        self._meter_level = None  # last drawn meter level; None = never drawn
        self.screen = ui.make_screen(_BG_ZOEK)
        self._build_zoek()
        self.setContentView(self.screen)

    def onResume(self, screen):
        super().onResume(screen)
        # debug switch (instellingen -> debug): pluk on ANY wifi network,
        # for walking-around tests before the camp's hotspots exist
        pluk_radio.RADIO.any_ssid = store.debug_cheat("pluk_any")
        self.timer = lv.timer_create(self._tick, 700, None)

    def onPause(self, screen):
        super().onPause(screen)
        if self.timer:
            self.timer.delete()
            self.timer = None
        pluk_radio.RADIO.stop()  # scanning hops channels; snuffelen pins one
        leds.off()

    # ── phase 1: zoeken ─────────────────────────────────────────────────
    def _build_zoek(self):
        s = self.screen
        s.set_style_bg_color(ui.hexc(_BG_ZOEK), 0)
        ui.banner(s, "PLUKKEN", ui.GREEN)
        self.right = ui.label(
            s, "wifi zoekt", 240, 8, ui.CREAM, ui.font_small(), w=72, center=True
        )

        # plukplek card: rings around the hotspot, bubble, status strip
        card = ui.panel(s, 6, 34, 224, 138, ui.SURFACE_SOFT)
        for d in (124, 90, 58):
            ring = ui.box(card, 110 - d // 2, 70 - d // 2, d, d)
            ring.set_style_radius(d // 2, 0)
            ring.set_style_border_width(ui.BORDER, 0)
            ring.set_style_border_color(ui.hexc(_RING), 0)
            ring.set_style_border_opa(90, 0)
        # the network the meter is homing on: fri3d-badge at camp, the real
        # SSID of whatever spot leads in any-wifi debug mode
        self.ssid_l = ui.label(
            card, pluk_radio.SSID, 7, 5, _SSID_INK, ui.font_small(), w=150
        )
        self.spot = art.icon(card, "hotspot", 5)
        self.spot.set_pos(85, 45)
        self.bubble_panel = ui.panel(card, 10, 24, 176, 20, ui.CREAM)
        self.bubble = ui.label(
            self.bubble_panel, "zoeken...", 5, 2, ui.INK, ui.font_small()
        )
        self.strip = ui.box(card, 0, 114, 220, 20, ui.GREEN_D)
        self.strip_l = ui.label(
            self.strip, "", 0, 3, ui.CREAM, ui.font_small(), w=220, center=True
        )

        # meter column: warm boven, koud onder — de LEDs in het echt
        ui.label(s, "WARM", 240, 34, ui.TERRA, ui.font_small(), w=74, center=True)
        self.cells = []
        for i in range(5):
            cell = ui.box(s, 256, 50 + i * 18, 42, 14, 0x222222, radius=2)
            cell.set_style_border_width(ui.BORDER, 0)
            cell.set_style_border_color(ui.hexc(ui.INK), 0)
            self.cells.append(cell)
        ui.label(s, "KOUD", 240, 140, ui.GREEN_D, ui.font_small(), w=74, center=True)
        ui.label(
            s, "= LEDs", 240, 154, ui.TEXT_MUTED, ui.font_small(), w=74, center=True
        )

        # pluk button: armed only while standing at a ready spot
        self.btn = ui.panel(s, 6, 178, 224, 30, ui.DORMANT)
        self.btn_l = ui.label(
            self.btn,
            "ZOEK EEN PLUKPLEK",
            0,
            6,
            ui.MYSTERY,
            ui.font_label(),
            w=220,
            center=True,
        )
        ui.focusable(self.btn, on_click=self._pluk)

        stat = ui.panel(s, 6, 214, 308, 22, ui.CREAM)
        art.icon(stat, "sig", 1).set_pos(6, 5)
        self.stat_l = ui.label(
            stat, "", 0, 4, ui.INK, ui.font_small(), w=304, center=True
        )
        self._update_stat()

    def _update_stat(self):
        n = store.pluk_count_today()
        self.stat_l.set_text(
            "vandaag: %d %s geplukt" % (n, "plek" if n == 1 else "plekken")
        )

    def _tick(self, t):
        if not self.has_foreground() or self._harvest is not None:
            return
        readings = pluk_radio.RADIO.scan()
        if not readings:
            self._show_none()
            return
        # one prefs read for the whole scan, not one per network
        waits = store.pluk_waits([r.bssid for r in readings])
        # prefer the strongest READY spot; only when everything nearby is
        # reloading do we show the reload story for the strongest one
        ready = [r for r in readings if waits[r.bssid] == 0]
        pool = ready or readings  # already sorted strongest-first
        target = self._sticky(pool)
        self._target = target
        self.ssid_l.set_text(target.ssid)
        self._show(target, waits[target.bssid])

    def _sticky(self, pool):
        """Keep homing on the spot we already lead with, unless it dropped
        out of the pool or something clearly beats it."""
        best = pool[0]
        held = self._target
        if held is not None:
            for r in pool:
                if r.bssid == held.bssid:
                    return r if best.rssi - r.rssi < _STICKY_DBM else best
        return best

    def _meter(self, level):
        leds.show_level(level)
        # Skip the restyle when the level is unchanged — each set_style call
        # invalidates its cell, and the tick repeats the same level far more
        # often than it changes it (same guard as VliegActivity._drift).
        if level == self._meter_level:
            return
        self._meter_level = level
        cols = leds.colors_for_level(level)
        for i, cell in enumerate(self.cells):  # top cell is the warm end
            rr, gg, bb = cols[4 - i]
            cell.set_style_bg_color(ui.hexc((rr << 16) | (gg << 8) | bb), 0)

    def _show_none(self):
        self._meter(0)
        self._arm(False)
        self.right.set_text("wifi zoekt")
        self.spot.set_style_opa(115, 0)
        self.bubble.set_text("nog geen plukplek gezien")
        self.strip.set_style_bg_color(ui.hexc(ui.GREEN_D), 0)
        self.strip_l.set_text("LOOP ROND EN ZOEK")

    def _show(self, target, wait):
        if wait > 0:
            # this spot is reloading FOR THIS BADGE — welcoming, never guilt
            self._meter(target.level)
            self._arm(False)
            self.right.set_text("plek leeg")
            self.spot.set_style_opa(115, 0)
            self.bubble.set_text("Plukplek herlaadt - kom straks terug!")
            self.strip.set_style_bg_color(ui.hexc(ui.TERRA), 0)
            self.strip_l.set_text(
                "NOG %d MIN - ZOEK EEN ANDERE PLEK" % (wait // 60 + 1)
            )
            self.btn_l.set_text("PLUKKEN KAN STRAKS WEER")
            return
        self._meter(target.level)
        self.right.set_text("wifi zoekt")
        self.spot.set_style_opa(lv.OPA.COVER, 0)
        if target.level >= pluk_radio.PLUK_LEVEL:
            self._arm(True)
            self.bubble.set_text("Hier! recht onder je neus")
            self.strip.set_style_bg_color(ui.hexc(ui.GREEN), 0)
            self.strip_l.set_text("KLAAR OM TE PLUKKEN")
        else:
            self._arm(False)
            self.bubble.set_text(
                "Warmer! bijna bij de plukplek"
                if target.level >= 2
                else "Koud - nog een eind lopen"
            )
            self.strip.set_style_bg_color(ui.hexc(ui.GREEN_D), 0)
            self.strip_l.set_text("VOLG HET SIGNAAL")
            self.btn_l.set_text("KOM DICHTERBIJ OM TE PLUKKEN")

    def _arm(self, on):
        self._armed = on
        self.btn.set_style_bg_color(ui.hexc(ui.GREEN if on else ui.DORMANT), 0)
        if on:
            self.btn_l.set_text("PLUK!")
        self.btn_l.set_style_text_color(ui.hexc(ui.CREAM if on else ui.MYSTERY), 0)

    def _pluk(self):
        if not self._armed or self._target is None:
            sound.play("error")
            return
        bssid = self._target.bssid
        oogst = pluk_radio.yield_for(bssid, store.pluk_phase())
        geluk = store.record_pluk(bssid, oogst)
        c = by_id(geluk) if geluk is not None else None
        sound.play("legendary" if c and c["rarity"] == "leg" else "caught")
        leds.off()
        self._harvest = oogst
        self.screen.clean()
        self._build_oogst(oogst, geluk)

    # ── phase 2: oogst (payoff) ─────────────────────────────────────────
    def _build_oogst(self, oogst, geluk=None):
        s = self.screen
        s.set_style_bg_color(ui.hexc(_BG_OOGST), 0)
        total = sum(oogst.values())
        ui.banner(s, "GEPLUKT!", ui.GOLD)
        ui.label(
            s, "+%d voer" % total, 240, 8, ui.CREAM, ui.font_small(), w=72, center=True
        )

        stage = ui.panel(s, 8, 34, 304, 112, ui.SURFACE_TINT)
        if geluk is not None:
            c = by_id(geluk)
            frame = {"norm": ui.GREEN, "rare": ui.TERRA, "leg": ui.GOLD}.get(
                c["rarity"], ui.GREEN
            )
            stage.set_style_border_color(ui.hexc(frame), 0)
            art.creature_panel(stage, c, 4, animate=True).set_pos(16, 18)
            art.icon(stage, "spoor", 1).set_pos(278, 10)
            ui.label(stage, "WILD SPOOR!", 98, 10, frame, ui.font_label())
            ui.label(stage, c["naam"], 98, 32, ui.INK, ui.font_title(), w=180)
            rarity = {
                "norm": "gewoon beest",
                "rare": "zeldzaam beest",
                "leg": "legendarisch beest",
            }.get(c["rarity"], "nieuw beest")
            ui.label(stage, rarity, 98, 58, ui.TEXT_MUTED, ui.font_small())
            ui.label(stage, "nieuw in je boek!", 98, 78, ui.GREEN_D, ui.font_label())
        else:
            art.icon(stage, "spark", 2).set_pos(14, 12)
            art.icon(stage, "spark", 1).set_pos(272, 20)
            ui.label(
                stage,
                "Je voorraad groeit",
                0,
                12,
                ui.GREEN_D,
                ui.font_title(),
                w=300,
                center=True,
            )
            gained = [(f, n) for f, n in oogst.items() if n > 0]
            gw = 58
            xs = 150 - (len(gained) * gw + (len(gained) - 1) * 16) // 2
            for i, (f, n) in enumerate(gained):
                x = xs + i * (gw + 16)
                art.icon(stage, f, 4).set_pos(x + 13, 44)
                ui.label(
                    stage,
                    "+%d" % n,
                    x,
                    80,
                    ui.INK,
                    ui.font_title(),
                    w=gw,
                    center=True,
                )

        v = store.voorraad()
        tiles = ui.row(s, 8, 154, 304, 42, gap=ui.GAP_M)
        for f in store.FOODS:
            tile = ui.panel(tiles, 0, 0, 97, 42, ui.CARD)
            art.icon(tile, f, 2).set_pos(22, 12)
            ui.label(tile, str(v[f]), 48, 10, ui.INK, ui.font_title())

        bw = 149
        left = ui.panel(s, 8, 202, bw, 32, ui.GREEN)
        ui.label(left, "KLAAR", 0, 8, ui.CREAM, ui.font_label(), w=bw - 4, center=True)
        ui.focusable(left, on_click=self._done)
        right = ui.panel(s, 8 + bw + 6, 202, bw, 32, ui.CARD)
        ui.label(
            right, "NOG EEN PLEK", 0, 8, ui.INK, ui.font_label(), w=bw - 4, center=True
        )
        ui.focusable(right, on_click=self._again)

    def _done(self):
        sound.play("tap")
        self.finish()

    def _again(self):
        sound.play("tap")
        self._harvest = None
        self._target = None
        self._meter_level = None  # fresh cells: the skip-cache must not match
        self.screen.clean()
        self._build_zoek()


# ═════════════════════════ screen_visitor ═════════════════════════
# screen_visitor.py — random visitor: meet the silhouette, then welcome the
# base-tier creature into the book. The schedule and pending visitor live in
# store.py; this screen only presents and claims one durable pending meeting.

import lvgl as lv
from mpos import Activity
import art
import sound
import store
import ui
from creatures import by_id

_BG = 0x2D492B
_GROUND = 0x405E35
_TEXT_SOFT = 0xC7DDAE

_TENT = (
    ".......kk.......",
    "......kaak......",
    ".....kaaaak.....",
    "....kaa..aak....",
    "...kaa....aak...",
    "..kaa......aak..",
    ".kaaaaaaaaaaaak.",
    "kaaaaaaaaaaaaaak",
    "kkkkkkkkkkkkkkkk",
)
_TENT_PAL = {"k": ui.INK, "a": ui.TERRA}


class VisitorActivity(Activity):
    def onCreate(self):
        self.fox_id = store.visitor_pending()
        self.c = by_id(self.fox_id) if self.fox_id is not None else None
        self.screen = ui.make_screen(_BG)
        # On the stack BEFORE the corrupt-state guard may finish(): finish
        # pops the top of the screen stack unconditionally, and before
        # setContentView that top is the HOME screen — the guard existed to
        # fail safely and instead threw the player out of the book.
        self.setContentView(self.screen)
        if self.c is None or self.c["rarity"] != "norm":
            self.finish()
            return
        self._build_meeting()

    def _button(self, text, on_click):
        btn = ui.panel(self.screen, 8, 198, 304, 34, ui.GREEN)
        label = ui.label(btn, text, 0, 0, ui.CREAM, ui.font_title(), w=300, center=True)
        label.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=on_click)

    def _build_meeting(self):
        s = self.screen
        s.clean()
        ui.label(
            s,
            "ER ZIT IETS IN DE STRUIKEN...",
            10,
            10,
            ui.CREAM,
            ui.font_title(),
            w=300,
        )
        ui.label(
            s,
            "Het lijkt op jou te wachten.",
            10,
            43,
            _TEXT_SOFT,
            ui.font_small(),
        )
        note = ui.box(s, 10, 62, 158, 22, 0x263F25, radius=ui.RADIUS)
        art.icon(note, "leaf", 1).set_pos(8, 7)
        ui.label(note, "het heeft geen haast", 25, 5, _TEXT_SOFT, ui.font_small())

        # Campsite at dusk: the player's tent on the left, paw prints leading
        # to the waiting silhouette on the right, hidden behind the shrub.
        ui.box(s, 0, 164, 320, 30, _GROUND)
        art.draw_sprite(s, _TENT, _TENT_PAL, 2).set_pos(18, 130)
        for x, y in ((118, 174), (150, 160)):
            art.icon(s, "spoor", 1).set_pos(x, y)
        creature = art.creature_panel(s, self.c, 5, silhouette=True)
        creature.set_pos(220, 92)
        art.icon(s, "bush", 5).set_pos(202, 122)
        for x, y in ((58, 34), (252, 24), (284, 82)):
            art.icon(s, "leaf", 1).set_pos(x, y)
        self._button("ZEG HALLO", self._reveal)

    def _reveal(self):
        cid = store.claim_visitor()
        if cid is None:
            sound.play("error")
            self.finish()
            return
        sound.play("caught")
        self._build_reveal()

    def _build_reveal(self):
        s = self.screen
        s.clean()
        s.set_style_bg_color(ui.hexc(0xCFE2AD), 0)
        ui.banner(s, "NIEUW BEZOEK", ui.GREEN)
        tier = ui.panel(s, 273, 5, 38, 17, ui.GREEN, border=ui.GREEN_D)
        ui.label(tier, "basis", 0, 3, ui.CREAM, ui.font_small(), w=34, center=True)

        card = ui.panel(s, 8, 32, 304, 120, ui.SURFACE_SOFT)
        art.icon(card, "leaf", 1).set_pos(12, 12)
        art.icon(card, "leaf", 1).set_pos(246, 78)
        art.icon(card, "bush", 2).set_pos(8, 78)
        speech = ui.panel(card, 62, 10, 48, 24, ui.CARD)
        ui.label(speech, "Prrr.", 7, 5, ui.INK, ui.font_small())
        sprite = art.creature_panel(card, self.c, 5, animate=True)
        sprite.set_pos(102, 34)
        ui.label(
            card,
            "%s WIL\nBLIJVEN!" % self.c["naam"].upper(),
            174,
            24,
            ui.GREEN_D,
            ui.font_title(),
            w=120,
            center=True,
        )

        info = ui.panel(s, 8, 158, 304, 32, ui.SURFACE_SOFT)
        art.icon(info, "boek", 1).set_pos(8, 9)
        ui.label(
            info,
            "%s - toegevoegd aan je boek!" % self.c["naam"],
            30,
            9,
            ui.INK,
            ui.font_small(),
            w=264,
        )
        self._button("VERDER", self._finish)

    def _finish(self):
        sound.play("tap")
        self.finish()
