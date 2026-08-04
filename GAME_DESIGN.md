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

The same philosophy extends to the exchange economy: players **give**, they do
not barter or haggle. There is no price screen and no trade negotiation; an
exchange is a gift plus a mutual reward for meeting.

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

What is missing is a game economy around these screens. Food is currently
unlimited, while petting and playing are repeatable actions, so bond can be
maximised through tapping alone. Gathering, activities, skills and social
events should give those actions meaning.

## The gatherer loop

### 1. Ontmoet

A hunter introduces a creature through a face-to-face exchange or a sharing
code. The hunter keeps the creature; the recipient begins their own
relationship with it.

### 2. Ga verzamelen

The gatherer roams the camp to collect food and materials. Foraging should be a
*physical* activity that mirrors the hunt with commodity hardware:

- **Forage spots**: cheap WiFi beacons (ESP32s broadcasting a recognisable
  SSID) hidden around the terrain. The badge scans for them; proximity — walk
  around, watch the signal grow — yields berries, nuts, acorns or rarer finds.
  This gives gatherers the same "walk toward an invisible signal" joy as
  direction finding, at WiFi ranges and difficulty a seven-year-old can manage.
- Camp assignments, movement missions and mini-games as alternative sources.

Different spots (or spots on different days) yield different resources, so a
complete pantry requires covering ground, just as a complete roster requires
finding every fox.

### 3. Verzorg

The player responds to a creature's current needs. Hunger makes food useful;
low energy may suggest a calm activity; a cheerful creature may want to play.

### 4. Speel of leer

The player completes an actual mini-game. Different creatures can prefer or
excel at different activities.

### 5. Groei samen

Bond unlocks expressions, animations, dossier pages, skills, habitat
decorations, avatar accessories and social abilities.

### 6. Deel

The gatherer's surplus becomes social currency: rare foods and crafted items
are gifts that hunters (and other gatherers) genuinely need. See *The
exchange* below.

Permanent progression consists of bond, skills, memories, decorations and
friendships. Hunger, energy and mood provide temporary context.

## The exchange: snuffelen en vonken

All face-to-face interactions run through **one physical mechanic** with
different payloads, rather than a different flow per feature.

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

### Payloads

One handshake, several things it can carry:

| Payload | Direction | What happens |
|---|---|---|
| **Spoor** | hunter → anyone | Introduces a creature; recipient starts their own bond. |
| **Hapje / materiaal** | gatherer → anyone | Gifts food or habitat material from inventory. |
| **Speeldate** | any ↔ any | Cooperative interaction; both creatures gain a shared memory. |

### De vonk (the anti-farming rule)

The *handshake itself* is the scored social event, separate from the payload.
The first snuffel between a given pair of players each day produces a **vonk**
for both — the meet-new-people reward. Repeats within the same pair still
transfer items (siblings and tent-mates can keep helping each other) but earn
no further vonken that day. This gives:

- an incentive to walk up to strangers (new pair → new vonk),
- no incentive to stand in a corner farming one friend,
- no hard "never again" wall between friends — utility transfer stays
  unlimited, only *score* is pair-limited.

Consider additionally capping vonken per day (e.g. the first ~10 count) so the
optimal strategy is "meet some new people every day", not "speed-boop the
entire dinner queue".

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

### Gatherer-to-gatherer sharing

A staged model preserves the value of hunting without making hunters permanent
gatekeepers:

1. A hunter introduces a newly discovered creature.
2. After reaching a strong bond level, a gatherer earns one mentor invitation
   for that creature and may introduce it onward.
3. The original hunter remains credited in the creature's lineage.
4. Everyone keeps their creature.

Playdates remain unlimited because they create shared experiences rather than
new creature ownership.

This decentralises distribution over the weekend and helps late arrivals join
when relatively few hunters are around.

## Economy across the weekend

The economy's centre of gravity shifts naturally, and that shift *is* the
pacing:

