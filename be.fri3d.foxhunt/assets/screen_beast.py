# screen_beast.py — BEEST-PAGINA: the hub for a caught creature.
#
# Portrait card with nickname on the left; Band hearts + Energie/Honger
# segment meters + found facts on the right; a 4-button action bar (VOER / AAI /
# SPEEL / DOSSIER). A finished friend (bond maxed) trades its meters for the
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
from screen_feed import FeedActivity
from screen_dossier import DossierActivity
from screen_school import SchoolActivity

# action-bar buttons: (icon, label, kind)
_ACTS = (
    ("food", "VOER", "feed"),
    ("paw", "AAI", "aaien"),
    ("ball", "SPEEL", "spelen"),
    ("book", "DOSSIER", "dossier"),
)
_SEG = (
    ("energy", "Energie", ui.GREEN),
    ("hunger", "Honger", ui.TERRA),
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
        bw = 73
        bar = ui.row(s, 6, 198, 4 * bw + 3 * 5, 36, gap=5)
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
            for i, (k, lab, col) in enumerate(_SEG):
                shown = (
                    pet.energy_segments(st[k]) if k == "energy" else pet.segments(st[k])
                )
                ui.seg_bar(g, 0, 44 + i * 22, lab, shown, col)
        ui.label(
            g,
            "gevonden " + st.get("date", "?"),
            0,
            96,
            ui.TEXT_MUTED,
            ui.font_small(),
            w=164,
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
        if kind == "feed":
            st = store.beast_state(self.fox_id)
            if st and pet.finished(st):
                # no refusal screen for a beste vriend — just the fact
                sound.play("tap")
                self._flash("hoeft niet meer te eten")
                return
            sound.play("tap")
            self.startActivity(
                Intent(activity_class=FeedActivity, extras={"fox_id": self.fox_id})
            )
        elif kind == "dossier":
            sound.play("tap")
            self.startActivity(
                Intent(activity_class=DossierActivity, extras={"fox_id": self.fox_id})
            )
        elif kind == "spelen":
            # spelen is no longer a free inline tap: it opens the
            # beestenschool, where a session costs energy and earns band
            sound.play("tap")
            self.startActivity(
                Intent(activity_class=SchoolActivity, extras={"fox_id": self.fox_id})
            )
        else:  # aaien — inline care, always free (basic affection)
            st, ok, msg = store.do_action(self.fox_id, kind)
            sound.play("tap" if ok else "error")
            self._flash(msg)
            self._refresh()

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
        # AAI, back-swipe within the 1.1s window, crash.
        if self._bubble_timer:
            self._bubble_timer.delete()
            self._bubble_timer = None
