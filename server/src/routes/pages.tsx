import { Hono } from "hono";
import type { Bindings, GameEvent, Player, ScoreRow } from "../types";
import { Layout } from "../components/Layout";
import { Home } from "../components/Home";
import { Companion } from "../components/Companion";
import { decodeCompanion } from "../lib/companion";
import { CREATURES, RARITY_LABEL, creatureById } from "../lib/creatures";
import { starterFor } from "../lib/starter";

export const pageRoutes = new Hono<{ Bindings: Bindings }>();

// The whole roster is the denominator — catching all of them is the game. The
// count comes from the roster itself so adding a beest moves the goalposts
// once, here, and not in a constant somebody forgets.
const ROSTER_SIZE = CREATURES.length;

// HOW MANY, never WHICH. The scoreboard is public and the roster is the
// player's to discover (CLAUDE.md, "Server pages"), so this query counts
// players_creatures and never reads a creature_id. profile_pic rides along
// because the maatje is the player's face on the board.
//
// A wiped account leaves the board the moment it is wiped: taking your name off
// this page is one of the two reasons the delete exists (auth.ts, DELETE /user).
async function fetchScores(db: D1Database): Promise<ScoreRow[]> {
  const { results } = await db
    .prepare(
      `SELECT p.id, p.name, p.hunter_id, p.profile_pic,
              COUNT(pc.creature_id) AS creatures_found,
              MAX(pc.dt_found) AS last_found
       FROM players p
       LEFT JOIN players_creatures pc ON pc.player_id = p.id
       WHERE p.dt_deleted IS NULL
       GROUP BY p.id
       ORDER BY creatures_found DESC, last_found ASC, p.name ASC`,
    )
    .all<ScoreRow>();
  return results;
}

// "2026-08-02T12:34:56.789Z" -> "12:34"
const shortTime = (iso: string | null) => (iso ? iso.slice(11, 16) : "—");

// "2026-08-02T12:34:56.789Z" -> "2026-08-02 12:34:56"
const fullTime = (iso: string | null) =>
  iso ? iso.slice(0, 19).replace("T", " ") : "—";

// The badge prints a hunter as "JGR-0042" everywhere (home, profiel,
// instellingen); a player without an antenna is a verzamelaar, not a jager.
// Never render a 0 as an id — the spec reserves it (CLAUDE.md, hunter_id).
const hunterLabel = (id: number | null) =>
  id ? `JGR-${String(id).padStart(4, "0")}` : "Verzamelaar";

// A missed detail page is a typed URL, not a broken link — say which id and
// point back at the list, in the same chrome as the page they wanted.
const NotFound = ({ what }: { what: string }) => (
  <Layout title="Niet gevonden">
    <section>
      <p class="empty">{what}</p>
      <p class="empty">
        <a href="/debug/players">Terug naar de spelerslijst</a>
      </p>
    </section>
  </Layout>
);

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
          <th>Maatje</th>
          <th>Speler</th>
          <th>Hunter</th>
          <th>Beesten</th>
          <th>Laatst</th>
        </tr>
      </thead>
      <tbody>
        {scores.map((s, i) => (
          <tr>
            <td class="rank">{i + 1}</td>
            <td>
              <Companion code={s.profile_pic} size={32} />
            </td>
            <td>{s.name}</td>
            <td class="muted">{s.hunter_id ?? "—"}</td>
            <td class="beesten">
              <span class="meter">
                <span
                  class="meter-fill"
                  style={`width:${Math.min(100, (s.creatures_found / ROSTER_SIZE) * 100)}%`}
                />
              </span>
              <span class="meter-count">
                {s.creatures_found}/{ROSTER_SIZE}
              </span>
            </td>
            <td class="muted">{shortTime(s.last_found)}</td>
          </tr>
        ))}
        {scores.length === 0 && (
          <tr>
            <td class="empty" colspan={6}>
              Nog geen spelers geregistreerd.
            </td>
          </tr>
        )}
      </tbody>
    </table>
  </section>
);

