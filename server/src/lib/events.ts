export async function logEvent(
  db: D1Database,
  type: string,
  payload: Record<string, unknown>,
): Promise<void> {
  await db
    .prepare("INSERT INTO game_events (type, payload) VALUES (?, ?)")
    .bind(type, JSON.stringify(payload))
    .run();
}
