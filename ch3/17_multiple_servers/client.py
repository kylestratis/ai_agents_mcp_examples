import logging
from typing import Any

from anthropic import Anthropic
from internal_tool import InternalTool
from mcp import ClientSession
from mcp.client.session_group import ClientSessionGroup, ServerParameters
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

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(
        self,
        name: str,
        llm_client: Anthropic,
    ) -> None:
        self.name = name
        self._llm_client = llm_client
        self._session_group = ClientSessionGroup()

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
                messages.append({"role": message.role, "content": message.content.text})
            else:
                # Handle other content types if needed
                messages.append({"role": message.role, "content": str(message.content)})

        response = self._llm_client.messages.create(
            max_tokens=params.maxTokens,
            messages=messages,
            model="claude-sonnet-4-0",
        )

    async def connect(self, server_parameters: ServerParameters) -> None:
        """
        Connect to the server set in the constructor.
        """
        connected_server = await self._session_group.connect_to_server(
            server_params=server_parameters,
        )
        connected_server._logging_callback = self._handle_logs
        connected_server._sampling_callback = self._handle_sampling

    async def use_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> list[str]:
        if not self._session_group.sessions:
            raise RuntimeError("Client not connected to a server")

        tool_call_result = await self._session_group.call_tool(
            name=tool_name, args=arguments
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
        if not self._session_group.sessions:
            raise RuntimeError("Client not connected to a server")
        resource_read_result = await self._session_group.read_resource(uri=uri)

        if not resource_read_result.contents:
            logger.warning(f"No content read for resource URI {uri}")
        return resource_read_result.contents

    async def load_prompt(
        self, name: str, arguments: dict[str, str]
    ) -> list[PromptMessage]:
        if not self._session_group.sessions:
            raise RuntimeError("Client not connected to a server")
        prompt_load_result = await self._session_group.get_prompt(
            name=name, arguments=arguments
        )

        if not prompt_load_result.messages:
            logger.warning(f"No prompt found for prompt {name}")
        else:
            logger.warning(
                f"Loaded prompt {name} with description {prompt_load_result.description}"
            )
        return prompt_load_result.messages

    async def get_available_resources(self) -> list[Resource]:
        if not self._session_group.sessions:
            raise RuntimeError("Client not connected to a server")

        resources_result = list(self._session_group.resources.values())
        if not resources_result:
            logger.warning("No resources found on server")
        return resources_result

    async def get_available_resource_templates(self) -> list[ResourceTemplate]:
        if not self._session_group.sessions:
            raise RuntimeError("Client not connected to a server")

        resource_templates_result = await self._session_group.list_resource_templates()
        if not resource_templates_result.resources:
            logger.warning("No resource templates found on server")
        return resource_templates_result.resources

    async def get_available_tools(self) -> list[dict[str, Any]]:
        if not self._session_group.sessions:
            raise RuntimeError("Client not connected to a server")

        if not self._session_group.tools:
            logger.warning("No tools found on server")
        available_tools = [
            InternalTool(
                name=tool.name,
                description=tool.description,
                input_schema=tool.inputSchema,
            )
            for tool in self._session_group.tools.values()
        ]
        return available_tools

    async def get_available_prompts(self) -> list[Prompt]:
        if not self._session_group.sessions:
            raise RuntimeError("Client not connected to a server")

        prompt_result = list(self._session_group.prompts.values())
        if not prompt_result:
            logger.warning("No prompts found on server")
        return prompt_result

    async def disconnect(self) -> None:
        """
        Clean up any resources
        """
        for session in self._session_group.sessions:
            await self._session_group.disconnect_from_server(session)
