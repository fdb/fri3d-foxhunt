# screen_hello.py — the snuffeltest: the hallo-spike screen (GAME_DESIGN.md
# "Badge-to-badge radio"). While open, the badge broadcasts a hello and lists
# every badge it hears — name, heard-count and the sender's maatje decoded
# live from the shortcode, so the payload proves itself on screen.
#
# A transport test wearing a party hat, not a game mode: no RSSI gate, no
# confirm, no payloads beyond hello. Those come after two physical badges
# have actually heard each other.

import lvgl as lv
from mpos import Activity
import ui
import sound
import store
import companion
from hello_link import LINK

_LIST_BG = 0xF6E7CD  # same warm card fill as the nearby cards
_ROW_H = 36


class HelloActivity(Activity):
    def onCreate(self):
        # peer id -> {"name", "companion", "count"}; insertion-ordered so the
        # list is stable while counts tick up.
        self._heard = {}

        s = ui.make_screen(ui.PAPER)
        ui.banner(s, "SNUFFELEN", ui.GREEN, right=LINK.transport)

        # who we are on the wire: portrait + name + the shortcode we broadcast
        p = store.profile() or {"name": "Jager", "head": "vos", "accs": [], "bg": 0}
        self._me = {
            "name": p.get("name", "Jager"),
            "companion": companion.encode(
                p.get("head", "vos"), p.get("accs", []), p.get("bg", 0)
            ),
        }
        card = ui.panel(s, 6, 34, 196, 44, ui.CARD)
        portrait = ui.panel(card, 4, 4, 32, 32, bg=companion.BGS[p.get("bg", 0)])
        companion.draw(portrait, p.get("head", "vos"), p.get("accs", []), 2, x=-2, y=-2)
        ui.label(card, self._me["name"], 46, 2, ui.INK, ui.font_title())
        ui.label(card, self._me["companion"], 46, 26, ui.MYSTERY, ui.font_small())

        # ZEG HALLO: sibling of the card, never nested (joystick nav is
        # geometric — see DESIGN.md rule 6)
        btn = ui.box(s, 208, 34, 106, 44, ui.GREEN, radius=ui.RADIUS)
        btn.set_style_border_width(ui.BORDER, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        bl = ui.label(
            btn, "ZEG HALLO", 0, 0, ui.CREAM, ui.font_small(), w=102, center=True
        )
        bl.align(lv.ALIGN.CENTER, 0, 0)
        ui.focusable(btn, on_click=self._say_hello)
        # LVGL hands keys to the focused widget (see screen_code): on desktop
        # H injects a fake passer-by; on the badge there are no letter keys,
        # and the real link has no simulate_hello, so this never fires there.
        btn.add_event_cb(self._on_key, lv.EVENT.KEY, None)

        ui.label(s, "GEHOORD", 6, 90, ui.TERRA, ui.font_small())
        self._count = ui.label(s, "0", 274, 90, ui.MYSTERY, ui.font_small(), w=40)
        self._count.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)

        self._list = ui.panel(s, 6, 104, 308, 112, _LIST_BG)
        self._list.add_flag(lv.obj.FLAG.SCROLLABLE)
        self._list.set_scroll_dir(lv.DIR.VER)
        self._list.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        self._list.set_style_pad_all(4, 0)
        self._list.set_style_pad_row(ui.GAP_S, 0)

        hint = (
            "H of ZEG HALLO = fake hallo"
            if hasattr(LINK, "simulate_hello")
            else "open dit scherm op allebei de badges"
        )
        ui.label(s, hint, 6, 222, ui.TEXT_MUTED, ui.font_small())

        self._paint_list()
        self.setContentView(s)

    # listen only while we're the foreground screen: the radio (or the fake)
    # runs between onResume and onPause, like the hunt's polling
    def onResume(self, screen):
        super().onResume(screen)
        LINK.start(self._me, self._on_hello)

    def onPause(self, screen):
        super().onPause(screen)
        LINK.stop()

    def _say_hello(self):
        sound.play("tap")
        LINK.say_hello()

    def _on_key(self, e):
        if e.get_key() in (ord("h"), ord("H")) and hasattr(LINK, "simulate_hello"):
            LINK.simulate_hello()

    def _on_hello(self, peer):
        known = self._heard.get(peer["id"])
        if known:
            known["count"] += 1
            known["name"] = peer["name"]  # a re-registered neighbour renames
            known["companion"] = peer["companion"]
        else:
            self._heard[peer["id"]] = {
                "name": peer["name"],
                "companion": peer["companion"],
                "count": 1,
            }
            sound.play("warmer")  # a NEW badge in range is the delight moment
        self._paint_list()

    def _paint_list(self):
        self._list.clean()
        self._count.set_text(str(len(self._heard)))
        if not self._heard:
            ui.label(
                self._list,
                "nog niemand gehoord...",
                4,
                4,
                ui.TEXT_MUTED,
                ui.font_small(),
            )
            return
        for peer in self._heard.values():
            row = ui.box(self._list, 0, 0, 292, _ROW_H, ui.CARD, radius=ui.RADIUS)
            row.set_style_border_width(ui.BORDER_THIN, 0)
            row.set_style_border_color(ui.hexc(ui.BORDER_REST), 0)
            head, accs, bg = companion.decode(peer["companion"])
            portrait = ui.panel(row, 2, 2, 32, 32, bg=companion.BGS[bg])
            companion.draw(portrait, head, accs, 2, x=-2, y=-2)
            ui.label(row, peer["name"] or "Jager", 42, 10, ui.INK, ui.font_small())
            cl = ui.label(
                row, "%dx" % peer["count"], 248, 10, ui.MYSTERY, ui.font_small(), w=40
            )
            cl.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)
