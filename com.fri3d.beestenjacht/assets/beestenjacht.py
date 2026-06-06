# beestenjacht.py — app entry. HomeActivity: the Pokedex grid (the "boek").
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

_COLS = (6, 84, 162, 240)
_ROWS = (30, 100, 170)


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
        ui.banner(s, "BEESTENJACHT", ui.GREEN,
                  right="%d/%d" % (len(caught), len(CREATURES)))

        for i, c in enumerate(CREATURES):
            x = _COLS[i % 4]
            y = _ROWS[i // 4]
            cid = c["id"]
            is_caught = cid in caught
            huntable = (cid in awake) and not is_caught

            # Only CAUGHT beasts are revealed (full art + name). Everything else
            # is a mystery silhouette — the catch is the reveal. Huntable ones
            # (transmitting right now) get an active green frame so the player
            # knows what's out there to find.
            bg = ui.CARD if (is_caught or huntable) else 0xD8C9A4
            cell = ui.box(s, x, y, 74, 66, bg, radius=2)

            if is_caught:
                rc = ui.TERRA if c["rarity"] == "rare" else ui.GOLD if c["rarity"] == "leg" else ui.GREEN_D
                cell.set_style_border_width(2, 0)
                cell.set_style_border_color(ui.hexc(rc), 0)
            elif huntable:
                cell.set_style_border_width(2, 0)
                cell.set_style_border_color(ui.hexc(ui.GREEN), 0)

            sp = art.creature_panel(cell, c, 3, silhouette=not is_caught)
            sp.align(lv.ALIGN.TOP_MID, 0, 3)

            ui.label(cell, c["naam"] if is_caught else "???", 0, 51,
                     ui.INK if is_caught else 0x8A7D5E, ui.font_small(), w=74, center=True)

            if is_caught:
                ui.label(cell, "v", 4, 2, ui.GREEN_D, ui.font_label())
            elif huntable:
                ui.focusable(cell, on_click=lambda cc=cid: self._hunt(cc))

    def _hunt(self, cid):
        sound.play("tap")
        self.startActivity(Intent(activity_class=HuntActivity, extras={"fox_id": cid}))
