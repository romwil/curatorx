"""Tests for setup wizard helpers."""

import unittest

from curatorx.config_store import Settings
from curatorx.web.setup import resolve_test_payload


class SetupTests(unittest.TestCase):
    def test_resolve_test_payload_backfills_llm_model(self) -> None:
        existing = Settings(llm_provider="anthropic", llm_model="claude-sonnet-4-6")
        merged = resolve_test_payload({"llm_provider": "anthropic"}, existing)
        self.assertEqual(merged["llm_model"], "claude-sonnet-4-6")

    def test_resolve_test_payload_preserves_incoming_llm_model(self) -> None:
        existing = Settings(llm_provider="anthropic", llm_model="claude-sonnet-4-6")
        merged = resolve_test_payload(
            {"llm_provider": "anthropic", "llm_model": "claude-sonnet-4-20250514"},
            existing,
        )
        self.assertEqual(merged["llm_model"], "claude-sonnet-4-20250514")


if __name__ == "__main__":
    unittest.main()
