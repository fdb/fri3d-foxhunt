import { Hono } from "hono";
import type { Bindings, Player } from "../types";
import { logEvent } from "../lib/events";
import { validateHunterId } from "../lib/validate";

export const playerRoutes = new Hono<{ Bindings: Bindings }>();

// POST /api/v1/player/found
// Sent by the LoRa bridge relay (not the badge), authenticated with the
// pre-shared BRIDGE_KEY. Body: { hunter_id, fox_id }
playerRoutes.post("/found", async (c) => {
  const auth = c.req.header("Authorization") ?? "";
  if (auth !== `Bearer ${c.env.BRIDGE_KEY}`) {
    return c.json({ error: "unauthorized" }, 401);
  }

  let body: Record<string, unknown>;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid JSON body" }, 400);
  }

  const hunterId = validateHunterId(body.hunter_id);
  if (hunterId === null || hunterId === "invalid")
    return c.json({ error: "invalid hunter_id (integer 0-31)" }, 400);

  const foxId = body.fox_id;
  if (
    typeof foxId !== "number" ||
    !Number.isInteger(foxId) ||
    foxId < 0 ||
    foxId > 31
  )
    return c.json({ error: "invalid fox_id (integer 0-31)" }, 400);

  const player = await c.env.DB.prepare(
    "SELECT * FROM players WHERE hunter_id = ?",
  )
    .bind(hunterId)
    .first<Player>();
  if (!player) return c.json({ error: "unknown hunter_id" }, 404);

  const result = await c.env.DB.prepare(
    "INSERT OR IGNORE INTO players_creatures (player_id, creature_id) VALUES (?, ?)",
  )
    .bind(player.id, foxId)
    .run();
  const duplicate = result.meta.changes === 0;

  if (!duplicate) {
    await logEvent(c.env.DB, "fox_found", {
      player_id: player.id,
      hunter_id: hunterId,
      fox_id: foxId,
    });
  }

  return c.json({ ok: true, player_id: player.id, fox_id: foxId, duplicate });
});
