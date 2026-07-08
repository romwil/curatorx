"""Frontend-backend contract tests for lens and persona APIs."""

from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class ApiContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ["DATA_DIR"] = self._tmpdir.name
        import curatorx.web.jobs as jobs

        jobs._manager = None
        import curatorx.web.app as app_mod

        importlib.reload(app_mod)
        self.client = TestClient(app_mod.app)

    def tearDown(self) -> None:
        import curatorx.web.jobs as jobs

        jobs._manager = None
        self._tmpdir.cleanup()

    def test_health_includes_version(self) -> None:
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("version", body)

    def test_lenses_active_defaults_to_general(self) -> None:
        resp = self.client.get("/api/lenses/active")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["lens_id"], "general")
        self.assertEqual(body["lens_name"], "General")

    def test_persona_defaults(self) -> None:
        resp = self.client.get("/api/persona")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["curator_name"], "Curator")
        self.assertEqual(body["val_bro_prof"], 0.5)

    def test_create_lens_and_switch_active(self) -> None:
        create = self.client.post(
            "/api/lenses",
            json={
                "lens_id": "noir-study",
                "lens_name": "Neo-Noir Study",
                "description": "Director-focused noir lane",
            },
        )
        self.assertEqual(create.status_code, 200)
        self.assertEqual(create.json()["lens_id"], "noir-study")

        switch = self.client.put("/api/lenses/active", json={"lens_id": "noir-study"})
        self.assertEqual(switch.status_code, 200)
        self.assertEqual(switch.json()["lens_id"], "noir-study")

        active = self.client.get("/api/lenses/active")
        self.assertEqual(active.json()["lens_id"], "noir-study")

    def test_chat_rejects_unknown_lens(self) -> None:
        resp = self.client.post(
            "/api/chat",
            json={"message": "hello", "lens_id": "does-not-exist"},
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
