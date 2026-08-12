# Vossenjacht — Game Design

## Purpose

Vossenjacht is an ARDF game for Fri3d Camp. Players with a LoRa antenna can hunt
physical transmitters and discover creatures. Not every player will have an
antenna, so the game also needs a complete experience for players who cannot
participate in the physical hunt.

The two play tracks are:

- **Hunters** (jagers) discover creatures using LoRa direction finding.
- **Gatherers** (verzamelaars) forage the camp for the food, toys and materials
  that creatures need.

Together they are the **jager-verzamelaars** — the Dutch term for
hunter-gatherers, which is exactly the fiction: a camp-wide tribe where some
bring back the animals and others bring back the berries, and everyone raises
the creatures together.

> Hunters bring creatures into the camp. Gatherers bring the means to raise
> them. Caring is the shared game everyone plays.

This is the structural insight that makes the split work: **Hunt and Gather are
acquisition tracks; Care is the common game.** Neither track is a lesser
substitute, because neither can progress fully alone — a hunter with no food
has hungry creatures, a gatherer with no creatures has a full pantry and no one
to feed. The bridge between them is a deliberate, face-to-face exchange.

Hunters may also gather and gatherers may also care deeply; having an antenna
*adds* the Hunt track, it excludes nothing. Specialisation emerges naturally
from where players spend their time, not from a locked role choice.

## Positive care philosophy

Creatures have one temporary need: energy. It drains over time and with
play, and eating refills it — a reason to interact. A tired creature is an
invitation to feed it, not a punishment for staying away.

Permanent progress is safe:

- Creatures never die, disappear or run away.
- Bond levels, skills, memories and unlocks never decay.
- Players do not lose points for being absent.
- There are no punitive streaks or deadlines.
- Returning language should be welcoming rather than guilt-inducing.

For example, the game should say, "Everzwaan heeft trek — tijd voor een
hapje!", not imply that the player neglected it.

Creatures may playfully refuse an unsuitable action—a full creature need not
eat and a tired creature may not want to play—but an unsuccessful choice should
not subtract permanent progress.

**Need is pull, not push — that is why a big roster is never a chore.** A
tired creature loses nothing: bond never decays, and low energy's only teeth
are that a tired creature will not play. So the player feeds the one creature
they are about to play with, at the moment they want to play; the other twenty
wait patiently, unharmed. Food demand scales with how many creatures you
*play* with, not how many you *own*. Guard this structurally: no roster-wide
need indicators (red badges on the home grid, "5 beesten zijn moe!"
notifications) and no need-stats in public score — either would turn the
collection into a feeding shift.

Energy is deliberately the ONLY living need. It used to sit beside hunger,
and the two gates could deadlock: a creature "not hungry" (so feeding
refused) yet too tired to play had no move left. One meter closes that loop
by construction — eating refills exactly the stat that play spends.

The same philosophy extends to the exchange economy: there is no exchange UI
at all. A snuffel *is* the exchange — both badges automatically share a
picknick, and sometimes a creature tags along (vonk-geluk). Nothing to
choose, nothing to price, nothing to haggle over: the reward is for meeting,
not for trading.

## Existing foundations

The current app already contains much of the presentation needed for the care
game:

- Bond, levels and hearts.
- Hunger and energy.
- Feeding, petting and playing.
- Berry, nut and acorn food, with creature-specific favourites.
- A dossier containing habitat, species, rarity and facts.
- Stored nickname and sightings fields that can be developed further.
- A customisable companion (maatje) created during onboarding.

The economy around these screens is the three verbs below, tied together by
the energy chain. It is implemented: food is a finite pantry (voorraad) that
feeding drains and plukken refills, play costs energy, and bond comes from
play — so neither food-dumping nor tap-farming can maximise bond.

## The three verbs: snuffelen, plukken, spelen

The gatherer game is three modes — one per thing the badge can sense — and
each is a physical behaviour:

| Verb | Radio | You need | Physical behaviour |
|---|---|---|---|
| **Snuffelen** | ESP-NOW | another *person* | walk up to someone |
| **Plukken** | WiFi scan, passive | a *place* | walk to a hotspot |
| **Spelen** | none | *time* | sit down with a creature |

Together they cover a camp day: sometimes you are near people, sometimes you
are roaming, sometimes it rains and you are in the tent. Each verb is the
fallback for the other two. Care — feeding, petting — is not a fourth mode;
it lives with the creature and is what the three verbs are *for*.

The verbs share one fiction: the player behaves like an animal too. You sniff
at strangers, you forage the terrain, you play. A jager-verzamelaar does not
only raise creatures — they are one.

### Snuffelen — meet people

The face-to-face ESP-NOW handshake, described in full under *The exchange*
below. It is one way a collection grows beyond the startbeest (vonk-geluk),
the source of vonken and vriendenboekje pages, and the way surplus food
reaches hungry hunters. Plukken is the independent terrain-based route into
the same creature-introduction payoff.

### Plukken — work the terrain

The camp terrain has multiple WiFi hotspots that all broadcast the badge
network `fri3d-badge`. Foraging is **listening** to them:

- The badge does a passive scan; it transmits nothing, and no beacon hardware
  is built or deployed for the game. The infrastructure is whatever already
  hangs on the terrain.
- The SSID is shared, so a spot's identity is its **BSSID** — the radio MAC
  the scan reports anyway.
- To pluk: open the plukscherm, scan, and walk toward a spot while the signal
  grows — the same "walk toward an invisible signal" joy as direction
  finding, at WiFi range and a difficulty a seven-year-old can manage. Above
  a signal threshold the spot can be harvested.
- **Each spot reloads per badge.** After you pluk hotspot X, X is depleted
  *for you* for on the order of an hour. Camping a spot yields once per
  reload; covering ground multiplies. Anti-camping is built into the
  mechanic and needs no server.
- **Yields come from a formula**, `(BSSID, camp phase) → resource`, so different
  spots give different food and every spot re-deals each camp phase — a complete
  pantry requires covering ground, just as a complete roster requires
  finding every fox. Base-tier encounters are a seeded roll on the same
  inputs, so rescanning cannot reroll them.
- **Any BSSID that broadcasts the SSID counts — no allowlist.** Someone who
  runs their own `fri3d-badge` hotspot beside their tent has hacked
  themselves some berries; at a hacker camp that is a feature, not a leak.
  Food is local state, so the cheat stays a single-player mod (see
  *Adversarial risks*).

#### Wild encounters while plukken

A plukplek can also hold a **wild creature encounter**. This is the
verzamelaar's terrain-discovery track: snuffelen encounters a creature through
another person, plukken encounters one through a place, and jagen encounters
one through a LoRa fox. All three end with the creature introducing itself;
their source and provenance stay distinct.

Creature opportunities follow a narrow, base-tier version of the
vonk-geluk shape:

