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

Creatures have temporary needs such as hunger, mood and energy. These may rise
or fall over time and give players a reason to interact. A hungry creature is an
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

**Hunger is pull, not push — that is why a big roster is never a chore.** A
hungry creature loses nothing: bond never decays, and hunger's only teeth are
that a tired creature will not play. So the player feeds the one creature they
are about to play with, at the moment they want to play; the other twenty wait
patiently, unharmed. Food demand scales with how many creatures you *play*
with, not how many you *own*. Guard this structurally: no roster-wide hunger
indicators (red badges on the home grid, "5 beesten hebben honger!"
notifications) and no need-stats in public score — either would turn the
collection into a feeding shift.

The same philosophy extends to the exchange economy: there is no exchange UI
at all. A snuffel *is* the exchange — both badges automatically share a
picknick, and sometimes a creature tags along (vonk-geluk). Nothing to
choose, nothing to price, nothing to haggle over: the reward is for meeting,
not for trading.

## Existing foundations

The current app already contains much of the presentation needed for the care
game:

- Bond, levels and hearts.
- Hunger, mood and energy.
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
below. It is how a collection grows beyond the startbeest (vonk-geluk), the
source of vonken and vriendenboekje pages, and the way surplus food reaches
hungry hunters.

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
- **Yields come from a formula**, `(BSSID, day) → resource`, so different
  spots give different food and every spot re-deals daily — a complete
  pantry requires covering ground, just as a complete roster requires
  finding every fox. Rare finds are a seeded roll on the same inputs, so
  rescanning cannot reroll them.
- **Any BSSID that broadcasts the SSID counts — no allowlist.** Someone who
  runs their own `fri3d-badge` hotspot beside their tent has hacked
  themselves some berries; at a hacker camp that is a feature, not a leak.
  Food is local state, so the cheat stays a single-player mod (see
  *Adversarial risks*).

Camp assignments, movement missions and mini-games stay as alternative food
sources for players who cannot roam.

### Spelen — turn food into bond

Mini-games close the economy. The chain is:

> **Plukken yields food → voederen restores energy → spelen spends energy
> and builds bond.**

- A play session costs the creature energy. A tired creature playfully
  refuses — "Everzwaan is moe — eerst een hapje?" — so the refusal *is* the
  rate limit, in fiction, exactly as the care philosophy asks.
- Feeding restores energy; a favourite food restores more and adds a mood
  bonus. Feeding itself grants little bond.
- **Bond comes from playing, not from feeding.** Feeding is the enabler,
  playing is the earner. One mechanism kills both economy bugs named above:
  food-dumping (50 berries is a very full creature, not max bond) and
  tap-farming (play needs energy, energy needs food, food needs walking).

The beestenschool's three launch games cover the badge's inputs with nothing
to explain — every control is one finger: **VLIEGEN** (tap to flap, dodge
the branches), **VANGEN** (the creature trots left and right, tap to turn,
catch the falling hapjes), **SIMON** (four pads, buzzer notes, the LEDs play
along). Costs are 2/1/1 energy segments; each creature favours one game for
extra band. DOOLHOF (tilt maze) waits on the IMU spike.

The companion stars in exactly one game moment: the tutorial, before the
player owns any creature. After that the active creature stars, because
playing is how bond grows and bond belongs to creatures. Petting and basic
affection stay free and unlimited — they give warmth and mood, not
progression.

Permanent progression consists of bond, skills, memories, decorations and
friendships. Hunger, energy and mood provide temporary context.

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

A **manual short code** remains the universal fallback (handshake failure, shy
players, broken hardware) and awards the same rewards.

### What a snuffel carries

Nothing is chosen and nothing is attached: the handshake itself pays out,
automatically and symmetrically, and the payoff screen has no buttons.

- **Every snuffel shares food.** A vonk is a picknick — both players gain
  2-5 hapjes of one random kind. A repeat meeting still hands both a single
  hapje for the road, so snuffelling a friend again is never pointless,
  just modest. The same pair can snuffel again after stepping apart.
- **A vonk can carry a creature** (vonk-geluk, below): one of the other
  player's creatures may introduce itself.
- **Speeldate** (any ↔ any) stays a deliberate, longer cooperative
  interaction — the one thing a plain handshake doesn't give you.

### De vonk (the anti-farming rule)

The *handshake itself* is the scored social event, separate from the payload.
The first snuffel between a given pair of players each day produces a **vonk**
for both — the meet-new-people reward. Repeats within the same pair still
share a small hapje (siblings and tent-mates can keep topping each other up)
but earn no further vonken that day. This gives:

- an incentive to walk up to strangers (new pair → new vonk),
- no incentive to stand in a corner farming one friend,
- no hard "never again" wall between friends — utility transfer stays
  unlimited, only *score* is pair-limited.

