import asyncio
import logging
import os
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import Resource, ResourceTemplate, TextResourceContents

load_dotenv()

LLM_API_KEY = os.environ["LLM_API_KEY"]
anthropic_client = Anthropic(api_key=LLM_API_KEY)
logger = logging.getLogger(__name__)


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

    async def use_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> list[str]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")

        tool_call_result = await self._session.call_tool(
            name=tool_name, arguments=arguments
        )
        logger.debug(f"Calling tool {tool_name} with arguments {arguments}")

        results = []
        if tool_call_result.content:
            for content in tool_call_result.content:
                match content.type:
                    case "text":
                        results.append(content.text)
                    case "image" | "audio":
                        results.append(content.data)
                    case "resource":
                        if isinstance(content.resource, TextResourceContents):
                            results.append(content.resource.text)
                        else:
                            results.append(content.resource.blob)
        else:
            logger.warning(f"No content in tool call result for tool {tool_name}")
        return results

    async def get_available_resources(self) -> list[Resource]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")

        resources_result = await self._session.list_resources()
        if not resources_result.resources:
            logger.warning("No resources found on server")
        return resources_result.resources

    async def get_available_resource_templates(self) -> list[ResourceTemplate]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")

        resource_templates_result = await self._session.list_resource_templates()
        if not resource_templates_result.resources:
            logger.warning("No resource templates found on server")
        return resource_templates_result.resources

    async def get_available_tools(self) -> list[dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")

        tools_result = await self._session.list_tools()
        if not tools_result.tools:
            logger.warning("No tools found on server")
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools_result.tools
        ]
        return available_tools

    async def disconnect(self) -> None:
        """
        Clean up any resources
        """
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._connected = False
            self._session = None


mcp_client = MCPClient(
    name="calculator_server_connection",
    command="uv",
    server_args=[
        "--directory",
        str(Path(__file__).parent.resolve()),
        "run",
        "calculator_server.py",
    ],
)


print("Welcome to your AI Assistant. Type 'goodbye' to quit.")


async def main():
    try:
        await mcp_client.connect()
        available_tools = await mcp_client.get_available_tools()
        print(
            f"Available tools: {", ".join([tool['name'] for tool in available_tools])}"
        )

        while True:
            prompt = input("You: ")
            if prompt.lower() == "goodbye":
                print("AI Assistant: Goodbye!")
                break
            message = anthropic_client.messages.create(
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="claude-sonnet-4-0",
                tools=available_tools,
                tool_choice={"type": "auto"},
            )

            tool_use_message_block = {"role": "user", "content": []}
            if message.stop_reason == "tool_use":
                tool_use_messages = [
                    message for message in message.content if message.type == "tool_use"
                ]
                for tool_use in tool_use_messages:
                    tool_result = await mcp_client.use_tool(
                        tool_name=tool_use.name, arguments=tool_use.input
                    )
                    tool_use_message_block["content"].append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": "\n".join(tool_result),
                        }
                    )

            if tool_use_message_block["content"]:
                response = anthropic_client.messages.create(
                    max_tokens=4096,
                    messages=[
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": message.content},
                        tool_use_message_block,
                    ],
                    model="claude-sonnet-4-0",
                    tools=available_tools,
                    tool_choice={"type": "auto"},
                )
            else:
                response = message

            display_response = next(
                message.text for message in response.content if hasattr(message, "text")
            )
            print(f"Assistant: {display_response}")
    finally:
        await mcp_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
