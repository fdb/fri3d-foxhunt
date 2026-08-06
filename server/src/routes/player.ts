import { Hono } from "hono";
import type { Bindings, Player } from "../types";
import { logEvent } from "../lib/events";
import { validateBadgeId, validateHunterId } from "../lib/validate";
import { CREATURES } from "../lib/creatures";

export const playerRoutes = new Hono<{ Bindings: Bindings }>();

const SPREADABLE = new Set(
  CREATURES.filter((c) => c.rarity !== "leg").map((c) => c.id),
);
const KNOWN_CREATURES = new Set(CREATURES.map((c) => c.id));
const BASE_CREATURES = new Set(
  CREATURES.filter((c) => c.rarity === "norm").map((c) => c.id),
);

// Server-owned bounds on the unauthenticated grant routes. The badge's own
// rate limits (per-pair cooldowns, one roll per spot per phase) all key on
// caller-supplied strings, so on their own they bound nothing: a curl loop
// with 22 invented BSSIDs once walked an account to the full roster — the
// exact quantity the public scoreboard ranks on. The server cannot verify a
// BSSID or a meeting, but it owns two things the caller does not: the clock
// and the count. So a grant must be reported near the day it claims to have
// happened (the outbox drains at every home resume, so honest reports arrive
// within hours), and each route grants at most what a very diligent honest
// player could earn. Over-cap or stale reports still record the meeting/spot
// and still answer ok — the badge keeps its local creature either way; the
// server just refuses to mint scoreboard weight for it.
const SNUFFEL_GRANTS_PER_DAY = 3;
const SNUFFEL_GRANTS_TOTAL = 6;
const PLUK_GRANTS_PER_PHASE = 3;
const PLUK_GRANTS_TOTAL = 8;

// day/phase within [-36h, +60h) of its UTC midnight: covers the Brussels
// offset, the 15:00 pluk-phase boundary and a day of outbox lag, nothing more.
function dayNear(day: string): boolean {
  const t = Date.parse(day + "T00:00:00Z");
  if (Number.isNaN(t)) return false;
  const diff = Date.now() - t;
  return diff > -36 * 3600 * 1000 && diff < 60 * 3600 * 1000;
}

