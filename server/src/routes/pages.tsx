import { Hono } from "hono";
import type { Bindings, GameEvent, ScoreRow } from "../types";
import { Layout } from "../components/Layout";

export const pageRoutes = new Hono<{ Bindings: Bindings }>();

async function fetchScores(db: D1Database): Promise<ScoreRow[]> {
  const { results } = await db
    .prepare(
      `SELECT p.id, p.name, p.hunter_id,
              COUNT(pc.creature_id) AS foxes_found,
              MAX(pc.dt_found) AS last_found
       FROM players p
       LEFT JOIN players_creatures pc ON pc.player_id = p.id
       GROUP BY p.id
       ORDER BY foxes_found DESC, last_found ASC, p.name ASC`,
    )
    .all<ScoreRow>();
  return results;
}

const Scoreboard = ({ scores }: { scores: ScoreRow[] }) => (
  <section
    id="scoreboard"
    hx-get="/scoreboard"
    hx-trigger="every 5s"
    hx-swap="outerHTML"
  >
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Player</th>
          <th>Hunter ID</th>
          <th>Foxes</th>
          <th>Last found</th>
        </tr>
      </thead>
      <tbody>
        {scores.map((s, i) => (
          <tr>
            <td>{i + 1}</td>
            <td>{s.name}</td>
            <td>{s.hunter_id ?? "—"}</td>
            <td>
              {"●".repeat(s.foxes_found)}
              {"○".repeat(Math.max(0, 4 - s.foxes_found))}
            </td>
            <td>{s.last_found ?? "—"}</td>
          </tr>
        ))}
        {scores.length === 0 && (
          <tr>
            <td colspan={5}>No players registered yet.</td>
          </tr>
        )}
      </tbody>
    </table>
  </section>
);

// Public dashboard
pageRoutes.get("/", async (c) => {
  const scores = await fetchScores(c.env.DB);
  return c.html(
    <Layout title="Foxhunt — Scores">
      <Scoreboard scores={scores} />
    </Layout>,
  );
});

// HTMX partial, polled by the dashboard
pageRoutes.get("/scoreboard", async (c) => {
  const scores = await fetchScores(c.env.DB);
  return c.html(<Scoreboard scores={scores} />);
});

// Event log: HTML table by default, JSON when requested
pageRoutes.get("/debug/log", async (c) => {
  const { results } = await c.env.DB.prepare(
    "SELECT * FROM game_events ORDER BY id DESC LIMIT 500",
  ).all<GameEvent>();

  if (c.req.header("Accept")?.includes("application/json")) {
    return c.json(
      results.map((e) => ({ ...e, payload: JSON.parse(e.payload) })),
    );
  }

  return c.html(
    <Layout title="Foxhunt — Event log">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Payload</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>
          {results.map((e) => (
            <tr>
              <td>{e.id}</td>
              <td>{e.type}</td>
              <td>
                <code>{e.payload}</code>
              </td>
              <td>{e.created_at}</td>
            </tr>
          ))}
          {results.length === 0 && (
            <tr>
              <td colspan={4}>No events yet.</td>
            </tr>
          )}
        </tbody>
      </table>
    </Layout>,
  );
});