1. Select one **base-tier** creature the player does not know.
2. Apply the seeded encounter chance.
3. A miss remains invisible; the normal food harvest still pays out.
4. A hit adds the creature permanently with `pluk` provenance and queues a
   narrow server report so account restore cannot lose it.

**Rare and legendary creatures are never eligible.** Plukken is the solo
collection floor and care economy; LoRa hunting and social spread own the
upper tiers. Badge id remains part of the seed, so repeating the same scan
never rerolls it.

Food and creatures have separate cadences:

- Food reloads per badge after roughly one hour, as before.
- A BSSID offers at most **one creature roll per badge per camp phase**.
- The 72-hour camp is three exact phases: Thursday 15:00–Friday 15:00,
  Friday 15:00–Saturday 15:00, and Saturday 15:00–Sunday 15:00. This avoids a
  fourth pseudo-day merely because the camp crosses four calendar dates.

With about 70 APs this gives 210 theoretical opportunities, but tuning targets
real walking routes rather than a full clear. Keep the existing invisible 40%
opportunity gate and 45% base encounter chance as starting values (18%
effective per opportunity), then tune against field data. Once a player knows
every base creature, plukken yields food only.

Camp assignments, movement missions and mini-games stay as alternative food
sources for players who cannot roam.

### Random visitors — the collection floor

A verzamelaar who does not gain enough creatures through snuffelen or plukken
receives up to three scheduled visitors. Their broad, per-badge seeded windows
are 2–4, 18–26 and 38–48 hours after registration; each is skipped when the
collection has already reached two, three or four creatures respectively. A
full-weekend solo player therefore reaches four creatures including the
startbeest, while an active player sees fewer or no fallback meetings.

A due visitor waits permanently behind a calm home-screen notification. The
player opens a campsite scene, says hello to the silhouette, and the creature
joins the book. There is no countdown, inventory cost, wrong choice or failure
state. Only one visitor waits at once, and claimed visits leave at least six
hours before another can appear.

Visitors are selected only from unknown **base-tier creatures**. This is a hard
rule on both badge and server: rare and legendary creatures never come from a
random visit. A waiting visitor survives a later WORD JAGER upgrade, but jagers
do not schedule new ones. The hidden debug menu can schedule a local-only visit
after ten seconds so the complete visual flow can be tested without changing
server collection state.

### Spelen — turn food into bond

Mini-games close the economy. The chain is:

> **Plukken yields food → voederen restores energy → spelen spends energy
> and builds bond.**

- A play session costs the creature energy. A tired creature playfully
  refuses — "Everzwaan is moe — eerst een hapje?" — so the refusal *is* the
  rate limit, in fiction, exactly as the care philosophy asks.
- Feeding restores energy; a favourite food restores more. Feeding itself
  grants little bond.
- **Bond comes from playing, not from feeding.** Feeding is the enabler,
  playing is the earner. One mechanism kills both economy bugs named above:
  food-dumping (50 berries is a very full creature, not max bond) and
  tap-farming (play needs energy, energy needs food, food needs walking).

The beestenschool's three launch games cover the badge's inputs with nothing
to explain: **VLIEGEN** (tap to flap, dodge the branches), **VANGEN** (the
creature trots left and right, tap to turn, catch the falling hapjes),
**DANSEN** (the creature demonstrates a sequence of directional moves for the
player to repeat with the joystick; buzzer notes and LEDs play along). Costs
are 2/1/1 energy segments; each creature favours one game for extra band.
DOOLHOF (tilt maze) waits on the IMU spike.

The companion stars in exactly one game moment: the tutorial, before the
player owns any creature. After that the active creature stars, because
playing is how bond grows and bond belongs to creatures. Petting and basic
affection stay free and unlimited — they give warmth and nothing else: no
stats, no progression, so bond can never be tapped into existence.

Permanent progression consists of bond, skills, memories, decorations and
friendships. Hunger and energy provide temporary context.

## The exchange: snuffelen en vonken

All face-to-face interactions run through **one physical mechanic** with
different payloads, rather than a different flow per feature. The mechanic is
also the home-screen mode: the button says **Snuffelen**, and opening it is
the consent step — both badges must be in the mode before anything is
exchanged. The radio demands the same thing anyway: ESP-NOW needs both badges
off camp WiFi and pinned to one shared channel (measured in the espnow-test
experiment), so the explicit mutual mode is physics and etiquette agreeing.

### Snuffelen (the ESP-NOW handshake)

Two badges are held together and exchange a small payload over **ESP-NOW**. The
fiction writes itself in Dutch: when two animals meet, they sniff each other —
**snuffelen**. Hold the badges nose to nose and the creatures *besnuffelen
elkaar*. On success both badges celebrate simultaneously — LEDs, buzzer,
matching animation — the audible "clink" that makes the moment feel real.

**Not IR, and that costs us something.** This section originally specified an
IR airdrop. The badge cannot do it: it has an IR *receiver* and no
transmitter, so there is nothing to snuffel *with*. ESP-NOW replaces it.

The swap matters more than a transport swap usually does. With IR, the terrible
range and alignment *were* the consent mechanism — free, and unspoofable from a
distance. ESP-NOW carries across the field, so proximity is no longer a property
of the radio. It is now **a rule we enforce, at an RSSI floor of -50 dBm**:
below that, a handshake is ignored. The intent is unchanged — nobody can be
sniffed from across the field, both players must physically opt in — but it
rests on a threshold we picked rather than on physics, which means it has to be
measured in the field and can be tuned or defeated. Payloads stay
shortcode-sized, far under anything ESP-NOW strains at.

There is no manual fallback: the snuffel code was cut in 2026-08 — it
carried no secret, typing any name minted the reward, so it was
self-service cheating rather than a fallback (see *Connectivity and
trust*). The SNF mirror frame covers the handshake race instead. The fox
keypad (`screen_code`) is a different mechanic and stays.

### What a snuffel carries

Nothing is chosen and nothing is attached: the handshake itself pays out,
automatically, and the payoff screen has no decisions. The two directions are
resolved independently; one player never needs to match the value of what the
other can share.

- **Food is generated, never transferred from inventory.** When one direction
  has no eligible creature, that player fictionally brings a picknick and the
  recipient gains generated food. The contributor loses nothing. This is a
  deliberate protection for new and younger players whose pantry must never
  become the price of participating.
- **Only a vonk can carry a creature** (vonk-geluk, below). A repeat snuffel
  without a vonk can generate food, but cannot introduce any creature even if
  the two books differ. This is the structural anti-spam rule: returning to
  the same friend every hour helps care, while growing the collection asks
  players to meet someone new or wait for that pair's next vonk.
- **Each direction resolves separately.** A new verzamelaar can receive a
  rare spoor from a jager while sending a generated picknick back. If both
  directions have eligible creatures, both may travel; if neither does, both
  receive food.
- **Speeldate** (any ↔ any) stays a deliberate, longer cooperative
  interaction — the one thing a plain handshake doesn't give you.

