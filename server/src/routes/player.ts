import { Hono } from "hono";
import type { Bindings, Player } from "../types";
import { logEvent } from "../lib/events";
import { validateBadgeId, validateHunterId } from "../lib/validate";
import { CREATURES } from "../lib/creatures";

export const playerRoutes = new Hono<{ Bindings: Bindings }>();

const KNOWN_CREATURES = new Set(CREATURES.map((c) => c.id));
const BASE_CREATURES = new Set(
  CREATURES.filter((c) => c.rarity === "norm").map((c) => c.id),
);
const CREATURE_BY_ID = new Map(CREATURES.map((c) => [c.id, c]));
const CAMP_START_S = 1_786_021_200; // 2026-08-06 15:00 Europe/Brussels
const CAMP_END_S = CAMP_START_S + 72 * 60 * 60;
const SPARK_COOLDOWN_S = 6 * 60 * 60;

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

type SnuffelReport = {
  id: number;
  player_id: number;
  encounter_id: string;
  peer: string;
  day: string;
  occurred_at: number;
  had_vonk: number;
  sent_creature_id: number | null;
  received_creature_id: number | null;
  received_was_new: number;
};

async function shareEligible(
  db: D1Database,
  giver: Player,
  recipient: Player,
  creatureId: number,
): Promise<boolean> {
  const creature = CREATURE_BY_ID.get(creatureId);
  if (!creature) return false;
  const owned = await db
    .prepare(
      "SELECT self_found FROM players_creatures WHERE player_id = ? AND creature_id = ?",
    )
    .bind(giver.id, creatureId)
    .first<{ self_found: number }>();
  if (!owned) return false;
  if (creature.rarity === "norm") return true;
  if (creature.rarity === "rare")
    return !giver.hunter_id || owned.self_found === 1;
  return !!giver.hunter_id && !recipient.hunter_id && owned.self_found === 1;
}

async function pairSparkReady(
  db: D1Database,
  giverId: number,
  recipientId: number,
  encounterId: string,
  occurredAt: number,
): Promise<boolean> {
  const playerA = Math.min(giverId, recipientId);
  const playerB = Math.max(giverId, recipientId);
  const recent = await db
    .prepare(
      `SELECT 1 FROM verified_sparks
       WHERE encounter_id <> ?
         AND player_a = ? AND player_b = ?
         AND occurred_at > ?
       LIMIT 1`,
    )
    .bind(encounterId, playerA, playerB, occurredAt - SPARK_COOLDOWN_S)
    .first();
  return !recent;
}

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
      return c.json({ error: "invalid hunter_id (integer 1-65535)" }, 400);
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
    `INSERT INTO players_creatures
       (player_id, creature_id, self_found, dt_self_found)
     VALUES (?, ?, 1, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
     ON CONFLICT(player_id, creature_id) DO UPDATE SET
       self_found = 1,
       dt_self_found = excluded.dt_self_found
     WHERE players_creatures.self_found = 0`,
  )
    .bind(player.id, foxId)
    .run();
  const alreadySelfFound = result.meta.changes === 0;

  if (!alreadySelfFound) {
    await logEvent(c.env.DB, "fox_found", {
      player_id: player.id,
      hunter_id: player.hunter_id,
      fox_id: foxId,
    });
  }

  return c.json({
    ok: true,
    player_id: player.id,
    fox_id: foxId,
    duplicate: alreadySelfFound,
    already_self_found: alreadySelfFound,
  });
});

