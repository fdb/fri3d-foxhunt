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
from pluk_radio import RADIO

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
        RADIO.any_ssid = store.debug_cheat("pluk_any")
        self.timer = lv.timer_create(self._tick, 700, None)

    def onPause(self, screen):
        super().onPause(screen)
        if self.timer:
            self.timer.delete()
            self.timer = None
        RADIO.stop()  # scanning hops channels; snuffelen pins one
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
        readings = RADIO.scan()
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
