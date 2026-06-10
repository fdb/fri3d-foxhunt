# foxhunt.py — app entry. HomeActivity: the Pokedex grid (the "boek").
#
# Loaded by MicroPythonOS via MANIFEST.JSON (classname HomeActivity). The
# assets/ dir is on sys.path, so the flat `import ui`, `import art`, etc. work.

import lvgl as lv
from mpos import Activity, Intent
import ui
import art
import store
import sound
from creatures import CREATURES
from fox_radio import RADIO
from screen_hunt import HuntActivity
from screen_beast import BeastActivity

_CELL_W, _CELL_H, _GAP = 74, 66, 4


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
        if self._fresh:
            self._fresh = False
            return
        self.screen.clean()
        self._populate()

    def _populate(self):
        s = self.screen
        awake = set(RADIO.active_foxes())
        caught = set(store.caught_ids())
        ui.banner(s, "FOXHUNT", ui.GREEN, right="%d/%d" % (len(caught), len(CREATURES)))

        # 4 cells per row; +2px slack so the exact-fit 4th column never wraps early
        grid = ui.row(
            s,
            6,
            30,
            4 * _CELL_W + 3 * _GAP + 2,
            3 * _CELL_H + 2 * _GAP,
            gap=_GAP,
            wrap=True,
        )
        for c in CREATURES:
            cid = c["id"]
            is_caught = cid in caught
            huntable = (cid in awake) and not is_caught

            # Only CAUGHT beasts are revealed (full art + name). Everything else
            # is a mystery silhouette — the catch is the reveal. Huntable ones
            # (transmitting right now) get an active green frame so the player
            # knows what's out there to find.
            bg = ui.CARD if (is_caught or huntable) else ui.DORMANT
            cell = ui.box(grid, 0, 0, _CELL_W, _CELL_H, bg, radius=2)

            # Every cell reserves a BORDER-wide border so the gold focus border
            # (same width) only recolours — never resizes the box and nudges the
            # contents. Resting colour signals state; dormant blends into its
            # own bg, invisible until focus recolours it gold.
            if is_caught:
                rc = (
                    ui.TERRA
                    if c["rarity"] == "rare"
                    else ui.GOLD
                    if c["rarity"] == "leg"
                    else ui.GREEN_D
                )
            elif huntable:
                rc = ui.GREEN
            else:
                rc = bg
            cell.set_style_border_width(ui.BORDER, 0)
            cell.set_style_border_color(ui.hexc(rc), 0)

            sp = art.creature_panel(cell, c, 3, silhouette=not is_caught)
            sp.align(lv.ALIGN.TOP_MID, 0, 3)

            ui.label(
                cell,
                c["naam"] if is_caught else "???",
                0,
                51,
                ui.INK if is_caught else ui.MYSTERY,
                ui.font_small(),
                w=_CELL_W,
                center=True,
            )

            # Every tile is navigable (arrows/click) so the grid never goes
            # dead: caught -> companion page, huntable -> the hunt, dormant ->
            # selectable but inert (still sleeping).
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

    def _hunt(self, cid):
        sound.play("tap")
        self.startActivity(Intent(activity_class=HuntActivity, extras={"fox_id": cid}))

    def _open(self, cid):
        sound.play("tap")
        self.startActivity(Intent(activity_class=BeastActivity, extras={"fox_id": cid}))
