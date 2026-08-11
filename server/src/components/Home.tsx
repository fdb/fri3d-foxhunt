/**
 * The public one-pager: what Vossenjacht is, and how the two play tracks —
 * jager (LoRa) and verzamelaar (WiFi, in development) — feed each other.
 *
 * Screenshots under /screens are 640x480: an exact 2x of the badge's 320x240
 * screen, so they stay pixel-crisp at 320 CSS px (1x) or 640 (2x). Anything
 * between those relies on `image-rendering: pixelated`.
 */
import { Icon } from "./Icon";

// The parade shows the roster as flat silhouettes, the way the badge's own
// title screen teases them — the Vos included. It used to stand in colour,
// being the favicon anyway, but one full-colour animal in a row of shapes
// reads as a mistake rather than as a hint. The roster is a discovery, so
// nothing here may give it away: the silhouettes are numbered rather than
// named, because a filename in view-source spoils just as well as a picture.
// Baked from artwork/animals/ by flattening the alpha to #86ad64, the title
// screen's silhouette green.
const PARADE = [
  "/art/silhouettes/01.png",
  "/art/silhouettes/02.png",
  "/art/silhouettes/03.png",
  "/art/silhouettes/04.png",
  "/art/silhouettes/05.png",
  "/art/silhouettes/11.png",
  "/art/silhouettes/06.png",
  "/art/silhouettes/07.png",
  "/art/silhouettes/08.png",
  "/art/silhouettes/09.png",
  "/art/silhouettes/10.png",
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
      <a href="#jacht">De jacht</a>
      <a href="#verzamelen">Verzamelen</a>
      <a href="#verzorgen">Verzorgen</a>
      <a href="#begin">Beginnen</a>
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
        <h1 class="wordmark">Vossenjacht</h1>
        <p class="tagline">Spoor de beesten van het bos op.</p>
        <p class="lede">
          Vossenjacht is het badge-spel van Fri3d Camp. Ergens op het terrein
          zitten <i>vossen</i> verstopt: kleine zendertjes die je met je badge
          kan opsporen. Vang je er een, dan verandert hij in een <b>beest</b>{" "}
          voor je boek — en vanaf dat moment zorg jij ervoor.
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
          {PARADE.map((src, i) => (
            <img src={src} width="16" height="16" alt="" style={`--i:${i}`} />
          ))}
        </div>
        <p class="strip-note">
          Allemaal beesten om te ontdekken — en een paar die je niet verwacht.
        </p>
      </div>
    </section>

    <section class="band band-paper">
      <div class="wrap">
        <h2>In het kort</h2>
        <div class="cards cards-3 cards-steps">
          <div class="card">
            <h3>Zoek</h3>
            <p>
              Je badge wordt warmer of kouder terwijl je loopt. Draai rond, volg
              de lampjes, tot je bij de <i>vos</i> staat.
            </p>
          </div>
          <div class="card">
            <h3>Vang</h3>
            <p>
              Op elke vos staat een code van vier cijfers. Tik hem in: de vos
              wordt een beest in je boek.
            </p>
          </div>
          <div class="card">
            <h3>Verzorg</h3>
            <p>
              Voeren, aaien, spelen. De band groeit, het dossier vult zich, je
              beest leert je kennen.
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
          <b>verzamelen</b>. Jagers en verzamelaars hebben elkaar nodig.
        </p>
        <div class="cards cards-2">
          <article class="card mode mode-hunter">
            <h3>
              <span class="icon">
                <Icon name="spoor" />
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
              wordt, en vindt de vos. Dat blijft de enige manier om een beest
              echt <b>zelf gevonden</b> te hebben.
            </p>
          </article>
          <article class="card mode mode-gatherer">
            <h3>
              <span class="icon">
                <Icon name="sig" />
              </span>
              Verzamelaar
            </h3>
            <p class="mode-req">Zonder LoRa-antenne</p>
            <p>
              Geen antenne? Dan ben je verzamelaar, en daarvoor heb je genoeg
              aan de WiFi die elke badge al aan boord heeft.
            </p>
            <p>
              Drie werkwoorden: <b>snuffelen</b> (zoek andere spelers op),{" "}
              <b>plukken</b> (loop naar plukplekken voor eten en wilde
              ontmoetingen) en <b>spelen</b> (speel spelletjes met je beest).
              Alles wat je daarvoor nodig hebt zit al op de badge.
            </p>
          </article>
        </div>
        <blockquote class="quote">
          Jagers vinden de vossen. Verzamelaars speuren het terrein af. Samen
          laten ze de beesten door het kamp zwerven.
        </blockquote>
        <p class="intro">
          Je kunt op eigen tempo vooruit, ook zonder iemand aan te spreken.
          Elkaar opzoeken blijft wel lonen: snuffelen geeft een picknick,
          vriendenboekje en kans op een onverwachte kennismaking.
        </p>
        <p class="note note-dark">
          Een antenne sluit niets uit, hij <i>voegt</i> de jacht toe. Jagers
          mogen ook verzamelen, verzamelaars zorgen net zo goed voor hun
          beesten. Je kiest geen rol — je kiest waar je je tijd aan besteedt.
        </p>
      </div>
    </section>

    <section class="band band-soft" id="jacht">
      <div class="wrap">
        <h2>
          De jacht <span class="tag tag-hunter">jager</span>
        </h2>
        <p class="intro">
          Radiovossen zoeken heet officieel <a href="https://ardf.be/">ARDF</a>.
          Via de antenne bepaal je de richting waar de vos zich bevindt. Dus:
          rondlopen, rondjes draaien, en goed kijken wanneer de balk warmer
          wordt.
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
        </h2>
        <p class="intro">
          Geen antenne? Dan is er nog altijd genoeg te doen buiten. De hele
          kringloop in één zin:{" "}
          <b>
            plukken geeft eten en soms een wild beest, eten geeft energie, en
            met energie kan je spelen
          </b>{" "}
          — en van spelen groeit je band.
        </p>
        <Shot
          src="oppad"
          alt="Het beginscherm van een verzamelaar met de knoppen snuffelen en plukken"
          caption="Op pad: snuffelen en plukken staan vooraan, je boek eronder."
          big
        />
        <div class="cards cards-3">
          <div class="card">
            <span class="icon">
              <Icon name="pluk" />
            </span>
            <h3>Plukken</h3>
            <p>
              Op het terrein hangen WiFi-hotspots. Je badge luistert ernaar en
              jij loopt erheen: hetzelfde warmer-kouder-gevoel als de jacht,
              maar zonder antenne. Soms laat een onbekend beest zich daar zien;
              zelfs een legendarisch beest, al is dat bijzonder zeldzaam.
            </p>
          </div>
          <div class="card">
            <span class="icon">
              <Icon name="bes" />
            </span>
            <h3>De voorraad</h3>
            <p>
              Elke pluk levert bessen, noten of eikels op. Daarna is die plek
              voor jou even leeg — dus loop je door naar de volgende. Eten
              herlaadt na een uur; een plek geeft maar een beestenkans per
              kampdag.
            </p>
          </div>
          <div class="card">
            <span class="icon">
              <Icon name="dans" />
            </span>
            <h3>Spelen</h3>
            <p>
              In de beestenschool kiest je beest een spelletje. Spelen kost
              energie en geeft <b>band</b> — en elk beest heeft een
              lievelingsspel dat extra telt.
            </p>
          </div>
        </div>
        <div class="shots">
          <Shot
            src="plukken"
            alt="Het plukscherm met warmtemeter en de knop PLUK"
            caption="Volg het signaal tot de meter warm staat. Dan mag je plukken."
          />
          <Shot
            src="oogst"
            alt="Geplukt: de voorraad groeit met twee bessen"
            caption="De oogst valt in je voorraad. Deze plek is nu even leeg — op naar de volgende."
          />
          <Shot
            src="school"
            alt="De beestenschool met drie spelletjes en hun energiekost"
            caption="De beestenschool: drie spelletjes, elk met een energieprijsje. Goud = het lievelingsspel."
          />
          <Shot
            src="vliegen"
            alt="Het vliegspel: de Vos fladdert tussen takken door, wolken op de achtergrond"
            caption="VLIEGEN — tik om te fladderen, ontwijk de takken."
          />
          <Shot
            src="vangen"
            alt="Het vangspel: de Vos vangt vallende ringen boven het kampterrein"
            caption="VANGEN — je beest draaft heen en weer, tik om te keren en vang de ringen."
          />
          <Shot
            src="dansen"
            alt="Het dansspel: de Vos doet een reeks pasjes voor"
            caption="DANSEN — kijk naar je beest en doe de pasjes na."
          />
        </div>
        <p class="note">
          Een geplukte plek is alleen voor <i>jou</i> even leeg. Om 15:00 begint
          een nieuwe kampdag en krijgen de plekken een nieuwe beestenkans.
          Verzamelen blijft dus een verkenning — en ook jagers komen eten
          tekort, dus die zie je hier net zo goed rondlopen.
        </p>
      </div>
    </section>

    <section class="band band-soft" id="verzorgen">
      <div class="wrap">
        <h2>Verzorgen — het gedeelde spel</h2>
        <p class="intro">
          Of je nu jaagt of verzamelt: hier komt alles samen. Elk beest heeft
          een band met jou, en energie die meebeweegt: spelen kost energie, eten
          vult ze weer aan.
        </p>
        <div class="shots">
          <Shot
            src="beest"
            alt="Beestscherm met band en energie"
            caption="Band en energie — plus de knoppen om te voeren, aaien, spelen."
          />
          <Shot
            src="voeren"
            alt="Voerscherm met de voorraad aan bessen, noten en eikels"
            caption="Bes, noot of eikel, recht uit je voorraad. Voeren vult de energie — en het lievelingshapje vult extra."
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
            moe beest is een uitnodiging, geen straf. Speel je een dag niet mee,
            dan staat alles er gewoon nog — geen strafpunten, geen verloren
            reeks, geen boos berichtje.
          </p>
        </div>
      </div>
    </section>

    <section class="band band-forest" id="samen">
      <div class="wrap">
        <h2>Elkaar tegenkomen</h2>
        <div class="cards cards-2">
          <article class="card">
            <h3>
              <span class="icon">
                <Icon name="snuf" />
              </span>
              Snuffelen
            </h3>
            <p>
              Hou twee badges met hun neuzen tegen elkaar en allebei juichen ze
              tegelijk. Je hoeft niets te kiezen: elke snuffel is vanzelf een{" "}
              <b>picknick</b> — jullie krijgen allebei eten. En de eerste keer
              dat twee badges elkaar <i>ooit</i> tegenkomen, schrijven ze elkaar
              in hun <b>vriendenboekje</b>. Dat boekje raak je nooit kwijt.
            </p>
            <p class="fine">
              De technologie hierachter heet ESP-NOW. Ze draagt verder dan een
              armlengte, dus we meten hoe hard het signaal binnenkomt en tellen
              een snuffel pas mee boven -50 dBm. Dat is met opzet: niemand kan
              je van ver besnuffelen, jullie moeten er allebei voor gaan staan.
              Werkt het even niet? Er is altijd een korte code als alternatief.
            </p>
          </article>
          <article class="card">
            <h3>
              <span class="icon">
                <Icon name="spark" />
              </span>
              De vonk
            </h3>
            <p>
              De eerste keer per dag dat je iemand tegenkomt, is het een{" "}
              <b>vonk</b>: een flinke picknick — en met wat geluk stelt een
              beest van de ander zich aan jou voor. Zo verspreiden de beesten
              zich over het kamp, van speler naar speler.
            </p>
            <p class="fine">
              Nog eens snuffelen met dezelfde persoon mag altijd (even uit
              elkaar stappen en opnieuw): je krijgt dan een hapje voor onderweg,
              maar geen nieuwe vonk. Nieuwe mensen aanspreken loont dus het
              meest.
            </p>
          </article>
        </div>
        <div class="shots">
          <Shot
            src="snuffelen"
            alt="Het snuffelscherm met spelers in de buurt en signaalbalkjes"
            caption="Wie wil er snuffelen? Sam staat dichtbij — hou de badges tegen elkaar."
          />
          <Shot
            src="vonk"
            alt="VONK! Twee maatjes delen een picknick van twee bessen"
            caption="VONK! Jullie delen een picknick, en Sam staat nu in je vriendenboekje."
          />
          <Shot
            src="vriendenboekje"
            alt="Het vriendenboekje met een pagina voor Sam"
            caption="Elke eerste ontmoeting is een pagina. Het boekje groeit het hele weekend."
          />
        </div>
      </div>
    </section>

    <section class="band band-soft" id="begin">
      <div class="wrap">
        <h2>Zo begin je</h2>
        <ol class="steps">
          <li>
            <div class="step-text">
              <h3>Zet je badge aan</h3>
              <p>
                Start Vossenjacht en druk op <b>Registreer</b>. Heb je al eens
                gespeeld maar je badge gereset? Dan haal je je account terug met
                “Herstel mijn account”.
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
              <h3>Klaar om te spelen</h3>
              <p>
                Je account wordt veilig bewaard in de cloud. Een lege badge is
                daardoor nooit een leeg spel: je haalt jezelf altijd terug.
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

    <section class="band band-paper band-end">
      <div class="wrap wrap-narrow">
        <h2>Wie loopt er voor?</h2>
        <p class="intro">Elke vangst verschijnt op het scorebord.</p>
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
