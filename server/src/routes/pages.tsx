import { Hono } from "hono";
import { getCookie, setCookie } from "hono/cookie";
import type {
  Bindings,
  FirstDiscovery,
  GameEvent,
  Player,
  ScoreBoards,
  ScoreRow,
} from "../types";
import { Layout } from "../components/Layout";
import { Home } from "../components/Home";
import { SnuffelRules } from "../components/SnuffelRules";
import { Companion } from "../components/Companion";
import { decodeCompanion } from "../lib/companion";
import { CREATURES, RARITY_LABEL, creatureById } from "../lib/creatures";
import { DISCOVERY_ART } from "../lib/discovery-art";
import { starterFor } from "../lib/starter";
import {
  SELF_FOUND_POINTS,
  HELP_POINTS,
  PLUK_POINTS,
  MEET_POINTS,
  BONDED_POINTS,
  CAMP_START_S,
  CAMP_END_S,
  CAMP_START_ISO,
  CAMP_END_ISO,
  CAMP_PHASES,
  BOSS_BADGE_IDS,
} from "../lib/scoring";

export const pageRoutes = new Hono<{ Bindings: Bindings }>();

// The /debug pages list every badge_id, and a badge_id is the only credential
// the unauthenticated API has — public, those pages turn "vandalise the one
// account whose MAC you can see" into "loop over the whole camp". With the
// DEBUG_KEY secret set they need ?key=<secret> once (a cookie carries it
// across the links); unset, they stay open for local dev. Set it in prod.
pageRoutes.use("/debug/*", async (c, next) => {
  const key = c.env.DEBUG_KEY;
  if (!key) return next();
  const offered = c.req.query("key");
  if (offered === key) {
    setCookie(c, "debug_key", key, {
      path: "/debug",
      httpOnly: true,
      secure: true,
      sameSite: "Lax",
      maxAge: 7 * 24 * 60 * 60,
    });
    return next();
  }
  if (
    getCookie(c, "debug_key") === key ||
    c.req.header("Authorization") === `Bearer ${key}`
  )
    return next();
  return c.text("debug is vergrendeld - voeg ?key=... toe", 403);
});

// The whole roster is the denominator — catching all of them is the game. The
// count comes from the roster itself so adding a beest moves the goalposts
// once, here, and not in a constant somebody forgets.
const ROSTER_SIZE = CREATURES.length;
const BASE_IDS = CREATURES.filter((c) => c.rarity === "norm")
  .map((c) => c.id)
  .join(",");
const RARE_IDS = CREATURES.filter((c) => c.rarity === "rare")
  .map((c) => c.id)
  .join(",");
const LEGENDARY_IDS = CREATURES.filter((c) => c.rarity === "leg")
  .map((c) => c.id)
  .join(",");

// The ranking tables show HOW MANY, never WHICH. The roster is the player's
// to discover (CLAUDE.md, "Server pages"), so this query counts
// players_creatures and never reads a creature_id out. The deliberately
// separate first-discovery query below is the narrow exception: it reveals a
// normal creature only after a hunter found it, and keeps rare/legendary
// identities behind pre-baked silhouettes. profile_pic rides along because
// the maatje is the player's face on the board.
//
// Two boards, never mixed (GAME_DESIGN.md, Scoring): the SQL collects the
// fenced per-tier/self-report COUNTS, TypeScript owns the point values
// (lib/scoring — one place to tune), and every live player lands on exactly
// one list, keyed on hunter_id.
//
// A wiped account leaves the board the moment it is wiped: taking your name off
// this page is one of the two reasons the delete exists (auth.ts, DELETE /user).
const CAMP_PHASE_LIST = CAMP_PHASES.map((p) => `'${p}'`).join(",");
const BOSS_BADGE_PLACEHOLDERS = BOSS_BADGE_IDS.map(() => "?").join(",");

interface ScoreCountRow {
  id: number;
  name: string;
  hunter_id: number | null;
  profile_pic: string;
  creatures_found: number;
  self_found: number;
  self_base: number;
  self_rare: number;
  self_leg: number;
  players_helped: number;
  pluks_scored: number;
  players_met: number;
  sparks: number;
  bonded: number;
  last_found: string | null;
}

interface FirstDiscoveryRow {
  creature_id: number;
  discovered_at: string;
  player_name: string;
  profile_pic: string;
}

