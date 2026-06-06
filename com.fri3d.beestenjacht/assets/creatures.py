# creatures.py — the beast roster. Pure data, no LVGL, runs anywhere.
#
# rarity : "norm" | "rare" | "leg"
# shape  : key into art.SH (fox / owl / deer / bird) — placeholder art
# pal    : key into art.PALS (recolour)
# code   : 4-digit code on the physical fox (checked offline for now)
# beacon : LoRa beacon id the real radio backend will key on
#
# Art is NOT final — swapping it later means editing art.SH/PALS or pointing
# art.creature_sprite() at real images. Nothing else in the app cares.

CREATURES = [
    {"id": 0,  "naam": "Vos",         "rarity": "norm", "shape": "fox",  "pal": "orange",   "code": "1234", "beacon": 0},
    {"id": 1,  "naam": "Egel",        "rarity": "norm", "shape": "owl",  "pal": "brown",    "code": "2345", "beacon": 1},
    {"id": 2,  "naam": "Uil",         "rarity": "norm", "shape": "owl",  "pal": "grey",     "code": "3456", "beacon": 2},
    {"id": 3,  "naam": "Everzwaan",   "rarity": "rare", "shape": "bird", "pal": "cream",    "code": "7391", "beacon": 3},
    {"id": 4,  "naam": "Kameleeuw",   "rarity": "rare", "shape": "deer", "pal": "green",    "code": "4567", "beacon": 4},
    {"id": 5,  "naam": "Tijghert",    "rarity": "rare", "shape": "deer", "pal": "orange",   "code": "5678", "beacon": 5},
    {"id": 6,  "naam": "Konijlpaard", "rarity": "rare", "shape": "deer", "pal": "tan",      "code": "6789", "beacon": 6},
    {"id": 7,  "naam": "Giraptor",    "rarity": "rare", "shape": "bird", "pal": "green",    "code": "7890", "beacon": 7},
    {"id": 8,  "naam": "Koekoekoek",  "rarity": "rare", "shape": "bird", "pal": "brown",    "code": "8901", "beacon": 8},
    {"id": 9,  "naam": "Schaapegaai", "rarity": "rare", "shape": "owl",  "pal": "bluegrey", "code": "9012", "beacon": 9},
    {"id": 10, "naam": "Kat",         "rarity": "norm", "shape": "fox",  "pal": "grey",     "code": "0123", "beacon": 10},
    {"id": 11, "naam": "Paauwpegaai", "rarity": "leg",  "shape": "bird", "pal": "gold",     "code": "1111", "beacon": 11},
]


def by_id(cid):
    for c in CREATURES:
        if c["id"] == cid:
            return c
    return None
