// The startbeest: every player receives one base-tier creature the moment
// their account exists (GAME_DESIGN.md, "The startbeest"). The pick is
// deterministic — FNV-1a over the canonical badge_id — so re-registering can
// never reroll it, the same principle as the seeded plukken yields. The
// creature "chose the player"; the hash is just how it remembers its choice.
//
// Keep BASE_CREATURE_IDS in sync with the "norm" tier in
// be.fri3d.foxhunt/assets/creatures.py (creatures.starter_for computes the
// identical pick badge-side, so an offline registration converges on sync).
// Feed this ONLY a badge_id that went through validateBadgeId — the hash runs
// over the trimmed, lowercased form, and the badge lowercases to match.
export const BASE_CREATURE_IDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];

export function starterFor(badgeId: string): number {
  let h = 0x811c9dc5;
  for (const byte of new TextEncoder().encode(badgeId)) {
    h ^= byte;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return BASE_CREATURE_IDS[h % BASE_CREATURE_IDS.length];
}