### De vonk (the anti-farming rule)

The handshake and vonk are eligibility events, not points by themselves. A
verified creature introduction may mark the recipient as **helped** by the
giver, worth 50 points only the first time that giver helps that player. A
snuffel between a given pair produces a **vonk** for both immediately on their
first meeting, then once the
pair's **6-hour cooldown** has passed. That cadence permits at most four
vonken for the same pair in any rolling 24 hours. A separate **1-hour food
cooldown** allows the same pair to share a generated picknick between vonken;
inside the hour the handshake still celebrates but pays nothing. This gives:

- an incentive to walk up to strangers (new pair → new vonk),
- no incentive to stand in a corner farming one friend,
- no hard "never again" wall between friends — utility transfer continues,
  once an hour, but creature transfer waits six hours,
- and a reason to seek new people: a fresh pair gets a vonk immediately while
  the familiar pair can offer only food.

Both cooldowns are per pair, wall-clock and survive midnight — a 23:00 vonk
does not re-arm at 00:00. "Four per day" is therefore a rolling consequence
of the six-hour cadence, not a calendar reset that can be gamed at midnight.

### Vonk-geluk (the creature chance)

On a vonk, each direction selects one eligible creature the recipient does not
know. If one exists, it introduces itself: both players keep the creature and
lineage is preserved. The introduction is guaranteed once selected; scarcity
comes from finding the creature, eligibility, the six-hour pair cadence and
meeting people, not from a second invisible failure roll. If no candidate is
eligible, that direction produces a generated picknick instead.

Eligibility depends on rarity:

- **Base:** any owner may share it with any other player on a vonk.
- **Rare:** the first social hop is jager → verzamelaar. After that, a rare
  spoor may continue through the graph: a verzamelaar who received it may
  share it with either role on a later vonk. Rares spread, but only through
  real face-to-face vonken. A jager who receives a rare this way owns it but
  does **not** receive the `zelf gevonden` stamp, its 300 discovery points, or
  permission to share it onward. If they later find that creature's LoRa fox
  themselves, the bridge upgrades it to `zelf gevonden`, awards the 300 points
  exactly once and unlocks sharing for that jager.
- **Legendary:** every lineage branch permits exactly one social hop, from a
  jager who has the creature stamped **zelf gevonden** to a verzamelaar. That
  self-finding jager may introduce it to other distinct verzamelaars on later
  eligible vonken, but every recipient is an endpoint. A jager who only
  received the legendary cannot share it; a receiving verzamelaar cannot
  forward it; and a legendary never travels to a jager. The `zelf` bit is
  therefore authoritative eligibility state, not decorative dossier copy.

A short random session token in the presence frame lets both badges derive the
same directed choices without either badge opening a trade UI.

### Het vriendenboekje (the permanent layer)

The vonk re-arms on its cooldown; the **vriendenboekje** never resets. The first time two
badges *ever* meet, each writes the other a page: companion avatar, name,
day. It is a pure collection — it never decays, it grows all weekend, and it
gives a snuffel between two empty-handed gatherers a payoff beyond the vonk.
Every kid at a Flemish camp knows the friend-book ritual; the artifact frames
meeting people as keeping memories, never as collecting people.

## Naming the clone

When a hunter shares a creature, the recipient gets their own copy and the
hunter keeps theirs. "Clone" is the mechanic; it should not be the word.
Candidates for the Dutch UI verb:

| Candidate | For | Against |
|---|---|---|
| **Een spoor delen** | In-fiction (ARDF trails); explains *why* both players have the creature — you shared the trail, they "met" it themselves. Already matches the lineage/dossier design. | Slightly indirect; needs the fiction to land. |
| **Een stekje geven** | Plant-cutting metaphor, culturally native (stekjesruil), wholesome, exact clone-and-keep semantics. | Cuttings are for plants; odd for animals. |
| **Forken** | Hacker-camp native; *precisely* the right semantics — copy, keep the original, preserve lineage. | Anglicism; opaque to young children as the primary verb. |
| **Klonen** | Every kid knows the word. | Cold, sci-fi, clashes with the warm fiction. |