async function fetchScores(db: D1Database): Promise<ScoreBoards> {
  const { results } = await db
    .prepare(
      `SELECT p.id, p.name, p.hunter_id, p.profile_pic,
              COUNT(pc.creature_id) AS creatures_found,
              COALESCE(SUM(CASE WHEN pc.self_found = 1 THEN 1 ELSE 0 END), 0)
                AS self_found,
              COALESCE(SUM(
                CASE
                  WHEN pc.self_found = 1
                   AND pc.dt_self_found >= '${CAMP_START_ISO}'
                   AND pc.dt_self_found <  '${CAMP_END_ISO}'
                   AND pc.creature_id IN (${BASE_IDS})
                  THEN 1 ELSE 0
                END), 0) AS self_base,
              COALESCE(SUM(
                CASE
                  WHEN pc.self_found = 1
                   AND pc.dt_self_found >= '${CAMP_START_ISO}'
                   AND pc.dt_self_found <  '${CAMP_END_ISO}'
                   AND pc.creature_id IN (${RARE_IDS})
                  THEN 1 ELSE 0
                END), 0) AS self_rare,
              COALESCE(SUM(
                CASE
                  WHEN pc.self_found = 1
                   AND pc.dt_self_found >= '${CAMP_START_ISO}'
                   AND pc.dt_self_found <  '${CAMP_END_ISO}'
                   AND pc.creature_id IN (${LEGENDARY_IDS})
                  THEN 1 ELSE 0
                END), 0) AS self_leg,
              (SELECT COUNT(*)
                 FROM helped_players hp
                 JOIN creature_shares first_share ON first_share.id = hp.first_share_id
                WHERE hp.giver_id = p.id
                  AND first_share.occurred_at >= ${CAMP_START_S}
                  AND first_share.occurred_at <  ${CAMP_END_S})
                AS players_helped,
              (SELECT COUNT(*) FROM pluks pk
                WHERE pk.player_id = p.id AND pk.scored = 1
                  AND pk.phase IN (${CAMP_PHASE_LIST}))
                AS pluks_scored,
              (SELECT COUNT(DISTINCT
                  CASE WHEN vs.player_a = p.id THEN vs.player_b
                       ELSE vs.player_a END)
                FROM verified_sparks vs
                WHERE (vs.player_a = p.id OR vs.player_b = p.id)
                  AND vs.occurred_at >= ${CAMP_START_S}
                  AND vs.occurred_at <  ${CAMP_END_S})
                AS players_met,
              (SELECT COUNT(*) FROM verified_sparks vs
                WHERE (vs.player_a = p.id OR vs.player_b = p.id)
                  AND vs.occurred_at >= ${CAMP_START_S}
                  AND vs.occurred_at <  ${CAMP_END_S})
                AS sparks,
              MIN(p.bonded, COUNT(pc.creature_id), ${ROSTER_SIZE}) AS bonded,
              MAX(pc.dt_found) AS last_found
       FROM players p
       LEFT JOIN players_creatures pc ON pc.player_id = p.id
       WHERE p.dt_deleted IS NULL
         AND p.badge_id NOT IN (${BOSS_BADGE_PLACEHOLDERS})
       GROUP BY p.id`,
    )
    .bind(...BOSS_BADGE_IDS)
    .all<ScoreCountRow>();

  const rows: ScoreRow[] = results.map((r) => ({
    ...r,
    hunter_score:
      r.self_base * SELF_FOUND_POINTS.norm +
      r.self_rare * SELF_FOUND_POINTS.rare +
      r.self_leg * SELF_FOUND_POINTS.leg +
      r.players_helped * HELP_POINTS,
    gatherer_score:
      r.pluks_scored * PLUK_POINTS +
      r.players_met * MEET_POINTS +
      r.bonded * BONDED_POINTS,
  }));

  const jagers = rows
    .filter((r) => r.hunter_id !== null)
    .sort(
      (a, b) =>
        b.hunter_score - a.hunter_score ||
        b.self_found - a.self_found ||
        b.players_helped - a.players_helped ||
        a.name.localeCompare(b.name),
    );
  const verzamelaars = rows
    .filter((r) => r.hunter_id === null)
    .sort(
      (a, b) =>
        b.gatherer_score - a.gatherer_score ||
        b.players_met - a.players_met ||
        b.bonded - a.bonded ||
        b.creatures_found - a.creatures_found ||
        a.name.localeCompare(b.name),
    );
  const { results: discoveryRows } = await db
    .prepare(
      `WITH ranked AS (
         SELECT pc.creature_id,
                pc.dt_self_found AS discovered_at,
                p.name AS player_name,
                p.profile_pic,
                ROW_NUMBER() OVER (
                  PARTITION BY pc.creature_id
                  ORDER BY pc.dt_self_found, p.id
                ) AS discovery_rank
           FROM players_creatures pc
           JOIN players p ON p.id = pc.player_id
          WHERE pc.self_found = 1
            AND pc.dt_self_found >= '${CAMP_START_ISO}'
            AND pc.dt_self_found <  '${CAMP_END_ISO}'
            AND p.hunter_id IS NOT NULL
            AND p.dt_deleted IS NULL
            AND p.badge_id NOT IN (${BOSS_BADGE_PLACEHOLDERS})
       )
       SELECT creature_id, discovered_at, player_name, profile_pic
         FROM ranked
        WHERE discovery_rank = 1
        ORDER BY discovered_at DESC, creature_id`,
    )
    .bind(...BOSS_BADGE_IDS)
    .all<FirstDiscoveryRow>();

  const first_discoveries: FirstDiscovery[] = discoveryRows.flatMap((row) => {
    const creature = creatureById(row.creature_id);
    const art = DISCOVERY_ART[row.creature_id];
    if (!creature || !art) return [];
    return [
      {
        ...row,
        creature_name: creature.rarity === "norm" ? creature.naam : null,
        rarity: creature.rarity,
        art,
      },
    ];
  });
  const most_social = rows
    .filter((r) => r.sparks > 0)
    .sort(
      (a, b) =>
        b.sparks - a.sparks ||
        b.players_met - a.players_met ||
        a.name.localeCompare(b.name),
    )
    .slice(0, 3);
  return { jagers, verzamelaars, first_discoveries, most_social };
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

const BeestenMeter = ({ found }: { found: number }) => (
  <td class="beesten">
    <span class="meter">
      <span
        class="meter-fill"
        style={`width:${Math.min(100, (found / ROSTER_SIZE) * 100)}%`}
      />
    </span>
    <span class="meter-count">
      {found}/{ROSTER_SIZE}
    </span>
  </td>
);

const Spotlight = ({
  title,
  subtitle,
  scores,
  value,
  empty,
  kind,
}: {
  title: string;
  subtitle: string;
  scores: ScoreRow[];
  value: (score: ScoreRow) => string;
  empty: string;
  kind: "helpful" | "social";
}) => (
  <article class={`spotlight spotlight-${kind}`}>
    <div class="spotlight-heading">
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </div>
    <ol>
      {scores.map((s, i) => (
        <li>
          <span class="spotlight-rank">{i + 1}</span>
          <Companion code={s.profile_pic} size={48} />
          <span class="spotlight-player">
            <strong>{s.name}</strong>
            <small>{s.hunter_id ? "Jager" : "Verzamelaar"}</small>
          </span>
          <strong class="spotlight-value">{value(s)}</strong>
        </li>
      ))}
      {scores.length === 0 && <li class="empty">{empty}</li>}
    </ol>
  </article>
);

const discoveryLabel = (discovery: FirstDiscovery) =>
  discovery.creature_name ??
  (discovery.rarity === "rare" ? "Zeldzaam beest" : "Legendarisch beest");

const FirstDiscoveries = ({
  discoveries,
}: {
  discoveries: FirstDiscovery[];
}) => (
  <article class="spotlight spotlight-discoveries">
    <div class="spotlight-heading">
      <h2>Eerste ontdekkers</h2>
      <p>Alle eerste vondsten — veeg of scroll om verder te kijken</p>
    </div>
    <ol tabindex={0} aria-label="Eerste ontdekkers, horizontaal scrollbaar">
      {discoveries.map((discovery) => {
        const label = discoveryLabel(discovery);
        return (
          <li class="first-discovery">
            <img
              class="discovery-art"
              src={discovery.art}
              alt={
                discovery.creature_name
                  ? label
                  : `Silhouet van een ${label.toLowerCase()}`
              }
              width="56"
              height="56"
            />
            <Companion code={discovery.profile_pic} size={40} />
            <span class="discovery-details">
              <strong>{label}</strong>
              <span>{discovery.player_name}</span>
              <small>gevonden om {shortTime(discovery.discovered_at)}</small>
            </span>
          </li>
        );
      })}
      {discoveries.length === 0 && (
        <li class="empty">Nog geen eerste vondsten.</li>
      )}
    </ol>
  </article>
);

// Two boards, two ranking keys, never one total (GAME_DESIGN.md, Scoring).
// Each table shows its score's own breakdown beside the total, and nothing
// of the other game's.
const Scoreboard = ({ scores }: { scores: ScoreBoards }) => (
  <section
    id="scoreboard"
    hx-get="/scoreboard"
    hx-trigger="every 5s"
    hx-swap="outerHTML"
  >
    <div class="scoreboard-column scoreboard-hunters">
      <div class="scoreboard-heading">
        <h2>Jagers</h2>
        <span>{scores.jagers.length}</span>
      </div>
      <div class="scoreboard-table">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Maatje</th>
              <th>Speler</th>
              <th>Score</th>
              <th>
                Beesten
                <span class="scoreboard-subhead">zelf gevonden</span>
              </th>
              <th>Laatst</th>
            </tr>
          </thead>
          <tbody>
            {scores.jagers.slice(0, 10).map((s, i) => (
              <tr>
                <td class="rank">{i + 1}</td>
                <td>
                  <Companion code={s.profile_pic} size={32} />
                </td>
                <td>{s.name}</td>
                <td class="score">{s.hunter_score}</td>
                <BeestenMeter found={s.self_found} />
                <td class="muted">{shortTime(s.last_found)}</td>
              </tr>
            ))}
            {scores.jagers.length === 0 && (
              <tr>
                <td class="empty" colspan={6}>
                  Nog geen jagers met een antenne.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>

    <div class="scoreboard-column scoreboard-gatherers">
      <div class="scoreboard-heading">
        <h2>Verzamelaars</h2>
        <span>{scores.verzamelaars.length}</span>
      </div>
      <div class="scoreboard-table">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Maatje</th>
              <th>Speler</th>
              <th>Score</th>
              <th>Pluk</th>
              <th>Ontmoet</th>
              <th>Besties</th>
              <th>
                Beesten
                <span class="scoreboard-subhead">in je boek</span>
              </th>
              <th>Laatst</th>
            </tr>
          </thead>
          <tbody>
            {scores.verzamelaars.slice(0, 10).map((s, i) => (
              <tr>
                <td class="rank">{i + 1}</td>
                <td>
                  <Companion code={s.profile_pic} size={32} />
                </td>
                <td>{s.name}</td>
                <td class="score">{s.gatherer_score}</td>
                <td>{s.pluks_scored}</td>
                <td>{s.players_met}</td>
                <td>{s.bonded}</td>
                <BeestenMeter found={s.creatures_found} />
                <td class="muted">{shortTime(s.last_found)}</td>
              </tr>
            ))}
            {scores.verzamelaars.length === 0 && (
              <tr>
                <td class="empty" colspan={9}>
                  Nog geen verzamelaars geregistreerd.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>

    <div class="scoreboard-spotlights">
      <FirstDiscoveries discoveries={scores.first_discoveries} />
      <Spotlight
        title="Meeste vonken"
        subtitle="De sociaalste spelers, over jagers en verzamelaars samen"
        scores={scores.most_social}
        value={(s) => `${s.sparks} vonken`}
        empty="Nog geen vonken geregistreerd."
        kind="social"
      />
    </div>
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

// Unlinked rules preview. It is intentionally absent from Home and the public
// navigation: players only reach it when somebody gives them the URL.
pageRoutes.get("/snuffelregels", (c) =>
  c.html(
    <Layout
      title="Snuffelregels — Vossenjacht"
      description="De nieuwe regels voor snuffelen, vonken, beesten delen en punten."
      bare
      noindex
    >
      <SnuffelRules />
    </Layout>,
  ),
);

// Public dashboard
pageRoutes.get("/scores", async (c) => {
  const scores = await fetchScores(c.env.DB);
  const count = scores.jagers.length + scores.verzamelaars.length;
  return c.html(
    <Layout title="Scorebord" right={`${count} spelers`} wide poll>
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
      `SELECT creature_id, dt_found, self_found, dt_self_found
       FROM players_creatures WHERE player_id = ? ORDER BY dt_found`,
    )
      .bind(id)
      .all<{
        creature_id: number;
        dt_found: string;
        self_found: number;
        dt_self_found: string | null;
      }>(),
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
              <th>Zelf gevonden</th>
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
                  <td class="muted">
                    {r.self_found ? fullTime(r.dt_self_found) : "—"}
                  </td>
                  <td class="muted">{fullTime(r.dt_found)}</td>
                </tr>
              );
            })}
            {caught.results.length === 0 && (
              <tr>
                <td class="empty" colspan={5}>
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
