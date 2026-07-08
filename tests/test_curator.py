"""Tests for CuratorAgent response parsing and tool loops."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from curatorx.agent.curator import (
    CuratorAgent,
    _extract_text,
    _extract_tool_calls,
)
from curatorx.agent.providers import _normalize_anthropic_response
from curatorx.config_store import Settings
from curatorx.library.db import Database


class CuratorResponseParsingTests(unittest.TestCase):
    def test_extract_text_from_anthropic_json(self) -> None:
        response = {
            "content": [{"type": "text", "text": "Try these picks."}],
            "role": "assistant",
            "stop_reason": "end_turn",
        }
        self.assertEqual(_extract_text(response), "Try these picks.")

    def test_extract_text_from_normalized_anthropic_json(self) -> None:
        response = _normalize_anthropic_response(
            {
                "content": [{"type": "text", "text": "Normalized text."}],
                "stop_reason": "end_turn",
            }
        )
        self.assertEqual(_extract_text(response), "Normalized text.")

    def test_extract_tool_calls_from_anthropic_tool_use(self) -> None:
        response = {
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_abc",
                    "name": "search_library",
                    "input": {"query": "noir"},
                }
            ],
            "stop_reason": "tool_use",
        }
        calls = _extract_tool_calls(response)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["function"]["name"], "search_library")


class CuratorAgentToolLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_anthropic_tool_use_runs_tools_not_empty_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            settings = Settings(
                llm_provider="anthropic",
                llm_api_key="test-key",
                llm_model="claude-sonnet-4-6",
            )
            agent = CuratorAgent(db, settings)

            tool_response = _normalize_anthropic_response(
                {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "search_library",
                            "input": {"query": "noir"},
                        }
                    ],
                    "stop_reason": "tool_use",
                }
            )
            text_response = _normalize_anthropic_response(
                {
                    "content": [{"type": "text", "text": "Here are some noir picks."}],
                    "stop_reason": "end_turn",
                }
            )

            call_count = {"n": 0}

            async def mock_chat(messages, tools=None):
                call_count["n"] += 1
                return tool_response if call_count["n"] == 1 else text_response

            agent.provider = MagicMock()
            agent.provider.chat = AsyncMock(side_effect=mock_chat)

            result = await agent.run("session-1", "find noir movies")
            blocks = result["message"]["blocks"]
            text_blocks = [block for block in blocks if block.get("type") == "text"]

            self.assertGreaterEqual(call_count["n"], 2)
            self.assertTrue(text_blocks)
            self.assertIn("noir", text_blocks[0]["content"].lower())

    async def test_multi_round_tool_use_continues_until_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            settings = Settings(
                llm_provider="anthropic",
                llm_api_key="test-key",
                llm_model="claude-sonnet-4-6",
            )
            agent = CuratorAgent(db, settings)

            tool_response = _normalize_anthropic_response(
                {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "search_library",
                            "input": {"query": "noir"},
                        }
                    ],
                    "stop_reason": "tool_use",
                }
            )
            text_response = _normalize_anthropic_response(
                {
                    "content": [{"type": "text", "text": "Done after two tool rounds."}],
                    "stop_reason": "end_turn",
                }
            )

            call_count = {"n": 0}

            async def mock_chat(messages, tools=None):
                call_count["n"] += 1
                if call_count["n"] < 3:
                    return tool_response
                return text_response

            agent.provider = MagicMock()
            agent.provider.chat = AsyncMock(side_effect=mock_chat)

            result = await agent.run("session-2", "find noir movies")
            text_blocks = [block for block in result["message"]["blocks"] if block.get("type") == "text"]

            self.assertEqual(call_count["n"], 3)
            self.assertEqual(text_blocks[0]["content"], "Done after two tool rounds.")


if __name__ == "__main__":
    unittest.main()
