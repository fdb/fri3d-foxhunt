import type { PropsWithChildren } from "hono/jsx";

export const Layout = ({
  title,
  right,
  children,
}: PropsWithChildren<{ title: string; right?: string }>) => (
  <html lang="nl">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>{title}</title>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="" />
      <link
        href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@400..700&display=swap"
        rel="stylesheet"
      />
      <link rel="icon" href="/vos.png" />
      <link rel="stylesheet" href="/styles.css" />
      <script src="https://unpkg.com/htmx.org@2.0.6" />
    </head>
    <body>
      <header>
        <img src="/vos.png" alt="" />
        <h1>{title}</h1>
        {right && <span class="banner-right">{right}</span>}
      </header>
      <main>{children}</main>
    </body>
  </html>
);