**Recommendation: "een spoor delen"** as the primary UI verb. It resolves an
open question elegantly: a shared creature is *the same creature known to both
players*, each with their own bond — not a duplicated object. That framing
kills any "clone inflation" ick before it starts, and it keeps the dossier's
social history honest ("Ontmoet via Noor · Oorspronkelijk gevonden door Sam ·
4 speelvrienden").

Keep **forken** as flavour for the hacker audience — e.g. the lineage screen or
scoreboard can wink with "12 forks" — without making it the verb children have
to learn. Code-side the concept stays `share`/`introduce`.

## Sharing fiction

Because the sender keeps the creature, the interaction should not be described
as selling or surrendering an animal. The recipient develops their own bond,
and the dossier preserves the social history:

> Ontmoet via Noor
> Oorspronkelijk gevonden door Sam
> 4 speelvrienden

The recipient receives the creature. The giver receives 50 help points only if
this is the first verified creature introduction from that giver to that
recipient; later creatures to the same player earn no more points. If both
directions introduce a creature, each giver can independently mark the other
player as helped. A vonk with food only is still useful but score-neutral.

### How creatures spread socially

Every vonk resolves vonk-geluk against the other player's eligible roster.
There is no share button — nobody can hand a chosen creature over, and nobody
can be pestered into one. Base creatures spread freely, rares form longer
person-to-person chains after their first jager → verzamelaar hop, while every
legendary branch makes only its verified self-found jager → verzamelaar hop. The
original source stays credited in the lineage and everyone keeps their
creature. Plukplekken remain an independent source of food and base creatures.

This replaces both the bond-gated mentor-invitation model and the earlier
finder-only deliberate spoor. It costs the deliberate gift moment and the
food-for-creature trade; it buys total simplicity, zero exchange UI, and an
economy bounded by the vonk itself: a no-vonk repeat can only move food, and
the same pair waits six hours before another creature may travel. The staff
safety valve survives: an organiser badge carrying only commons can guarantee
an eligible introduction on its next vonk.

Playdates remain unlimited because they create shared experiences rather than
new creature ownership.

## Economy across the weekend

The economy's centre of gravity shifts naturally, and that shift *is* the
pacing:

- **Day 1 — hunters have leverage.** Everyone has a startbeest, but variety
  is scarce: foxes introduce species quickly while pluk discoveries take a
  walking route and luck, so meeting a hunter is still attractive. Food is
  plentiful because nobody has much to feed yet.
- **Day 2–3 — gatherers have leverage.** Most players have creatures; bond
  progression consumes food, and favourite/rare foods come from forage spots
  hunters haven't had time to cover. Now hunters queue at the gatherers.

Levers to keep both halves relevant all weekend:

- **Staged fox activation.** Don't switch on every transmitter on Friday.
  Activating new foxes (or rotating which creature a fox transmits) each day
  keeps new creatures entering the economy, so hunters matter on Sunday too.
- **Rotating yields.** The `(BSSID, day)` yield formula re-deals every
  plukplek daily, so gathering stays an exploration, not a milk run — no
  hardware moves, and the per-badge reload already stops camping.
- **Gatherer-exclusive rares.** Favourite foods (big bond bonus) and habitat
  materials come primarily from foraging. Hunters *can* forage, but their time
  is split — realistic scarcity without hard role locks.
- **A staff safety valve.** An organiser badge at the infodesk can introduce
  one common creature to anyone the normal paths missed. Cap it to commons
  so hunters keep their prestige. The startbeest makes this a true backstop
  (swapped badges, failed registrations) rather than a queue every child
  must pass; no child should be blocked from the whole game because they
  don't know the right teenager.

Tuning target, order of magnitude: a creature wants a few feedings per day; an
hour of casual foraging should feed one creature for a day with a small
surplus. A hunter actively hunting should run *short* by roughly half a day of
care — enough to genuinely want a gatherer friend, not so much that their
creatures are perpetually sad.

## Scale: what ~100 players in a 600-person camp means

- **Density.** One person in six plays. The pair-uniqueness of vonken never
  exhausts (100 players ≈ 5,000 possible pairs), but *finding* fellow players
  is the real constraint. Players need to be visible: an idle-screen "wil
  snuffelen" state, a distinctive LED pattern, or a lanyard flag. Consider a
  daily **verzamelmoment** (campfire trade fair) that guarantees liquidity for
  anyone who hasn't bumped into partners organically.
- **Half the camp is children.** Expect antennas — and direction-finding skill
  — to skew teen/adult, so creature flow runs older → younger. That's a sweet
  mentor dynamic, but it needs the staff safety valve above so kid-only groups
  aren't starved. The gatherer loop must be fully playable by a
  seven-year-old: short Dutch words, big touch targets, forgiving mini-games.
- **Family units distort the economy.** Siblings will exchange constantly. The
  vonk rule and one-time helped-player credit handle this (utility yes, repeat
  score no).
- **Adults approaching children for points.** Fri3d is a family camp and the
  incentive is symmetric and mild, but keep the framing "help fellow players",
  never "collect people". The one-time 50-point help value stays modest beside
  the 100/300/800 self-find values.

## Risks, unknown unknowns and perverse incentives

### Hardware unknowns (need debug tests before designing further)

- **RSSI as a consent boundary — partly answered.** The espnow-test spike
  measured badge-to-badge RSSI: touching is about -40 dBm, two metres about
  -75, but the curve is *not monotonic* (antenna nulls, hands, bodies), so
  -50 dBm works as a CLOSE verdict only if it is smoothed over several
  consecutive beacons and required *on both sides*. Usefully, RSSI is read by
  the receiver's own radio and never carried in the payload, so closeness
  cannot be claimed — only amplified. Still to test outdoors in a crowd; if
  the threshold proves unstable there, retune the verdict (threshold, streak
  length, SNF mirror margin) rather than shipping a boundary that lies.
- **ESP-NOW and camp WiFi on one radio — answered.** The espnow-test spike
  measured it: a badge associated with an AP is pinned to that AP's channel
  and cannot change it, so snuffel mode must disconnect (keeping the radio
  up), pin one fixed camp-wide channel, exchange, and rejoin (~4-5 s). Both
  badges entering the mode explicitly is what the consent design wanted
  anyway.
- **The WiFi scan spike is now the gating one**: can the badge scan while
  associated with camp WiFi, how long does one scan take, and what does a
  scan burst cost in battery? A warmer/colder loop needs a fresh reading
  every few seconds; if scan-while-associated proves flaky, the plukscherm
  falls back to the same disconnect-and-rejoin recipe as snuffelen.
- **Battery.** LoRa + WiFi scanning + screen over a camp day, with scarce
  charging. The forage scan should be user-initiated bursts, not a background
  radar.

### Economy and incentive risks

- **Creature saturation.** By day 2 most players may have many creatures, and
  hunting deflates. Mitigate with staged fox activation, rotating creature IDs
  per fox, and the one-roll-per-BSSID-per-phase pluk limit — scarcity should
  come from *time and effort*, not from telling a child "sorry, out of
  clones". Saturation of commons is acceptable if rares keep trickling; the
  endgame shifts to bond depth and communal goals, which is by design.
- **Introduction spam — bounded by the vonk.** Social spread only happens on
  a vonk. The same pair gets one immediately and then waits six hours; their
  hourly repeat can move generated food only. There is no share button to
  spam. Pluk encounters have their own BSSID/phase ledger.
- **Badge speed-dating.** Helping distinct players is intentionally better than
  farming one friend, but the scoreboard must not turn the food queue into a
  booping assembly line. Credit each giver/recipient pair once and only after a
  verified creature introduction; food-only vonken score nothing. Consider a
  short joint payload if field play shows that the introduction is still too
  cheap.
- **Food dumping — resolved by the energy chain.** Bond comes from play, not
  from feeding, so 50 gifted berries make a very full creature, not max bond.
  The playful refusal ("creature is full / tired") is the visible face of a
  real rate limit.
- **Shaking the badge** to fake movement missions — already addressed: short
  foreground missions, no all-day step leaderboard, non-motion alternatives.
- **Forage spot camping — resolved by the per-badge reload.** A plukplek
  yields once per reload per badge; sitting beside it gains nothing over
  walking a loop. The daily yield rotation keeps the loop itself fresh.

### Social risks

- **Shy players and non-Dutch speakers.** Walking up to strangers is the point,
  but it must never be the *only* path: the daily verzamelmoment and
  solo-viable progression (care + activities) keep the game playable
  without cold-approaching anyone.
- **Non-players getting pestered.** 500 people aren't playing. Visible
  player-state (the "wil snuffelen" idle screen) tells kids who is fair game
  to approach.
- **Badge swapping.** Children will physically trade badges. Identity is the
  badge; keep it low-stakes and recoverable server-side rather than trying to
  prevent it.

### Adversarial risks (it's a hacker camp)

Assume the protocol is public by Saturday morning: forged shortcodes, spoofed
handshakes, replayed spoor payloads, spoofed `fri3d-badge` hotspots. ESP-NOW widens this a
little — an attacker with a stock ESP32 and an amplifier can present whatever
RSSI they like, so the -50 dBm gate stops honest badges at range, not
determined ones. Respond by making cheating *boring*, not impossible:

- Personal care state is local and forgiving — nothing to steal, nothing worth
  forging.
- Public score counts only bridge-verified self-finds and corroborated first
  helped-player events, which the server can dedupe and rate-limit.
- Replayed fox codes cannot mint discovery points: the self-found bit for
  `(player_id, creature_id)` only transitions from 0 to 1 once. Every later
  submission returns `already_self_found` and has no reward side effects.
- A forged creature on your own badge is a single-player mod, not an exploit.
- A forged single-sided snuffel report can at most affect the forger's own
  forgiving local/base-or-rare collection state and earns no score. A
  legendary grant requires the matching peer report plus a bridge-verified
  `zelf gevonden` source, so its one-hop rule cannot be claimed by one badge.
- A forged pluk report can mint collection state on the forger's own profile,
  but cannot claim a LoRa find or hunter score. BSSID/phase deduplication keeps
  honest retries bounded; generating fake hotspots remains an intentionally
  boring hacker-camp mod.
- A home-brew `fri3d-badge` hotspot mints only local food: the same boring,
  single-player mod — and at this camp, a small prize in itself.
- Lean in: hide an easter-egg creature that can *only* be obtained by
  reverse-engineering the ESP-NOW protocol. At Fri3d, the person who hacks the
  game should win a prize inside it, and it channels that energy toward a
  target you chose.

## Activity families

The badge has an accelerometer and gyroscope, touch screen, physical buttons,
five LEDs, a buzzer, WiFi (with ESP-NOW for badge-to-badge traffic) and an IR
receiver — receive only, there is no IR transmitter.

| Mode | Example activity | Reward |
|---|---|---|
| **Op avontuur** | A short walk or movement session | Food and expedition postcards |
| **Plukken** | Walk to `fri3d-badge` hotspots around the terrain | Food, base encounters and materials |
| **Beestenschool** | Tilt maze, rhythm game, Flappy-style game or LED Simon | Skills and bond |
| **Habitat bouwen** | Gather and spend materials on a small habitat | Decorations and animations |
| **Onderzoek** | Visual quizzes, behaviour puzzles and pattern matching | Dossier pages and discoveries |
| **Speeldate** | A cooperative interaction between two badges | Friendship stamps and shared rewards |
| **Camp-opdracht** | Visit a workshop or staff station and enter a code | Special materials or story chapters |

**Scope 2026: of this table only Beestenschool ships**, alongside the
three verbs. Every other family is a later year — a lot already ships this
year, and the core loop must stay the focus.

### Creature-specific variations

The same small set of game systems can feel different through creature
personality:

- Flying creatures steer through rings by tilting the badge.
- Fast creatures enjoy walking or rhythm assignments.
- Shy creatures prefer balance and memory games.
- Musical creatures specialise in rhythm or call-and-response.
- Foragers search a visual grid for their favourite food.
- Mud-loving creatures return from expeditions with a touch-based grooming
  game.

These preferences can grant bonuses without preventing a creature from joining
other activities.

### Movement design

Prefer short, foreground missions over an all-day step leaderboard. Exact step
counting requires calibration, can be imitated by shaking the badge and can
unfairly favour older or more mobile players.

Examples include:

- Walk together for two minutes.
- Complete a short movement target.
- Keep a nest level for thirty seconds.
- Follow a sequence of safe tilts and gestures.
- Guide a creature through a tilt maze.

Every motion assignment should have a non-motion alternative with an equivalent
reward.

## Onboarding: the antenna question and the startbeest

Setup asks no antenna question: everyone starts as verzamelaar, and the
upgrade is one button. Instellingen has **WORD JAGER**: it probes the SPI
bus for the physical LoRa kit (a Seeed Wio-SX1262-N; read its packet type,
whose only valid values are GFSK and LoRa — a missing module answers bus
noise), celebrates "Antenne
gevonden!", enables Jagen and mints the hunter_id. Not found → a friendly
"geen antenne gevonden" and nothing changes. An explicit button beats a
boot probe: the player presses it at the moment they finished soldering,
which is exactly when the celebration lands. A constructed software driver
does not count: the SX1262 itself must answer. The separate radiating element
has no electrical detect signal, so the badge cannot distinguish that final
solder joint from the attached kit. Probing is receive-only and safe; the
module must simply never transmit without its antenna.

**Upgrading is purely additive.** A verzamelaar who installs an antenna
gains the Hunt track and loses nothing — not creatures, not bond, not food.
An earlier draft considered wiping the roster "so there is something to
hunt"; that breaks the game's one absolute rule (permanent progress is
safe) and lands on exactly the player most worth rewarding: the kid who got
hooked without an antenna and then went and got one. What keeps hunting
meaningful for an upgrader is already in the design — plukken never grants
upper tiers, legendary sharing requires a self-found jager, staged fox
activation keeps new species entering all weekend, and *zelf vinden* (below)
makes the first physical find of a socially known creature a scored, celebrated
event. The upgrade moment is the WORD JAGER
button above — pressed right after soldering, celebrated on the spot, the
hunter_id minted through the server. Toggling Jagen off later simply
leaves the id dormant.

