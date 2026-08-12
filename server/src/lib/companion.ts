// The companion ("maatje") as the server sees it: a head, stacked accessories
// and a backdrop, decoded from the 8-char shortcode in players.profile_pic.
//
// PORT of com.enigmeta.foxhunt/assets/companion.py — keep the three tables below
// in sync with it. They are the whole contract between badge and server:
//
//   HEADS  order == the zero-padded, 1-based H index in the shortcode
//   ACCS   order == both the accessory bit positions AND the draw order
//   BGS    order == the 1-based C index
//
// The badge draws these as LVGL layers, the server as stacked <img>. Same
// stack, same order, so a maatje looks the same on both.
//
// BIT POSITIONS ARE APPEND-ONLY (companion.py says so at length): bit i is
// ACCS[i], so a new accessory goes at the END, where it also draws on top.
// Insert one in the middle and every shortcode already in D1 changes meaning.

export const HEADS = [
  "vos",
  "uil",
  "beer",
  "konijn",
  "varken",
  "leeuw",
  "zeemeeuw",
  "kikker",
  "zeehond",
  "pinguin",
  "ijsbeer",
  "muis",
  "eekhoorn",
  "axolotl",
];

export const ACCS = [
  "bril",
  "strik",
  "hoed",
  "bloem",
  "sjaal",
  "pet",
  "koptelefoon",
  "snor",
  "kroon",
  "sterren",
];

export const BGS = [
  "#e9f1cf",
  "#f7f0df",
  "#efe0bb",
  "#cfe0ea",
  "#f0d3d6",
  "#ded3ea",
  "#3a4a34",
];

export interface Companion {
  head: string;
  accs: string[];
  bg: string;
}

const DEFAULT: Companion = { head: HEADS[0], accs: [], bg: BGS[0] };

/**
 * "H01A003C1" -> { head: "vos", accs: ["bril", "strik"], bg: "#e9f1cf" }.
 *
 * Anything malformed or out of range falls back to the default companion —
 * the same forgiveness companion.decode() applies on the badge. A debug page
 * that renders a plain fox for a corrupt shortcode beats one that throws.
 */
export function decodeCompanion(code: string | null | undefined): Companion {
  // Read the former H1...H9 form as well as the canonical H01...H99 form so
  // existing profiles keep their companion after the format upgrade.
  const m = /^H(\d{1,2})A([0-9A-Fa-f]{3})C(\d)$/.exec(code ?? "");
  if (!m) return DEFAULT;
  const h = Number(m[1]);
  const mask = parseInt(m[2], 16);
  const c = Number(m[3]);
  return {
    head: h >= 1 && h <= HEADS.length ? HEADS[h - 1] : HEADS[0],
    accs: ACCS.filter((_, i) => mask & (1 << i)),
    bg: c >= 1 && c <= BGS.length ? BGS[c - 1] : BGS[0],
  };
}
