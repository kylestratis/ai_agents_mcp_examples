from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession


class MCPClient:
    """MCP Client class for connecting to and interacting with MCP servers."""

    def __init__(
        self,
        name: str,
        command: str,
        server_args: list[str],
        env_vars: dict[str, str] = None,
    ) -> None:
        """Initialize the MCPClient with server connection parameters."""
        self.name = name
        self.command = command
        self.server_args = server_args
        self.env_vars = env_vars
        self._session: ClientSession = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()
        self._connected: bool = False

    async def connect(self) -> None:
        """Connect to the server set in the constructor."""
        pass

    async def get_available_tools(self) -> list[Any]:
        """Retrieve tools that the server has made available."""
        pass

    async def use_tool(self, tool_name: str, tool_args: list | None = None):
        """Given a tool name and optionally a list of argumnents, execute the tool."""
        pass

    async def disconnect(self) -> None:
        """Clean up any resources."""
        pass