- **Day 1 — hunters have leverage.** Creatures are scarce; everyone wants an
  introduction. Food is plentiful because nobody has much to feed yet.
- **Day 2–3 — gatherers have leverage.** Most players have creatures; bond
  progression consumes food, and favourite/rare foods come from forage spots
  hunters haven't had time to cover. Now hunters queue at the gatherers.

Levers to keep both halves relevant all weekend:

- **Staged fox activation.** Don't switch on every transmitter on Friday.
  Activating new foxes (or rotating which creature a fox transmits) each day
  keeps new creatures entering the economy, so hunters matter on Sunday too.
- **Rotating forage spots.** Move or re-seed WiFi forage spots daily so
  gathering stays an exploration, not a milk run, and no single spot gets
  camped.
- **Gatherer-exclusive rares.** Favourite foods (big bond bonus) and habitat
  materials come primarily from foraging. Hunters *can* forage, but their time
  is split — realistic scarcity without hard role locks.
- **A staff safety valve.** An organiser badge at the infodesk can introduce
  one common starter creature to anyone who can't find a hunter. Cap it to
  commons so hunters keep their prestige; no child should be blocked from the
  whole game because they don't know the right teenager.

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

- **RSSI as a consent boundary.** -50 dBm is a guess until it is measured, and
  it is now the only thing keeping the snuffel face-to-face. The failure modes
  are asymmetric: too strict and the handshake never fires in a crowd, too
  loose and you can be sniffed from the next picnic table. *Build the RSSI
  debug test first*: log RSSI against measured distance outdoors, with badges
  in hands and in pockets, with bodies in between, and with a dozen other
  badges nearby. If the number proves unstable, promote the manual code to
  co-equal status rather than shipping a boundary that lies.
- **ESP-NOW and camp WiFi on one radio.** ESP-NOW peers must sit on the same
  WiFi channel, and associating with an access point pins the badge to that
  AP's channel. Confirm the two can coexist — and what happens to a snuffel
  between one badge on camp WiFi and one that is not.
- **Also confirm**: can the badge scan for SSIDs while associated with camp
  WiFi (needed for forage spots)? What do continuous scans cost in battery?
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
- **Introduction spam.** A hunter handing a spoor to fifty people at the bar
  tops the discovery board without hunting anything new. Cap scored
  introductions per creature (e.g. the first five unique recipients count);
  further sharing is generosity, not points.
- **Badge speed-dating.** If vonken dominate scoring, optimal play is booping
  every stranger in the food queue. Mitigate with the daily vonk cap, modest
  vonk value, and optionally requiring a 30-second joint payload (mini
  playdate) so each scored exchange has a time cost and an actual interaction.
- **Food dumping.** A gatherer showers one friend with 50 berries →
  instant max bond. The playful-refusal rule ("creature is full") must be a
  real rate limit on bond-from-feeding, not just flavour text.
- **Shaking the badge** to fake movement missions — already addressed: short
  foreground missions, no all-day step leaderboard, non-motion alternatives.
- **Forage spot camping.** A known static spot becomes a farm; rotate spots
  and cap yield per spot per player per day.

### Social risks

- **Shy players and non-Dutch speakers.** Walking up to strangers is the point,
  but it must never be the *only* path: manual codes, the daily
  verzamelmoment, and solo-viable progression (care + activities) keep the
  game playable without cold-approaching anyone.
- **Non-players getting pestered.** 500 people aren't playing. Visible
  player-state (the "wil snuffelen" idle screen) tells kids who is fair game
  to approach.
- **Badge swapping.** Children will physically trade badges. Identity is the
  badge; keep it low-stakes and recoverable server-side rather than trying to
  prevent it.

### Adversarial risks (it's a hacker camp)

Assume the protocol is public by Saturday morning: forged shortcodes, spoofed
handshakes, replayed spoor payloads, fake forage beacons. ESP-NOW widens this a
little — an attacker with a stock ESP32 and an amplifier can present whatever
RSSI they like, so the -50 dBm gate stops honest badges at range, not
determined ones. Respond by making cheating *boring*, not impossible:

