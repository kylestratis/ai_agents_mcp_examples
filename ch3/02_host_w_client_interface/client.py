from typing import Any


class MCPClient:
    def __init__(self) -> None:
        pass

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
