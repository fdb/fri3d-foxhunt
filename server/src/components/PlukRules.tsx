import { Icon } from "./Icon";

const Stars = () => (
  <div class="stars" aria-hidden="true">
    {Array.from({ length: 14 }, () => (
      <span />
    ))}
  </div>
);

const Hotspot = ({ empty = false }: { empty?: boolean }) => (
  <span class={`pluk-hotspot${empty ? " is-empty" : ""}`} aria-hidden="true">
    <i />
    <i />
    <i />
    <b />
  </span>
);

const Meter = ({ level }: { level: number }) => (
  <span class="pluk-meter" aria-label={`Signaalniveau ${level} van 5`}>
    {Array.from({ length: 5 }, (_, i) => (
      <i class={i < level ? "lit" : undefined} />
    ))}
  </span>
);

const DemoPanel = ({
  id,
  title,
  text,
  level,
  empty = false,
}: {
  id: string;
  title: string;
  text: string;
  level: number;
  empty?: boolean;
}) => (
  <article class="pluk-demo-panel" data-pluk-panel={id} hidden={id !== "zoek"}>
    <div class="pluk-demo-screen">
      <div class="pluk-demo-banner">
        <b>{empty ? "GEPLUKT!" : "PLUKKEN"}</b>
        <span>{empty ? "+2 voer" : "wifi zoekt"}</span>
      </div>
      <div class="pluk-demo-field">
        <Hotspot empty={empty} />
        <p>{text}</p>
      </div>
      <Meter level={level} />
      <div class={`pluk-demo-button${level >= 4 && !empty ? " is-ready" : ""}`}>
        {empty
          ? "OP NAAR DE VOLGENDE"
          : level >= 4
            ? "PLUK!"
            : "VOLG HET SIGNAAL"}
      </div>
    </div>
    <div class="pluk-demo-copy">
      <h3>{title}</h3>
      <p>
        {id === "zoek" &&
          "De badge kiest een beschikbare plek en maakt het WiFi-signaal leesbaar als koud of warm."}
        {id === "dichtbij" &&
          "Pas vanaf vier gevulde vakjes staat PLUK klaar. Een korte radioschommeling laat de meter niet meteen van doel wisselen."}
        {id === "oogst" &&
          "Het eten gaat direct in je voorraad. Deze plek onthoudt de badge nu als leeg, alleen voor jou."}
      </p>
    </div>
  </article>
);

const script = `
(() => {
  const tabs = [...document.querySelectorAll('[data-pluk-tab]')];
  const panels = [...document.querySelectorAll('[data-pluk-panel]')];
  tabs.forEach((tab) => tab.addEventListener('click', () => {
    const id = tab.dataset.plukTab;
    tabs.forEach((item) => {
      const active = item.dataset.plukTab === id;
      item.classList.toggle('active', active);
      item.setAttribute('aria-selected', String(active));
    });
    panels.forEach((panel) => { panel.hidden = panel.dataset.plukPanel !== id; });
  }));
})();`;

