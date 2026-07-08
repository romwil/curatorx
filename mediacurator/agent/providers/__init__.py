"""BYOP LLM provider implementations."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, List, Mapping, Optional, Protocol

import httpx

from mediacurator.config_store import Settings


class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> List[float]: ...


class ChatProvider(Protocol):
    async def chat(
        self,
        messages: List[Mapping[str, Any]],
        tools: Optional[List[Mapping[str, Any]]] = None,
    ) -> Mapping[str, Any]: ...

    async def stream(
        self,
        messages: List[Mapping[str, Any]],
        tools: Optional[List[Mapping[str, Any]]] = None,
    ) -> AsyncIterator[Mapping[str, Any]]: ...


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def chat(
        self,
        messages: List[Mapping[str, Any]],
        tools: Optional[List[Mapping[str, Any]]] = None,
    ) -> Mapping[str, Any]:
        body: Dict[str, Any] = {"model": self.model, "messages": list(messages)}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
            return response.json()

    async def stream(
        self,
        messages: List[Mapping[str, Any]],
        tools: Optional[List[Mapping[str, Any]]] = None,
    ) -> AsyncIterator[Mapping[str, Any]]:
        body: Dict[str, Any] = {"model": self.model, "messages": list(messages), "stream": True}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:].strip()
                    if payload == "[DONE]":
                        break
                    yield json.loads(payload)


class OpenAIEmbeddingProvider:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def embed(self, text: str) -> List[float]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": text},
            )
            response.raise_for_status()
            payload = response.json()
            return payload["data"][0]["embedding"]


class AnthropicProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def chat(
        self,
        messages: List[Mapping[str, Any]],
        tools: Optional[List[Mapping[str, Any]]] = None,
    ) -> Mapping[str, Any]:
        system = ""
        converted: List[Dict[str, Any]] = []
        for message in messages:
            if message["role"] == "system":
                system = str(message.get("content") or "")
                continue
            converted.append(
                {
                    "role": message["role"],
                    "content": [{"type": "text", "text": str(message.get("content") or "")}],
                }
            )
        body: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": converted,
        }
        if system:
            body["system"] = system
        if tools:
            body["tools"] = [
                {
                    "name": tool["function"]["name"],
                    "description": tool["function"].get("description", ""),
                    "input_schema": tool["function"].get("parameters", {"type": "object", "properties": {}}),
                }
                for tool in tools
            ]
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            return response.json()

    async def stream(
        self,
        messages: List[Mapping[str, Any]],
        tools: Optional[List[Mapping[str, Any]]] = None,
    ) -> AsyncIterator[Mapping[str, Any]]:
        result = await self.chat(messages, tools)
        yield {"anthropic_complete": result}


def get_chat_provider(settings: Settings) -> ChatProvider:
    provider = settings.llm_provider.lower()
    if provider == "anthropic":
        return AnthropicProvider(settings.llm_api_key, settings.llm_model)
    base_url = settings.llm_base_url or "http://localhost:11434/v1"
    if provider == "ollama":
        base_url = settings.llm_base_url or "http://localhost:11434/v1"
    return OpenAICompatibleProvider(base_url, settings.llm_api_key, settings.llm_model)


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    base_url = settings.llm_embedding_base_url or settings.llm_base_url or "https://api.openai.com/v1"
    return OpenAIEmbeddingProvider(base_url, settings.llm_api_key, settings.llm_embedding_model)
