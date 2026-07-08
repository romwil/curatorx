"""Curator agent orchestration."""

from __future__ import annotations

import json
import uuid
from typing import Any, AsyncIterator, Dict, List, Mapping

from mediacurator.agent.providers import get_chat_provider
from mediacurator.agent.tools import TOOL_DEFINITIONS, ToolRegistry, build_system_prompt
from mediacurator.config_store import Settings
from mediacurator.library.db import Database
from mediacurator.models.schemas import ChatMessageBlock


def _extract_tool_calls(response: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    if "choices" in response:
        message = response["choices"][0]["message"]
        return list(message.get("tool_calls") or [])
    if "content" in response:
        tool_uses = []
        for block in response.get("content") or []:
            if block.get("type") == "tool_use":
                tool_uses.append(
                    {
                        "id": block.get("id"),
                        "function": {
                            "name": block.get("name"),
                            "arguments": json.dumps(block.get("input") or {}),
                        },
                    }
                )
        return tool_uses
    return []


def _assistant_message_from_response(response: Mapping[str, Any]) -> Dict[str, Any]:
    if "choices" in response:
        return dict(response["choices"][0]["message"])
    return {"role": "assistant", "content": response.get("content") or []}


def _extract_text(response: Mapping[str, Any]) -> str:
    if "choices" in response:
        message = response["choices"][0]["message"]
        return str(message.get("content") or "")
    if "content" in response:
        parts = []
        for block in response.get("content") or []:
            if block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "".join(parts)
    return ""


class CuratorAgent:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.provider = get_chat_provider(settings) if settings.llm_api_key or settings.llm_provider == "ollama" else None

    async def _fallback_run(self, registry: ToolRegistry, user_message: str) -> str:
        lowered = user_message.lower()
        if any(word in lowered for word in ("purge", "remove", "clunker", "space", "delete")):
            await registry.execute("suggest_purge_candidates", {"limit": 10})
            return "Here are titles that may not be worth the drive space based on play history and taste fit."
        if any(word in lowered for word in ("add", "missing", "gap", "recommend", "gem", "70s", "80s", "genre")):
            await registry.execute(
                "find_collection_gaps",
                {"media_type": "movie", "year_from": 1970, "year_to": 1979} if "70s" in lowered else {"media_type": "movie"},
            )
            return "I searched for missing titles that fit what you described. Review the cards below."
        if "watch" in lowered or "tonight" in lowered:
            await registry.execute("search_library", {"query": user_message, "media_type": "movie"})
            return "Based on your library, here are some options worth revisiting tonight."
        await registry.execute("search_library", {"query": user_message})
        return "Here's what I found in your library. Configure an LLM provider for richer conversation."

    async def run(self, session_id: str, user_message: str) -> Dict[str, Any]:
        self.db.ensure_chat_session(session_id)
        registry = ToolRegistry(self.db, self.settings)

        if not self.provider:
            text = await self._fallback_run(registry, user_message)
            blocks: List[Dict[str, Any]] = [{"type": "text", "content": text}]
            if registry.cards:
                blocks.append({"type": "title_cards", "items": [card.model_dump() for card in registry.cards]})
                blocks.append(
                    {
                        "type": "action_prompt",
                        "action": "open_viewport",
                        "payload": {"title": "Results", "items": [c.model_dump() for c in registry.cards]},
                    }
                )
            user_id = uuid.uuid4().hex
            assistant_id = uuid.uuid4().hex
            self.db.save_chat_message(session_id, user_id, "user", [{"type": "text", "content": user_message}])
            self.db.save_chat_message(session_id, assistant_id, "assistant", blocks)
            return {
                "session_id": session_id,
                "message": {"id": assistant_id, "role": "assistant", "blocks": blocks},
                "pending_tokens": registry.pending_tokens,
            }

        history = self.db.chat_history(session_id, limit=20)
        messages: List[Dict[str, Any]] = [{"role": "system", "content": build_system_prompt(self.db)}]
        for entry in history:
            text = " ".join(
                block.get("content", "")
                for block in entry.get("blocks", [])
                if block.get("type") == "text"
            )
            if text:
                messages.append({"role": entry["role"], "content": text})
        messages.append({"role": "user", "content": user_message})

        registry = ToolRegistry(self.db, self.settings)
        use_tools = bool(self.settings.llm_api_key or self.settings.llm_provider == "ollama")
        response = await self.provider.chat(messages, tools=TOOL_DEFINITIONS if use_tools else None)
        tool_calls = _extract_tool_calls(response)

        if tool_calls:
            messages.append(_assistant_message_from_response(response))
            for call in tool_calls:
                fn = call.get("function") or {}
                name = fn.get("name")
                args = json.loads(fn.get("arguments") or "{}")
                result = await registry.execute(str(name), args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id"),
                        "content": result,
                    }
                )
            response = await self.provider.chat(messages)

        text = _extract_text(response)
        blocks: List[Dict[str, Any]] = []
        if text:
            blocks.append({"type": "text", "content": text})
        if registry.cards:
            blocks.append({"type": "title_cards", "items": [card.model_dump() for card in registry.cards]})
            blocks.append(
                {
                    "type": "action_prompt",
                    "action": "open_viewport",
                    "payload": {"title": "Recommendations", "items": [c.model_dump() for c in registry.cards]},
                }
            )

        user_id = uuid.uuid4().hex
        assistant_id = uuid.uuid4().hex
        self.db.save_chat_message(session_id, user_id, "user", [{"type": "text", "content": user_message}])
        self.db.save_chat_message(session_id, assistant_id, "assistant", blocks)

        return {
            "session_id": session_id,
            "message": {
                "id": assistant_id,
                "role": "assistant",
                "blocks": blocks,
            },
            "pending_tokens": registry.pending_tokens,
        }


async def stream_agent(db: Database, settings: Settings, session_id: str, user_message: str) -> AsyncIterator[str]:
    result = await CuratorAgent(db, settings).run(session_id, user_message)
    text_blocks = [b for b in result["message"]["blocks"] if b.get("type") == "text"]
    content = text_blocks[0]["content"] if text_blocks else ""
    chunk_size = 40
    for index in range(0, len(content), chunk_size):
        yield json.dumps({"type": "text_delta", "content": content[index : index + chunk_size]}) + "\n"
    yield json.dumps({"type": "complete", "message": result["message"], "pending_tokens": result["pending_tokens"]}) + "\n"
