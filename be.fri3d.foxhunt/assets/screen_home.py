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
from screen_hunt import HuntActivity
from screen_beast import BeastActivity
from screen_profile import ProfileActivity
from screen_settings import SettingsActivity
from screen_snuffel import SnuffelActivity
from screen_pluk import PlukActivity

_CELL_W, _CELL_H, _GAP = 74, 52, 4  # boek tiles
_HAIR = 0xDCCFA9  # section hairline on paper
_NEAR_BG = 0xF6E7CD  # nearby-card fill
_SEG_OFF = 0xE4D6BC  # unlit heat segment
_RARITY_FRAME = {"rare": ui.TERRA, "leg": ui.GOLD}


class HomeActivity(Activity):
    def onCreate(self):
        self._fresh = True
        self.screen = ui.make_screen(ui.PAPER)
        self._populate()
        self.setContentView(self.screen)

    def onResume(self, screen):
        super().onResume(screen)
        # Refresh caught state in place. Do NOT call setContentView again — it
        # appends a new screen to the stack and leaks the old one (11 canvas
        # buffers!). clean() frees the previous cells before repopulating.
        if self._fresh:  # onCreate built it a moment ago
            self._fresh = False
            return
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
        # standard ring. A jager grows two more stops (snuffel + pluk with
        # count badges), so the fox row keeps its whole width and JE BOEK
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
            self._kop_btn(182, "snuf", str(store.vonk_count_today()), self._snuffel)
            self._kop_btn(227, "pluk", str(store.spots_ready_count()), self._pluk)
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
        for c in boek:
            cid = c["id"]
            is_caught = cid in caught
            huntable = (cid in awake) and not is_caught

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

    def _kop_btn(self, x, icon, count, on_click):
        """Jager header shortcut: a 42px icon panel with a gold count badge
        (today's vonken / reloaded plukplekken)."""
        s = self.screen
        btn = ui.panel(s, x, 6, 42, 40, bg=ui.CARD)
        art.icon(btn, icon, 1).align(lv.ALIGN.CENTER, 0, 4)
        badge = ui.box(btn, 24, 0, 14, 12, ui.GOLD)
        badge.set_style_border_width(ui.BORDER_THIN, 0)
        badge.set_style_border_color(ui.hexc(ui.INK), 0)
        ui.label(badge, count, 0, 0, ui.INK, ui.font_small(), w=12, center=True)
        ui.focusable(btn, on_click=on_click)

    def _nearby_row(self, s, awake, caught):
        # ── nu in de buurt: every transmitting fox, caught or not ─────────
        self._section(52, "NU IN DE BUURT", ui.TERRA)
        nearby = []
        for c in CREATURES:
            if c["id"] in awake:
                r = RADIO.reading(c["id"])
                heat = max(1, min(3, (r.level * 3 + 4) // 5))
                nearby.append((c, heat))
        # still-huntable first (the row is a hunt shortcut), warmest leading;
        # already-caught ones trail as "she's out there" sightings
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
                on_click = self._open if is_caught else self._hunt
                ui.focusable(
                    cell,
                    on_click=lambda cc=c["id"], fn=on_click: fn(cc),
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
        # unhuntable) fox row would be. Big cards with a live stat each.
        self._section(52, "OP PAD", ui.GREEN_D)
        vonken = store.vonk_count_today()
        klaar = store.spots_ready_count()
        snuf_stat = (
            "%d vonk%s vandaag" % (vonken, "" if vonken == 1 else "en")
            if vonken
            else "zoek een maatje"
        )
        pluk_stat = (
            "%d plek%s klaar" % (klaar, "" if klaar == 1 else "ken")
            if klaar
            else "ga op zoek"
        )
        for x, icon, titel, stat, col, fn in (
            (6, "snuf", "SNUFFELEN", snuf_stat, 0x8A6A2E, self._snuffel),
            (163, "pluk", "PLUKKEN", pluk_stat, ui.TEXT_MUTED, self._pluk),
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
