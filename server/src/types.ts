export type Bindings = {
  DB: D1Database;
  BRIDGE_KEY: string;
};

export interface Player {
  id: number;
  hunter_id: number | null;
  badge_id: string;
  name: string;
  profile_pic: string;
  dt_created: string;
  dt_updated: string;
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
  foxes_found: number;
  last_found: string | null;
}