export const PlukRules = () => (
  <div class="rules-page pluk-page">
    <nav class="nav rules-nav" aria-label="Navigatie op deze pagina">
      <a class="nav-brand" href="/">
        <img src="/vos.png" alt="" width="24" height="24" />
        Vossenjacht
      </a>
      <a href="#zoeken">Zoeken</a>
      <a href="#plek">Plukplekken</a>
      <a href="#oogst">Oogst</a>
      <a href="#tijd">Tijd</a>
      <a href="#punten">Punten</a>
      <a href="#regels">Regels</a>
    </nav>

    <section class="hero rules-hero pluk-hero">
      <Stars />
      <div class="wrap">
        <p class="rules-kicker">Veldgids voor verzamelaars</p>
        <h1 class="wordmark">Plukken</h1>
        <p class="tagline">Volg WiFi. Oogst voer. Vind een wild spoor.</p>
        <p class="lede">
          Elk WiFi-netwerk in de buurt is een plukplek. Je badge luistert, jij
          volgt de warmtemeter. Dicht genoeg krijg je bessen, noten of eikels —
          en soms stelt een onbekend gewoon beest zich voor.
        </p>
        <div class="rules-hero-art pluk-hero-art" aria-hidden="true">
          <span class="rules-badge-card pluk-signal-card">
            <Hotspot />
            <b>PLUKPLEK</b>
          </span>
          <span class="pluk-hero-trail">
            <i />
            <i />
            <i />
          </span>
          <span class="rules-badge-card pluk-hand-card">
            <Icon name="pluk" />
            <b>OOGST</b>
          </span>
        </div>
      </div>
    </section>

    <aside class="rules-spoiler">
      <div class="wrap">
        <b>Deze pagina bevat plukregels</b>
        <span>
          Inclusief hoe wilde ontmoetingen, wachttijden en punten werken.
        </span>
      </div>
    </aside>

    <section class="band band-paper" id="zoeken">
      <div class="wrap">
        <p class="rules-section-no">01 · VAN KOUD NAAR WARM</p>
        <h2>Je badge wijst naar één plukplek tegelijk</h2>
        <p class="intro">
          Plukken maakt geen verbinding met een hotspot en verstuurt er niets
          naartoe. De badge luistert alleen hoe sterk de plukplekken in de buurt
          klinken. Kies hieronder een stap uit de wandeling.
        </p>
        <div
          class="rules-tabs pluk-tabs"
          role="tablist"
          aria-label="Stappen van plukken"
        >
          <button
            class="active"
            type="button"
            role="tab"
            aria-selected="true"
            data-pluk-tab="zoek"
          >
            1 · Zoek
          </button>
          <button
            type="button"
            role="tab"
            aria-selected="false"
            data-pluk-tab="dichtbij"
          >
            2 · Kom dichtbij
          </button>
          <button
            type="button"
            role="tab"
            aria-selected="false"
            data-pluk-tab="oogst"
          >
            3 · Pluk
          </button>
        </div>
        <div class="pluk-demo">
          <DemoPanel
            id="zoek"
            title="Koud — loop rond"
            text="Nog een eind lopen"
            level={1}
          />
          <DemoPanel
            id="dichtbij"
            title="Warm — recht onder je neus"
            text="Hier! recht onder je neus"
            level={4}
          />
          <DemoPanel
            id="oogst"
            title="De plek is nu even leeg"
            text="Je voorraad groeit"
            level={0}
            empty
          />
        </div>
        <p class="note">
          Liggen twee plekken bijna even sterk? Dan houdt de badge even vast aan
          het huidige doel. Ook kleine schommelingen worden gladgestreken, zodat
          de meter tijdens het lopen niet zenuwachtig heen en weer springt. Een
          duidelijk sterker doel mag het overnemen.
        </p>
      </div>
    </section>

    <section class="band band-soft" id="plek">
      <div class="wrap">
        <p class="rules-section-no">02 · WAT IS ÉÉN PLEK?</p>
        <h2>Elk netwerk telt. Het zenderadres maakt de plek uniek.</h2>
        <div class="pluk-identity">
          <article class="card">
            <span class="icon">
              <Icon name="sig" />
            </span>
            <h3>De zichtbare naam</h3>
            <code>elk netwerk met een naam</code>
            <p>
              Elk WiFi-netwerk dat je badge hoort, is een plukplek. Een
              verborgen netwerk zonder naam telt niet mee.
            </p>
          </article>
          <span class="pluk-not-equal" aria-hidden="true">
            ≠
          </span>
          <article class="card">
            <Hotspot />
            <h3>De unieke plekcode</h3>
            <code>aa:bb:cc:dd:ee:ff</code>
            <p>
              Onder de naam zit het zenderadres, de <b>BSSID</b>. Dat adres
              gebruikt de badge om twee hotspots met dezelfde naam uit elkaar te
              houden.
            </p>
          </article>
        </div>
        <div class="cards cards-3 pluk-memory-cards">
          <article class="card">
            <h3>Zelfde BSSID</h3>
            <p>
              Dezelfde plek, ook na weglopen, opnieuw openen of herstarten. De
              badge bewaart het adres in kleine letters met het laatste
              plukmoment.
            </p>
          </article>
          <article class="card">
            <h3>Zelfde naam, andere BSSID</h3>
            <p>
              Een andere plukplek. Twee zenders mogen dus dezelfde WiFi-naam
              dragen en toch apart herladen.
            </p>
          </article>
          <article class="card">
            <h3>Adres verandert</h3>
            <p>
              Dan ziet de badge een nieuwe plek. Een vaste hotspot is dus een
              betere plukplek dan een telefoon die telkens een nieuw adres
              kiest.
            </p>
          </article>
        </div>
      </div>
    </section>

    <section class="band band-forest" id="oogst">
      <div class="wrap">
        <p class="rules-section-no">03 · WAT KOMT ER UIT?</p>
        <h2>Voer is zeker. Een wild beest is bijzonder.</h2>
        <div class="cards cards-2 pluk-yield-grid">
          <article class="card pluk-yield-card food">
            <span class="icon">
              <Icon name="bes" />
            </span>
            <p class="rules-tier-tag">Elke pluk</p>
            <h3>1 tot 3 hapjes</h3>
            <p>
              Bessen, noten en eikels gaan meteen naar je voorraad. De mix ligt
              voor die plek en kampdag vast. Iedereen krijgt daar die dag dus
              dezelfde oogst; opnieuw scannen verandert niets.
            </p>
          </article>
          <article class="card pluk-yield-card beast">
            <img
              class="pluk-silhouette"
              src="/art/silhouettes/04.png"
              alt="Silhouet van een nog onbekend beest"
              width="64"
              height="64"
            />
            <p class="rules-tier-tag">Eerste pluk per kampdag</p>
            <h3>Soms een wild spoor</h3>
            <p>
              Alleen bij je eerste pluk aan deze plek in de lopende kampdag
              wordt de persoonlijke beestenkans gebruikt. Over veel nieuwe
              plek-dagcombinaties komt die uit op ongeveer <b>18%</b>.
            </p>
          </article>
        </div>
        <div
          class="pluk-seed-flow"
          aria-label="Hoe een wild beest gekozen wordt"
        >
          <article>
            <span>1</span>
            <b>Persoonlijk</b>
            <p>
              Jouw badge, deze BSSID en de kampdag vormen samen de vaste
              sleutel.
            </p>
          </article>
          <article>
            <span>2</span>
            <b>Nog onbekend</b>
            <p>
              De keuze komt alleen uit gewone beesten die nog niet in je boek
              staan.
            </p>
          </article>
          <article>
            <span>3</span>
            <b>Geen herkansing</b>
            <p>Raak of mis: deze plek is voor deze kampdag afgehandeld.</p>
          </article>
        </div>
        <blockquote class="quote">
          De badge gooit niet bij elke druk opnieuw. De uitkomst is
          reproduceerbaar: opnieuw laden, weglopen of herstarten maakt van een
          misser geen treffer.
        </blockquote>
        <p class="note note-dark">
          Plukken geeft alleen <b>gewone</b> beesten. Zeldzame en legendarische
          beesten komen via de jacht en geschikte snuffelontmoetingen. Ken je
          alle gewone beesten al, dan blijft de oogst gewoon voer.
        </p>
      </div>
    </section>

    <section class="band band-paper" id="tijd">
      <div class="wrap">
        <p class="rules-section-no">04 · TWEE KLOKKEN</p>
        <h2>Een uur voor voer. Om 15:00 een nieuwe beestenkans.</h2>
        <div class="rules-timeline pluk-timeline">
          <article>
            <b>NU · GEPLUKT</b>
            <span>
              Het voer is binnen. De eerste beestenkans van deze plek is
              gebruikt.
            </span>
          </article>
          <article>
            <b>+1 UUR · VOER KLAAR</b>
            <span>
              Dezelfde badge mag hier weer eten plukken, maar krijgt geen nieuwe
              beestenworp.
            </span>
          </article>
          <article>
            <b>15:00 · NIEUWE KAMPDAG</b>
            <span>
              Elke plek krijgt voor jou een nieuwe vaste beestenkans en een
              nieuwe voermix.
            </span>
          </article>
          <article>
            <b>LET OP · UUR LOOPT DOOR</b>
            <span>
              Pluk je om 14:45, dan blijft die plek tot ongeveer 15:45 leeg, ook
              al begon om 15:00 een nieuwe kampdag.
            </span>
          </article>
        </div>
        <p class="note">
          Een verlopen wachttijd wordt niet uit het geheugen gewist: de plek
          wordt simpelweg weer als <b>klaar</b> gezien. Zo kan het beginscherm
          tonen hoeveel eerder bezochte plekken opnieuw gevuld zijn.
        </p>
      </div>
    </section>

    <section class="band band-soft" id="punten">
      <div class="wrap">
        <p class="rules-section-no">05 · BOEK, CLOUD EN PUNTEN</p>
        <h2>Alleen een nieuw wild beest levert plukpunten op</h2>
        <div class="rules-score-grid pluk-score-grid">
          <article class="card rules-score-card help">
            <h3>Wilde ontmoeting</h3>
            <strong class="rules-big-points">+50</strong>
            <p>
              Een nieuw gewoon beest uit een plukplek telt voor de
              verzamelaarsscore. Voer, een lege beestenkans en elk beest dat al
              in je boek stond leveren geen plukpunten op.
            </p>
          </article>
          <article class="card rules-score-card">
            <h3>Offline blijft werken</h3>
            <p>
              Het beest komt eerst lokaal in je boek. Het bewijs wacht in een
              uitgaande wachtrij tot de badge weer werkende internettoegang
              heeft. De cloud bewaart geen voer.
            </p>
          </article>
        </div>
        <div class="rules-formula">
          <b>PLUKSCORE = 50 × GELDIGE WILDE ONTMOETINGEN</b>
          <p>
            De cloud telt maximaal drie plukontmoetingen per kampdag en acht
            over het hele kamp mee. Een latere of dubbele melding kan lokaal nog
            steeds in je boek staan, maar levert geen extra score op.
          </p>
        </div>
        <div class="pluk-restore-note">
          <b>Wat blijft waar?</b>
          <p>
            Herstarten bewaart je plekken, wachttijden, oogst en boek. Bij
            accountherstel kan de cloud gemelde wilde beesten teruggeven, maar
            niet je lokale voorraad, lege plekken of gemiste kansen.{" "}
            <b>ALLES WISSEN</b> ruimt ook de volledige lokale plukgeschiedenis
            op.
          </p>
        </div>
      </div>
    </section>

    <section class="band band-paper" id="regels">
      <div class="wrap">
        <p class="rules-section-no">06 · HET KORTE REGELBOEK</p>
        <h2>Zeven plukregels om te onthouden</h2>
        <div class="cards cards-2 rules-rulebook">
          <article class="card">
            <span>01</span>
            <h3>Volg het warmste vrije signaal</h3>
            <p>
              De badge verkiest een plek die nu voor jou klaar is. Zijn ze
              allemaal leeg, dan toont hij de sterkste met zijn wachttijd.
            </p>
          </article>
          <article class="card">
            <span>02</span>
            <h3>Kom echt dichtbij</h3>
            <p>
              Pas bij minstens vier van de vijf meterstappen wordt de knop PLUK
              actief.
            </p>
          </article>
          <article class="card">
            <span>03</span>
            <h3>Een BSSID is één plek</h3>
            <p>
              De WiFi-naam zie je staan; het unieke zenderadres bewaart de
              geschiedenis.
            </p>
          </article>
          <article class="card">
            <span>04</span>
            <h3>Voer herlaadt na een uur</h3>
            <p>
              Dat geldt per badge. Iemand anders kan dezelfde plek ondertussen
              gewoon plukken.
            </p>
          </article>
          <article class="card">
            <span>05</span>
            <h3>De kampdag begint om 15:00</h3>
            <p>
              Dan veranderen de voermix en persoonlijke beestenkans. De lopende
              uurwachttijd blijft gelden.
            </p>
          </article>
          <article class="card">
            <span>06</span>
            <h3>Een beestenkans rolt nooit opnieuw</h3>
            <p>
              De eerste pluk noteert ook een misser. Elk uur opnieuw proberen
              verandert die uitkomst niet.
            </p>
          </article>
          <article class="card">
            <span>07</span>
            <h3>Alleen gewoon en onbekend</h3>
            <p>
              Een wild spoor kiest nooit zeldzaam of legendarisch en nooit een
              gewoon beest dat je al kent.
            </p>
          </article>
        </div>
      </div>
    </section>

    <footer class="site-footer">
      <div class="wrap">
        <p>
          <b>Vossenjacht</b> — plukregels voor Fri3d Camp.
        </p>
        <p class="fine">
          <a href="/">Terug naar de gewone uitleg</a>
        </p>
      </div>
    </footer>

    <script dangerouslySetInnerHTML={{ __html: script }} />
  </div>
);
