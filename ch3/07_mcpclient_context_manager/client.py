from contextlib import AsyncExitStack
from typing import Any

import httpx2
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client


class MCPClient:
    def __init__(self, name: str, server_url: str) -> None:
        self.name = name
        self.server_url = server_url
        self._client: Client | None = None
        self._exit_stack = AsyncExitStack()
        self._connected: bool = False

    async def __aenter__(self) -> "MCPClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    async def connect(self, headers: dict[str, str] | None = None) -> None:
        if self._connected:
            raise RuntimeError("Client is already connected")

        try:
            if headers:
                http_client = await self._exit_stack.enter_async_context(
                    httpx2.AsyncClient(
                        headers=headers,
                        timeout=httpx2.Timeout(30.0, read=300.0),
                        follow_redirects=True,
                    )
                )
                transport = streamable_http_client(
                    url=self.server_url, http_client=http_client
                )
                self._client = Client(transport)
            else:
                self._client = Client(self.server_url)

            await self._exit_stack.enter_async_context(self._client)
        except Exception:
            await self._exit_stack.aclose()
            raise
        self._connected = True

    async def get_available_tools(self) -> list[Any]:
        """
        Retrieve tools that the server has made available.
        """
        pass

    async def use_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ):
        """
        Given a tool name and optionally a dictionary of arguments, execute
        the tool
        """
        pass

    async def disconnect(self) -> None:
        """
        Clean up any resources
        """
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._connected = False
            self._client = None
