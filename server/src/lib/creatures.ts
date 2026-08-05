// The beast roster, as much of it as the server needs: a creature_id in
// players_creatures is a number, and a debug page showing "7" instead of
// "Eend" is not an inspection tool.
//
// PORT of be.fri3d.foxhunt/assets/creatures.py — id, name and tier only; the
// badge keeps the codes, blurbs and art. List order is book order (base,
// rare, legendary); ids are the wire identity and do not follow it.
//
// Names, deliberately, and nothing more. The roster is a discovery for the
// player (CLAUDE.md, "Server pages"), so it lives here in the worker source
// and on an unlinked /debug route — never in static/, where a filename in
// view-source would hand it to anyone who loads the landing page.

export interface Creature {
  id: number;
  naam: string;
  rarity: "norm" | "rare" | "leg";
}

export const CREATURES: Creature[] = [
  { id: 0, naam: "Vos", rarity: "norm" },
  { id: 1, naam: "Egel", rarity: "norm" },
  { id: 2, naam: "Kat", rarity: "norm" },
  { id: 3, naam: "Axolotl", rarity: "norm" },
  { id: 4, naam: "Capybara", rarity: "norm" },
  { id: 5, naam: "Koe", rarity: "norm" },
  { id: 6, naam: "Hond", rarity: "norm" },
  { id: 7, naam: "Eend", rarity: "norm" },
  { id: 8, naam: "Kip", rarity: "norm" },
  { id: 9, naam: "Koala", rarity: "norm" },
  { id: 10, naam: "Konijn", rarity: "norm" },
  { id: 11, naam: "Varken", rarity: "norm" },
  { id: 16, naam: "Everzwaan", rarity: "rare" },
  { id: 17, naam: "Kameleeuw", rarity: "rare" },
  { id: 18, naam: "Koekoekoek", rarity: "rare" },
  { id: 19, naam: "Konijlpaard", rarity: "rare" },
  { id: 20, naam: "Slakamander", rarity: "rare" },
  { id: 21, naam: "Tijghert", rarity: "rare" },
  { id: 12, naam: "Knoricorn", rarity: "leg" },
  { id: 13, naam: "Glitch Vos", rarity: "leg" },
  { id: 14, naam: "Party Vos", rarity: "leg" },
  { id: 15, naam: "Zwarte Vos", rarity: "leg" },
];

const BY_ID = new Map(CREATURES.map((c) => [c.id, c]));

/** Unknown ids are not an error: a bridge running a newer roster can report
 *  a creature this worker has never heard of, and the catch still counts. */
export const creatureById = (id: number): Creature | undefined => BY_ID.get(id);

export const RARITY_LABEL: Record<Creature["rarity"], string> = {
  norm: "Gewoon",
  rare: "Zeldzaam",
  leg: "Legendarisch",
};
