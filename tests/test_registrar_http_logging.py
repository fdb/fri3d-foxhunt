import asyncio
import builtins
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch


ASSETS = Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets"


def load_registrar():
    mpos = types.ModuleType("mpos")
    mpos.TaskManager = MagicMock()
    spec = importlib.util.spec_from_file_location(
        "registrar_http_logging_under_test", ASSETS / "registrar.py"
    )
    registrar = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"lvgl": types.ModuleType("lvgl"), "mpos": mpos}):
        spec.loader.exec_module(registrar)
    return registrar


class RegistrarHttpLoggingTest(unittest.TestCase):
    def test_request_and_response_are_logged_without_query_values(self):
        registrar = load_registrar()

        async def fake_request(method, path, body):
            return 200, {"ok": True}

        registrar._json_request_raw = fake_request
        with patch.object(builtins, "print") as log:
            result = asyncio.run(
                registrar._json_request(
                    "PATCH",
                    "/api/v1/auth/user?badge_id=SECRET",
                    {"profile_pic": "H14A000C1"},
                )
            )

        self.assertEqual(result, (200, {"ok": True}))
        self.assertEqual(
            log.call_args_list,
            [
                call("registrar: HTTP", "PATCH", "/api/v1/auth/user", "..."),
                call("registrar: HTTP", "PATCH", "/api/v1/auth/user", "->", 200),
            ],
        )

    def test_failed_request_is_logged_and_reraised(self):
        registrar = load_registrar()

        async def fake_request(method, path, body):
            raise OSError("offline")

        registrar._json_request_raw = fake_request
        with patch.object(builtins, "print") as log:
            with self.assertRaises(OSError):
                asyncio.run(registrar._json_request("POST", "/api/v1/player/pluk"))

        self.assertEqual(
            log.call_args_list,
            [
                call("registrar: HTTP", "POST", "/api/v1/player/pluk", "..."),
                call(
                    "registrar: HTTP",
                    "POST",
                    "/api/v1/player/pluk",
                    "-> FAILED",
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
