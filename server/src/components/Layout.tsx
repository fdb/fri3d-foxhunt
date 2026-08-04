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
  description,
  children,
}: PropsWithChildren<{
  title: string;
  right?: string;
  bare?: boolean;
  description?: string;
}>) => (
  <html lang="nl">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>{title}</title>
      {description && <meta name="description" content={description} />}
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
      <link
        href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@400..700&family=Nunito:wght@400;600;800&display=swap"
        rel="stylesheet"
      />
      <link rel="icon" href="/vos.png" />
      <link rel="stylesheet" href="/styles.css" />
      <script src="https://unpkg.com/htmx.org@2.0.6" />
    </head>
    <body>
      {!bare && (
        <header>
          <img src="/vos.png" alt="" />
          <h1>{title}</h1>
          {right && <span class="banner-right">{right}</span>}
          <a class="banner-home" href="/">
            Uitleg
          </a>
        </header>
      )}
      {bare ? children : <main>{children}</main>}
    </body>
  </html>
);