### The startbeest

**Every player receives one base-tier creature at registration** — jager
and verzamelaar alike. It is the tutorial creature: the companion teaches
the verbs, then hands over to a real beest, so feeding, playing and bond
start immediately — before the first fox is found or the first stranger
snuffeled.

- **The creature chooses the player.** The pick is deterministic —
  `f(badge_id) → one of the base tier` — and presented as "…heeft jou
  gekozen!". That is the same fiction as vonk-geluk (creatures always
  introduce themselves), and determinism means re-registering cannot reroll
  it — the same principle as the seeded plukken yields.
- **Random-per-badge, not player-chosen**, because the camp needs variety:
  the vonk-geluk pool is the other player's roster, and a hundred
  hand-picked vossen would make day-1 contagion monotone. A spread of
  starters seeds the social graph with something to pass on from the first
  handshake.
- **The reveal is a setup moment.** After registration succeeds, a
  dedicated screen introduces the creature — silhouette first, then the
  reveal, then straight into a first feeding with the tutorial's gathered
  hapjes. It is the emotional payoff of onboarding and the bridge from
  companion tutorial to care game.

The startbeest fixes the cold-start hole in the contagion model: vonk-geluk
rolls against the *other player's* roster, and before hunters fan out every
roster was empty — two day-1 verzamelaars could snuffel forever and spread
nothing. With starters seeded, gatherer↔gatherer spread works from the
first morning. It also covers the day-1 jager whose first hunts come home
empty — direction finding is hard — and it demotes the staff safety valve
to a true backstop.

### Zelf vinden (the first physical find)

This is the payoff of the **wordt-jager** upgrade: a verzamelaar whose
roster grew through snuffels presses WORD JAGER, and every known
creature's fox becomes a fresh target — the collection turns back into a
hunting list. It applies equally to any hunter tracking the fox of a
creature they already know (startbeest, snuffel). That find is not a dud;
it is an upgrade:

- The dossier gains the **"Zelf gevonden!"** stamp. The social history
  stays honest and gets richer — "Ontmoet via Noor · Later zelf gevonden".
  Lineage is never rewritten, only extended.
- The find scores as a discovery. Hunter score is for *finding foxes*, not
  for first ownership, so a former verzamelaar's hunt track is worth
  exactly as much as anyone's.