// POST /api/v1/player/found
// Sent by the LoRa bridge relay (not the badge), authenticated with the
// pre-shared BRIDGE_KEY. Body: { hunter_id, fox_id }
//
// fox_id is CHAR — the creature's character code — NOT the FID byte it rides
// in on (FID = CHAR << 3 | SEQ, spec §2.1). A relay must send FID >> 3; the
// raw byte silently credits the wrong creature for CHAR 0-3. See server/README.
playerRoutes.post("/found", async (c) => {
  const auth = c.req.header("Authorization") ?? "";
  // Fail closed when the secret was never set: on a re-created worker with no
  // BRIDGE_KEY, `Bearer ${undefined}` is the literal string "Bearer undefined"
  // — valid credentials anyone can type. No key configured = no bridge.
  const bridged = !!c.env.BRIDGE_KEY && auth === `Bearer ${c.env.BRIDGE_KEY}`;

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

  // The grant caps, counted BEFORE this report's row lands (see the bounds
  // comment at the top): a capped or stale report still records the meeting
  // below, it just cannot mint another creature.
  let allowGrant = creatureId !== null && dayNear(day);
  if (allowGrant) {
    const counts = await c.env.DB.prepare(
      `SELECT COUNT(*) AS total, COALESCE(SUM(day = ?), 0) AS today
         FROM snuffels WHERE player_id = ? AND creature_id IS NOT NULL`,
    )
      .bind(day, player.id)
      .first<{ total: number; today: number }>();
    allowGrant =
      (counts?.total ?? 0) < SNUFFEL_GRANTS_TOTAL &&
      (counts?.today ?? 0) < SNUFFEL_GRANTS_PER_DAY;
  }

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
  if (allowGrant && !duplicate) {
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

// POST /api/v1/player/pluk
// Sent by the badge outbox after a successful wild encounter. Food never
// leaves the badge; this narrow report only makes the new creature survive an
// account restore. The badge's roll is deterministic in badge/BSSID/phase and
// the server deduplicates that physical opportunity. As with snuffel grants,
// this is generous unauthenticated collection state, not a verified LoRa find
// and not hunter score. Legendary ids are deliberately valid here.
playerRoutes.post("/pluk", async (c) => {
  let body: Record<string, unknown>;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid JSON body" }, 400);
  }

  const badgeId = validateBadgeId(body.badge_id);
  if (!badgeId) return c.json({ error: "invalid badge_id" }, 400);

  const bssid = validateBadgeId(body.bssid);
  if (!bssid) return c.json({ error: "invalid bssid" }, 400);

  const phase = typeof body.phase === "string" ? body.phase : "";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(phase))
    return c.json({ error: "invalid phase (YYYY-MM-DD)" }, 400);

  const creatureId = body.creature_id;
  if (
    typeof creatureId !== "number" ||
    !Number.isInteger(creatureId) ||
    !KNOWN_CREATURES.has(creatureId)
  )
    return c.json({ error: "invalid creature_id" }, 400);

  const player = await c.env.DB.prepare(
    "SELECT * FROM players WHERE badge_id = ? AND dt_deleted IS NULL",
  )
    .bind(badgeId)
    .first<Player>();
  if (!player) return c.json({ error: "unknown badge_id" }, 404);

  // Same server-owned bounds as snuffel: every pluks row is a grant attempt
  // (the badge only reports successful rolls), so the caps count rows.
  let allowGrant = dayNear(phase);
  if (allowGrant) {
    const counts = await c.env.DB.prepare(
      `SELECT COUNT(*) AS total, COALESCE(SUM(phase = ?), 0) AS this_phase
         FROM pluks WHERE player_id = ?`,
    )
      .bind(phase, player.id)
      .first<{ total: number; this_phase: number }>();
    allowGrant =
      (counts?.total ?? 0) < PLUK_GRANTS_TOTAL &&
      (counts?.this_phase ?? 0) < PLUK_GRANTS_PER_PHASE;
  }

  const result = await c.env.DB.prepare(
    "INSERT OR IGNORE INTO pluks (player_id, bssid, phase, creature_id) VALUES (?, ?, ?, ?)",
  )
    .bind(player.id, bssid, phase, creatureId)
    .run();
  const duplicate = result.meta.changes === 0;

  let granted = false;
  if (!duplicate) {
    const grant = allowGrant
      ? await c.env.DB.prepare(
          "INSERT OR IGNORE INTO players_creatures (player_id, creature_id) VALUES (?, ?)",
        )
          .bind(player.id, creatureId)
          .run()
      : null;
    granted = (grant?.meta.changes ?? 0) > 0;
    await logEvent(c.env.DB, "pluk_creature_found", {
      player_id: player.id,
      bssid,
      phase,
      creature_id: creatureId,
      granted,
    });
  }

  return c.json({ ok: true, duplicate, granted });
});

// POST /api/v1/player/visitor
// Sent through the badge outbox after a scheduled fallback meeting. The badge
// owns the offline-friendly timing; the server owns two hard safety rails:
// three slots at most and base-tier creatures only. In particular, a forged or
// corrupted badge report can never turn a random meeting into a legendary.
playerRoutes.post("/visitor", async (c) => {
  let body: Record<string, unknown>;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid JSON body" }, 400);
  }

  const badgeId = validateBadgeId(body.badge_id);
  if (!badgeId) return c.json({ error: "invalid badge_id" }, 400);

  const slot = body.slot;
  if (
    typeof slot !== "number" ||
    !Number.isInteger(slot) ||
    slot < 0 ||
    slot > 2
  )
    return c.json({ error: "invalid slot (integer 0-2)" }, 400);

  const creatureId = body.creature_id;
  if (
    typeof creatureId !== "number" ||
    !Number.isInteger(creatureId) ||
    !BASE_CREATURES.has(creatureId)
  )
    return c.json({ error: "invalid creature_id (base tier only)" }, 400);

  const player = await c.env.DB.prepare(
    "SELECT * FROM players WHERE badge_id = ? AND dt_deleted IS NULL",
  )
    .bind(badgeId)
    .first<Player>();
  if (!player) return c.json({ error: "unknown badge_id" }, 404);

  const result = await c.env.DB.prepare(
    "INSERT OR IGNORE INTO visitors (player_id, slot, creature_id) VALUES (?, ?, ?)",
  )
    .bind(player.id, slot, creatureId)
    .run();
  const duplicate = result.meta.changes === 0;

  let granted = false;
  if (!duplicate) {
    const grant = await c.env.DB.prepare(
      "INSERT OR IGNORE INTO players_creatures (player_id, creature_id) VALUES (?, ?)",
    )
      .bind(player.id, creatureId)
      .run();
    granted = grant.meta.changes > 0;
    await logEvent(c.env.DB, "visitor_claimed", {
      player_id: player.id,
      slot,
      creature_id: creatureId,
      granted,
    });
  }

  return c.json({ ok: true, duplicate, granted });
});
