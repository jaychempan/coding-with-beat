"""Small synchronous client for coding-with-beat's HTTP MCP server."""
from __future__ import annotations

import os
from typing import Any

import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .config import MCP_URL_FILE


MCP_URL_ENV = "CWB_MCP_URL"
LEGACY_MCP_URL_ENV = "CC_JUKEBOX_MCP_URL"
DEFAULT_MCP_URL = "http://127.0.0.1:8765/mcp"


class MCPClientError(RuntimeError):
    pass


def configured_url() -> str:
    env_url = (
        os.environ.get(MCP_URL_ENV, "").strip()
        or os.environ.get(LEGACY_MCP_URL_ENV, "").strip()
    )
    if env_url:
        return env_url
    try:
        saved_url = MCP_URL_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        saved_url = ""
    return saved_url or DEFAULT_MCP_URL


def call_tool(
    name: str,
    kwargs: dict[str, Any] | None = None,
    *,
    url: str | None = None,
    timeout: float = 30,
) -> str:
    target = url or configured_url()
    try:
        return anyio.run(_call_tool_async, target, name, kwargs or {}, timeout)
    except MCPClientError:
        raise
    except Exception as e:
        raise MCPClientError(
            f"coding-with-beat MCP server is not reachable at {target}: {e}\n"
            "Start it with: cwb server"
        ) from e


async def _call_tool_async(url: str, name: str, kwargs: dict[str, Any], timeout: float) -> str:
    async with streamablehttp_client(
        url,
        timeout=timeout,
        sse_read_timeout=timeout,
    ) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, kwargs)
            text = _content_text(result.content)
            is_error = getattr(result, "isError", False) or getattr(result, "is_error", False)
    if is_error:
        raise MCPClientError(text or f"MCP tool failed: {name}")
    return text


def _content_text(content: list[Any]) -> str:
    parts: list[str] = []
    for item in content:
        text = getattr(item, "text", None)
        if text is not None:
            parts.append(str(text))
        else:
            parts.append(str(item))
    return "\n".join(part for part in parts if part)
