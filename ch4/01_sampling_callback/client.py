import logging
from contextlib import AsyncExitStack
from typing import Any, Callable

from anthropic import Anthropic
from mcp.client import Client
from mcp.client.session import ClientRequestContext
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp_types import (
    BlobResourceContents,
    CreateMessageRequestParams,
    CreateMessageResult,
    ErrorData,
    LoggingMessageNotificationParams,
    Prompt,
    PromptMessage,
    Resource,
    ResourceTemplate,
    TextContent,
    TextResourceContents,
)

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(
        self,
        name: str,
        command: str,
        server_args: list[str],
        llm_client: Anthropic,
        env_vars: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.command = command
        self.server_args = server_args
        self.env_vars = env_vars
        self._client: Client | None = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()
        self._connected: bool = False
        self._llm_client = llm_client

    async def __aenter__(self) -> "MCPClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    async def _handle_logs(
        self, params: LoggingMessageNotificationParams
    ) -> None:
        if params.level in ("debug", "error", "critical", "alert", "emergency"):
            print(f"[{params.level}] - {params.data}")

    async def _handle_sampling(
        self,
        context: ClientRequestContext,
        params: CreateMessageRequestParams,
    ) -> CreateMessageResult | ErrorData:
        messages = []
        for message in params.messages:
            if isinstance(message.content, TextContent):
                messages.append(
                    {"role": message.role, "content": message.content.text}
                )
            else:
                # Handle other content types if needed
                messages.append(
                    {"role": message.role, "content": str(message.content)}
                )

        response = self._llm_client.messages.create(
            max_tokens=params.max_tokens,
            messages=messages,
            model="claude-sonnet-5",
        )

        # Content is a list of blocks; use the first text block
        if response.content and hasattr(response.content[0], "text"):
            content_data = TextContent(
                type="text", text=response.content[0].text
            )
        else:
            # Fallback to string representation
            content_data = TextContent(
                type="text", text=str(response.content)
            )

        return CreateMessageResult(
            role=response.role,
            content=content_data,
            model="claude-sonnet-5",
        )

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

        transport = stdio_client(server_parameters)

        # Start the MCP client
        self._client = Client(
            transport,
            logging_callback=self._handle_logs,
            sampling_callback=self._handle_sampling,
        )
        await self._exit_stack.enter_async_context(self._client)
        self._connected = True

    async def get_available_tools(self) -> list[dict[str, Any]]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")

        tools_result = await self._client.list_tools()
        if not tools_result.tools:
            logger.warning("No tools found on server")
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in tools_result.tools
        ]
        return available_tools

    async def use_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        progress_callback: Callable | None = None,
    ) -> list[str]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")

        tool_call_result = await self._client.call_tool(
            name=tool_name,
            arguments=arguments,
            progress_callback=progress_callback,
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

        resources_result = await self._client.list_resources()
        if not resources_result.resources:
            logger.warning("No resources found on server")
        return resources_result.resources

    async def get_available_resource_templates(self) -> list[ResourceTemplate]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")

        resource_templates_result = await self._client.list_resource_templates()
        if not resource_templates_result.resource_templates:
            logger.warning("No resource templates found on server")
        return resource_templates_result.resource_templates

    async def get_resource(
        self, uri: str
    ) -> list[BlobResourceContents | TextResourceContents]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")
        resource_read_result = await self._client.read_resource(uri=uri)

        if not resource_read_result.contents:
            logger.warning(f"No content read for resource URI {uri}")
        return resource_read_result.contents

    async def get_available_prompts(self) -> list[Prompt]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")

        prompt_result = await self._client.list_prompts()
        if not prompt_result.prompts:
            logger.warning("No prompts found on server")
        return prompt_result.prompts

    async def load_prompt(
        self, name: str, arguments: dict[str, str]
    ) -> list[PromptMessage]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")
        prompt_load_result = await self._client.get_prompt(
            name=name, arguments=arguments
        )

        if not prompt_load_result.messages:
            logger.warning(f"No prompt found for prompt {name}")
        else:
            logger.info(
                f"Loaded prompt {name} with description "
                f"{prompt_load_result.description}"
            )
        return prompt_load_result.messages

    async def disconnect(self) -> None:
        """
        Clean up any resources
        """
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._connected = False
            self._client = None
