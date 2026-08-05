import { Hono } from "hono";
import type { Bindings, Player } from "../types";
import { logEvent } from "../lib/events";
import { starterFor } from "../lib/starter";
import {
  validateBadgeId,
  validateHunterId,
  validateName,
  validateProfilePic,
} from "../lib/validate";

export const authRoutes = new Hono<{ Bindings: Bindings }>();

function uniqueConflict(err: unknown): "badge_id" | "hunter_id" | null {
  const msg = err instanceof Error ? err.message : String(err);
  if (msg.includes("players.badge_id")) return "badge_id";
  if (msg.includes("players.hunter_id")) return "hunter_id";
  return null;
}

// The account this badge is playing on, or null. A soft-deleted row is not one:
// every player-facing route must read the player through this, so that a wiped
// badge looks exactly like a badge the server has never seen. /register is the
// deliberate exception — it needs to see the deleted row in order to revive it.
function livePlayer(db: D1Database, badgeId: string) {
  return db
    .prepare("SELECT * FROM players WHERE badge_id = ? AND dt_deleted IS NULL")
    .bind(badgeId)
    .first<Player>();
}

// POST /api/v1/auth/register
// Body: { badge_id, name, hunter_id?, profile_pic? }
authRoutes.post("/register", async (c) => {
  let body: Record<string, unknown>;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid JSON body" }, 400);
  }

  const badgeId = validateBadgeId(body.badge_id);
  if (!badgeId) return c.json({ error: "invalid badge_id" }, 400);

  const name = validateName(body.name);
  if (!name)
    return c.json({ error: "invalid name (1-32 chars, no emoji)" }, 400);

  const hunterId = validateHunterId(body.hunter_id);
  if (hunterId === "invalid")
    return c.json({ error: "invalid hunter_id (integer 1-9999)" }, 400);

  // The companion shortcode rides along with registration: it is what a restore
  // hands back, so a badge that never sent one can never recover its avatar.
  // The column is NOT NULL DEFAULT '', so "no companion" is the empty string.
  let profilePic = "";
  if (body.profile_pic !== undefined) {
    const validated = validateProfilePic(body.profile_pic);
    if (validated === null)
      return c.json(
        { error: "invalid profile_pic (companion shortcode)" },
        400,
      );
    profilePic = validated;
  }

  // badge_id is UNIQUE across deleted rows too, so the insert cannot tell a
  // live account from a wiped one — it just conflicts. Read first: a wiped
  // badge must come back as a NEW player, not as a 409 the flow would show as
  // "deze badge is al bekend".
  const existing = await c.env.DB.prepare(
    "SELECT * FROM players WHERE badge_id = ?",
  )
    .bind(badgeId)
    .first<Player>();

  let player: Player | null;
  if (existing?.dt_deleted) {
    // Revive the row rather than add a second one, so badge_id stays unique
    // and an organiser can still find the wipe in the log. Everything the old
    // player owned goes: the roster, and the hunter_id — the next player on
    // this badge mints their own, and an in-flight bridge report for the old
    // HID must not credit them.
    await c.env.DB.prepare("DELETE FROM players_creatures WHERE player_id = ?")
      .bind(existing.id)
      .run();
    player = await c.env.DB.prepare(
      `UPDATE players
          SET name = ?, profile_pic = ?, hunter_id = ?, dt_deleted = NULL,
              dt_created = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
              dt_updated = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE id = ? RETURNING *`,
    )
      .bind(name, profilePic, hunterId, existing.id)
      .first<Player>();
  } else if (existing) {
    return c.json({ error: "badge_id already registered" }, 409);
  } else {
    try {
      player = await c.env.DB.prepare(
        "INSERT INTO players (badge_id, name, hunter_id, profile_pic) VALUES (?, ?, ?, ?) RETURNING *",
      )
        .bind(badgeId, name, hunterId, profilePic)
        .first<Player>();
    } catch (err) {
      const conflict = uniqueConflict(err);
      if (conflict)
        return c.json({ error: `${conflict} already registered` }, 409);
      throw err;
    }
  }

  await logEvent(c.env.DB, "player_registered", {
    player_id: player!.id,
    badge_id: badgeId,
    hunter_id: hunterId,
    name,
    profile_pic: profilePic,
    revived: existing ? true : undefined,
  });

  // The startbeest rides the registration: the server is the durable record
  // a restore rebuilds from, so the grant happens here, not on the badge.
  // Normal catches stay bridge-only; this is the one creature the server
  // itself hands out (GAME_DESIGN.md, "How a creature reaches the profile").
  const starterId = starterFor(badgeId);
  await c.env.DB.prepare(
    "INSERT OR IGNORE INTO players_creatures (player_id, creature_id) VALUES (?, ?)",
  )
    .bind(player!.id, starterId)
    .run();
  await logEvent(c.env.DB, "starter_granted", {
    player_id: player!.id,
    badge_id: badgeId,
    creature_id: starterId,
  });

  return c.json({ ...player, starter: starterId }, 201);
});

