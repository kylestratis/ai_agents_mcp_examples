import logging
from contextlib import AsyncExitStack
from typing import Any

from anthropic import Anthropic
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.context import RequestContext
from mcp.types import (
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

from internal_tool import InternalTool

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(
        self,
        name: str,
        command: str,
        server_args: list[str],
        llm_client: Anthropic,
        env_vars: dict[str, str] = None,
    ) -> None:
        self.name = name
        self.command = command
        self.server_args = server_args
        self.env_vars = env_vars
        self._session: ClientSession = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()
        self._connected: bool = False
        self._llm_client = llm_client

    async def _handle_logs(self, params: LoggingMessageNotificationParams) -> None:
        """
        Log handler that simply prints log messages to the console, implementing the
        LoggingFnT protocol.
        """
        if params.level in ("info", "error", "critical", "alert", "emergency"):
            print(f"[{params.level}] - {params.data}")

    async def _handle_sampling(
        self,
        context: RequestContext[ClientSession, None],
        params: CreateMessageRequestParams,
    ) -> CreateMessageResult | ErrorData:
        """
        Sampling handler that passes the server's prompt to the LLM client, implementing
        the SamplingFnT protocol, which is why the unused context parameter is included.
        """
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
            max_tokens=params.maxTokens,
            messages=messages,
            model="claude-sonnet-4-0",
        )

        # Extract content from the response - content is a list of content blocks
        if response.content and len(response.content) > 0:
            content = response.content[0]
            if hasattr(content, "text"):
                content_data = TextContent(type="text", text=content.text)
            elif hasattr(content, "data"):
                content_data = BlobResourceContents(
                    type="blob",
                    data=content.data,
                    mimeType=content.mimeType,
                )
            else:
                # Fallback to string representation
                content_data = TextContent(type="text", text=str(content))
        else:
            # No content in response
            content_data = ""

        return CreateMessageResult(
            role=response.role, content=content_data, model="claude-sonnet-4-0"
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

        # Connect to stdio server, starting subprocess
        stdio_connection = await self._exit_stack.enter_async_context(
            stdio_client(server_parameters)
        )
        self.read, self.write = stdio_connection

        # Start MCP client session
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(
                read_stream=self.read,
                write_stream=self.write,
                logging_callback=self._handle_logs,
                sampling_callback=self._handle_sampling,
            ),
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

    async def get_resource(
        self, uri: str
    ) -> list[BlobResourceContents | TextResourceContents]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")
        resource_read_result = await self._session.read_resource(uri=uri)

        if not resource_read_result.contents:
            logger.warning(f"No content read for resource URI {uri}")
        return resource_read_result.contents

    async def load_prompt(
        self, name: str, arguments: dict[str, str]
    ) -> list[PromptMessage]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")
        prompt_load_result = await self._session.get_prompt(
            name=name, arguments=arguments
        )

        if not prompt_load_result.messages:
            logger.warning(f"No prompt found for prompt {name}")
        else:
            logger.debug(
                f"Loaded prompt {name} with description {prompt_load_result.description}"
            )
        return prompt_load_result.messages

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
            InternalTool(
                name=tool.name,
                description=tool.description,
                input_schema=tool.inputSchema,
            )
            for tool in tools_result.tools
        ]
        return available_tools

    async def get_available_prompts(self) -> list[Prompt]:
        if not self._connected:
            raise RuntimeError("Client not connected to a server")

        prompt_result = await self._session.list_prompts()
        if not prompt_result.prompts:
            logger.warning("No prompts found on server")
        return prompt_result.prompts

    async def disconnect(self) -> None:
        """
        Clean up any resources
        """
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._connected = False
            self._session = None