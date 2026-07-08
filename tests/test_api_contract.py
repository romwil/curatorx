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
        os.environ["CURATORX_SKIP_DOTENV"] = "1"
        os.environ["LLM_PROVIDER"] = "ollama"
        import curatorx.web.jobs as jobs

        jobs._manager = None
        import curatorx.web.app as app_mod

        importlib.reload(app_mod)
        self.client = TestClient(app_mod.app)

    def tearDown(self) -> None:
        import curatorx.web.jobs as jobs

        jobs._manager = None
        os.environ.pop("CURATORX_SKIP_DOTENV", None)
        os.environ.pop("LLM_PROVIDER", None)
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
        self.assertEqual(body["persona_mode"], "sliders")
        self.assertIn("assembled_prompt", body)

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
        body = resp.json()
        self.assertIn("detail", body)

    def test_chat_returns_json_error_on_llm_failure(self) -> None:
        from unittest.mock import AsyncMock, patch

        with patch("curatorx.web.app.CuratorAgent") as agent_cls:
            agent = AsyncMock()
            agent.run = AsyncMock(side_effect=RuntimeError("LLM provider unavailable"))
            agent_cls.return_value = agent

            resp = self.client.post(
                "/api/chat",
                json={"message": "hello"},
            )
            self.assertEqual(resp.status_code, 500)
            body = resp.json()
            self.assertIn("detail", body)
            self.assertIn("LLM provider unavailable", body["detail"])

    def test_wizard_status_shape(self) -> None:
        resp = self.client.get("/api/setup/wizard")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("current_step", body)
        self.assertIn("steps", body)
        self.assertIn("identity_seed", body["steps"])
        self.assertIn("infrastructure", body["steps"])
        self.assertIn("dropdown_mapping", body["steps"])
        self.assertNotIn("persona", body["steps"])
        self.assertFalse(body["onboarding_complete"])

    def test_llm_test_requires_api_key(self) -> None:
        resp = self.client.post(
            "/api/setup/test/llm",
            json={"llm_provider": "openai", "llm_model": "gpt-4o-mini"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["ok"])
        self.assertIn("api key", body["message"].lower())

    def test_service_integration_persisted_on_plex_failure(self) -> None:
        resp = self.client.post(
            "/api/setup/test/plex",
            json={"plex_url": "http://invalid.local", "plex_token": "bad"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["ok"])

        import curatorx.web.jobs as jobs

        row = jobs.get_job_manager().db.get_service_integration("plex")
        self.assertIsNotNone(row)
        self.assertEqual(str(row["connection_status"]), "failed")
        self.assertEqual(int(row["certified"]), 0)

    def test_certifications_endpoint_shape(self) -> None:
        resp = self.client.get("/api/setup/certifications")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("services", body)
        for service in ("llm", "plex", "radarr", "sonarr", "tmdb", "fanart", "tautulli"):
            self.assertIn(service, body["services"])
            entry = body["services"][service]
            self.assertIn("certified", entry)
            self.assertIn("connection_status", entry)
            self.assertIn("last_tested_at", entry)

    def test_wizard_includes_certifications(self) -> None:
        resp = self.client.get("/api/setup/wizard")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("certifications", body)
        self.assertIn("llm", body["certifications"])

    def test_active_context_defaults_to_general(self) -> None:
        resp = self.client.get("/api/context/active")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["context_hash"], "general")
        self.assertEqual(body["inferred_label"], "General Exploration")

    def test_service_integration_certified_on_llm_success(self) -> None:
        from unittest.mock import AsyncMock, patch

        mock_chat = AsyncMock(return_value={"content": [{"type": "text", "text": "pong"}]})
        with patch("curatorx.web.setup.get_chat_provider") as get_provider:
            provider = AsyncMock()
            provider.chat = mock_chat
            get_provider.return_value = provider

            resp = self.client.post(
                "/api/setup/test/llm",
                json={
                    "llm_provider": "openai",
                    "llm_api_key": "test-key",
                    "llm_model": "gpt-4o-mini",
                },
            )
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json()["ok"])

        import curatorx.web.jobs as jobs

        row = jobs.get_job_manager().db.get_service_integration("llm")
        self.assertIsNotNone(row)
        self.assertEqual(int(row["certified"]), 1)
        self.assertEqual(str(row["connection_status"]), "verified")

    def test_certification_invalidated_when_llm_url_changes(self) -> None:
        from unittest.mock import AsyncMock, patch

        mock_chat = AsyncMock(return_value={"content": [{"type": "text", "text": "pong"}]})
        with patch("curatorx.web.setup.get_chat_provider") as get_provider:
            provider = AsyncMock()
            provider.chat = mock_chat
            get_provider.return_value = provider
            self.client.post(
                "/api/setup/test/llm",
                json={
                    "llm_provider": "openai",
                    "llm_api_key": "test-key",
                    "llm_model": "gpt-4o-mini",
                },
            )

        import curatorx.web.jobs as jobs

        row = jobs.get_job_manager().db.get_service_integration("llm")
        self.assertEqual(int(row["certified"]), 1)

        put = self.client.put(
            "/api/settings",
            json={"llm_base_url": "https://api.openai.com/v1", "llm_model": "gpt-4o-mini"},
        )
        self.assertEqual(put.status_code, 200)

        row = jobs.get_job_manager().db.get_service_integration("llm")
        self.assertEqual(int(row["certified"]), 1)

        put = self.client.put(
            "/api/settings",
            json={"llm_base_url": "https://custom.example.com/v1"},
        )
        self.assertEqual(put.status_code, 200)

        row = jobs.get_job_manager().db.get_service_integration("llm")
        self.assertEqual(int(row["certified"]), 0)
        self.assertEqual(str(row["connection_status"]), "unverified")

    def test_settings_masks_secrets_with_source(self) -> None:
        os.environ["LLM_API_KEY"] = "env-secret"
        import curatorx.web.jobs as jobs

        jobs._manager = None
        import curatorx.web.app as app_mod

        importlib.reload(app_mod)
        client = TestClient(app_mod.app)

        resp = client.get("/api/settings")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["llm_api_key"], "")
        self.assertTrue(body["llm_api_key_set"])
        self.assertEqual(body["llm_api_key_source"], "env")
        del os.environ["LLM_API_KEY"]

    def test_llm_test_uses_env_key_when_ui_empty(self) -> None:
        os.environ["LLM_API_KEY"] = "env-secret"
        import curatorx.web.jobs as jobs

        jobs._manager = None
        import curatorx.web.app as app_mod

        importlib.reload(app_mod)
        client = TestClient(app_mod.app)

        resp = client.post(
            "/api/setup/test/llm",
            json={"llm_provider": "openai", "llm_model": "gpt-4o-mini"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["ok"])
        self.assertNotIn("API key is required", body["message"])
        del os.environ["LLM_API_KEY"]

    def test_llm_providers_includes_gemini(self) -> None:
        resp = self.client.get("/api/setup/llm-providers")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("gemini", body["base_urls"])
        self.assertIn("anthropic", body["base_urls"])
        self.assertIn("anthropic", body["models"])

    def test_llm_test_routes_anthropic_provider(self) -> None:
        from unittest.mock import AsyncMock, patch

        mock_chat = AsyncMock(return_value={"content": [{"type": "text", "text": "pong"}]})
        with patch("curatorx.web.setup.get_chat_provider") as get_provider:
            provider = AsyncMock()
            provider.chat = mock_chat
            get_provider.return_value = provider

            resp = self.client.post(
                "/api/setup/test/llm",
                json={
                    "llm_provider": "anthropic",
                    "llm_api_key": "test-key",
                    "llm_model": "gpt-4o-mini",
                },
            )
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertTrue(body["ok"])
            self.assertIn("anthropic", body["message"])
            self.assertIn("claude-sonnet-4-6", body["message"])

            settings = get_provider.call_args.args[0]
            self.assertEqual(settings.llm_provider, "anthropic")
            self.assertEqual(settings.llm_model, "claude-sonnet-4-6")
            mock_chat.assert_awaited_once()

    def test_settings_sync_llm_to_db(self) -> None:
        put = self.client.put(
            "/api/settings",
            json={
                "llm_provider": "openrouter",
                "llm_base_url": "https://openrouter.ai/api/v1",
                "llm_model": "deepseek-chat",
            },
        )
        self.assertEqual(put.status_code, 200)

        import curatorx.web.jobs as jobs

        db = jobs.get_job_manager().db
        self.assertEqual(db.get_config("llm_provider"), "openrouter")
        self.assertEqual(db.get_config("llm_base_url"), "https://openrouter.ai/api/v1")
        self.assertEqual(db.get_config("llm_model"), "deepseek-chat")

    def test_saved_llm_settings_override_env_on_get(self) -> None:
        os.environ["LLM_PROVIDER"] = "openai_compatible"
        os.environ["LLM_BASE_URL"] = "https://api.openai.com/v1"
        os.environ["LLM_MODEL"] = "gpt-4o-mini"
        try:
            put = self.client.put(
                "/api/settings",
                json={
                    "llm_provider": "anthropic",
                    "llm_base_url": "https://api.anthropic.com",
                    "llm_model": "claude-sonnet-4-6",
                    "llm_api_key": "test-key",
                },
            )
            self.assertEqual(put.status_code, 200)
            self.assertEqual(put.json()["llm_provider"], "anthropic")
            self.assertEqual(put.json()["llm_model"], "claude-sonnet-4-6")

            get = self.client.get("/api/settings")
            self.assertEqual(get.status_code, 200)
            body = get.json()
            self.assertEqual(body["llm_provider"], "anthropic")
            self.assertEqual(body["llm_base_url"], "https://api.anthropic.com")
            self.assertEqual(body["llm_model"], "claude-sonnet-4-6")
            self.assertTrue(body["llm_api_key_set"])
            self.assertEqual(body["llm_api_key_source"], "file")
        finally:
            del os.environ["LLM_PROVIDER"]
            del os.environ["LLM_BASE_URL"]
            del os.environ["LLM_MODEL"]

    def test_chat_threads_crud_contract(self) -> None:
        from unittest.mock import AsyncMock, patch

        create = self.client.post("/api/chat/threads", json={"thread_title": "Neo-noir hunt"})
        self.assertEqual(create.status_code, 200)
        created = create.json()
        self.assertIn("session_id", created)
        self.assertEqual(created["thread_title"], "Neo-noir hunt")
        session_id = created["session_id"]

        listed = self.client.get("/api/chat/threads")
        self.assertEqual(listed.status_code, 200)
        threads = listed.json()
        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0]["id"], session_id)
        self.assertEqual(threads[0]["thread_title"], "Neo-noir hunt")

        with patch("curatorx.web.app.CuratorAgent") as agent_cls:
            agent = AsyncMock()
            agent.run = AsyncMock(
                return_value={
                    "session_id": session_id,
                    "lens_id": "general",
                    "message": {
                        "id": "assistant-1",
                        "role": "assistant",
                        "blocks": [{"type": "text", "content": "Try Blade Runner."}],
                        "lens_id": "general",
                    },
                    "pending_tokens": [],
                }
            )
            agent_cls.return_value = agent

            chat = self.client.post(
                "/api/chat",
                json={"message": "Find neo-noir films", "session_id": session_id},
            )
            self.assertEqual(chat.status_code, 200)

            import curatorx.web.jobs as jobs

            db = jobs.get_job_manager().db
            db.save_chat_message(
                session_id,
                "user-1",
                "user",
                [{"type": "text", "content": "Find neo-noir films"}],
            )
            db.save_chat_message(
                session_id,
                "assistant-1",
                "assistant",
                [{"type": "text", "content": "Try Blade Runner."}],
            )

        messages = self.client.get(f"/api/chat/threads/{session_id}/messages")
        self.assertEqual(messages.status_code, 200)
        body = messages.json()
        self.assertEqual(body["session_id"], session_id)
        self.assertGreaterEqual(len(body["messages"]), 1)

        renamed = self.client.patch(
            f"/api/chat/threads/{session_id}",
            json={"thread_title": "Rainy city picks"},
        )
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.json()["thread_title"], "Rainy city picks")

        deleted = self.client.delete(f"/api/chat/threads/{session_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["deleted"])

        missing = self.client.get(f"/api/chat/threads/{session_id}/messages")
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
