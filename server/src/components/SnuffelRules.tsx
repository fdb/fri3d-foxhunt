const TIJGHERT =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAOdJREFUOI2VkrEOgkAMhj8ubmwmPoAxYSUmDjiY8DTuLEaegNHRhNdxgM3dhTdwc2E5F6o9OASbXNJr7//7t1fwmz3ut1Z8HQfochbAjBBoIg3sExLMAANQVnchoKzuU1hHsrRjtfQ5CgBsk0VOYH15OLipGQQdQICDOczp46cKrcCOHIo6pI1T2jgdtLDQVYo6JE9eCOjrw2qz656WjhqjvytPXhR16PUBlofjoG0zBRT/fLp6B2Rk0vrxP2b6Gycm3zbHbJNFny1rskhv2+feizsK4LvftHHqrTIWB7DPW+lln8gB8Ab/rXwL8Ukk8wAAAABJRU5ErkJggg==";

const Stars = () => (
  <div class="stars" aria-hidden="true">
    {Array.from({ length: 14 }, () => (
      <span />
    ))}
  </div>
);

const Beast = ({ kind = "base" }: { kind?: "base" | "rare" | "secret" }) => {
  if (kind === "secret") {
    return (
      <span class="rules-secret-beast" aria-label="Geheim legendarisch beest">
        ?
      </span>
    );
  }
  return (
    <img
      class="rules-beast"
      src={kind === "rare" ? TIJGHERT : "/vos.png"}
      alt={kind === "rare" ? "Tijghert" : "Vos"}
      width="64"
      height="64"
    />
  );
};

const Picnic = () => (
  <span class="rules-picnic" aria-label="Gegenereerde picknick">
    <i />
    <i />
    <i />
  </span>
);

const Player = ({
  name,
  role,
  children,
}: {
  name: string;
  role: "Jager" | "Verzamelaar";
  children: any;
}) => (
  <div class={`rules-player ${role === "Jager" ? "is-hunter" : ""}`}>
    <div class="rules-player-top">
      <b>{name}</b>
      <span>{role}</span>
    </div>
    <small>In het boek</small>
    <div class="rules-roster">{children}</div>
    <div class="rules-picnic-dock" data-picnic-dock />
  </div>
);

const Scene = ({
  id,
  left,
  right,
  leftGift,
  rightGift,
  result,
  spark = true,
}: {
  id: string;
  left: any;
  right: any;
  leftGift: any;
  rightGift: any;
  result: any;
  spark?: boolean;
}) => (
  <article
    class="rules-scene"
    data-rule-scene={id}
    hidden={id !== "rare-first"}
  >
    <div class="rules-stage">
      {left}
      <div class="rules-motion">
        <span class={`rules-vonk${spark ? "" : " no-spark"}`}>
          {spark ? "VONK" : "GEEN VONK"}
        </span>
        <div class="rules-lane to-right">{leftGift}</div>
        <div class="rules-lane to-left">{rightGift}</div>
        <button class="rules-snuffel" type="button" data-snuffel-button>
          <b>✦</b>
          <span>SNUFFEL!</span>
        </button>
      </div>
      {right}
    </div>
    <div class="rules-result">{result}</div>
  </article>
);

