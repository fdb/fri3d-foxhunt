export type Bindings = {
  DB: D1Database;
  // Secrets, so absent until `wrangler secret put` — code must treat them as
  // optional and fail closed (BRIDGE_KEY) or stay open (DEBUG_KEY, opt-in).
  BRIDGE_KEY?: string;
  DEBUG_KEY?: string;
};

export interface Player {
  id: number;
  hunter_id: number | null;
  badge_id: string;
  name: string;
  profile_pic: string;
  dt_created: string;
  dt_updated: string;
  // Self-reported count of band-5 creatures (PATCH /auth/user, display only).
  bonded: number;
  // Soft delete: NULL while the account is live. A deleted account is invisible
  // to every player-facing route (restore, PATCH, /found, the scoreboard) and
  // is revived, not duplicated, when the badge registers again.
  dt_deleted: string | null;
}

export interface GameEvent {
  id: number;
  type: string;
  payload: string;
  created_at: string;
}

export interface ScoreRow {
  id: number;
  name: string;
  hunter_id: number | null;
  profile_pic: string;
  // A count, never a list: the scoreboard is public and which beesten a player
  // holds is a spoiler. See fetchScores.
  creatures_found: number;
  self_found: number;
  players_helped: number;
  score: number;
  last_found: string | null;
}
