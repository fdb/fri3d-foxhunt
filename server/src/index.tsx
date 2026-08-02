import { Hono } from "hono";
import type { Bindings } from "./types";
import { authRoutes } from "./routes/auth";
import { playerRoutes } from "./routes/player";
import { pageRoutes } from "./routes/pages";

const app = new Hono<{ Bindings: Bindings }>();

app.route("/api/v1/auth", authRoutes);
app.route("/api/v1/player", playerRoutes);
app.route("/", pageRoutes);

export default app;