- The creature, delighted to be visited at home, hands over a
  **verzorgingspakket** — a bundle of hapjes weighted toward its own
  favourite food. The bonus lands in the care economy, where an active
  hunter is chronically short.
- Nothing is removed, replaced or reset. Bond carries straight through;
  the beest simply knows the player better now.

`Zelf gevonden` is a **once-per-player-per-creature** milestone. Conceptually,
each player owns a `self_found_mask` with one bit per creature. A successful
bridge-confirmed fox code performs an atomic test-and-set of that creature's
bit:

- **Bit was 0:** set it to 1, add the `Zelf gevonden!` stamp, award that tier's
  100/300/800 points and grant one verzorgingspakket.
- **Bit was already 1:** change nothing and show an explicit badge error such
  as `AL ZELF GEVONDEN · +0 PUNTEN`. Award no points and no second package.

This is not a cooldown and never resets. A player may self-find every different
creature once, but cannot stand beside one fox and submit its code repeatedly.
The server representation may be a bitmask or an equivalent unique set; the
semantic key is `(player_id, creature_id)`, enforced atomically server-side so
retries, reconnects and concurrent duplicate submissions remain idempotent.

## The first gatherer experience

Nobody begins with an empty collection: the startbeest (see *Onboarding*)
arrives at registration. The tutorial is one taught tap, not a course: the
starter pantry is pre-seeded (2 bes, 1 noot, 1 eikel) and the startbeest
reveal ends in a **guided first feeding** — "geef het eerste hapje" — so
the player leaves onboarding having fed a creature once. Playing teaches
itself from the beest page's own buttons; the uitleg screen (see *Roles
and navigation*) names the wider loop.

The companion need not become a collectible creature. Its purpose is to make
the game immediately playable and give every participant a personal identity.

Avatar accessories should have multiple unlock paths. A hunter might unlock an
item through discoveries, while a gatherer can unlock the same item through
bond, skills or social milestones.

## Resources and rewards

The existing foods provide a natural first resource system:

- **Bes**
- **Noot**
- **Eikel**

Foraging and assignments award these directly. Feeding a favourite food grants
a larger energy bonus. Other possible resources include toys, habitat
materials, stickers and story fragments.

Basic affection should never require a scarce resource. Petting, comforting and
at least one simple activity should always remain available so a player cannot
be locked out by an empty inventory.

Resources may be spent, but creature ownership, bond, memories and skills are
never spent or lost.

## Progression

Bond levels should unlock tangible changes rather than merely a larger number.
Possible rewards include:

- New expressions and idle animations.
- Additional dossier facts or story pages.
- A nickname editor.
- Habitat decorations.
- Creature-specific mini-games or difficulty levels.
- Companion accessories.
- Playdates.
- Special postcards from expeditions.

Progression should reward both breadth and depth:

- **Breadth:** meet and care for several different creatures.
- **Depth:** develop one favourite creature extensively.

The emotional centre can be one favourite creature while the wider collection
provides variety.

## What bond buys

The chain ends in bond, so bond must end in something. Animal Crossing's
answer applies directly: the terminal reward is expression, identity and
social display — never power. There is no battle system and nothing to
min-max, so a power reward would have nothing to spend itself on. Bond pays
out in this order — the first two ship in 2026, the rest are parked.

- **De ster (the finish line — ships 2026).** Reaching band 5 marks the
  creature's tile on the home grid with a gold star and its beest page
  trades the meters for "Beste vriend!". A creature can be *finished*.
  That is the anti-grind: depth has a destination, and the next creature
  offers a fresh one. (Animal Crossing's villager photo — the community's
  canonical proof of friendship — is the model.)

  **A finished friend retires from the economy, not from the game.** At
  band 5 the living stats freeze — permanently content, never hungry or
  tired again — and play becomes free, forever: "een beste vriend speelt
  altijd mee." No more feeding, no more refusals; the beest page trades its
  meters for the star and the foto. The creature stays fully present — it
  walks with the maatje, plays on request, and remains the player's most
  eager ambassador at snuffels. Food therefore flows only to relationships
  under construction, so the pantry pressure follows the player to the next
  friendship by itself. Two guards: free play yields warmth only — no
  skills, no communal counters, nothing the economy counts, or the finished
  friend becomes the infinite farming route; and the stats *freeze* rather
  than the costs being waived, so the meters never show a hungry creature
  happily playing.
- **The bonded count (ships 2026).** The scoreboard shows how many
  creatures each player has fully bonded, next to their catch count. The
  badge reports the number itself (through the report outbox, below) —
  self-claimed, display-only, and never the ranking key, so it stays
  consistent with "public score counts only server-verified events" by not
  being score at all: it is a public shelf for private care.

### Parked bond ideas (not 2026)

Designed, still wanted, deliberately not this year — the star and the
bonded count carry the payoff alone: the **walking friend** (band-5
creature beside the maatje on the home screen), **de foto** (a dated
beste-vrienden page in the dossier), **ambassadeurschap** (vonk-geluk
weighted by bond within a tier — note it needs a "loved" bit per roster
entry in the snuffel payload, a protocol change), **beste-vriend thrones**
(per-creature fame on the scoreboard), and **de zin** (the seeded daily
want). Revisit after a camp of playtest data.

### What gatherers give hunters

Two flows, both UI-less, both firing automatically on the same handshake:

- **Food.** Hunters run short by design (about half a day of care); every
  snuffel picknick moves gatherer surplus to them.
- **Reach.** Every verified directed creature introduction records who shared
  which creature with whom. Rares can build chains through later owners;
  each legendary branch credits only its self-found jager → verzamelaar hop. Surface
  this as generosity rather than ownership: "jouw spoor hielp 12 spelers."

This is the symmetric want that makes an economy with no trade UI: hunters
want their finds in the hands of good carers (reach and food), carers want
hunters nearby (new species and zin variety). Nothing to choose, nothing to
price — consistent with the snuffel philosophy.

The full loop, by timescale:

> **Minute:** pluk → voer → speel.
> **Day:** fresh vonken per pair, re-dealt plukplekken, newly staged foxes.
> **Weekend:** the roster fills, the stars accumulate, the bonded count
> climbs the scoreboard.

## Scoring

The public total combines two kinds of mastery but always shows their breakdown:
**zelf gevonden** and **spelers geholpen**. A large number should never hide
whether it came from hunting or generosity.

### Discovery and help score

One transparent score combines verified hunting with social generosity:

> **score = Σ(points for self-found creatures) + 50 × distinct players helped**

Initial self-find values are **base 100, rare 300, legendary 800 points**.
These and the 50-point help value are tuning values, not protocol constants;
keep them in server configuration.

Creature ownership alone is score-neutral. A creature contributes discovery
points only when the LoRa bridge has stamped it **zelf gevonden** for that
player. A startbeest, pluk encounter or creature received through snuffelen is
worth zero discovery points until that player personally finds its fox. This
keeps the score about action rather than luck or collection size. The
self-found contribution is a set sum, not an event sum: each creature's tier
value appears at most once per player. Duplicate fox-code submissions return
`already_self_found`, add zero points and do not grant another care package.

