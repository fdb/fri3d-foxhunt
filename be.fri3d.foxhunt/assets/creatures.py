# creatures.py — the beast roster. Pure data, no LVGL, runs anywhere.
#
# rarity  : "norm" | "rare" | "leg"
# shape   : key into art.SH (fox / owl / deer / bird) — placeholder art
# pal     : key into art.PALS (recolour)
# code    : 4-digit code on the physical fox (checked offline for now)
# beacon  : LoRa beacon id the real radio backend will key on
# soort   : dossier "species" blurb
# biotoop : dossier habitat
# favoriet: favourite food ("bes" | "noot" | "eikel") — feeding it grants +band
# weetje  : a fun fact shown on the dossier
#
# Art is NOT final — swapping it later means editing art.SH/PALS or pointing
# art.creature_panel() at real images. Nothing else in the app cares.

CREATURES = [
    {"id": 0,  "naam": "Vos",         "rarity": "norm", "shape": "fox",  "pal": "orange",   "code": "1234", "beacon": 0,  "img": "vos.png",
     "soort": "Sluiper",  "biotoop": "Beukenbos", "favoriet": "bes",   "weetje": "De Vos jaagt het liefst in de schemering."},
    {"id": 1,  "naam": "Egel",        "rarity": "norm", "shape": "owl",  "pal": "brown",    "code": "2345", "beacon": 1,  "img": "egel.png",
     "soort": "Snuffelaar","biotoop": "Heggen",   "favoriet": "eikel", "weetje": "De Egel rolt zich op als hij schrikt."},
    {"id": 2,  "naam": "Uil",         "rarity": "norm", "shape": "owl",  "pal": "grey",     "code": "3456", "beacon": 2,
     "soort": "Nachtwacht","biotoop": "Oud bos",  "favoriet": "noot",  "weetje": "De Uil draait z'n kop bijna helemaal rond."},
    {"id": 3,  "naam": "Everzwaan",   "rarity": "rare", "shape": "bird", "pal": "cream",    "code": "7391", "beacon": 3,
     "soort": "Plonzer",  "biotoop": "Moeras",    "favoriet": "bes",   "weetje": "De Everzwaan poetst z'n veren met modder."},
    {"id": 4,  "naam": "Kameleeuw",   "rarity": "rare", "shape": "deer", "pal": "green",    "code": "4567", "beacon": 4,
     "soort": "Kleurling","biotoop": "Varens",    "favoriet": "bes",   "weetje": "De Kameleeuw verkleurt als hij blij is."},
    {"id": 5,  "naam": "Tijghert",    "rarity": "rare", "shape": "deer", "pal": "orange",   "code": "5678", "beacon": 5,
     "soort": "Renner",   "biotoop": "Open plek", "favoriet": "eikel", "weetje": "Het Tijghert rent sneller dan de wind."},
    {"id": 6,  "naam": "Konijlpaard", "rarity": "rare", "shape": "deer", "pal": "tan",      "code": "6789", "beacon": 6,
     "soort": "Springer", "biotoop": "Weide",     "favoriet": "noot",  "weetje": "Het Konijlpaard springt over hoge struiken."},
    {"id": 7,  "naam": "Giraptor",    "rarity": "rare", "shape": "bird", "pal": "green",    "code": "7890", "beacon": 7,
     "soort": "Spurter",  "biotoop": "Hoog gras", "favoriet": "bes",   "weetje": "De Giraptor pikt vruchten uit de hoogste takken."},
    {"id": 8,  "naam": "Koekoekoek",  "rarity": "rare", "shape": "bird", "pal": "brown",    "code": "8901", "beacon": 8,
     "soort": "Roeper",   "biotoop": "Loofbos",   "favoriet": "noot",  "weetje": "De Koekoekoek roept z'n eigen naam."},
    {"id": 9,  "naam": "Schaapegaai", "rarity": "rare", "shape": "owl",  "pal": "bluegrey", "code": "9012", "beacon": 9,
     "soort": "Kletser",  "biotoop": "Naaldbos",  "favoriet": "eikel", "weetje": "De Schaapegaai praat andere dieren na."},
    {"id": 10, "naam": "Kat",         "rarity": "norm", "shape": "fox",  "pal": "grey",     "code": "0123", "beacon": 10, "img": "kat.png",
     "soort": "Sluiper",  "biotoop": "Schuur",    "favoriet": "bes",   "weetje": "De Kat slaapt het liefst in de zon."},
    {"id": 11, "naam": "Paauwpegaai", "rarity": "leg",  "shape": "bird", "pal": "gold",     "code": "1111", "beacon": 11,
     "soort": "Pronker",  "biotoop": "Open plek", "favoriet": "bes",   "weetje": "De Paauwpegaai toont z'n staart enkel bij volle maan."},
]


def by_id(cid):
    for c in CREATURES:
        if c["id"] == cid:
            return c
    return None
