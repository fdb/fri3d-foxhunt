import type { PropsWithChildren } from "hono/jsx";

/**
 * Two page shells, one <head>.
 *
 * The default is the badge-flavoured app chrome: green banner, narrow column,
 * card panels — used by the scoreboard and the /debug/* pages.
 *
 * `bare` drops the banner and the width cap for the public landing page, which
 * brings its own full-bleed sections.
 */
export const Layout = ({
  title,
  right,
  bare,
  wide,
  description,
  poll,
  noindex,
  children,
}: PropsWithChildren<{
  title: string;
  right?: string;
  bare?: boolean;
  // The live scoreboard is meant for a large shared display and needs room
  // for its two boards. Debug pages keep the narrower reading column.
  wide?: boolean;
  description?: string;
  // Loads htmx, for the one page that live-polls (the scoreboard). Off by
  // default: the other pages run no scripts, so they ship none.
  poll?: boolean;
  // Unlinked preview/rules pages should not become searchable spoilers.
  noindex?: boolean;
}>) => (
  <html lang="nl">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>{title}</title>
      {description && <meta name="description" content={description} />}
      {noindex && <meta name="robots" content="noindex,nofollow,noarchive" />}
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
      <link
        href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@400..700&family=Nunito:wght@400;600;800&display=swap"
        rel="stylesheet"
      />
      <link rel="icon" href="/vos.png" />
      <link rel="stylesheet" href="/styles.css" />
      {poll && (
        <script
          src="https://unpkg.com/htmx.org@2.0.6"
          integrity="sha384-Akqfrbj/HpNVo8k11SXBb6TlBWmXXlYQrCSqEWmyKJe+hDm3Z/B2WVG4smwBkRVm"
          crossorigin="anonymous"
        />
      )}
    </head>
    <body>
      {!bare && (
        <header>
          <a class="banner-logo" href="/" aria-label="Naar de startpagina">
            <img src="/vos.png" alt="" />
          </a>
          <h1>{title}</h1>
          {right && <span class="banner-right">{right}</span>}
          <a class="banner-home" href="/">
            Uitleg
          </a>
        </header>
      )}
      {bare ? (
        children
      ) : (
        <main class={wide ? "wide" : undefined}>{children}</main>
      )}
    </body>
  </html>
);
