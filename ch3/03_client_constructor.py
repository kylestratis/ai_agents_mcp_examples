import os
from contextlib import AsyncExitStack
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession

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
        pass

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
        pass


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