- Personal care state is local and forgiving — nothing to steal, nothing worth
  forging.
- Public score counts only server-verified unique events (pair vonken,
  first introductions), which the server can dedupe and rate-limit.
- A forged creature on your own badge is a single-player mod, not an exploit.
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
| **Foerageren** | Follow WiFi forage spots around the terrain | Food, rare finds and materials |
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

## The first gatherer experience

A gatherer should not begin with an empty collection and an instruction to
find somebody with extra hardware.

The existing companion can serve as a tutorial guide:

- Complete a first short activity.
- Gather a starter berry, nut and acorn.
- Learn how feeding and playing work.
- Carry those resources forward when the first creature is introduced.

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
- Playdates and mentor invitations.
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

- Unique creatures discovered.
- Unique players introduced to each creature, with sensible caps.
- Special discoveries and legendary appearances.

### Gatherer progress

- Bond milestones across creatures.
- Deepest individual relationship.
- Variety of forage finds and completed assignments.
- Skills learned and dossier pages unlocked.
- Vonken, playdates and successful mentorships.

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

The passive antenna cannot be detected reliably by software, so the Hunt track
should be enabled explicitly during setup or in settings.

The home experience will need a top-level distinction between collection,
activities and hunting. Simply placing more buttons inside a caught creature's
detail page would leave a new gatherer with nothing to do.

## Connectivity and trust

Core care and mini-games work offline and synchronise later. Sharing
transports, in order of universality:

- A short, one-time manual code as the universal baseline.
- The ESP-NOW snuffel, gated at -50 dBm, for deliberate face-to-face exchanges.
- The same ESP-NOW link, held open, for richer playdates.
- Camp WiFi and the cloud server for durable provenance, scoring and recovery.

Public points favour verifiable, unique events (vonken, first introductions,
cooperative handshakes). Personal care state remains forgiving and locally
owned.

## Recommended first playable slice

Before building a large economy, test a compact experience:

0. **Hardware spikes first**: the ESP-NOW snuffel debug test (RSSI against
   real distance, error rate, coexistence with camp WiFi) and a WiFi SSID scan
   test. These two results shape everything above.
1. Companion tutorial.
2. Hunter-to-gatherer spoor via one-time code, then via snuffel.
3. One WiFi forage spot with a signal-strength "warmer/colder" screen.
4. One motion mini-game, such as a tilt maze.
5. One touch/button game, such as LED Simon or Flappy.
6. Berry, nut and acorn inventory with favourite-food bonuses.
7. Bond level 2 unlocks a dossier page and habitat decoration.
8. One badge-to-badge playdate with the vonk rule.
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
- How many mentor invitations may a strong gatherer create?
- Which rewards remain local and which contribute to public scoring?
- How many foxes will be deployed, and can their activation be staged across
  the weekend? How many players will have antennas? (Both numbers gate the
  economy tuning — ask the orga.)
- Which camp stations can host forage beacons or physical assignments?
- Does the vonk need a time-cost payload (mini playdate) or is a plain
  handshake enough?
- How prominent should competition be compared with the communal sanctuary?

## Glossary additions

Following the one-word-per-thing rule:

| Code (English) | UI (Dutch) | What it is |
| --- | --- | --- |
| **gatherer** | **verzamelaar** | The non-antenna play track: foraging resources for creature care. |
| **share / introduce** | **een spoor delen** | A hunter (or mentor) letting another player meet a creature; both keep it. Never "clone" in the UI. |
| **boop** | **snuffelen** | The face-to-face handshake, over ESP-NOW, gated at -50 dBm RSSI. |
| **spark** | **vonk** | The once-per-pair-per-day mutual reward for a first snuffel. |
| **forage spot** | **plukplek** | A WiFi beacon location that yields resources when found. |
