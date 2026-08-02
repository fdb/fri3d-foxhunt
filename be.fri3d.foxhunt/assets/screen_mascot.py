# screen_mascot.py — onboarding 2/3: build your maatje.
#
# Live preview on the left, three tabs on the right (KOP / EXTRA / KLEUR) over
# one shared tile grid (design: mascotte.jsx). Most accessories are locked
# until enough creatures are caught — at registration that is all of them
# except bril + snor, which is the point: the avatar grows with the hunt.
# REGISTREER saves the profile locally and hands off to the send screen.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import sound
import store
import mascot
import registrar
from screen_reg_send import RegSendActivity

LOCKED_BG = 0xE0D6BD
LOCKED_TX = 0x5C4F38
_GRID_X, _GRID_Y, _GRID_W = 128, 62, 184
_TILE_W = 42


class MascotActivity(Activity):
    def onCreate(self):
        self.name = self.getIntent().extras.get("name", "Jager")
        self.head = "vos"
        self.accs = []
        self.bg = 0
        self.tab = 0
        caught = store.caught_ids()
        self._caught_n = len(caught)
        self._has_leg = False  # a legendary catch unlocks "sterren"
        from creatures import by_id

        for cid in caught:
            c = by_id(cid)
            if c and c["rarity"] == "leg":
                self._has_leg = True

        s = ui.make_screen(ui.PAPER)
        self.screen = s
        ui.banner(s, "MAAK JE MAATJE", ui.GREEN, right="2/3")

        # live preview: the maatje on its backdrop, name plate underneath
        self.preview = ui.panel(s, ui.PAD, 32, 112, 170, bg=mascot.BGS[self.bg])
        plate = ui.box(self.preview, 0, 148, 108, 18, ui.GREEN)
        ui.label(plate, self.name, 0, 2, ui.CREAM, ui.font_small(), w=108, center=True)
        self._mascot = None
        self._draw_preview()

        # tabs
        self.tabs = []
        tabrow = ui.row(s, _GRID_X, 32, _GRID_W, 24, gap=5)
        for i, t in enumerate(("KOP", "EXTRA", "KLEUR")):
            b = ui.box(tabrow, 0, 0, 58, 24, ui.CARD, radius=ui.RADIUS)
            b.set_style_border_width(ui.BORDER, 0)
            lbl = ui.label(b, t, 0, 3, ui.INK, ui.font_small(), w=54, center=True)
            ui.focusable(b, on_click=lambda ii=i: self._switch_tab(ii))
            self.tabs.append((b, lbl))
        self._style_tabs()

        self._grid = None
        self._hint = None
        self._build_tab()

        btn = ui.box(s, ui.PAD, 208, 304, 26, ui.GREEN, radius=ui.RADIUS)
        btn.set_style_border_width(ui.BORDER, 0)
        btn.set_style_border_color(ui.hexc(ui.INK), 0)
        ui.label(btn, "REGISTREER", 0, 0, ui.CREAM, ui.font_title(), w=300, center=True)
        ui.focusable(btn, on_click=self._register)

        self.setContentView(s)

    # ---- preview ----------------------------------------------------------
    def _draw_preview(self):
        if self._mascot is not None:
            self._mascot.delete()
        self.preview.set_style_bg_color(ui.hexc(mascot.BGS[self.bg]), 0)
        self._mascot = mascot.draw(self.preview, self.head, self.accs, 6, x=6, y=24)

    # ---- tabs -------------------------------------------------------------
    def _style_tabs(self):
        for i, (b, lbl) in enumerate(self.tabs):
            on = i == self.tab
            b.set_style_bg_color(ui.hexc(ui.GREEN if on else ui.CARD), 0)
            b.set_style_border_color(ui.hexc(ui.INK), 0)
            lbl.set_style_text_color(ui.hexc(ui.CREAM if on else ui.INK), 0)

    def _switch_tab(self, i):
        if i == self.tab:
            return
        sound.play("tap")
        self.tab = i
        self._style_tabs()
        self._build_tab()

    def _clear_grid(self):
        if self._grid is not None:
            self._grid.delete()
            self._grid = None
        if self._hint is not None:
            self._hint.delete()
            self._hint = None

    def _build_tab(self):
        self._clear_grid()
        if self.tab == 0:
            self._build_heads()
        elif self.tab == 1:
            self._build_accs()
        else:
            self._build_colors()

    # ---- KOP --------------------------------------------------------------
    def _build_heads(self):
        th = 46
        self._grid = ui.row(
            self.screen, _GRID_X, _GRID_Y, _GRID_W, 2 * th + 5, gap=5, wrap=True
        )
        for h in mascot.HEADS:
            on = h["id"] == self.head
            cell = self._tile(th, on)
            spr = art.draw_sprite(cell, mascot.head_rows(h), mascot.head_pal(h), 2)
            spr.set_pos(3, 0)
            ui.label(
                cell,
                h["naam"],
                0,
                31,
                ui.GREEN_D if on else ui.MYSTERY,
                ui.font_small(),
                w=38,
                center=True,
            )
            ui.focusable(
                cell,
                on_click=lambda hid=h["id"]: self._pick_head(hid),
                focus_border=True,
            )

    def _pick_head(self, hid):
        sound.play("tap")
        self.head = hid
        self._draw_preview()
        self._build_tab()

    # ---- EXTRA ------------------------------------------------------------
    def _build_accs(self):
        th = 38
        self._grid = ui.row(
            self.screen, _GRID_X, _GRID_Y, _GRID_W, 3 * th + 2 * 5, gap=5, wrap=True
        )
        for a in mascot.ACCS:
            on = a["id"] in self.accs or (a["id"] == "geen" and not self.accs)
            locked = not mascot.is_unlocked(a, self._caught_n, self._has_leg)
            cell = self._tile(th, on, bg=LOCKED_BG if locked else None)
            if "rows" in a:
                rows = mascot.crop(a["rows"])
                w, h = len(rows[0]), len(rows)
                scale = min(3, max(1, min(36 // w, 20 // h)))
                spr = art.draw_sprite(cell, rows, a["pal"], scale)
                spr.set_pos((38 - w * scale) // 2, max(0, (22 - h * scale) // 2))
                if locked:
                    spr.set_style_opa(97, 0)  # ~38%: visible, clearly not yours yet
            else:
                dash = ui.label(cell, "-", 0, 2, ui.MYSTERY, ui.font_small(), w=38)
                dash.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
            if locked:
                art.icon(cell, "lock", 1).set_pos(29, 1)
            ui.label(
                cell,
                a["naam"],
                0,
                23,
                LOCKED_TX if locked else (ui.GREEN_D if on else ui.MYSTERY),
                ui.font_small(),
                w=38,
                center=True,
            )
            ui.focusable(
                cell,
                on_click=lambda aa=a["id"], ll=locked: self._pick_acc(aa, ll),
                focus_border=True,
            )
        self._hint = ui.label(
            self.screen,
            "speel vrij door beesten te vinden",
            _GRID_X,
            _GRID_Y + 3 * th + 2 * 5 + 4,
            ui.TEXT_MUTED,
            ui.font_small(),
        )

    def _pick_acc(self, aid, locked):
        if locked:
            sound.play("error")
            return
        sound.play("tap")
        if aid == "geen":
            self.accs = []
        elif aid in self.accs:
            self.accs.remove(aid)
        else:
            self.accs.append(aid)
        self._draw_preview()
        self._build_tab()

    # ---- KLEUR ------------------------------------------------------------
    def _build_colors(self):
        th = 41
        self._grid = ui.row(
            self.screen, _GRID_X, _GRID_Y, _GRID_W, 2 * th + 5, gap=5, wrap=True
        )
        for i, c in enumerate(mascot.BGS):
            on = i == self.bg
            cell = self._tile(th, on, bg=c)
            if on:
                dark_swatch = i == len(mascot.BGS) - 1
                ic = art.icon(cell, "check_light" if dark_swatch else "check", 2)
                ic.align(lv.ALIGN.CENTER, 0, 0)
            ui.focusable(
                cell, on_click=lambda ii=i: self._pick_bg(ii), focus_border=True
            )
        self._hint = ui.label(
            self.screen,
            "tik of kies met de pijltjes",
            _GRID_X,
            _GRID_Y + 2 * th + 5 + 4,
            ui.TEXT_MUTED,
            ui.font_small(),
        )

    def _pick_bg(self, i):
        sound.play("tap")
        self.bg = i
        self._draw_preview()
        self._build_tab()

    # ---- shared tile ------------------------------------------------------
    def _tile(self, h, selected, bg=None):
        """A grid cell in the quiet-frame-at-rest style of the home grid;
        selection shows as a green frame on a pale green fill."""
        if bg is None:
            bg = ui.SURFACE_SOFT if selected else ui.CARD
        cell = ui.box(self._grid, 0, 0, _TILE_W, h, bg, radius=ui.RADIUS)
        cell.set_style_border_width(ui.BORDER, 0)
        cell.set_style_border_color(
            ui.hexc(ui.GREEN if selected else ui.BORDER_REST), 0
        )
        return cell

    # ---- REGISTREER -------------------------------------------------------
    def _register(self):
        sound.play("tap")
        # Save first: whatever the network does, the profile is on the badge.
        store.save_profile(
            {
                "name": self.name,
                "head": self.head,
                "accs": self.accs,
                "bg": self.bg,
                "badge_id": registrar.badge_id(),
                "hunter_id": None,
                "synced": False,
            }
        )
        self.startActivityForResult(
            Intent(activity_class=RegSendActivity), self._child_done
        )

    def _child_done(self, result):
        if result and result.get("result_code") == "registered":
            self.setResult("registered")
            self.finish()