// POST /api/v1/auth/starter
// Body: { badge_id }. The catch-up path: hand the deterministic startbeest to
// an account that predates the feature (scripts/get_random_creature.sh drives
// it over USB) or that adopted an existing row via re-register. Only an EMPTY
// roster is granted — an account with creatures already had its start.
// Unauthenticated on purpose: the only thing this can ever do is give an
// empty account the same creature registration would have given it, and the
// pick cannot be chosen or rerolled.
authRoutes.post("/starter", async (c) => {
  let body: Record<string, unknown>;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid JSON body" }, 400);
  }

  const badgeId = validateBadgeId(body.badge_id);
  if (!badgeId) return c.json({ error: "invalid badge_id" }, 400);

  const player = await livePlayer(c.env.DB, badgeId);
  if (!player) return c.json({ error: "unknown badge_id" }, 404);

  const { results } = await c.env.DB.prepare(
    "SELECT creature_id FROM players_creatures WHERE player_id = ? ORDER BY creature_id",
  )
    .bind(player.id)
    .all<{ creature_id: number }>();
  const have = results.map((r) => r.creature_id);

  const starterId = starterFor(badgeId);
  if (have.length > 0) {
    // Re-running the script is not an error when all it would redo is done.
    if (have.length === 1 && have[0] === starterId)
      return c.json({ ok: true, starter: starterId, duplicate: true });
    return c.json({ error: "roster not empty", creatures: have }, 409);
  }

  await c.env.DB.prepare(
    "INSERT INTO players_creatures (player_id, creature_id) VALUES (?, ?)",
  )
    .bind(player.id, starterId)
    .run();
  await logEvent(c.env.DB, "starter_granted", {
    player_id: player.id,
    badge_id: badgeId,
    creature_id: starterId,
  });

  return c.json({ ok: true, starter: starterId, duplicate: false });
});

// GET /api/v1/auth/user?badge_id=...
// The badge's "restore" route: a badge that lost its filesystem still knows
// its own MAC, so that is the key it recovers an account with. 404 means the
// badge is simply new — the app sends it to registration.
authRoutes.get("/user", async (c) => {
  const badgeId = validateBadgeId(c.req.query("badge_id"));
  if (!badgeId) return c.json({ error: "invalid badge_id" }, 400);

  const player = await livePlayer(c.env.DB, badgeId);
  if (!player) return c.json({ error: "unknown badge_id" }, 404);

  // The catch list rides along with the account. players_creatures is the only
  // record of it that survives a wiped badge, and the restored profile is
  // wrong without it in a way you can see: the maatje's accessory unlocks are
  // counted straight off this list, so a restore that dropped it would hand
  // the player back an avatar wearing things it says they haven't earned.
  const { results } = await c.env.DB.prepare(
    "SELECT creature_id FROM players_creatures WHERE player_id = ? ORDER BY creature_id",
  )
    .bind(player.id)
    .all<{ creature_id: number }>();

  return c.json({ ...player, creatures: results.map((r) => r.creature_id) });
});

