import os
from contextlib import AsyncExitStack
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

load_dotenv()

LLM_API_KEY = os.environ["LLM_API_KEY"]
anthropic_client = Anthropic(api_key=LLM_API_KEY)


class MCPClient:
    def __init__(
        self,
        name: str,
        command: str,
        server_args: list[str],
        env_vars: dict[str, str] = None,
    ) -> None:
        self.name = name
        self.command = command
        self.server_args = server_args
        self.env_vars = env_vars
        self._session: ClientSession = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()
        self._connected: bool = False

    async def connect(self) -> None:
        """
        Connect to the server set in the constructor.
        """
        if self._connected:
            raise RuntimeError("Client is already connected")

        server_parameters = StdioServerParameters(
            command=self.command,
            args=self.server_args,
            env=self.env_vars if self.env_vars else None,
        )

        # Connect to stdio server, starting subprocess
        stdio_connection = await self._exit_stack.enter_async_context(
            stdio_client(server_parameters)
        )
        self.read, self.write = stdio_connection

        # Start MCP client session
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream=self.read, write_stream=self.write)
        )

        # Initialize session
        await self._session.initialize()
        self._connected = True

    async def get_available_tools(self) -> list[Any]:
        """
        Retrieve tools that the server has made available.
        """
        pass

    async def use_tool(self, tool_name: str, tool_args: list | None = None):
        """
        Given a tool name and optionally a list of argumnents, execute the
        tool
        """
        pass

    async def disconnect(self) -> None:
        """
        Clean up any resources
        """
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._connected = False
            self._session = None


print("Welcome to your AI Assistant. Type 'goodbye' to quit.")

while True:
    prompt = input("You: ")
    if prompt.lower() == "goodbye":
        print("AI Assistant: Goodbye!")
        break
    message = anthropic_client.messages.create(
        max_tokens=1024,
        system="You are a helpful assistant.",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="claude-sonnet-4-0",
    )
    for response in message.content:
        print(f"Assistant: {response.text}")