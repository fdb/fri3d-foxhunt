// Scoring configuration — tuning values, not protocol constants
// (GAME_DESIGN.md, Scoring). Two separate boards that never mix:
//
//   jagersscore       = Σ self-found tier points
//                     + HELP_POINTS × distinct players helped with an OWN find
//   verzamelaarsscore = PLUK_POINTS × verified pluk encounters
//                     + MEET_POINTS × distinct players met with a vonk
//                     + BONDED_POINTS × band-5 creatures (bounded, self-reported)
//
// The badge mirrors these values in store.py so the profile screen predicts
// the same numbers this server puts on the board — change them together.

import type { Creature } from "./creatures";

export const SELF_FOUND_POINTS: Record<Creature["rarity"], number> = {
  norm: 100,
  rare: 300,
  leg: 800,
};
export const HELP_POINTS = 50;

export const PLUK_POINTS = 50;
export const MEET_POINTS = 25;
export const BONDED_POINTS = 100;

// The camp window fences every scored event (GAME_DESIGN.md, Buiten het
// kamp): Thursday 2026-08-13 15:00 through Sunday 2026-08-16 15:00
// Europe/Brussels, expressed once in epoch seconds, once in the ISO strings
// players_creatures timestamps compare against, and once as the three
// 15:00-to-15:00 pluk-phase labels.
export const CAMP_START_S = 1_786_626_000;
export const CAMP_END_S = CAMP_START_S + 72 * 60 * 60;
export const CAMP_START_ISO = "2026-08-13T13:00:00Z";
export const CAMP_END_ISO = "2026-08-16T13:00:00Z";
export const CAMP_PHASES = ["2026-08-13", "2026-08-14", "2026-08-15"];