// PATCH /api/v1/auth/user
// Body: { badge_id, name?, hunter_id?, profile_pic? } — badge_id identifies
// the account, the other fields are applied when present.
authRoutes.patch("/user", async (c) => {
  let body: Record<string, unknown>;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid JSON body" }, 400);
  }

  const badgeId = validateBadgeId(body.badge_id);
  if (!badgeId) return c.json({ error: "invalid badge_id" }, 400);

  const existing = await livePlayer(c.env.DB, badgeId);
  if (!existing) return c.json({ error: "unknown badge_id" }, 404);

  const fields: string[] = [];
  const values: (string | number | null)[] = [];
  const changes: Record<string, unknown> = {};

  if (body.name !== undefined) {
    const name = validateName(body.name);
    if (!name)
      return c.json({ error: "invalid name (1-32 chars, no emoji)" }, 400);
    fields.push("name = ?");
    values.push(name);
    changes.name = name;
  }
  if (body.hunter_id !== undefined) {
    const hunterId = validateHunterId(body.hunter_id);
    if (hunterId === "invalid")
      return c.json({ error: "invalid hunter_id (integer 1-9999)" }, 400);
    fields.push("hunter_id = ?");
    values.push(hunterId);
    changes.hunter_id = hunterId;
  }
  if (body.profile_pic !== undefined) {
    const profilePic = validateProfilePic(body.profile_pic);
    if (profilePic === null)
      return c.json(
        { error: "invalid profile_pic (companion shortcode)" },
        400,
      );
    fields.push("profile_pic = ?");
    values.push(profilePic);
    changes.profile_pic = profilePic;
  }
  if (fields.length === 0) return c.json({ error: "nothing to update" }, 400);

  fields.push("dt_updated = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')");

  let player: Player | null;
  try {
    player = await c.env.DB.prepare(
      `UPDATE players SET ${fields.join(", ")} WHERE badge_id = ? AND dt_deleted IS NULL RETURNING *`,
    )
      .bind(...values, badgeId)
      .first<Player>();
  } catch (err) {
    const conflict = uniqueConflict(err);
    if (conflict)
      return c.json({ error: `${conflict} already registered` }, 409);
    throw err;
  }

  await logEvent(c.env.DB, "player_updated", {
    player_id: existing.id,
    ...changes,
  });
  return c.json(player);
});

// DELETE /api/v1/auth/user
// Body: { badge_id }. The badge's "alles wissen": the player gives the badge
// away, or wants their name off the public scoreboard. The account leaves the
// game — restore 404s, the scoreboard drops it, the bridge can no longer credit
// it — and registering again on this badge starts a genuinely empty one.
//
// SOFT, on purpose. Unauthenticated is the house style here (a PATCH can
// already rename any account whose MAC you can see), but delete is the first
// irreversible one, and a catch list can only be rebuilt by walking back to the
// foxes. So the row survives, an organiser can clear dt_deleted to undo it, and
// the log keeps both the wipe and the registration that preceded it. That last
// part is the honest limit: this removes the account from the game, it does not
// erase the player from game_events.
//
// Idempotent: a badge that wiped, lost the response and retried gets ok again,
// never a 404 it would have to explain.
authRoutes.delete("/user", async (c) => {
  let body: Record<string, unknown>;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid JSON body" }, 400);
  }

  const badgeId = validateBadgeId(body.badge_id);
  if (!badgeId) return c.json({ error: "invalid badge_id" }, 400);

  const existing = await c.env.DB.prepare(
    "SELECT * FROM players WHERE badge_id = ?",
  )
    .bind(badgeId)
    .first<Player>();
  if (!existing) return c.json({ error: "unknown badge_id" }, 404);
  if (existing.dt_deleted)
    return c.json({ ok: true, player_id: existing.id, already: true });

  await c.env.DB.prepare(
    `UPDATE players
        SET dt_deleted = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
            dt_updated = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
      WHERE id = ?`,
  )
    .bind(existing.id)
    .run();

  await logEvent(c.env.DB, "player_deleted", {
    player_id: existing.id,
    badge_id: badgeId,
    hunter_id: existing.hunter_id,
    name: existing.name,
  });

  return c.json({ ok: true, player_id: existing.id, already: false });
});
