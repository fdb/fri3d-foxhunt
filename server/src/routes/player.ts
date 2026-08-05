import { Hono } from "hono";
import type { Bindings, Player } from "../types";
import { logEvent } from "../lib/events";
import { validateBadgeId, validateHunterId } from "../lib/validate";
import { CREATURES } from "../lib/creatures";

export const playerRoutes = new Hono<{ Bindings: Bindings }>();

const SPREADABLE = new Set(
  CREATURES.filter((c) => c.rarity !== "leg").map((c) => c.id),
);

// POST /api/v1/player/found
// Sent by the LoRa bridge relay (not the badge), authenticated with the
// pre-shared BRIDGE_KEY. Body: { hunter_id, fox_id }
//
// fox_id is CHAR — the creature's character code — NOT the FID byte it rides
// in on (FID = CHAR << 3 | SEQ, spec §2.1). A relay must send FID >> 3; the
// raw byte silently credits the wrong creature for CHAR 0-3. See server/README.
playerRoutes.post("/found", async (c) => {
  const auth = c.req.header("Authorization") ?? "";
  const bridged = auth === `Bearer ${c.env.BRIDGE_KEY}`;

  let body: Record<string, unknown>;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid JSON body" }, 400);
  }

  const foxId = body.fox_id;
  if (
    typeof foxId !== "number" ||
    !Number.isInteger(foxId) ||
    foxId < 0 ||
    foxId > 31
  )
    return c.json({ error: "invalid fox_id (integer 0-31)" }, 400);

  if (!bridged && foxId !== 13) {
    return c.json({ error: "unauthorized" }, 401);
  }

  let player: Player | null;
  if (bridged) {
    const hunterId = validateHunterId(body.hunter_id);
    if (hunterId === null || hunterId === "invalid")
      return c.json({ error: "invalid hunter_id (integer 1-9999)" }, 400);
    // dt_deleted IS NULL: a wiped account keeps its row (auth.ts, DELETE
    // /user), and the bridge may still hold its HID for a while. A find must
    // not resurrect it — nor land on the next player, who will mint a new HID.
    player = await c.env.DB.prepare(
      "SELECT * FROM players WHERE hunter_id = ? AND dt_deleted IS NULL",
    )
      .bind(hunterId)
      .first<Player>();
    if (!player) return c.json({ error: "unknown hunter_id" }, 404);
  } else {
    const badgeId = validateBadgeId(body.badge_id);
    if (!badgeId) return c.json({ error: "invalid badge_id" }, 400);
    player = await c.env.DB.prepare(
      "SELECT * FROM players WHERE badge_id = ? AND dt_deleted IS NULL",
    )
      .bind(badgeId)
      .first<Player>();
    if (!player) return c.json({ error: "unknown badge_id" }, 404);
  }

  const result = await c.env.DB.prepare(
    "INSERT OR IGNORE INTO players_creatures (player_id, creature_id) VALUES (?, ?)",
  )
    .bind(player.id, foxId)
    .run();
  const duplicate = result.meta.changes === 0;

  if (!duplicate) {
    await logEvent(c.env.DB, "fox_found", {
      player_id: player.id,
      hunter_id: player.hunter_id,
      fox_id: foxId,
    });
  }

  return c.json({ ok: true, player_id: player.id, fox_id: foxId, duplicate });
});

// POST /api/v1/player/snuffel
// Sent by the BADGE (through its report outbox), unauthenticated. Body:
// { badge_id, peer, day, creature_id? }. The badge reports a MEETING, never
// a catch: a single-sided report is enough to store the vonk-geluk creature
// — grants are generous, because a child must never lose a beest to a
// friend's dead battery — but it is rate-limited (one row per player, peer
// and day) and rarity-capped at the spreadable tiers. Vonk SCORE, when
// built, corroborates the pair's two rows and applies the camp window; a
// forged report mints at most a common creature on the forger's own profile
// and no points (GAME_DESIGN.md, "How a creature reaches the profile").
playerRoutes.post("/snuffel", async (c) => {
  let body: Record<string, unknown>;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid JSON body" }, 400);
  }

  const badgeId = validateBadgeId(body.badge_id);
  if (!badgeId) return c.json({ error: "invalid badge_id" }, 400);

  // The peer is the other badge's MAC — same alphabet as a badge_id.
  const peer = validateBadgeId(body.peer);
  if (!peer) return c.json({ error: "invalid peer" }, 400);
  if (peer === badgeId) return c.json({ error: "peer is self" }, 400);

  const day = typeof body.day === "string" ? body.day : "";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day))
    return c.json({ error: "invalid day (YYYY-MM-DD)" }, 400);

  let creatureId: number | null = null;
  if (body.creature_id !== undefined && body.creature_id !== null) {
    if (
      typeof body.creature_id !== "number" ||
      !Number.isInteger(body.creature_id) ||
      !SPREADABLE.has(body.creature_id)
    )
      return c.json({ error: "invalid creature_id (spreadable tiers)" }, 400);
    creatureId = body.creature_id;
  }

  const player = await c.env.DB.prepare(
    "SELECT * FROM players WHERE badge_id = ? AND dt_deleted IS NULL",
  )
    .bind(badgeId)
    .first<Player>();
  if (!player) return c.json({ error: "unknown badge_id" }, 404);

  const result = await c.env.DB.prepare(
    "INSERT OR IGNORE INTO snuffels (player_id, peer, day, creature_id) VALUES (?, ?, ?, ?)",
  )
    .bind(player.id, peer, day, creatureId)
    .run();
  const duplicate = result.meta.changes === 0;

  // The grant: the vonk-geluk creature reaches the durable record, so a
  // restore hands it back. Rides the meeting's dedupe — a duplicate report
  // grants nothing new (INSERT OR IGNORE covers the re-send race anyway).
  let granted = false;
  if (creatureId !== null && !duplicate) {
    const grant = await c.env.DB.prepare(
      "INSERT OR IGNORE INTO players_creatures (player_id, creature_id) VALUES (?, ?)",
    )
      .bind(player.id, creatureId)
      .run();
    granted = grant.meta.changes > 0;
  }

  if (!duplicate) {
    await logEvent(c.env.DB, "snuffel_reported", {
      player_id: player.id,
      peer,
      day,
      creature_id: creatureId,
      granted,
    });
  }

  return c.json({ ok: true, duplicate, granted });
});
