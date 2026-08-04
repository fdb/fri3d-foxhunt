/**
 * The public one-pager: what Vossenjacht is, and how the two play tracks —
 * jager (LoRa) and verzamelaar (WiFi, in development) — feed each other.
 *
 * Screenshots under /screens are 640x480: an exact 2x of the badge's 320x240
 * screen, so they stay pixel-crisp at 320 CSS px (1x) or 640 (2x). Anything
 * between those relies on `image-rendering: pixelated`.
 */

const CREATURES = [
  "vos",
  "kat",
  "egel",
  "konijlpaard",
  "everzwaan",
  "kameleeuw",
  "tijghert",
  "axolotl",
  "slakamander",
  "koekoekoek",
  "knoricorn",
];

const Shot = ({
  src,
  alt,
  caption,
  big,
}: {
  src: string;
  alt: string;
  caption: string;
  big?: boolean;
}) => (
  <figure class={big ? "shot shot-big" : "shot"}>
    <div class="bezel">
      <img src={`/screens/${src}.png`} width="640" height="480" alt={alt} />
    </div>
    <figcaption>{caption}</figcaption>
  </figure>
);

export const Home = () => (
  <>
    <nav class="nav">
      <a class="nav-brand" href="/">
        <img src="/vos.png" alt="" width="24" height="24" />
        Vossenjacht
      </a>
      <a href="#spelen">Twee manieren</a>
      <a href="#begin">Beginnen</a>
      <a href="#jacht">De jacht</a>
      <a href="#verzorgen">Verzorgen</a>
      <a class="nav-cta" href="/scores">
        Scorebord
      </a>
    </nav>

    <section class="hero">
      <div class="stars" aria-hidden="true">
        {Array.from({ length: 14 }, () => (
          <span />
        ))}
      </div>
      <div class="wrap">
        <h1 class="sr-only">Vossenjacht</h1>
        <div class="sign">
          <img
            src="/art/title-screen.png"
            width="320"
            height="120"
            alt="Vossenjacht"
          />
        </div>
        <p class="tagline">Spoor de beesten van het bos op.</p>
        <p class="lede">
          Vossenjacht is het badge-spel van Fri3d Camp. Ergens op het terrein
          staan <b>vossen</b> verstopt: kleine zendertjes die je met je badge
          kan opsporen. Elke vos die je vindt geeft je een <b>beest</b> voor je
          boek — en vanaf dat moment zorg jij ervoor.
        </p>
        <p class="buttons">
          <a class="btn btn-primary" href="#spelen">
            Zo speel je
          </a>
          <a class="btn btn-ghost" href="/scores">
            Bekijk het scorebord
          </a>
        </p>
        <div class="strip" aria-hidden="true">
          {CREATURES.map((c, i) => (
            <img
              src={`/art/animals/${c}.png`}
              width="16"
              height="16"
              alt=""
              style={`--i:${i}`}
            />
          ))}
        </div>
        <p class="strip-note">
          Twaalf beesten om te ontdekken — en een paar die je niet verwacht.
        </p>
      </div>
    </section>

    <section class="band band-paper">
      <div class="wrap">
        <h2>In het kort</h2>
        <div class="cards cards-3">
          <div class="card">
            <span class="icon" aria-hidden="true">
              📡
            </span>
            <h3>Zoek</h3>
            <p>
              Je badge wordt warmer of kouder terwijl je rondloopt. Draai,
              luister naar de lampjes, en volg het signaal tot je bij de vos
              staat.
            </p>
          </div>
          <div class="card">
            <span class="icon" aria-hidden="true">
              🔢
            </span>
            <h3>Vang</h3>
            <p>
              Op elke vos staat een code van vier cijfers. Tik hem in en het
              beest dat erbij hoort komt in je boek.
            </p>
          </div>
          <div class="card">
            <span class="icon" aria-hidden="true">
              🫐
            </span>
            <h3>Verzorg</h3>
            <p>
              Voeren, aaien, spelen. Je band groeit, het dossier vult zich, en
              je beest leert je kennen.
            </p>
          </div>
        </div>
      </div>
    </section>

    <section class="band band-forest" id="spelen">
      <div class="wrap">
        <h2>Twee manieren om te spelen</h2>
        <p class="intro">
          Vossenjacht heeft twee speelwijzen: je kan <b>jagen</b> of{" "}
          <b>verzamelen</b>. Samen zijn ze de jager-verzamelaars, en ze hebben
          elkaar nodig.
        </p>
        <div class="cards cards-2">
          <article class="card mode mode-hunter">
            <h3>
              <span class="icon" aria-hidden="true">
                🦊
              </span>
              Jager
            </h3>
            <p class="mode-req">Met LoRa-antenne</p>
            <p>
              Voor de badge bestaat een losse <b>LoRa-antenne</b>: die bestel je
              erbij en soldeer je zelf op je badge. Daarmee gaat de jacht open.
            </p>
            <p>
              Je loopt ermee het terrein af, draait rond tot het signaal warm
              wordt, en vindt de vos. Jij brengt de nieuwe beesten het kamp in —
              en jij deelt ze met de rest.
            </p>
          </article>
          <article class="card mode mode-gatherer">
            <span class="ribbon">In ontwikkeling</span>
            <h3>
              <span class="icon" aria-hidden="true">
                🧺
              </span>
              Verzamelaar
            </h3>
            <p class="mode-req">Zonder antenne — WiFi is genoeg</p>
            <p>
              Geen antenne? Dan ben je verzamelaar, en daarvoor heb je genoeg
              aan de WiFi die elke badge al aan boord heeft.
            </p>
            <p>
              Je zoekt <b>plukplekken</b> op het terrein en speelt spelletjes.
              Zo verzamel je bessen, noten, eikels en materiaal: precies wat de
              beesten nodig hebben om te groeien.
            </p>
          </article>
        </div>
        <blockquote class="quote">
          Jagers brengen de beesten binnen. Verzamelaars brengen wat ze nodig
          hebben. <b>Verzorgen is het spel dat iedereen speelt.</b>
        </blockquote>
        <p class="intro">
          Daardoor loopt het in twee richtingen. Een jager zonder eten heeft
          hongerige beesten; een verzamelaar zonder beesten heeft een volle
          voorraadkast en niemand om te voeren. Je hebt elkaar echt nodig — en
          dat ruil je uit door elkaar op te zoeken.
        </p>
        <p class="note note-dark">
          Een antenne sluit niets uit, hij <i>voegt</i> de jacht toe. Jagers
          mogen ook verzamelen, verzamelaars zorgen net zo goed voor hun
          beesten. Je kiest geen rol — je kiest waar je je tijd aan besteedt.
        </p>
      </div>
    </section>

    <section class="band band-paper" id="begin">
      <div class="wrap">
        <h2>Zo begin je</h2>
        <ol class="steps">
          <li>
            <div class="step-text">
              <h3>Zet je badge aan</h3>
              <p>
                Start Vossenjacht en druk op <b>Registreer</b>. Heb je hier al
                eens gespeeld? Dan haal je je account terug met “Herstel mijn
                account”.
              </p>
            </div>
            <Shot
              src="welkom"
              alt="Het welkomscherm met de knop Registreer"
              caption="Het beginscherm"
            />
          </li>
          <li>
            <div class="step-text">
              <h3>Maak je maatje</h3>
              <p>
                Je maatje is je eigen figuurtje: kies een kop, plak er extra’s
                op en kies een kleur. Je ziet meteen wat je maakt.
              </p>
            </div>
            <div class="shot-pair">
              <Shot
                src="maatje-kop"
                alt="Maatje maken: keuze uit vijf koppen"
                caption="Kies een kop"
              />
              <Shot
                src="maatje-extra"
                alt="Maatje maken: brillen, hoeden en andere extra's"
                caption="En wat extra’s"
              />
            </div>
          </li>
          <li>
            <div class="step-text">
              <h3>Klaar om te jagen</h3>
              <p>
                Je account staat in de cloud. Een lege badge is daardoor nooit
                een leeg spel: je haalt jezelf altijd terug.
              </p>
            </div>
            <Shot
              src="ingeschreven"
              alt="Bevestiging: je bent ingeschreven"
              caption="Ingeschreven"
            />
          </li>
        </ol>
      </div>
    </section>

    <section class="band band-soft" id="jacht">
      <div class="wrap">
        <h2>
          De jacht <span class="tag tag-hunter">jager</span>
        </h2>
        <p class="intro">
          Radiovossen zoeken heet officieel <i>ARDF</i>. In het echt is het
          vooral: rondlopen, rondjes draaien, en heel blij worden als de balk
          warmer wordt.
        </p>
        <div class="shots">
          <Shot
            src="jacht"
            alt="Het jachtscherm met een koud-warm balk en een silhouet"
            caption="Draai rond met je antenne. De balk gaat van koud naar warm, en de vijf lampjes op je badge doen mee."
          />
          <Shot
            src="code"
            alt="Cijferklavier om de code van de vos in te tikken"
            caption="Gevonden? Op de vos staat een code van vier cijfers. Tik hem in."
          />
          <Shot
            src="gevangen"
            alt="Gevangen! De Kat is toegevoegd aan je boek"
            caption="Het beest is van jou — toegevoegd aan je boek."
          />
          <Shot
            src="boek"
            alt="Het boek met gevangen en nog onbekende beesten"
            caption="Je boek: wie je al hebt, wie in de buurt zit, en wie nog een raadsel is."
          />
        </div>
      </div>
    </section>

    <section class="band band-paper" id="verzamelen">
      <div class="wrap">
        <h2>
          Verzamelen <span class="tag tag-gatherer">verzamelaar</span>
          <span class="tag tag-soon">binnenkort</span>
        </h2>
        <p class="intro">
          Geen antenne? Dan is er nog altijd genoeg te doen buiten. Verzamelaars
          halen uit het kamp wat de beesten nodig hebben.
        </p>
        <div class="cards cards-3">
          <div class="card">
            <span class="icon" aria-hidden="true">
              📶
            </span>
            <h3>Plukplekken</h3>
            <p>
              Kleine WiFi-bakens, verspreid over het terrein. Je badge zoekt
              ernaar en jij loopt erheen: hetzelfde warmer-kouder-gevoel als de
              jacht, maar zonder antenne — en makkelijk genoeg voor een
              zevenjarige.
            </p>
          </div>
          <div class="card">
            <span class="icon" aria-hidden="true">
              🎮
            </span>
            <h3>Spelletjes</h3>
            <p>
              Een tiltdoolhof, een ritmespel, LED-Simon. Elk beest heeft zijn
              eigen lievelingsspel, en daar is het net iets beter in.
            </p>
          </div>
          <div class="card">
            <span class="icon" aria-hidden="true">
              🗺️
            </span>
            <h3>Opdrachten</h3>
            <p>
              Korte wandelingen, workshops en stations in het kamp. Overal valt
              iets te halen: bessen, noten, eikels en zeldzamer spul.
            </p>
          </div>
        </div>
        <p class="note">
          Plukplekken wisselen van plaats, zodat verzamelen een verkenning
          blijft en niemand op één plek gaat kamperen. En sommige lekkernijen
          vind je alleen zo — dus ook jagers komen bij de verzamelaars langs.
        </p>
      </div>
    </section>

    <section class="band band-soft" id="verzorgen">
      <div class="wrap">
        <h2>Verzorgen — het gedeelde spel</h2>
        <p class="intro">
          Of je nu jaagt of verzamelt: hier komt alles samen. Elk beest heeft
          een band met jou, en een humeur, energie en honger die meebewegen.
        </p>
        <div class="shots">
          <Shot
            src="beest"
            alt="Beestscherm met band, humeur, energie en honger"
            caption="Band, humeur, energie en honger — plus de knoppen om te voeren, aaien, spelen."
          />
          <Shot
            src="voeren"
            alt="Voerscherm met bes, noot en eikel"
            caption="Bes, noot of eikel. Elk beest heeft een lievelingshapje, en dat geeft extra band."
          />
          <Shot
            src="dossier"
            alt="Dossier met soort, biotoop, zeldzaamheid en een weetje"
            caption="Het dossier vult zich terwijl de band groeit: soort, biotoop, weetjes."
          />
        </div>
        <div class="panel-safe">
          <h3>Beesten gaan nooit dood</h3>
          <p>
            Ze lopen niet weg en je verliest nooit wat je hebt opgebouwd. Een
            hongerig beest is een uitnodiging, geen straf. Speel je een dag niet
            mee, dan staat alles er gewoon nog — geen strafpunten, geen verloren
            reeks, geen boos berichtje.
          </p>
        </div>
      </div>
    </section>

    <section class="band band-forest" id="samen">
      <div class="wrap">
        <h2>
          Elkaar tegenkomen <span class="tag tag-soon">binnenkort</span>
        </h2>
        <div class="cards cards-2">
          <article class="card">
            <h3>
              <span class="icon" aria-hidden="true">
                👃
              </span>
              Snuffelen
            </h3>
            <p>
              Hou twee badges met hun neuzen tegen elkaar. Via infrarood
              wisselen ze iets uit: het <b>spoor</b> van een beest, een hapje
              uit je voorraad, of gewoon een speeldate. Bij een geslaagde
              snuffel juichen allebei de badges tegelijk.
            </p>
            <p class="fine">
              Infrarood is expres slecht op afstand. Dat is de bedoeling:
              niemand kan je van ver besnuffelen, jullie moeten er allebei voor
              gaan staan. Werkt het even niet? Er is altijd een korte code als
              alternatief.
            </p>
          </article>
          <article class="card">
            <h3>
              <span class="icon" aria-hidden="true">
                ✨
              </span>
              De vonk
            </h3>
            <p>
              De eerste keer per dag dat je iemand <i>nieuw</i> tegenkomt, geeft
              dat allebei een <b>vonk</b>. Bij dezelfde persoon nog eens
              snuffelen mag altijd — spullen doorgeven blijft werken — maar het
              levert die dag geen vonk meer op.
            </p>
            <p class="fine">
              Zo loont het om nieuwe mensen aan te spreken, en niet om in een
              hoekje met dezelfde vriend te blijven staan.
            </p>
          </article>
        </div>
      </div>
    </section>

    <section class="band band-paper band-end">
      <div class="wrap wrap-narrow">
        <h2>Wie loopt er voor?</h2>
        <p class="intro">
          Elke vangst komt binnen bij de bridge en verschijnt op het scorebord.
        </p>
        <p class="buttons">
          <a class="btn btn-primary" href="/scores">
            Naar het scorebord
          </a>
        </p>
      </div>
    </section>

    <footer class="site-footer">
      <div class="wrap">
        <p>
          <b>Vossenjacht</b> — badge-spel voor Fri3d Camp. Draait op de Fri3d
          2026-badge.
        </p>
        <p class="fine">
          <a href="/scores">Scorebord</a> ·{" "}
          <a href="https://fri3d.be">fri3d.be</a>
        </p>
      </div>
    </footer>
  </>
);