const script = `
(() => {
  const tabs = [...document.querySelectorAll('[data-rule-tab]')];
  const scenes = [...document.querySelectorAll('[data-rule-scene]')];

  function show(id) {
    tabs.forEach((tab) => {
      const active = tab.dataset.ruleTab === id;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-selected', String(active));
    });
    scenes.forEach((scene) => {
      const active = scene.dataset.ruleScene === id;
      scene.hidden = !active;
      scene.classList.remove('is-moving', 'is-done');
      scene.querySelectorAll('[data-arrived]').forEach((item) => item.remove());
      const label = scene.querySelector('[data-snuffel-button] span');
      if (label) label.textContent = 'SNUFFEL!';
    });
  }

  function creatureKind(gift) {
    if (gift.querySelector('.rules-secret-beast')) return 'legendary';
    if (gift.querySelector('img[alt="Tijghert"]')) return 'rare';
    if (gift.querySelector('.rules-beast')) return 'base';
    return null;
  }

  function makeLanding(gift, target) {
    const kind = creatureKind(gift);
    const visual = gift.querySelector('.rules-beast, .rules-secret-beast, .rules-picnic');
    const landing = document.createElement('span');
    landing.dataset.arrived = '';
    landing.className = kind
      ? 'rules-roster-item arrived ' + kind
      : 'rules-arrived-picnic';
    landing.append(visual.cloneNode(true));

    if (kind) {
      target.querySelector('.rules-roster').append(landing);
    } else {
      const dock = target.querySelector('[data-picnic-dock]');
      const caption = document.createElement('small');
      caption.textContent = 'Net gekregen';
      landing.prepend(caption);
      dock.append(landing);
    }
    return landing;
  }

  function sourceRect(gift, source, spark) {
    const kind = creatureKind(gift);
    if (!kind) return spark.getBoundingClientRect();
    const selector = kind === 'rare'
      ? '.rules-roster-item.rare'
      : kind === 'legendary'
        ? '.rules-roster-item.legendary'
        : '.rules-roster > .rules-beast';
    return (source.querySelector(selector) || source.querySelector('.rules-roster')).getBoundingClientRect();
  }

  function flyGift(gift, source, target, spark, delay, reducedMotion) {
    const landing = makeLanding(gift, target);
    const from = sourceRect(gift, source, spark);
    const to = landing.getBoundingClientRect();
    const visual = gift.querySelector('.rules-beast, .rules-secret-beast, .rules-picnic');
    const flyer = document.createElement('span');
    flyer.className = 'rules-flyer';
    flyer.append(visual.cloneNode(true));
    document.body.append(flyer);

    const size = Math.max(58, Math.min(72, from.width, from.height));
    const startX = from.left + from.width / 2 - size / 2;
    const startY = from.top + from.height / 2 - size / 2;
    const endX = to.left + to.width / 2 - size / 2;
    const endY = to.top + to.height / 2 - size / 2;
    flyer.style.left = startX + 'px';
    flyer.style.top = startY + 'px';
    flyer.style.width = size + 'px';
    flyer.style.height = size + 'px';

    if (reducedMotion) {
      flyer.remove();
      landing.classList.add('has-landed');
      return Promise.resolve();
    }

    const dx = endX - startX;
    const dy = endY - startY;
    return flyer.animate([
      { transform: 'translate(0, 0) scale(.75) rotate(-5deg)', opacity: 0 },
      { transform: 'translate(' + (dx * .5) + 'px, ' + (dy * .5 - 58) + 'px) scale(1.12) rotate(4deg)', opacity: 1, offset: .48 },
      { transform: 'translate(' + dx + 'px, ' + dy + 'px) scale(.9) rotate(0)', opacity: 1 }
    ], {
      duration: 1050,
      delay,
      easing: 'cubic-bezier(.22,.75,.18,1)',
      fill: 'forwards'
    }).finished.then(() => {
      flyer.remove();
      landing.classList.add('has-landed');
    });
  }

  tabs.forEach((tab) => tab.addEventListener('click', () => show(tab.dataset.ruleTab)));
  document.querySelectorAll('[data-snuffel-button]').forEach((button) => {
    button.addEventListener('click', async () => {
      const scene = button.closest('[data-rule-scene]');
      scene.classList.remove('is-moving', 'is-done');
      scene.querySelectorAll('[data-arrived]').forEach((item) => item.remove());
      void scene.offsetWidth;
      scene.classList.add('is-moving');
      button.disabled = true;
      button.querySelector('span').textContent = 'SNUFFELT…';
      const players = scene.querySelectorAll('.rules-player');
      const spark = scene.querySelector('.rules-vonk');
      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const rightGift = scene.querySelector('.to-right .rules-moving-gift');
      const leftGift = scene.querySelector('.to-left .rules-moving-gift');

      await Promise.all([
        flyGift(rightGift, players[0], players[1], spark, 0, reducedMotion),
        flyGift(leftGift, players[1], players[0], spark, 120, reducedMotion)
      ]);
      scene.classList.add('is-done');
      scene.classList.remove('is-moving');
      button.disabled = false;
      button.querySelector('span').textContent = 'NOG EENS';
    });
  });
})();`;