A player is **helped** when they receive a verified, eligible creature directly
from the scorer. Deduplicate on `(giver, recipient)`: the first corroborated
introduction is worth 50 points, and every later creature or vonk between that
pair is worth zero. Rare relays can therefore earn a gatherer help points
without pretending the relayed creature was self-found. Generated food,
food-only vonken and merely receiving a creature never score.

Example: one base and one rare creature self-found, plus three distinct players
helped, scores `100 + 300 + (3 × 50) = 550`.

### Hunter progress

- Unique creatures stamped zelf gevonden: physically finding a creature first met
  through others scores at its tier value, because the score is for finding
  the fox, not for first ownership.
- Distinct players helped, at 50 points once per recipient.
- Special discoveries and legendary appearances.

### Gatherer progress

- Fully bonded creatures — the scoreboard's bonded count (self-reported,
  display-only, never the ranking key).
- Variety of forage finds and completed assignments.
- Skills learned and dossier pages unlocked.
- Vonken, playdates and rare creatures spread onward through vonk-geluk.

### Shared camp progress

A communal forest or sanctuary can grow through every discovery, bond milestone
and exchange. Weekend-wide goals encourage cooperation, for example:

- Take 500 creatures on an outing.
- Complete every habitat type.
- Organise 200 playdates.
- Introduce every creature to at least ten players.

The creature lineage trees ("who introduced whom") make a lovely communal
visualisation for the scoreboard screen.

Current energy should not affect public score. Neither should
raw taps or unlimited step totals.

## Roles and navigation

Hunter and gatherer are play tracks rather than permanent, exclusive
identities:

- Everyone has access to Care, Gathering, Activities and Friends.
- Players with an antenna can additionally enable Hunt.
- Players may add an antenna or change their preference later.

The Hunt track enables through the WORD JAGER button in instellingen,
which probes the badge's SPI bus for the LoRa radio (see *Onboarding*).
Verzamelaars never enter the hunt: for them an awake creature's grid tile
stays as inert as a sleeping one — a mode you cannot play must not open.

One **uitleg** screen states the core loop in the player's own mode, in
three short lines — jager: "jij vindt de beesten; verzamelaars hebben het
eten"; verzamelaar: "jij plukt het eten, ontmoet spelers en speelt;
jagers brengen nieuwe beesten binnen". It shows once after onboarding and
stays reachable from instellingen. The text changes when the mode does.

The home experience's top level is the triad plus the collection —
Snuffelen, Plukken, Spelen, Beesten — with Jagen added for players with an
antenna. Simply placing more buttons inside a caught creature's detail page
would leave a new gatherer with nothing to do.

## Connectivity and trust

Core care and mini-games work offline and synchronise later. Sharing
transports, in order of universality:

- The ESP-NOW snuffel, gated at -50 dBm, for deliberate face-to-face
  exchanges — the baseline. Its SNF mirror frame lets one completed streak
  pay out both badges, so the two sides need not finish together.
  (The manual code that once sat below it was cut in 2026-08: it carried no
  secret — typing any name minted the reward — so it was self-service
  cheating, not a fallback.)
- The same ESP-NOW link, held open, for richer playdates.
- Camp WiFi and the cloud server for durable provenance, scoring and recovery.

Public points favour verifiable, unique milestones: bridge-confirmed self-finds
and the first corroborated creature introduction from one giver to each
recipient. Vonken, food and repeat introductions are score-neutral. Personal
care state remains forgiving and locally owned.

### How a creature reaches the profile

The server's creature list is the durable record a restore rebuilds from, so
every legitimate acquisition path must end there — and each path has its own
writer:

- **Startbeest** — minted by the server itself inside the registration POST
  and returned in the response. The pick function is deterministic and
  shared, so a badge that registers offline computes the identical creature
  and the records converge on the next sync.
- **Hunt** — written only by the LoRa bridge, exactly as before; the badge
  never claims its own catches. If the creature row exists from another
  source, the first bridge report atomically upgrades its self-found bit from
  0 to 1. If that bit is already 1, the API returns `already_self_found`; it
  writes no score or package event. A uniqueness constraint or compare-and-set
  on `(player_id, creature_id)` makes bridge retries and repeated keypad codes
  idempotent.
- **Snuffel** — the gap: a verzamelaar has no antenna, so nothing on the
  bridge path ever writes their vonk-geluk creatures, and a restore would
  hand back an account without them. The fix is a narrow badge→server
  **snuffel report**: when the badge next has WiFi it posts its snuffel
  events (shared encounter id, pair, directed giver/recipient, whether the
  meeting had a vonk, and which creature introduced itself). The badge still
  never claims a *catch* — it reports a *meeting*, which the server can
  cross-check against the partner's matching report. The report must retain
  provenance needed by the tier rules: rare lineage and, for legendary
  sharing, the giver's bridge-verified `zelf gevonden` state. Reports queue in an
  on-badge **outbox** and flush whenever WiFi actually works — woods WiFi
  is spotty, and the outbox is the general mechanism for every
  badge→server report (snuffel events, the bonded count).
- **Pluk** — a successful wild encounter queues `(BSSID, camp phase,
  creature)` through the same outbox. The server deduplicates that physical
  opportunity and adds the creature to the durable roster. Food and failed
  rolls stay local. A pluk report is explicitly not a bridge-verified fox find
  and awards no hunter provenance or hunter score.

**Local grants are generous; legendary provenance and points are verified.**
The recipient sees the offline payoff immediately. A single-sided report may
preserve a base or rare creature so a child does not lose it to a friend's
dead battery, but earns no score. A legendary reaches the durable server roster
only after both reports corroborate and the server confirms that the giver is
a jager with that creature marked `zelf gevonden`; this enforces its single
jager → verzamelaar hop. Help points require both reports, a vonk, the camp
window, tier eligibility and `(giver, recipient)` deduplication. Self-find
points come only from the LoRa bridge. A forged grant can at most alter the
forger's forgiving collection state and cannot mint verified help or
self-find points.

## Buiten het kamp (before and after)

The game must not die at the terrain fence. Care, spelen and snuffelen
already work anywhere — only plukken is camp-bound, because it keys on the
`fri3d-badge` SSID. Decided:

- **No public thuismodus setting.** The any-SSID switch ("pluk overal")
  stays in the hidden debug screen, where it already exists for pre-camp
  testing. During camp, finding it takes the same effort-and-knowledge
  barrier as the home-brew hotspot the adversarial section already accepts,
  and the payout is the same local food: boring. A visible settings toggle
  would remove that barrier and spread one tap at a time through a tent row.
