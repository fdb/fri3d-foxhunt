import { CREATURES } from "./creatures";

// The startbeest: every player receives one base-tier creature the moment
// their account exists (GAME_DESIGN.md, "The startbeest"). The pick is
// deterministic — FNV-1a over the canonical badge_id — so re-registering can
// never reroll it, the same principle as the seeded plukken yields. The
// creature "chose the player"; the hash is just how it remembers its choice.
//
// Derived from the roster, never hand-listed: the pick is `hash % length`, so
// a base creature added to CREATURES but not here would silently change the
// denominator only badge-side and de-converge every startbeest. The "norm"
// tier in lib/creatures.ts mirrors creatures.py (order included), which keeps
// creatures.starter_for computing the identical pick badge-side.
// Feed this ONLY a badge_id that went through validateBadgeId — the hash runs
// over the trimmed, lowercased form, and the badge lowercases to match.
export const BASE_CREATURE_IDS = CREATURES.filter(
  (c) => c.rarity === "norm",
).map((c) => c.id);

export function starterFor(badgeId: string): number {
  let h = 0x811c9dc5;
  for (const byte of new TextEncoder().encode(badgeId)) {
    h ^= byte;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return BASE_CREATURE_IDS[h % BASE_CREATURE_IDS.length];
}