Consider additionally capping vonken per day (e.g. the first ~10 count) so the
optimal strategy is "meet some new people every day", not "speed-boop the
entire dinner queue".

### Vonk-geluk (the creature chance)

Every vonk also rolls a chance that one of the *other* player's creatures
takes a liking to you — a **spontaneous spoor**: the creature introduces
itself, both players keep it, and lineage is preserved exactly as with a
deliberate spoor. The roll is weighted by rarity: commons spread eagerly,
rares reluctantly, legendaries never spread on their own. Meeting people is
therefore how a gatherer's collection grows — and *who* you meet matters,
because the pool is the other player's actual roster, not a lottery from
nowhere. The startbeest guarantees that pool is never empty: even two
brand-new verzamelaars have something to spread from their first handshake.

### Het vriendenboekje (the permanent layer)

The vonk resets daily; the **vriendenboekje** never does. The first time two
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

Both players receive a reward for the first successful introduction of a given
creature between them. Repeating the same exchange does not produce unlimited
public points (see *De vonk*).

### How creatures spread

Only by meeting people: every vonk rolls vonk-geluk against the other
player's roster. There is no share button — nobody can hand a chosen
creature over, and nobody can be pestered into one. Distribution is pure
contagion through the social graph: hunters seed new species by finding
them, commons race through the camp, rares trickle, the original finder
stays credited in the lineage, and everyone keeps their creature.

This replaces both the bond-gated mentor-invitation model and the earlier
finder-only deliberate spoor. It costs the deliberate gift moment and the
food-for-creature trade; it buys total simplicity, zero exchange UI, and an
economy that cannot be spammed — the introduction-spam caps fall away with
the feature. The staff safety valve survives: an organiser badge carrying
only commons can simply guarantee its geluk roll.

Playdates remain unlimited because they create shared experiences rather than
new creature ownership.

## Economy across the weekend

The economy's centre of gravity shifts naturally, and that shift *is* the
pacing:

- **Day 1 — hunters have leverage.** Everyone has a startbeest, but variety
  is scarce: new species enter the camp only through foxes, so everyone
  wants to meet a hunter. Food is plentiful because nobody has much to feed
  yet.
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
  vonk rule already handles this (utility yes, repeat score no).
- **Adults approaching children for points.** Fri3d is a family camp and the
  incentive is symmetric and mild, but keep the framing "meet fellow players",
  never "collect people", and keep vonk value modest relative to care and
  discovery scores.

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

- **Creature saturation.** By day 2 most players may have most creatures, and
  hunting deflates. Mitigate with staged fox activation and rotating creature
  IDs per fox — scarcity should come from *time*, not from telling a child
  "sorry, out of clones". Saturation of commons is acceptable if rares keep
  trickling; the endgame shifts to bond depth and communal goals, which is by
  design.
- **Introduction spam — resolved by removing deliberate introductions.**
  Creatures spread only through the vonk-geluk roll, which is bounded by the
  vonk rules (per-pair-per-day, daily cap); there is no share button to spam.
- **Badge speed-dating.** If vonken dominate scoring, optimal play is booping
  every stranger in the food queue. Mitigate with the daily vonk cap, modest
  vonk value, and optionally requiring a 30-second joint payload (mini
  playdate) so each scored exchange has a time cost and an actual interaction.
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
- Public score counts only server-verified unique events (pair vonken,
  first introductions), which the server can dedupe and rate-limit.
- A forged creature on your own badge is a single-player mod, not an exploit.
- A forged snuffel report mints at most a spreadable-tier creature on the
  forger's own profile and no vonk score (score needs the partner's
  matching report): boring.
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
| **Plukken** | Walk to `fri3d-badge` hotspots around the terrain | Food, rare finds and materials |
| **Beestenschool** | Tilt maze, rhythm game, Flappy-style game or LED Simon | Skills and bond |
| **Habitat bouwen** | Gather and spend materials on a small habitat | Decorations and animations |
| **Onderzoek** | Visual quizzes, behaviour puzzles and pattern matching | Dossier pages and discoveries |
| **Speeldate** | A cooperative interaction between two badges | Friendship stamps and shared rewards |
| **Camp-opdracht** | Visit a workshop or staff station and enter a code | Special materials or story chapters |

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

