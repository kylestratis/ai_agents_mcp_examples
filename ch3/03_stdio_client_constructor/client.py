from contextlib import AsyncExitStack
from typing import Any

from mcp.client import Client


class MCPClient:
    def __init__(
        self,
        name: str,
        command: str,
        server_args: list[str],
        env_vars: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.command = command
        self.server_args = server_args
        self.env_vars = env_vars
        self._client: Client | None = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()
        self._connected: bool = False

    async def connect(self) -> None:
        """
        Connect to the server set in the constructor.
        """
        pass

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
        pass