// POST /api/v1/player/snuffel
// Each badge reports the same encounter plus both directed outcomes. A lone
// report may preserve a base/rare introduction, but legendary durability and
// help score require an exact matching report from the peer.
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

  const encounterId =
    typeof body.encounter_id === "string" ? body.encounter_id : "";
  if (!/^[A-Za-z0-9:@|._-]{8,180}$/.test(encounterId))
    return c.json({ error: "invalid encounter_id" }, 400);

  const occurredAt = body.occurred_at;
  if (
    typeof occurredAt !== "number" ||
    !Number.isInteger(occurredAt) ||
    occurredAt <= 0
  )
    return c.json({ error: "invalid occurred_at" }, 400);

  if (typeof body.vonk !== "boolean")
    return c.json({ error: "invalid vonk" }, 400);
  const hadVonk = body.vonk;

  const creatureField = (name: string): number | null | "invalid" => {
    const value = body[name];
    if (value === undefined || value === null) return null;
    return typeof value === "number" &&
      Number.isInteger(value) &&
      KNOWN_CREATURES.has(value)
      ? value
      : "invalid";
  };
  const sentCreatureId = creatureField("sent_creature_id");
  const receivedCreatureId = creatureField("received_creature_id");
  if (sentCreatureId === "invalid" || receivedCreatureId === "invalid")
    return c.json({ error: "invalid directed creature id" }, 400);
  if (!hadVonk && (sentCreatureId !== null || receivedCreatureId !== null))
    return c.json({ error: "creatures require a vonk" }, 400);

  const player = await c.env.DB.prepare(
    "SELECT * FROM players WHERE badge_id = ? AND dt_deleted IS NULL",
  )
    .bind(badgeId)
    .first<Player>();
  if (!player) return c.json({ error: "unknown badge_id" }, 404);

  const peerPlayer = await c.env.DB.prepare(
    "SELECT * FROM players WHERE badge_id = ? AND dt_deleted IS NULL",
  )
    .bind(peer)
    .first<Player>();

  const result = await c.env.DB.prepare(
    `INSERT OR IGNORE INTO snuffel_reports
       (player_id, encounter_id, peer, day, occurred_at, had_vonk,
        sent_creature_id, received_creature_id)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
  )
    .bind(
      player.id,
      encounterId,
      peer,
      day,
      occurredAt,
      hadVonk ? 1 : 0,
      sentCreatureId,
      receivedCreatureId,
    )
    .run();
  const duplicate = result.meta.changes === 0;

  // Forgiving recovery for base/rare: the receiver's own report is enough.
  // The caps bound forged badge traffic; legendary always waits for both.
  let granted = false;
  const receivedCreature =
    receivedCreatureId === null
      ? undefined
      : CREATURE_BY_ID.get(receivedCreatureId);
  let allowGrant =
    !duplicate &&
    hadVonk &&
    !!peerPlayer &&
    !!receivedCreature &&
    receivedCreature.rarity !== "leg" &&
    (dayNear(day) || (occurredAt >= CAMP_START_S && occurredAt < CAMP_END_S));
  if (allowGrant && peerPlayer && receivedCreatureId !== null) {
    allowGrant =
      (await shareEligible(c.env.DB, peerPlayer, player, receivedCreatureId)) &&
      (await pairSparkReady(
        c.env.DB,
        player.id,
        peerPlayer.id,
        encounterId,
        occurredAt,
      ));
  }
  if (allowGrant) {
    const counts = await c.env.DB.prepare(
      `SELECT COUNT(*) AS total, COALESCE(SUM(day = ?), 0) AS today
         FROM snuffel_reports
        WHERE player_id = ? AND received_was_new = 1`,
    )
      .bind(day, player.id)
      .first<{ total: number; today: number }>();
    allowGrant =
      (counts?.total ?? 0) < SNUFFEL_GRANTS_TOTAL &&
      (counts?.today ?? 0) < SNUFFEL_GRANTS_PER_DAY;
  }

  if (allowGrant && !duplicate) {
    const grant = await c.env.DB.prepare(
      "INSERT OR IGNORE INTO players_creatures (player_id, creature_id) VALUES (?, ?)",
    )
      .bind(player.id, receivedCreatureId)
      .run();
    granted = grant.meta.changes > 0;
    if (granted) {
      await c.env.DB.prepare(
        `UPDATE snuffel_reports SET received_was_new = 1
         WHERE player_id = ? AND encounter_id = ?`,
      )
        .bind(player.id, encounterId)
        .run();
    }
  }

  if (!duplicate) {
    await logEvent(c.env.DB, "snuffel_reported", {
      player_id: player.id,
      peer,
      day,
      encounter_id: encounterId,
      had_vonk: hadVonk,
      sent_creature_id: sentCreatureId,
      received_creature_id: receivedCreatureId,
      granted,
    });
  }

  let verifiedShares = 0;
  let helpCredits = 0;
  if (peerPlayer) {
    const reports = await c.env.DB.prepare(
      `SELECT * FROM snuffel_reports
       WHERE encounter_id = ? AND player_id IN (?, ?)`,
    )
      .bind(encounterId, player.id, peerPlayer.id)
      .all<SnuffelReport>();
    const mine = reports.results.find((r) => r.player_id === player.id);
    const theirs = reports.results.find((r) => r.player_id === peerPlayer.id);
    const corroborated =
      mine &&
      theirs &&
      mine.peer === peerPlayer.badge_id &&
      theirs.peer === player.badge_id &&
      mine.had_vonk === 1 &&
      theirs.had_vonk === 1 &&
      mine.sent_creature_id === theirs.received_creature_id &&
      theirs.sent_creature_id === mine.received_creature_id &&
      Math.abs(mine.occurred_at - theirs.occurred_at) <= 5 * 60;

    const verifyDirection = async (
      giver: Player,
      recipient: Player,
      giverReport: SnuffelReport,
      recipientReport: SnuffelReport,
    ) => {
      const creatureId = giverReport.sent_creature_id;
      if (creatureId === null) return;
      if (!(await shareEligible(c.env.DB, giver, recipient, creatureId)))
        return;

      const creature = CREATURE_BY_ID.get(creatureId)!;
      let wasNew = recipientReport.received_was_new === 1;
      if (creature.rarity === "leg") {
        const grant = await c.env.DB.prepare(
          "INSERT OR IGNORE INTO players_creatures (player_id, creature_id) VALUES (?, ?)",
        )
          .bind(recipient.id, creatureId)
          .run();
        wasNew = grant.meta.changes > 0;
      }
      if (!wasNew) return;

      const share = await c.env.DB.prepare(
        `INSERT OR IGNORE INTO creature_shares
           (encounter_id, giver_id, recipient_id, creature_id, occurred_at)
         VALUES (?, ?, ?, ?, ?)`,
      )
        .bind(
          encounterId,
          giver.id,
          recipient.id,
          creatureId,
          giverReport.occurred_at,
        )
        .run();
      if (share.meta.changes === 0) return;
      verifiedShares += 1;

      const shareRow = await c.env.DB.prepare(
        `SELECT id FROM creature_shares
         WHERE encounter_id = ? AND giver_id = ? AND recipient_id = ? AND creature_id = ?`,
      )
        .bind(encounterId, giver.id, recipient.id, creatureId)
        .first<{ id: number }>();
      const inCamp =
        giverReport.occurred_at >= CAMP_START_S &&
        giverReport.occurred_at < CAMP_END_S;
      let helpCredited = false;
      if (inCamp && shareRow) {
        const help = await c.env.DB.prepare(
          `INSERT OR IGNORE INTO helped_players
             (giver_id, recipient_id, first_share_id)
           VALUES (?, ?, ?)`,
        )
          .bind(giver.id, recipient.id, shareRow.id)
          .run();
        helpCredited = help.meta.changes > 0;
        helpCredits += help.meta.changes;
      }
      await logEvent(c.env.DB, "creature_shared", {
        player_id: giver.id,
        encounter_id: encounterId,
        giver_id: giver.id,
        recipient_id: recipient.id,
        creature_id: creatureId,
        help_credited: helpCredited,
      });
    };

    if (
      corroborated &&
      (await pairSparkReady(
        c.env.DB,
        player.id,
        peerPlayer.id,
        encounterId,
        Math.min(mine.occurred_at, theirs.occurred_at),
      ))
    ) {
      const playerA = Math.min(player.id, peerPlayer.id);
      const playerB = Math.max(player.id, peerPlayer.id);
      await c.env.DB.prepare(
        `INSERT OR IGNORE INTO verified_sparks
           (encounter_id, player_a, player_b, occurred_at)
         VALUES (?, ?, ?, ?)`,
      )
        .bind(
          encounterId,
          playerA,
          playerB,
          Math.min(mine.occurred_at, theirs.occurred_at),
        )
        .run();
      await verifyDirection(player, peerPlayer, mine, theirs);
      await verifyDirection(peerPlayer, player, theirs, mine);
    }
  }

  return c.json({
    ok: true,
    duplicate,
    granted,
    verified_shares: verifiedShares,
    help_credits: helpCredits,
  });
});

// POST /api/v1/player/pluk
// Sent by the badge outbox after a successful wild encounter. Food never
// leaves the badge; this narrow report only makes the new creature survive an
// account restore. The badge's roll is deterministic in badge/BSSID/phase and
// the server deduplicates that physical opportunity. As with snuffel grants,
// this is generous unauthenticated collection state, not a verified LoRa find
// and not hunter score. Only base-tier ids are valid here.
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
    !BASE_CREATURES.has(creatureId)
  )
    return c.json({ error: "invalid creature_id (base tier only)" }, 400);

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
