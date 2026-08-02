import type { PropsWithChildren } from "hono/jsx";

export const Layout = ({
  title,
  children,
}: PropsWithChildren<{ title: string }>) => (
  <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>{title}</title>
      <link rel="stylesheet" href="/styles.css" />
      <script src="https://unpkg.com/htmx.org@2.0.6" />
    </head>
    <body>
      <header>
        <h1>🦊 Foxhunt</h1>
      </header>
      <main>{children}</main>
    </body>
  </html>
);