- **After the camp, the secret is the souvenir.** The closing announcement
  tells everyone how to open the debug screen (tap the badge id five times
  in instellingen) and flip "pluk overal": the neighbourhood becomes the
  terrain and the badge keeps living as a huisdier. Known cost, accepted
  deliberately: the same screen holds the roster unlocks, so the reveal also
  hands out the skip-the-game buttons. After teardown the stakes are zero —
  your badge, your rules is the point at this camp.
- **The server fences score to the camp window.** Scored events — self-finds,
  first helped-player introductions and any future bond-milestone reports — count only when they fall inside
  the camp dates; outside the window the server still accepts grants
  (creature spread, restores) but writes no score. This is a server rule,
  never a badge rule: client toggles cannot guard score, because the
  protocol is public by Saturday. Pre-camp play therefore costs the
  scoreboard nothing — a kid who arrives with a full pantry and a loved
  startbeest arrives *readier*, not richer: tutorial done at home, day-1
  infodesk queue shorter.

## Recommended first playable slice

Before building a large economy, test a compact experience:

0. **Hardware spikes first**: the ESP-NOW spike is done (see the espnow-test
   experiment: the channel recipe, the RSSI curve, the trust model). The WiFi
   scan spike remains: scan-while-associated, scan latency, battery per
   burst, and a census of `fri3d-badge` BSSIDs on the terrain.
1. Companion tutorial, ending in the startbeest reveal (server-minted in
   the registration POST).
2. Directed creature spread through vonk-geluk over snuffel: base sharing,
   rare relay, the legendary self-found one-hop rule, generated-picnic
   fallback and a snuffel report syncing the result to the profile.
3. Plukken against real `fri3d-badge` hotspots: warmer/colder screen, BSSID
   identity, per-badge food reload and one wild-creature roll per camp phase.
4. One motion mini-game, such as a tilt maze.
5. One touch/button game, such as LED Simon or Flappy.
6. Berry, nut and acorn inventory with favourite-food bonuses.
7. Bond level 2 unlocks a dossier page and habitat decoration.
8. One badge-to-badge snuffel: the 1-hour food / 6-hour vonk rules, a
   vriendenboekje page and directed vonk-geluk.
9. Separate discovery and bond achievements.

This slice tests the essential questions: is caring for and playing with a
creature satisfying without a LoRa hunt, and does the snuffel moment deliver
enough delight to carry the social economy?

## Open design questions

- ~~Is each roster entry one named creature shared by many players, or a
  species from which each player receives their own individual creature?~~
  → Resolved by the "spoor" fiction: the same creature known to many players,
  each with their own bond.
- ~~Should the main gatherer fantasy emphasise one deep relationship or a
  broad sanctuary collection?~~ → Resolved by *What bond buys*: both, in
  series. Breadth is free to hold (need is pull, no upkeep); depth has a
  finish line (de foto), so the fantasy is a sanctuary of *finished*
  friendships, built one beste vriend at a time.
- ~~How many mentor invitations may a strong gatherer create?~~
  → Resolved: the mentor model is replaced by automatic vonk-geluk. Rare
  sporen may relay; legendary sporen are self-found jager → verzamelaar only.
- Confirm the estimated roughly 70 `fri3d-badge` BSSIDs on the terrain and
  map how many are distinct physical walking destinations rather than radios
  clustered at one place.
- Tuning numbers that need playtesting: the self-find values (initially
  100/300/800) and helped-player value (initially 50), the bond weighting
  inside a tier, the zin bonus size, the plukplek
  food reload, the 40%/45% base encounter curve, and energy cost/restore per
  play session.
- Which rewards remain local and which contribute to public scoring?
- How many foxes will be deployed, and can their activation be staged across
  the weekend? How many players will have antennas? (Both numbers gate the
  economy tuning — ask the orga.)
- Which camp stations sit near a `fri3d-badge` hotspot or can host physical
  assignments?
- Does the vonk need a time-cost payload (mini playdate) or is a plain
  handshake enough?
- How prominent should competition be compared with the communal sanctuary?
- ~~Is the startbeest score-neutral (everyone has one) or does it count?~~
  → Resolved: ownership is score-neutral. Its fox is worth 100 points only if
  the player later earns the base creature's `zelf gevonden` stamp.

## Glossary additions

Following the one-word-per-thing rule:

| Code (English) | UI (Dutch) | What it is |
| --- | --- | --- |
| **gatherer** | **verzamelaar** | The non-antenna play track: foraging resources for creature care. |
| **spread** | **vonk-geluk** | The directed payoff on a vonk: an eligible creature the recipient does not know introduces itself; both keep it. Base spreads freely. A gatherer may relay rare; a hunter may share rare only after finding it personally. Every legendary branch ends after self-found jager→verzamelaar. Never "clone" in the UI. |
| **boop / socialize** | **snuffelen** | The face-to-face handshake over ESP-NOW, gated at -50 dBm RSSI on both sides — and the home-screen mode named after it. |
| **spark** | **vonk** | The mutual creature-sharing window: immediate for a new pair, then per pair every 6 hours (at most four in a rolling 24h). A no-vonk repeat can share generated food only. |
| **friend book** | **vriendenboekje** | The permanent collection: one page per first-ever meeting between two badges. |
| **forage** | **plukken** | Passively scanning for `fri3d-badge` hotspots and harvesting a nearby one. |
| **forage spot** | **plukplek** | One physical hotspot, identified by its BSSID, with hourly food and one creature roll per camp phase. |
| **reload** | — | The per-badge cooldown before the same plukplek yields food again. It does not reroll its phase creature. |
| **starter** | **startbeest** | The one base-tier creature every player receives at registration, deterministic per badge; the tutorial creature for both tracks. |
| **self-found** | **zelf gevonden** | The permanent per-player/per-creature bit set by the first bridge-confirmed fox find, including for a creature already known. Scores once at the tier value (100/300/800) and pays one verzorgingspakket. Repeating the code returns `already_self_found`, changes nothing and awards zero. |
| **care package** | **verzorgingspakket** | The food bundle a zelf-gevonden creature hands over, weighted toward its favourite. |
| **snuffel report** | — | The badge→server sync of a directed snuffel event (encounter, pair, vonk, giver/recipient, creature and provenance). Base/rare recovery may be single-sided; legendary durability and the 50-point first-help credit need corroboration. |
| **star** | **ster** | The band-5 finish mark on grid tile and beest page. A creature can be *finished*: its stats freeze and play is free forever. |
| **photo** | **foto** | Parked (not 2026): a dated beste-vrienden dossier page at band 5. |
| **daily want** | **zin** | Parked (not 2026): a creature's seeded daily craving — one food or one game. Bonus band to fulfil; free to ignore. |
| **best friend** | **beste vriend** | The band-5 state of one creature (the star). The per-creature scoreboard title is parked (not 2026); the scoreboard shows the bonded *count* instead. |
| **report outbox** | — | The on-badge queue of badge→server reports (snuffel events, bonded count), flushed whenever WiFi works. |

Retired: **foerageren** (say plukken).
