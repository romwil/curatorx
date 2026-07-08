"""Tests for Anthropic provider error handling."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from curatorx.agent.providers import AnthropicProvider, LLMProviderError, _format_anthropic_error


class AnthropicProviderTests(unittest.IsolatedAsyncioTestCase):
    def test_format_anthropic_model_not_found_error(self) -> None:
        response = httpx.Response(
            404,
            json={
                "type": "error",
                "error": {
                    "type": "not_found_error",
                    "message": "model: claude-sonnet-4",
                },
            },
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
        )
        message = _format_anthropic_error(response)
        self.assertIn("model not found", message.lower())
        self.assertIn("claude-sonnet-4", message)

    async def test_chat_sends_plain_string_content(self) -> None:
        provider = AnthropicProvider("test-key", "claude-sonnet-4-6")
        mock_response = MagicMock()
        mock_response.is_error = False
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "pong"}],
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("curatorx.agent.providers.httpx.AsyncClient", return_value=mock_client):
            await provider.chat([{"role": "user", "content": "ping"}])

        body = mock_client.post.await_args.kwargs["json"]
        self.assertEqual(body["model"], "claude-sonnet-4-6")
        self.assertEqual(body["messages"], [{"role": "user", "content": "ping"}])

    async def test_chat_raises_provider_error_on_model_not_found(self) -> None:
        provider = AnthropicProvider("test-key", "claude-sonnet-4")
        mock_response = MagicMock()
        mock_response.is_error = True
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "type": "error",
            "error": {
                "type": "not_found_error",
                "message": "model: claude-sonnet-4",
            },
        }
        mock_response.text = ""

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("curatorx.agent.providers.httpx.AsyncClient", return_value=mock_client):
            with self.assertRaises(LLMProviderError) as ctx:
                await provider.chat([{"role": "user", "content": "ping"}])

        self.assertIn("model not found", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