Setup answers its one game question by itself: **is the LoRa kit
installed?** The kit's radio — a Seeed Wio-SX1262-N module — solders onto
the badge's SPI bus, so the app can probe for it: read a register with a
known reset value, and a missing module answers with bus noise (0x00/0xFF).
Detected → Jagen is on, and setup says so ("Antenne gevonden!"). Not
detected → verzamelaar, and no question is asked. A settings toggle remains
as the override in both directions, because the probe sees the radio
module, not the antenna: the spiral antenna solders on separately and is
invisible to software, so a player mid-assembly may want Jagen off, and a
false negative must never lock anyone out. Probing is receive-only and
safe; the module must simply never transmit without its antenna (a
hardware warning, and another reason the badge only listens). A wrongly
enabled Jagen is harmless either way: a quiet hunt screen, and a hunter_id
the LoRa bridge never attributes anything to.

**Upgrading is purely additive.** A verzamelaar who installs an antenna
gains the Hunt track and loses nothing — not creatures, not bond, not food.
An earlier draft considered wiping the roster "so there is something to
hunt"; that breaks the game's one absolute rule (permanent progress is
safe) and lands on exactly the player most worth rewarding: the kid who got
hooked without an antenna and then went and got one. What keeps hunting
meaningful for an upgrader is already in the design — rares and legendaries
never arrive by vonk-geluk, staged fox activation keeps new species
entering all weekend, and *zelf vinden* (below) makes re-finding a known
creature a scored, celebrated event. The kit is soldered, so the upgrade
moment is a boot: the first launch that detects the module celebrates it —
"Antenne gevonden!" — and mints a hunter_id (via the existing profile
PATCH). Toggling Jagen off later simply leaves the id dormant.

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

### Zelf vinden (the re-find)

A hunter will sooner or later track a fox whose creature they already know
— as their startbeest or through a snuffel. That find is not a dud; it is
an upgrade:

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

## The first gatherer experience

Nobody begins with an empty collection: the startbeest (see *Onboarding*)
arrives at registration. The companion opens the game as the tutorial
guide:

- Complete a first short activity.
- Gather a starter berry, nut and acorn.
- Learn how feeding and playing work.
- Hand over to the startbeest, which those resources then feed.

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
a larger bond or mood bonus. Other possible resources include toys, habitat
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

## Scoring

Hunter and gatherer accomplishments should remain legible as different kinds
of mastery rather than being forced into one raw leaderboard.

### Hunter progress

- Unique creatures discovered — including zelf vinden: re-finding a creature
  first met through others scores as a discovery, because the score is for
  finding the fox, not for first ownership.
- Unique players introduced to each creature, with sensible caps.
- Special discoveries and legendary appearances.

### Gatherer progress

- Bond milestones across creatures.
- Deepest individual relationship.
- Variety of forage finds and completed assignments.
- Skills learned and dossier pages unlocked.
- Vonken, playdates and creatures spread onward through vonk-geluk.

### Shared camp progress

A communal forest or sanctuary can grow through every discovery, bond milestone
and exchange. Weekend-wide goals encourage cooperation, for example:

- Take 500 creatures on an outing.
- Complete every habitat type.
- Organise 200 playdates.
- Introduce every creature to at least ten players.

The creature lineage trees ("who introduced whom") make a lovely communal
visualisation for the scoreboard screen.

Current hunger, mood and energy should not affect public score. Neither should
raw taps or unlimited step totals.

## Roles and navigation

Hunter and gatherer are play tracks rather than permanent, exclusive
identities:

- Everyone has access to Care, Gathering, Activities and Friends.
- Players with an antenna can additionally enable Hunt.
- Players may add an antenna or change their preference later.

The LoRa kit's radio module sits on the badge's SPI bus and is probed at
startup, so the Hunt track enables itself; a settings toggle covers the
edge cases the probe cannot see (see *Onboarding*).

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

Public points favour verifiable, unique events (vonken, first introductions,
cooperative handshakes). Personal care state remains forgiving and locally
owned.

### How a creature reaches the profile

The server's creature list is the durable record a restore rebuilds from, so
every legitimate acquisition path must end there — and each path has its own
writer:

- **Startbeest** — minted by the server itself inside the registration POST
  and returned in the response. The pick function is deterministic and
  shared, so a badge that registers offline computes the identical creature
  and the records converge on the next sync.
- **Hunt** — written only by the LoRa bridge, exactly as before; the badge
  never claims its own catches. If the row already exists from another
  source, the bridge report *upgrades* it to zelf gevonden instead of
  duplicating it.
- **Snuffel** — the gap: a verzamelaar has no antenna, so nothing on the
  bridge path ever writes their vonk-geluk creatures, and a restore would
  hand back an account without them. The fix is a narrow badge→server
  **snuffel report**: when the badge next has WiFi it posts its snuffel
  events (pair, day, and which creature introduced itself). The badge still
  never claims a *catch* — it reports a *meeting*, which the server can
  cross-check against the partner's matching report.

