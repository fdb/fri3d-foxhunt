# Vossenjacht — Game Design

## Purpose

Vossenjacht is an ARDF game for Fri3d Camp. Players with a LoRa antenna can hunt
physical transmitters and discover creatures. Not every player will have an
antenna, so the game also needs a complete experience for players who cannot
participate in the physical hunt.

The two main play tracks are:

- **Hunters** discover creatures using LoRa direction finding.
- **Caretakers** help creatures experience the world through care, activities,
  games and social interactions.

These should feel like complementary ways to participate, not a primary game
and a lesser substitute.

> Hunters discover creatures. Caretakers help creatures experience the world.

Hunters may also care for creatures. Having an antenna adds the Hunt track; it
does not exclude the rest of the game.

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

## Existing foundations

The current app already contains much of the presentation needed for a
caretaker game:

- Bond, levels and hearts.
- Hunger, mood and energy.
- Feeding, petting and playing.
- Berry, nut and acorn food, with creature-specific favourites.
- A dossier containing habitat, species, rarity and facts.
- Stored nickname and sightings fields that can be developed further.
- A customisable companion (maatje) created during onboarding.

What is missing is a game economy around these screens. Food is currently
unlimited, while petting and playing are repeatable actions, so bond can be
maximised through tapping alone. Activities, resources, skills and social
events should give those actions meaning.

## Core caretaker loop

### 1. Ontmoet

A hunter introduces a creature through a sharing code or a local badge-to-badge
interaction. The hunter keeps the creature; the recipient begins their own
relationship with it.

### 2. Ga op pad

The caretaker selects a short physical, puzzle or camp assignment. Completing
it earns food, toys, materials or memories.

### 3. Verzorg

The player responds to the creature's current needs. Hunger makes food useful;
low energy may suggest a calm activity; a cheerful creature may want to play.

### 4. Speel of leer

The player completes an actual mini-game. Different creatures can prefer or
excel at different activities.

### 5. Groei samen

Bond unlocks expressions, animations, dossier pages, skills, habitat
decorations, avatar accessories and social abilities.

### 6. Ga op speeldate

Two players bring their badges together for a cooperative interaction. Both
creatures receive a shared memory or reward.

Permanent progression consists of bond, skills, memories, decorations and
friendships. Hunger, energy and mood provide temporary context.

## Activity families

The badge has an accelerometer and gyroscope, touch screen, physical buttons,
five LEDs, a buzzer, WiFi, IR and support for local wireless communication.

| Mode | Example activity | Reward |
|---|---|---|
| **Op avontuur** | A short walk or movement session | Food and expedition postcards |
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

## Sharing fiction

Because the sender keeps the creature, the interaction should not be described
as selling or surrendering an animal. Better language includes:

- **Stel je beest voor**
- **Deel een vriendencode**
- **Geef een vriendschapsvonkje**
- **Deel een spoor**

The recipient develops their own bond. The dossier can preserve the social
history:

> Ontmoet via Noor  
> Oorspronkelijk gevonden door Sam  
> 4 speelvrienden

Both players receive a reward for the first successful introduction of a given
creature between them. Repeating the same exchange should not produce unlimited
public points.

### Caretaker-to-caretaker sharing

A staged model preserves the value of hunting without making hunters permanent
gatekeepers:

1. A hunter introduces a newly discovered creature.
2. After reaching a strong bond level, a caretaker earns one mentor invitation
   for that creature.
3. The original hunter remains credited in the creature's lineage.
4. Everyone keeps their creature.

Playdates can remain unlimited because they create shared experiences rather
than new creature ownership.

This also provides a meaningful bond unlock and helps late arrivals join the
game when relatively few hunters are available.

## The first caretaker experience

A caretaker should not begin with an empty collection and an instruction to
find somebody with extra hardware.

The existing companion can serve as a tutorial guide:

- Complete a first short activity.
- Gather a starter berry, nut and acorn.
- Learn how feeding and playing work.
- Carry those resources forward when the first creature is introduced.

The companion need not become a collectible creature. Its purpose is to make the game
immediately playable and give every participant a personal identity.

Avatar accessories should have multiple unlock paths. A hunter might unlock an
item through discoveries, while a caretaker can unlock the same item through
bond, skills or social milestones.

## Resources and rewards

The existing foods provide a natural first resource system:

- **Bes**
- **Noot**
- **Eikel**

Assignments can award these directly. Feeding a favourite food grants a larger
bond or mood bonus. Other possible resources include toys, habitat materials,
stickers and story fragments.

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

Hunter and caretaker accomplishments should remain legible as different kinds
of mastery rather than being forced into one raw leaderboard.

### Hunter progress

- Unique creatures discovered.
- Unique players introduced to each creature, with sensible caps.
- Special discoveries and legendary appearances.

### Caretaker progress

- Bond milestones across creatures.
- Deepest individual relationship.
- Variety of completed assignments.
- Skills learned and dossier pages unlocked.
- Playdates and successful mentorships.

### Shared camp progress

A communal forest or sanctuary can grow through every discovery, bond milestone
and playdate. Weekend-wide goals encourage cooperation, for example:

- Take 500 creatures on an outing.
- Complete every habitat type.
- Organise 200 playdates.
- Introduce every creature to at least ten caretakers.

Current hunger, mood and energy should not affect public score. Neither should
raw taps or unlimited step totals.

## Roles and navigation

Hunter and caretaker are best treated as play tracks rather than permanent,
exclusive identities:

- Everyone has access to Care, Activities and Friends.
- Players with an antenna can additionally enable Hunt.
- Players may add an antenna or change their preference later.

The passive antenna cannot be detected reliably by software, so the Hunt track
should be enabled explicitly during setup or in settings.

The home experience will need a top-level distinction between collection,
activities and hunting. Simply placing more buttons inside a caught creature's
detail page would leave a new caretaker with nothing to do.

## Connectivity and trust

Core care and mini-games should work offline and synchronise later. Possible
sharing transports include:

- A short, one-time manual code as the universal baseline.
- An IR "nose boop" for deliberate face-to-face exchanges.
- Local wireless communication for richer playdates.
- Camp WiFi and the cloud server for durable provenance, scoring and recovery.

Public points should favour verifiable, unique events such as a new
hunter-to-caretaker introduction or cooperative handshake. Personal care state
can remain forgiving and locally owned.

## Recommended first playable slice

Before building a large economy, test a compact caretaker experience:

1. Companion tutorial.
2. Hunter-to-caretaker one-time sharing code.
3. One short foraging walk or movement mission.
4. One motion mini-game, such as a tilt maze.
5. One touch/button game, such as LED Simon or Flappy.
6. Berry, nut and acorn inventory with favourite-food bonuses.
7. Bond level 2 unlocks a dossier page and habitat decoration.
8. One badge-to-badge playdate.
9. Separate discovery and bond achievements.

This slice tests the essential question: is caring for and playing with a
creature satisfying even when the player never performs a LoRa hunt?

## Open design questions

- Is each roster entry one named creature shared by many players, or a species
  from which each player receives their own individual creature?
- Should the main caretaker fantasy emphasise one deep relationship or a broad
  sanctuary collection?
- How many mentor invitations may a strong caretaker create?
- Which rewards remain local and which contribute to public scoring?
- Which camp stations can support optional physical assignments?
- How prominent should competition be compared with the communal sanctuary?