// Public landing page: what the game is, for players who just got a badge
pageRoutes.get("/", (c) =>
  c.html(
    <Layout
      title="Vossenjacht — het badge-spel van Fri3d Camp"
      description="Spoor de beesten van het bos op. Jaag met een LoRa-antenne op verstopte vossen, of verzamel als verzamelaar het eten dat de beesten nodig hebben."
      bare
    >
      <Home />
    </Layout>,
  ),
);

// Public dashboard
pageRoutes.get("/scores", async (c) => {
  const scores = await fetchScores(c.env.DB);
  return c.html(
    <Layout title="Scorebord" right={`${scores.length} spelers`}>
      <Scoreboard scores={scores} />
    </Layout>,
  );
});

// HTMX partial, polled by the dashboard
pageRoutes.get("/scoreboard", async (c) => {
  const scores = await fetchScores(c.env.DB);
  return c.html(<Scoreboard scores={scores} />);
});

// Player list: HTML table by default, JSON when requested.
// The catch count rides along so the list answers "who is doing well" without
// a click; the click (/debug/players/:id) answers "with what".
//
// Wiped accounts stay listed, tagged GEWIST. The public pages drop them, but
// this page is where an organiser undoes one — you cannot restore a row you
// cannot see, and the wipe is only reversible until the badge registers again.
interface PlayerRow extends Player {
  creature_count: number;
}

