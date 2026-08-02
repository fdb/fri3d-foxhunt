import { Hono } from "hono";
import type { Bindings, GameEvent, ScoreRow } from "../types";
import { Layout } from "../components/Layout";

export const pageRoutes = new Hono<{ Bindings: Bindings }>();

const FOX_COUNT = 4;

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

// "2026-08-02T12:34:56.789Z" -> "12:34"
const shortTime = (iso: string | null) => (iso ? iso.slice(11, 16) : "—");

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
          <th>Speler</th>
          <th>Hunter</th>
          <th>Vossen</th>
          <th>Laatst</th>
        </tr>
      </thead>
      <tbody>
        {scores.map((s, i) => (
          <tr>
            <td class="rank">{i + 1}</td>
            <td>{s.name}</td>
            <td class="muted">{s.hunter_id ?? "—"}</td>
            <td>
              {Array.from({ length: FOX_COUNT }, (_, n) => (
                <span class={n < s.foxes_found ? "seg seg-on" : "seg"} />
              ))}
            </td>
            <td class="muted">{shortTime(s.last_found)}</td>
          </tr>
        ))}
        {scores.length === 0 && (
          <tr>
            <td class="empty" colspan={5}>
              Nog geen spelers geregistreerd.
            </td>
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
    <Layout title="Foxhunt" right={`${scores.length} spelers`}>
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
    <Layout title="Event log" right={`${results.length} events`}>
      <section>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Payload</th>
              <th>Tijd</th>
            </tr>
          </thead>
          <tbody>
            {results.map((e) => (
              <tr>
                <td class="muted">{e.id}</td>
                <td>{e.type}</td>
                <td>
                  <code>{e.payload}</code>
                </td>
                <td class="muted">
                  {e.created_at.slice(0, 19).replace("T", " ")}
                </td>
              </tr>
            ))}
            {results.length === 0 && (
              <tr>
                <td class="empty" colspan={4}>
                  Nog geen events.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </Layout>,
  );
});
