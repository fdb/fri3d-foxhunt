# Vossenjacht notifications — design

Push "a creature became active" to interested players' badges, delivered
appropriately for whatever state the badge is in. Research verified on the
physical badge (2026-08-02): MicroPythonOS ships an Android-style
`NotificationManager` (persistent, bell + drawer UI, tap-to-launch intents)
and a `boot_completed` service mechanism — we build on both, no OS changes.

## Architecture at a glance

```
Cloudflare Worker (Hono + D1)                    Badge
─────────────────────────────                    ─────
game_events log ──▶ /api/v1/notifications ◀──── FoxhuntNotifierService (boot service,
                    ?since=<cursor>              TaskManager async poll loop)
                    &hunter_id=<id>                  │
                                                     ├─ foxhunt foreground → in-app banner
                                                     └─ otherwise → NotificationManager.notify()
                                                        + LED pulse (mpos.lights)
```

One delivery pipeline, one router. The **boot service** is the single place
that learns about events (survives app switches, runs from OS boot); a small
**router** decides the presentation per badge state. The foxhunt app itself
never polls — it only registers/unregisters an in-app presenter with the
service when it comes to the foreground.

## The five states

| State | Delivery | Mechanism |
|---|---|---|
| 1. Badge off | Later, on next boot | Server-side cursor replay; expired events dropped |
| 2. On, screen dimmed¹ | LED pulse (+ buzzer), drawer entry | Service runs regardless of backlight; `mpos.lights` |
| 3. On, home screen | Bell icon + drawer entry | Built-in `NotificationManager.notify()` behavior |
| 4. On, another app | Later, visible from home | Same `notify()` — OS keeps the bar hidden in apps; entry persists in drawer. LED pulse bridges the gap² |
| 5. On, foxhunt | In-app popup banner (WhatsApp-style) | Custom LVGL overlay on `lv.layer_top()`; no drawer entry |

¹ **There is no true "screen off, badge running" state in MicroPythonOS
today.** The drawer brightness slider bottoms out at 1% (`topmenu.py`,
slider range 1–100) and the power button is `machine.deepsleep()` — CPU
halted, no WiFi, no LEDs, indistinguishable from state 1. So state 2 as
specced only exists as "screen dimmed very low". Everything (asyncio loop,
WiFi, LEDs, buzzer) keeps running in that state, so the LED behavior works —
but if we want a real one-button screen-off we'd have to propose it upstream.
Decision needed: accept "dimmed ≙ screen off", or file an OS issue.

² State 4 is where players actually live at a hunt (playing Breakout in the
queue). A drawer entry alone is invisible until they go home — the OS never
force-opens the bar and has no toast primitive. The LED pulse + buzzer beep
is what actually tells them something happened. If we want zero interruption
of other games, we make LED/buzzer a per-state choice (see Open questions).

## Server side

The Worker already has an append-only `game_events` log; notifications are a
projection of it, same as the scoreboard.

- **New route** `GET /api/v1/notifications?hunter_id=X&since=<event_id>` →
  `{ events: [{id, type, creature_id, title, text, expires_at}], cursor }`.
  Monotonic `id` from `game_events` doubles as the cursor.
- **"Interested players"**: server-side filter — default *players who have
  not yet found that creature* (the projection tables already know). Keeps
  badge logic dumb: it shows whatever the server sends.
