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
        registrar.BASE_URL = "http://localhost:8787"

        async def fake_request(method, path, body):
            return 200, {"ok": True}

        registrar._json_request_raw = fake_request
        with patch.object(builtins, "print") as log:
            result = asyncio.run(
                registrar.api_request(
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
        registrar.BASE_URL = "http://localhost:8787"

        async def fake_request(method, path, body):
            raise OSError("offline")

        registrar._json_request_raw = fake_request
        with patch.object(builtins, "print") as log:
            with self.assertRaises(OSError):
                asyncio.run(registrar.api_request("POST", "/api/v1/player/pluk"))

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

    def test_standalone_request_is_a_noop(self):
        registrar = load_registrar()
        registrar._json_request_raw = MagicMock()

        result = asyncio.run(registrar.api_request("POST", "/api/v1/player/pluk"))

        self.assertEqual(result, (0, None))
        registrar._json_request_raw.assert_not_called()

    def test_local_hunter_id_uses_nonzero_mac_suffix(self):
        registrar = load_registrar()

        self.assertEqual(registrar.local_hunter_id("A4:CF:12:9B:03:7E"), 0x037E)
        self.assertEqual(registrar.local_hunter_id("A4:CF:12:9B:00:00"), 1)

    def test_word_jager_mints_locally_after_lora_check(self):
        registrar = load_registrar()
        updates = []

        with patch.object(registrar, "has_lora", return_value=True):
            registrar.REGISTRAR.word_jager("A4:CF:12:9B:03:7E", updates.append)

        self.assertEqual(updates[0]["hunter_id"], 0x037E)
        self.assertTrue(updates[0]["ok"])
        registrar.TaskManager.create_task.assert_not_called()

    def test_registration_grants_starter_locally(self):
        registrar = load_registrar()
        creatures = types.ModuleType("creatures")
        creatures.starter_for = MagicMock(return_value=7)
        updates = []

        with patch.dict(sys.modules, {"creatures": creatures}):
            registrar.REGISTRAR.register(
                "Sam", "A4:CF:12:9B:03:7E", "H01A000C1", updates.append
            )

        self.assertTrue(updates[0]["ok"])
        self.assertEqual(updates[0]["starter"], 7)
        registrar.TaskManager.create_task.assert_not_called()


if __name__ == "__main__":
    unittest.main()
