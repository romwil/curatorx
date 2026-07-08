"""Tests for config store."""

import os
import tempfile
import unittest
from pathlib import Path

from curatorx.config_store import (
    Settings,
    load_dotenv_file,
    load_merged_settings,
    model_looks_openai,
    resolve_llm_base_url,
    resolve_llm_model,
    save_settings,
    secret_field_sources,
)


class ConfigStoreTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings = Settings(plex_url="http://plex", tmdb_api_key="secret")
            save_settings(data_dir, settings)
            loaded = load_merged_settings(data_dir)
            self.assertEqual(loaded.plex_url, "http://plex")
            self.assertEqual(loaded.tmdb_api_key, "secret")

    def test_from_mapping_ignores_unknown(self) -> None:
        settings = Settings.from_mapping({"plex_url": "x", "unknown": "y"})
        self.assertEqual(settings.plex_url, "x")

    def test_env_overrides_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            save_settings(data_dir, Settings(llm_api_key="from-file"))
            os.environ["LLM_API_KEY"] = "from-env"
            try:
                loaded = load_merged_settings(data_dir)
                self.assertEqual(loaded.llm_api_key, "from-env")
            finally:
                del os.environ["LLM_API_KEY"]

    def test_empty_env_does_not_clear_file_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            save_settings(data_dir, Settings(llm_api_key="from-file"))
            os.environ["LLM_API_KEY"] = ""
            try:
                loaded = load_merged_settings(data_dir)
                self.assertEqual(loaded.llm_api_key, "from-file")
            finally:
                del os.environ["LLM_API_KEY"]

    def test_secret_field_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            save_settings(data_dir, Settings(tmdb_api_key="file-key"))
            os.environ["LLM_API_KEY"] = "env-key"
            try:
                sources = secret_field_sources(data_dir)
                self.assertEqual(sources["llm_api_key"], "env")
                self.assertEqual(sources["tmdb_api_key"], "file")
                self.assertEqual(sources["plex_token"], "")
            finally:
                del os.environ["LLM_API_KEY"]

    def test_resolve_llm_model_switches_openai_model_for_anthropic(self) -> None:
        self.assertEqual(
            resolve_llm_model("anthropic", "gpt-4o-mini"),
            "claude-sonnet-4-6",
        )
        self.assertEqual(resolve_llm_model("anthropic", ""), "claude-sonnet-4-6")
        self.assertEqual(
            resolve_llm_model("anthropic", "claude-3-5-sonnet-20241022"),
            "claude-sonnet-4-6",
        )

    def test_resolve_llm_model_normalizes_anthropic_aliases(self) -> None:
        self.assertEqual(
            resolve_llm_model("anthropic", "claude-sonnet-4"),
            "claude-sonnet-4-6",
        )
        self.assertEqual(
            resolve_llm_model("anthropic", "claude-3-5-sonnet-latest"),
            "claude-sonnet-4-6",
        )
        self.assertEqual(
            resolve_llm_model("anthropic", "claude-sonnet-4-6"),
            "claude-sonnet-4-6",
        )
        self.assertEqual(
            resolve_llm_model("anthropic", "claude-sonnet-4-20250514"),
            "claude-sonnet-4-20250514",
        )

    def test_load_merged_settings_normalizes_stale_anthropic_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            save_settings(
                data_dir,
                Settings(llm_provider="anthropic", llm_model="claude-sonnet-4"),
            )
            loaded = load_merged_settings(data_dir)
            self.assertEqual(loaded.llm_model, "claude-sonnet-4-6")
            self.assertEqual(loaded.llm_base_url, "https://api.anthropic.com")

    def test_resolve_llm_base_url_anthropic_without_chat_completions(self) -> None:
        self.assertEqual(resolve_llm_base_url("anthropic", ""), "https://api.anthropic.com")
        self.assertEqual(
            resolve_llm_base_url("anthropic", "https://api.anthropic.com/v1"),
            "https://api.anthropic.com",
        )
        self.assertEqual(resolve_llm_base_url("openai", ""), "https://api.openai.com/v1")

    def test_model_looks_openai(self) -> None:
        self.assertTrue(model_looks_openai("gpt-4o-mini"))
        self.assertFalse(model_looks_openai("claude-sonnet-4-20250514"))

    def test_load_dotenv_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("LLM_API_KEY=dotenv-key\n# comment\nEMPTY=\n", encoding="utf-8")
            original = os.environ.pop("LLM_API_KEY", None)
            try:
                load_dotenv_file(env_path)
                self.assertEqual(os.environ["LLM_API_KEY"], "dotenv-key")
            finally:
                if original is None:
                    os.environ.pop("LLM_API_KEY", None)
                else:
                    os.environ["LLM_API_KEY"] = original


if __name__ == "__main__":
    unittest.main()
