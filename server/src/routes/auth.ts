import { Hono } from "hono";
import type { Bindings, Player } from "../types";
import { logEvent } from "../lib/events";
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
      return c.json({ error: "invalid profile_pic (companion shortcode)" }, 400);
    profilePic = validated;
  }

  let player: Player | null;
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

  await logEvent(c.env.DB, "player_registered", {
    player_id: player!.id,
    badge_id: badgeId,
    hunter_id: hunterId,
    name,
    profile_pic: profilePic,
  });
  return c.json(player, 201);
});

// GET /api/v1/auth/user?badge_id=...
// The badge's "restore" route: a badge that lost its filesystem still knows
// its own MAC, so that is the key it recovers an account with. 404 means the
// badge is simply new — the app sends it to registration.
authRoutes.get("/user", async (c) => {
  const badgeId = validateBadgeId(c.req.query("badge_id"));
  if (!badgeId) return c.json({ error: "invalid badge_id" }, 400);

  const player = await c.env.DB.prepare(
    "SELECT * FROM players WHERE badge_id = ?",
  )
    .bind(badgeId)
    .first<Player>();
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

  const existing = await c.env.DB.prepare(
    "SELECT * FROM players WHERE badge_id = ?",
  )
    .bind(badgeId)
    .first<Player>();
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
      return c.json({ error: "invalid profile_pic (companion shortcode)" }, 400);
    fields.push("profile_pic = ?");
    values.push(profilePic);
    changes.profile_pic = profilePic;
  }
  if (fields.length === 0) return c.json({ error: "nothing to update" }, 400);

  fields.push("dt_updated = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')");

  let player: Player | null;
  try {
    player = await c.env.DB.prepare(
      `UPDATE players SET ${fields.join(", ")} WHERE badge_id = ? RETURNING *`,
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
