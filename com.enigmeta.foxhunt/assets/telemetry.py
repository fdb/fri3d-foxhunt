# telemetry.py — usage reporting, runs once at app start.

import store
import registrar
from mpos import TaskManager

_EVENT_ID = 13
_ACK = "t13"


def boot():
    if (
        registrar.server_configured()
        and store.is_caught(_EVENT_ID)
        and not store.flag(_ACK)
    ):
        TaskManager.create_task(_send())


async def _send():
    body = {"badge_id": registrar.badge_id(), "fox_id": _EVENT_ID}
    try:
        status, data = await registrar.api_request("POST", "/api/v1/player/found", body)
    except Exception:
        return
    if status == 200 and data and data.get("ok"):
        store.set_flag(_ACK)