**Grants are generous; points are verified.** A single-sided snuffel report
is enough to store the creature — rate-limited, per-pair-per-day enforced,
and rarity-capped at the spreadable tiers — because a child must never lose
a beest to a friend's dead battery or a badge that never reconnects. Vonk
*score*, by contrast, counts only when both sides' reports corroborate,
consistent with the rule that public score counts only server-verified
unique events. The worst a forged report can mint is a common creature on
the forger's own profile and no points: the same boring single-player mod
the adversarial section already accepts.

## Recommended first playable slice

Before building a large economy, test a compact experience:

0. **Hardware spikes first**: the ESP-NOW spike is done (see the espnow-test
   experiment: the channel recipe, the RSSI curve, the trust model). The WiFi
   scan spike remains: scan-while-associated, scan latency, battery per
   burst, and a census of `fri3d-badge` BSSIDs on the terrain.
1. Companion tutorial, ending in the startbeest reveal (server-minted in
   the registration POST).
2. Creature spread through vonk-geluk over snuffel, with the snuffel
   report syncing the result to the profile.
3. Plukken against one real `fri3d-badge` hotspot: warmer/colder screen,
   BSSID identity, per-badge reload.
4. One motion mini-game, such as a tilt maze.
5. One touch/button game, such as LED Simon or Flappy.
6. Berry, nut and acorn inventory with favourite-food bonuses.
7. Bond level 2 unlocks a dossier page and habitat decoration.
8. One badge-to-badge snuffel: the vonk rule, a vriendenboekje page and the
   vonk-geluk roll.
9. Separate discovery and bond achievements.

This slice tests the essential questions: is caring for and playing with a
creature satisfying without a LoRa hunt, and does the snuffel moment deliver
enough delight to carry the social economy?

## Open design questions

- ~~Is each roster entry one named creature shared by many players, or a
  species from which each player receives their own individual creature?~~
  → Resolved by the "spoor" fiction: the same creature known to many players,
  each with their own bond.
- Should the main gatherer fantasy emphasise one deep relationship or a broad
  sanctuary collection?
- ~~How many mentor invitations may a strong gatherer create?~~
  → Resolved: the mentor model is replaced by vonk-geluk spread; deliberate
  sharing is finder-only.
- How many `fri3d-badge` hotspots hang on the terrain, and roughly where?
  (Gates plukken tuning: reload duration and yields per day.)
- Tuning numbers that need playtesting: the vonk-geluk odds per rarity tier,
  the plukplek reload duration, and energy cost/restore per play session.
- Which rewards remain local and which contribute to public scoring?
- How many foxes will be deployed, and can their activation be staged across
  the weekend? How many players will have antennas? (Both numbers gate the
  economy tuning — ask the orga.)
- Which camp stations sit near a `fri3d-badge` hotspot or can host physical
  assignments?
- Does the vonk need a time-cost payload (mini playdate) or is a plain
  handshake enough?
- How prominent should competition be compared with the communal sanctuary?
- Is the startbeest score-neutral (everyone has one) or does it count in
  breadth milestones?

## Glossary additions

Following the one-word-per-thing rule:

| Code (English) | UI (Dutch) | What it is |
| --- | --- | --- |
| **gatherer** | **verzamelaar** | The non-antenna play track: foraging resources for creature care. |
| **spread** | **vonk-geluk** | The chance, on a vonk, that one of the other player's creatures introduces itself; both keep it. Never "clone" in the UI. The only way creatures spread. |
| **boop / socialize** | **snuffelen** | The face-to-face handshake over ESP-NOW, gated at -50 dBm RSSI on both sides — and the home-screen mode named after it. |
| **spark** | **vonk** | The once-per-pair-per-day mutual reward for a first snuffel. |
| **friend book** | **vriendenboekje** | The permanent collection: one page per first-ever meeting between two badges. |
| **forage** | **plukken** | Passively scanning for `fri3d-badge` hotspots and harvesting a nearby one. |
| **forage spot** | **plukplek** | One physical hotspot, identified by its BSSID, that reloads per badge. |
| **reload** | — | The per-badge cooldown before the same plukplek yields again. |
| **starter** | **startbeest** | The one base-tier creature every player receives at registration, deterministic per badge; the tutorial creature for both tracks. |
| **self-found** | **zelf gevonden** | The dossier upgrade when a hunter finds the fox of a creature they already knew. Scores as a discovery and pays a verzorgingspakket; nothing is removed. |
| **care package** | **verzorgingspakket** | The food bundle a zelf-gevonden creature hands over, weighted toward its favourite. |
| **snuffel report** | — | The badge→server sync of a snuffel event (pair, day, vonk-geluk outcome). Grants are single-sided and rarity-capped; score needs both sides. |

Retired: **foerageren** (say plukken).