export const SnuffelRules = () => (
  <div class="rules-page">
    <nav class="nav rules-nav" aria-label="Navigatie op deze pagina">
      <a class="nav-brand" href="/">
        <img src="/vos.png" alt="" width="24" height="24" />
        Vossenjacht
      </a>
      <a href="#proberen">Proberen</a>
      <a href="#beesten">Beesten</a>
      <a href="#wachttijd">Wachttijd</a>
      <a href="#punten">Punten</a>
      <a href="#regels">Regels</a>
    </nav>

    <section class="hero rules-hero">
      <Stars />
      <div class="wrap">
        <p class="rules-kicker">Nieuwe spelregels</p>
        <h1 class="wordmark">Snuffelen</h1>
        <p class="tagline">Eén ontmoeting. Twee cadeaus.</p>
        <p class="lede">
          Met een <b>vonk</b> kan in elke richting een beest reizen. Is er geen
          passend beest? Dan verschijnt er een picknick. Niemand hoeft iets uit
          zijn eigen voorraad af te geven.
        </p>
        <div class="rules-hero-art" aria-hidden="true">
          <span class="rules-badge-card">
            <Beast />
            <b>BEEST</b>
          </span>
          <span class="rules-hero-spark">✦</span>
          <span class="rules-badge-card">
            <Picnic />
            <b>PICKNICK</b>
          </span>
        </div>
      </div>
    </section>

    <aside class="rules-spoiler">
      <div class="wrap">
        <b>⚠ Deze pagina bevat spoilers</b>
        <span>
          Lees alleen verder als je de nieuwe snuffelregels al wil kennen.
        </span>
      </div>
    </aside>

    <section class="band band-paper" id="proberen">
      <div class="wrap">
        <p class="rules-section-no">01 · PROBEER HET</p>
        <h2>Hou twee badges neus aan neus</h2>
        <p class="intro">
          Kies een voorbeeld en druk op <b>SNUFFEL!</b> Zo zie je wat er van de
          ene speler naar de andere gaat.
        </p>
        <div class="rules-tabs" role="tablist" aria-label="Voorbeelden">
          <button
            class="active"
            type="button"
            role="tab"
            aria-selected="true"
            data-rule-tab="rare-first"
          >
            Jager deelt zeldzaam
          </button>
          <button
            type="button"
            role="tab"
            aria-selected="false"
            data-rule-tab="rare-relay"
          >
            Zeldzaam doorgeven
          </button>
          <button
            type="button"
            role="tab"
            aria-selected="false"
            data-rule-tab="no-spark"
          >
            Geen vonk
          </button>
          <button
            type="button"
            role="tab"
            aria-selected="false"
            data-rule-tab="legendary-first"
          >
            Legendarisch delen
          </button>
          <button
            type="button"
            role="tab"
            aria-selected="false"
            data-rule-tab="legendary-stop"
          >
            Legendarisch stopt
          </button>
        </div>

        <div class="rules-simulator">
          <Scene
            id="rare-first"
            left={
              <Player name="Mila" role="Verzamelaar">
                <Beast />
              </Player>
            }
            right={
              <Player name="Sam" role="Jager">
                <Beast />
                <span class="rules-roster-item rare self">
                  <Beast kind="rare" />
                </span>
              </Player>
            }
            leftGift={
              <span class="rules-moving-gift">
                <Picnic />
                <small>Mila → Sam</small>
              </span>
            }
            rightGift={
              <span class="rules-moving-gift">
                <Beast kind="rare" />
                <small>Sam → Mila</small>
              </span>
            }
            result={
              <>
                <b>Sam helpt Mila.</b>
                <p>
                  Mila leert Tijghert kennen. Sam ving Tijghert zelf, dus hij
                  kan 50 punten krijgen — als hij Mila nog nooit eerder met een
                  eigen vondst hielp.
                </p>
              </>
            }
          />
          <Scene
            id="rare-relay"
            left={
              <Player name="Noor" role="Verzamelaar">
                <Beast />
                <span class="rules-roster-item rare">
                  <Beast kind="rare" />
                </span>
              </Player>
            }
            right={
              <Player name="Wout" role="Jager">
                <Beast />
              </Player>
            }
            leftGift={
              <span class="rules-moving-gift">
                <Beast kind="rare" />
                <small>Noor → Wout</small>
              </span>
            }
            rightGift={
              <span class="rules-moving-gift">
                <Picnic />
                <small>Wout → Noor</small>
              </span>
            }
            result={
              <>
                <b>Wout krijgt Tijghert, maar niet de ZELF-stempel.</b>
                <p>
                  Hij krijgt nu 0 vindpunten. Vindt hij later zelf de
                  Tijghert-vos met LoRa? Dan krijgt hij één keer de ZELF-stempel
                  en 300 punten. Pas dan mag hij Tijghert verder delen. Noor
                  krijgt geen hulppunten: Tijghert is niet haar eigen vondst.
                  Doorgeven blijft nuttig — het beest reist verder — maar alleen
                  een eigen vondst delen levert punten op.
                </p>
              </>
            }
          />
          <Scene
            id="no-spark"
            spark={false}
            left={
              <Player name="Lio" role="Verzamelaar">
                <Beast />
                <span class="rules-roster-item rare">
                  <Beast kind="rare" />
                </span>
              </Player>
            }
            right={
              <Player name="Fien" role="Jager">
                <Beast />
              </Player>
            }
            leftGift={
              <span class="rules-moving-gift">
                <Picnic />
                <small>Lio → Fien</small>
              </span>
            }
            rightGift={
              <span class="rules-moving-gift">
                <Picnic />
                <small>Fien → Lio</small>
              </span>
            }
            result={
              <>
                <b>Zonder vonk reist alleen eten.</b>
                <p>
                  Ook als de spelers een nieuw beest voor elkaar hebben. Ze
                  moeten een nieuwe speler zoeken of wachten tot hun volgende
                  vonk.
                </p>
              </>
            }
          />
          <Scene
            id="legendary-first"
            left={
              <Player name="Ada" role="Verzamelaar">
                <Beast />
              </Player>
            }
            right={
              <Player name="Jules" role="Jager">
                <Beast />
                <span class="rules-roster-item legendary self">
                  <Beast kind="secret" />
                </span>
              </Player>
            }
            leftGift={
              <span class="rules-moving-gift">
                <Picnic />
                <small>Ada → Jules</small>
              </span>
            }
            rightGift={
              <span class="rules-moving-gift">
                <Beast kind="secret" />
                <small>Jules → Ada</small>
              </span>
            }
            result={
              <>
                <b>Een legendarisch beest maakt één sprong.</b>
                <p>
                  Alleen de jager die het zelf vond, mag het aan een verzamelaar
                  voorstellen. Welk beest dit is, blijft hier geheim.
                </p>
              </>
            }
          />
          <Scene
            id="legendary-stop"
            left={
              <Player name="Mila" role="Verzamelaar">
                <Beast />
              </Player>
            }
            right={
              <Player name="Jules" role="Verzamelaar">
                <Beast />
                <span class="rules-roster-item legendary blocked">
                  <Beast kind="secret" />
                </span>
              </Player>
            }
            leftGift={
              <span class="rules-moving-gift">
                <Picnic />
                <small>Mila → Jules</small>
              </span>
            }
            rightGift={
              <span class="rules-moving-gift">
                <Picnic />
                <small>Jules → Mila</small>
              </span>
            }
            result={
              <>
                <b>Jules is het eindpunt.</b>
                <p>
                  Hij kreeg het legendarische beest van een jager en mag het
                  niet verder delen. Daarom verschijnt er een picknick.
                </p>
              </>
            }
          />
        </div>
      </div>
    </section>

    <section class="band band-soft" id="beesten">
      <div class="wrap">
        <p class="rules-section-no">02 · WELKE BEESTEN REIZEN?</p>
        <h2>Drie soorten, drie regels</h2>
        <div class="cards cards-3 rules-tiers">
          <article class="card rules-tier base">
            <span class="rules-tier-tag">Gewoon</span>
            <Beast />
            <h3>Gewone beesten zijn vriendelijke zwervers</h3>
            <p>
              Je kunt ze vinden bij het plukken. Tijdens een vonk mogen ze van
              elke speler naar elke andere speler reizen.
            </p>
          </article>
          <article class="card rules-tier rare">
            <span class="rules-tier-tag">Zeldzaam</span>
            <Beast kind="rare" />
            <h3>Zeldzame beesten reizen door</h3>
            <p>
              Eerst deelt een jager het met een verzamelaar. Een verzamelaar mag
              het verder delen. Een jager mag dat pas nadat die het beest zelf
              heeft gevonden.
            </p>
          </article>
          <article class="card rules-tier legendary">
            <span class="rules-tier-tag">Legendarisch</span>
            <Beast kind="secret" />
            <h3>Legendarische beesten maken maar één sprong</h3>
            <p>
              Alleen de jager die het zelf vond, mag het aan verzamelaars
              voorstellen. Elke ontvanger is een eindpunt.
            </p>
          </article>
        </div>
        <p class="note">
          <b>Plukken geeft alleen gewone beesten.</b> Zeldzame en legendarische
          beesten komen niet uit een WiFi-plukplek.
        </p>
      </div>
    </section>

    <section class="band band-forest" id="wachttijd">
      <div class="wrap">
        <p class="rules-section-no">03 · DE TWEE WACHTTIJDEN</p>
        <h2>Na één uur eten. Na zes uur een nieuwe vonk.</h2>
        <div class="rules-timeline">
          <article>
            <b>NU · VONK</b>
            <span>
              Een nieuw duo krijgt meteen een vonk. Een passend beest kan
              reizen.
            </span>
          </article>
          <article>
            <b>+1 UUR · ETEN</b>
            <span>
              Hetzelfde duo mag weer snuffelen. Zonder vonk reizen alleen twee
              picknicks.
            </span>
          </article>
          <article>
            <b>+6 UUR · VONK</b>
            <span>
              Hetzelfde duo krijgt opnieuw een vonk. Een beest kan weer reizen.
            </span>
          </article>
          <article>
            <b>24 UUR · MAX 4</b>
            <span>
              Door de zes uur wachttijd kan hetzelfde duo hoogstens vier vonken
              per dag krijgen.
            </span>
          </article>
        </div>
        <blockquote class="quote">
          Wil je sneller nieuwe beesten ontmoeten? Zoek dan iemand met wie je
          nog niet gesnuffeld hebt.
        </blockquote>
      </div>
    </section>

    <section class="band band-paper" id="punten">
      <div class="wrap">
        <p class="rules-section-no">04 · PUNTEN</p>
        <h2>Twee scoreborden: jagers en verzamelaars sparen apart</h2>
        <p class="intro">
          Jagers en verzamelaars spelen een ander spel, dus ze staan op twee
          aparte lijsten met elk hun eigen punten. De twee tellen nooit bij
          elkaar op.
        </p>
        <div class="rules-score-grid">
          <article class="card rules-score-card">
            <h3>Jagers: zelf gevonden</h3>
            <div class="rules-point-chips">
              <span class="base">
                Gewoon <b>100</b>
              </span>
              <span class="rare">
                Zeldzaam <b>300</b>
              </span>
              <span class="legendary">
                Legendarisch <b>800</b>
              </span>
            </div>
            <p>
              Je krijgt deze punten alleen als je de vos zelf met LoRa vindt.
              Een beest krijgen via snuffelen of plukken telt niet.
            </p>
          </article>
          <article class="card rules-score-card help">
            <h3>Jagers: iemand geholpen</h3>
            <strong class="rules-big-points">+50</strong>
            <p>
              Laat je een <b>eigen vondst</b> kennismaken met een nieuwe speler?
              Dan krijg je één keer 50 punten voor die speler. Een beest
              doorgeven dat je zelf kreeg, of nog een beest aan dezelfde speler
              geven, levert geen punten op.
            </p>
          </article>
        </div>
        <div class="rules-formula">
          <b>
            JAGERSSCORE = ZELF GEVONDEN BEESTEN + 50 × SPELERS GEHOLPEN MET EEN
            EIGEN VONDST
          </b>
          <p>
            Voorbeeld: één gewoon en één zeldzaam beest zelf gevonden, plus drie
            spelers geholpen = 100 + 300 + 150 = <strong>550 punten</strong>.
          </p>
        </div>
        <div class="rules-formula">
          <b>
            VERZAMELAARSSCORE = 50 × PLUKVANGSTEN + 25 × NIEUWE SNUFFELVRIENDEN
            + 100 × BESTE VRIENDEN
          </b>
          <p>
            Verzamelaars sparen op hun eigen lijst: 50 punten per wild beest van
            een plukplek, 25 punten per nieuwe speler waarmee je een vonk deelt
            (elke speler telt één keer), en 100 punten per beest dat je tot
            beste vriend maakt.
          </p>
        </div>
        <div class="rules-error">
          <b>FOUT · AL ZELF GEVONDEN · +0 PUNTEN</b>
          <p>
            Elk beest kun je maar één keer zelf vinden. Voer je dezelfde
            vossencode opnieuw in? Dan verandert er niets en krijg je geen
            nieuwe punten.
          </p>
        </div>
      </div>
    </section>

    <section class="band band-soft" id="regels">
      <div class="wrap">
        <p class="rules-section-no">05 · HET KORTE REGELBOEK</p>
        <h2>Zeven regels om te onthouden</h2>
        <div class="cards cards-2 rules-rulebook">
          <article class="card">
            <span>01</span>
            <h3>Jullie kiezen allebei</h3>
            <p>Open allebei Snuffelen en hou de badges dicht bij elkaar.</p>
          </article>
          <article class="card">
            <span>02</span>
            <h3>Twee aparte cadeaus</h3>
            <p>
              Elke richting wordt apart bekeken. De ene speler hoeft niets even
              waardevols terug te geven.
            </p>
          </article>
          <article class="card">
            <span>03</span>
            <h3>Snuffelen pakt nooit iets af</h3>
            <p>
              Je houdt elk beest dat je deelt. Een picknick wordt voor de
              ontmoeting gemaakt en komt niet uit jouw voorraad.
            </p>
          </article>
          <article class="card">
            <span>04</span>
            <h3>Zeldzaam mag doorreizen</h3>
            <p>
              Een ontvangen jager krijgt geen ZELF-stempel. Hij kan het beest
              pas verder delen nadat hij het één keer zelf vindt. Dan krijgt hij
              ook de punten.
            </p>
          </article>
          <article class="card">
            <span>05</span>
            <h3>Legendarisch stopt na één sprong</h3>
            <p>
              Alleen de jager die het zelf vond mag delen, en alleen met een
              verzamelaar. Die ontvanger deelt het nooit verder.
            </p>
          </article>
          <article class="card">
            <span>06</span>
            <h3>Zonder vonk reist alleen eten</h3>
            <p>
              Na één uur kan hetzelfde duo picknicken. Voor een nieuw beest
              wachten ze zes uur of zoeken ze een nieuwe speler.
            </p>
          </article>
          <article class="card">
            <span>07</span>
            <h3>Elk punt telt maar één keer</h3>
            <p>
              Elk beest kun je één keer zelf vinden. Elke andere speler kun je
              één keer helpen voor 50 punten — en alleen met een eigen vondst.
            </p>
          </article>
        </div>
      </div>
    </section>

    <footer class="site-footer">
      <div class="wrap">
        <p>
          <b>Vossenjacht</b> — geheime snuffelregels voor Fri3d Camp.
        </p>
        <p class="fine">
          <a href="/">Terug naar de gewone uitleg</a>
        </p>
      </div>
    </footer>

    <script dangerouslySetInnerHTML={{ __html: script }} />
  </div>
);