pageRoutes.get("/debug/players", async (c) => {
  const { results } = await c.env.DB.prepare(
    `SELECT p.*, COUNT(pc.creature_id) AS creature_count
     FROM players p
     LEFT JOIN players_creatures pc ON pc.player_id = p.id
     GROUP BY p.id
     ORDER BY p.id DESC`,
  ).all<PlayerRow>();

  if (c.req.header("Accept")?.includes("application/json")) {
    return c.json(results);
  }

  return c.html(
    <Layout
      title="Spelers"
      right={`${results.filter((p) => !p.dt_deleted).length} spelers`}
    >
      <section>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Maatje</th>
              <th>Naam</th>
              <th>Badge</th>
              <th>Hunter</th>
              <th>Beesten</th>
              <th>Aangemaakt</th>
            </tr>
          </thead>
          <tbody>
            {results.map((p) => (
              <tr>
                <td class="muted">{p.id}</td>
                <td>
                  <Companion code={p.profile_pic} size={32} />
                </td>
                <td>
                  <a href={`/debug/players/${p.id}`}>{p.name}</a>
                  {p.dt_deleted && <span class="tag tag-deleted">gewist</span>}
                </td>
                <td class="muted">
                  <code>{p.badge_id}</code>
                </td>
                <td class="muted">{p.hunter_id ?? "—"}</td>
                <td class="muted">{p.creature_count}</td>
                <td class="muted">{fullTime(p.dt_created)}</td>
              </tr>
            ))}
            {results.length === 0 && (
              <tr>
                <td class="empty" colspan={7}>
                  Nog geen spelers geregistreerd.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </Layout>,
  );
});

// One player, everything the server knows: the maatje its shortcode decodes
// to, the account fields, the catch list with names, and the events that
// wrote all of it.
pageRoutes.get("/debug/players/:id", async (c) => {
  const id = Number(c.req.param("id"));
  const wantsJson = c.req.header("Accept")?.includes("application/json");
  if (!Number.isInteger(id) || id < 1) {
    if (wantsJson) return c.json({ error: "invalid player id" }, 400);
    return c.html(<NotFound what="Ongeldig speler-id." />, 400);
  }

  const player = await c.env.DB.prepare("SELECT * FROM players WHERE id = ?")
    .bind(id)
    .first<Player>();
  if (!player) {
    if (wantsJson) return c.json({ error: "unknown player id" }, 404);
    return c.html(<NotFound what={`Geen speler met id ${id}.`} />, 404);
  }

  const [caught, events] = await Promise.all([
    c.env.DB.prepare(
      "SELECT creature_id, dt_found FROM players_creatures WHERE player_id = ? ORDER BY dt_found",
    )
      .bind(id)
      .all<{ creature_id: number; dt_found: string }>(),
    // The event log is append-only and every entry this player caused carries
    // its player_id in the payload — json_extract is the only way back in.
    c.env.DB.prepare(
      `SELECT * FROM game_events
       WHERE json_extract(payload, '$.player_id') = ?
       ORDER BY id DESC LIMIT 100`,
    )
      .bind(id)
      .all<GameEvent>(),
  ]);

  // Which creature the account started with is not stored — it is a pure
  // function of the badge_id (lib/starter.ts), so it can be recomputed here
  // and the one grant the server made itself is labelled as such.
  const starterId = starterFor(player.badge_id);

  if (wantsJson) {
    return c.json({
      ...player,
      starter: starterId,
      creatures: caught.results.map((r) => ({
        ...r,
        naam: creatureById(r.creature_id)?.naam ?? null,
        rarity: creatureById(r.creature_id)?.rarity ?? null,
      })),
      companion: decodeCompanion(player.profile_pic),
      events: events.results.map((e) => ({
        ...e,
        payload: JSON.parse(e.payload),
      })),
    });
  }

  return c.html(
    <Layout title={player.name} right={`${caught.results.length} beesten`}>
      <section class="profile">
        <Companion code={player.profile_pic} size={96} />
        <dl>
          <dt>Speler</dt>
          <dd>
            {player.name} <span class="muted">#{player.id}</span>
            {player.dt_deleted && <span class="tag tag-deleted">gewist</span>}
          </dd>
          <dt>Hunter</dt>
          <dd>{hunterLabel(player.hunter_id)}</dd>
          <dt>Badge</dt>
          <dd>
            <code>{player.badge_id}</code>
          </dd>
          <dt>Maatje</dt>
          <dd>
            <code>{player.profile_pic || "—"}</code>
          </dd>
          <dt>Aangemaakt</dt>
          <dd class="muted">{fullTime(player.dt_created)}</dd>
          <dt>Gewijzigd</dt>
          <dd class="muted">{fullTime(player.dt_updated)}</dd>
          {player.dt_deleted && (
            <>
              <dt>Gewist</dt>
              <dd class="muted">{fullTime(player.dt_deleted)}</dd>
            </>
          )}
        </dl>
      </section>

      <h2>Beesten</h2>
      <section>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Naam</th>
              <th>Zeldzaamheid</th>
              <th>Gevangen</th>
            </tr>
          </thead>
          <tbody>
            {caught.results.map((r) => {
              const creature = creatureById(r.creature_id);
              return (
                <tr>
                  <td class="muted">{r.creature_id}</td>
                  <td>
                    {creature?.naam ?? <span class="muted">onbekend</span>}
                    {r.creature_id === starterId && (
                      <span class="tag tag-starter">startbeest</span>
                    )}
                  </td>
                  <td class="muted">
                    {creature ? RARITY_LABEL[creature.rarity] : "—"}
                  </td>
                  <td class="muted">{fullTime(r.dt_found)}</td>
                </tr>
              );
            })}
            {caught.results.length === 0 && (
              <tr>
                <td class="empty" colspan={4}>
                  Nog geen beesten gevangen.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <h2>Events</h2>
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
            {events.results.map((e) => (
              <tr>
                <td class="muted">{e.id}</td>
                <td>{e.type}</td>
                <td>
                  <code>{e.payload}</code>
                </td>
                <td class="muted">{fullTime(e.created_at)}</td>
              </tr>
            ))}
            {events.results.length === 0 && (
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
                <td class="muted">{fullTime(e.created_at)}</td>
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
