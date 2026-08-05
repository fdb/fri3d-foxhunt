# sync.py — drain the report outbox to the server, opportunistically.
#
# Woods WiFi is spotty (GAME_DESIGN.md, "How a creature reaches the
# profile"), so badge→server reports never block a screen: writers call
# store.enqueue_report and forget; flush() drains what it can from natural
# moments (the home screen's resume) and leaves the rest queued. Delivery
# rules per report: 2xx = delivered; 4xx = the server refused it forever —
# drop it, or the queue wedges behind one bad report; anything else (no
# network, 5xx) = stop and let the next natural moment retry.

import store
import registrar
from mpos import TaskManager

_ROUTES = {
    "snuffel": ("POST", "/api/v1/player/snuffel"),
    "pluk": ("POST", "/api/v1/player/pluk"),
    "bonded": ("PATCH", "/api/v1/auth/user"),
    "profile": ("PATCH", "/api/v1/auth/user"),
}
_busy = False


def flush():
    """Fire-and-forget: start a drain unless one is already running."""
    global _busy
    if _busy or not store.outbox():
        return
    _busy = True
    TaskManager.create_task(_drain())


async def _drain():
    global _busy
    try:
        while True:
            box = store.outbox()
            if not box:
                return
            item = box[0]
            route = _ROUTES.get(item.get("kind"))
            if route is None:  # unknown kind: drop, never wedge the queue
                store.outbox_pop()
                continue
            body = dict(item.get("data") or {})
            body["badge_id"] = registrar.badge_id()
            try:
                status, _ = await registrar._json_request(route[0], route[1], body)
            except Exception:
                return  # no network; the next natural moment retries
            if 200 <= status < 300 or 400 <= status < 500:
                store.outbox_pop()
            else:
                return  # server trouble: keep the report, retry later
    finally:
        _busy = False
