import os
from contextlib import AsyncExitStack
from typing import Any, Callable

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

LLM_API_KEY = os.environ["LLM_API_KEY"]
anthropic_client = Anthropic(api_key=LLM_API_KEY)


class MCPClient:
    def __init__(self, name: str, server_url: str) -> None:
        self.name = name
        self.server_url = server_url
        self._session: ClientSession = None
        self.exit_stack = AsyncExitStack()
        self._connected: bool = False
        self._get_session_id: Callable[[], str] = None

    async def connect(self, headers: dict | None = None) -> None:
        if self._connected:
            raise RuntimeError("Client is already connected")

        # Connect to Streamable HTTP server
        streamable_connection = await self._exit_stack.enter_async_context(
            streamablehttp_client(url=self.server_url, headers=headers)
        )
        self.read, self.write, self._get_session_id = streamable_connection

        # Start MCP client session
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream=self.read, write_stream=self.write)
        )

        # Initialize session
        await self._session.initialize()
        self._connected = True

    async def list_tools(self) -> list[Any]:
        """
        Retrieve tools that the server has made available.
        """
        pass

    async def call_tool(self, tool_name: str, tool_args: list | None = None):
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