- **Expiry**: every activation event carries `expires_at` (end of the
  creature's active window). The server doesn't send expired events; the
  badge double-checks on receipt (clock skew, long WiFi gaps). This is what
  makes "delivered later" safe — a badge that boots two hours late doesn't
  send its player chasing a fox that already went to sleep.
- **Auth**: same `badge_id`/`hunter_id` identity the registrar already POSTs.

## Badge side

### FoxhuntNotifierService (new: `assets/notifier.py`)

Declared in `MANIFEST.JSON`:

```json
"services": [{"entrypoint": "assets/notifier.py",
              "classname": "FoxhuntNotifierService",
              "intent_filters": [{"action": "boot_completed"}]}]
```

`onStart` spawns one `TaskManager.create_task(self._run())` (never import
asyncio directly — OS rule). The loop, following the `osupdate` pattern:

1. Sleep `POLL_SECONDS` (~30–60 s; battery/liveness tradeoff, tune at event).
2. Skip if `ConnectivityManager` says offline (desktop always reports online,
   so the emulator exercises the full path).
3. Fetch `/api/v1/notifications` with the persisted cursor
   (`SharedPreferences`, foxhunt app namespace).
4. Drop expired events; advance + persist cursor.
5. Route each survivor (below).

Errors never kill the loop — log, back off, retry next tick. The service
also handles state 1 for free: first poll after boot replays everything
since the stored cursor.

### Routing

```
if mpos.get_foreground_app() == "com.enigmeta.foxhunt" and app registered a presenter:
    presenter(event)                      # in-app banner, state 5
else:
    NotificationManager.notify(...)       # states 2/3/4
    mpos.lights.set_notification_color(...)   # no-ops on desktop
```

- **Drawer notification**: stable `notification_id=f"foxhunt.active.{creature_id}"`
  — a re-activation of the same creature updates the existing entry in RAM
  (no flash write, OS handles this), instead of stacking duplicates.
  `priority=PRIORITY_HIGH`, `intent=Intent(app_fullname="com.enigmeta.foxhunt")`
  (later: an action that deep-links to the hunt screen), `auto_cancel=True`.
  Icon: foxhunt app icon path.
- **Sound**: the badge firmware already beeps the buzzer inside `notify()`
  (`_play_notification_sound`, respects the system notification-sound
  setting) — nothing to build for states 2–4. State 5's banner plays its own
  short jingle via `sound.py` since `notify()` isn't called there.
- **LED**: `mpos.lights.set_notification_color()` on delivery; cleared when
  the count of foxhunt notifications drops to zero, observed via
  `NotificationManager.register_listener` (fires on notify/cancel/trigger,
  so tapping or dismissing in the drawer clears the LED automatically).
  Desktop: `mpos.lights.is_available()` is False → falls back to the
  existing on-screen LED mirror convention.

### In-app banner (state 5, new: `assets/notify_banner.py` + ui.py tokens)

WhatsApp-style: a slide-down card on `lv.layer_top()` (above every screen,
including the drawer), creature sprite + title + one line of text,
auto-dismiss after ~4 s, tap → jump to the relevant screen. One banner at a
time; a newer event replaces the current one. Sizes/colours become tokens in
`ui.py` and get a block in `layout/foxhunt-layout.html` like every other
screen element.

Wiring: the foxhunt Activity registers the presenter in `onResume` and
unregisters in `onPause` — the same suppression idiom `osupdate` uses. While
registered, events **bypass** `NotificationManager` entirely: the player saw
the banner, so no residual drawer entry (matches WhatsApp: no tray
notification for the chat you're looking at). If we later decide missed
banners should persist, flip that to notify-then-cancel-on-view.

## Testing

- **Emulator first**: the whole pipeline minus LED/buzzer runs identically
  on desktop (notification manager, drawer, banner are pure Python + LVGL;
  connectivity always "online"). Drive with the emulator REPL
  (click + screenshot) against a local `npm run dev` Worker.
- **Unit-ish**: router logic (foreground vs not, expiry filtering, cursor
  advance) is plain Python — testable without LVGL.
- **Badge**: end-to-end with the deployed Worker; verify state 2 (dim screen,
  watch LED), state 4 (open Breakout, wait for beep, find entry in drawer),
  reboot replay (state 1).

## Open questions

1. **State 2 scope** — accept "screen dimmed = screen off" for the 2026
   badge, or push a real display-off state upstream to MicroPythonOS?
2. **Interrupting other games** — is a buzzer beep during someone else's
   game acceptable, or LED-only in state 4? (Firmware beep is controlled by
   the system-wide notification-sound setting; per-app override would be
   our own suppression logic.)
3. **Interest filter** — "hasn't found it yet" is the proposed default; do
   we also want opt-in per creature (favorites), or distance/zone-based
   interest later?
4. **Poll cadence vs battery** — 30–60 s proposed; needs a real-world
   battery measurement at the event. LoRa/ESP-NOW broadcast from the
   existing bridge is the WiFi-free fallback if the venue WiFi is bad —
   deliberately out of scope for v1, but the service/router split means only
   the transport layer would change.
5. **Other notification types** — this doc covers "creature became active";
   the same pipeline trivially carries "you were found", "hunt starts in
   10 min", etc. Worth listing before the event so the server event types
   are settled once.
