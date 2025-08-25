import json
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
    ElicitRequestParams,
    ElicitResult,
    ErrorData,
    ListRootsResult,
    LoggingMessageNotificationParams,
    Prompt,
    PromptMessage,
    Resource,
    ResourceTemplate,
    Root,
    TextContent,
    TextResourceContents,
)

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(
        self,
        name: str,
        llm_client: Anthropic,
        file_roots: list[str] = None,
    ) -> None:
        self.name = name
        self.file_roots = file_roots
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

    async def _handle_roots(
        self,
        context: RequestContext[ClientSession, Any],
    ) -> ListRootsResult | ErrorData:
        """
        Roots handler that returns the file roots, implementing the RootsFnT protocol.
        """
        roots_result = []
        for root in self.file_roots:
            if not root.startswith("file:///"):
                logger.warning(f"Root {root} does not start with file:///, ignoring")
            else:
                roots_result.append(Root(uri=root))
        if roots_result is None:
            return ErrorData(code=-32602, message="No valid file roots provided")
        return ListRootsResult(roots=roots_result)

    def _collect_form_data(self, schema: dict[str, Any]) -> dict[str, Any] | None:
        """
        Collect form data from the user based on the provided schema.

        Args:
            schema: The JSON schema defining the required fields

        Returns:
            Dictionary containing the collected form data, or None if cancelled
        """
        print(f"\n{'='*60}")
        print("FORM DATA REQUIRED")
        print(f"{'='*60}")

        # Display schema information
        if "properties" in schema:
            print("Required fields:")
            for field_name, field_info in schema["properties"].items():
                field_type = field_info.get("type", "string")
                description = field_info.get("description", "")
                required = field_name in schema.get("required", [])
                required_text = " (required)" if required else " (optional)"
                print(f"  • {field_name} ({field_type}){required_text}: {description}")
        else:
            print("Schema:")
            print(json.dumps(schema, indent=2))

        print(f"{'='*60}")

        collected_data = {}

        # Collect data for each field in the schema
        if "properties" in schema:
            for field_name, field_info in schema["properties"].items():
                field_type = field_info.get("type", "string")
                description = field_info.get("description", "")
                required = field_name in schema.get("required", [])

                while True:
                    prompt = f"\nEnter {field_name}"
                    if description:
                        prompt += f" ({description})"
                    if not required:
                        prompt += " [optional]"
                    prompt += ": "

                    value = input(prompt).strip()

                    # Handle optional fields
                    if not value and not required:
                        break

                    # Validate required fields
                    if not value and required:
                        print(f"Error: {field_name} is required")
                        continue

                    # Type conversion
                    try:
                        if field_type == "integer":
                            collected_data[field_name] = int(value)
                        elif field_type == "number":
                            collected_data[field_name] = float(value)
                        elif field_type == "boolean":
                            collected_data[field_name] = value.lower() in [
                                "true",
                                "yes",
                                "y",
                                "1",
                            ]
                        else:  # string or any other type
                            collected_data[field_name] = value
                        break
                    except ValueError:
                        print(f"Error: Invalid {field_type} value. Please try again.")
        else:
            # Fallback for non-standard schemas
            print("Please provide data as JSON:")
            while True:
                json_input = input("JSON data: ").strip()
                try:
                    collected_data = json.loads(json_input)
                    break
                except json.JSONDecodeError:
                    print("Error: Invalid JSON. Please try again.")

        return collected_data

    async def _handle_elicitation(
        self,
        context: RequestContext[ClientSession, Any],
        params: ElicitRequestParams,
    ) -> ElicitResult | ErrorData:
        """
        Elicitation handler that displays the server request to the user, handles
        their accept/decline response, and collects form data when accepted,
        implementing the ElicitFnT protocol.
        """
        # Get the server name from the client instance
        requesting_server = self.name

        # Display the elicitation request to the user
        print(f"\n{'='*60}")
        print(f"ELICITATION REQUEST FROM SERVER: {requesting_server}")
        print(f"{'='*60}")
        print(f"Message: {params.message}")
        print(f"{'='*60}")

        # Get user input for accept/decline
        while True:
            user_response = (
                input("\nDo you want to accept this request? (y/n/c for cancel): ")
                .lower()
                .strip()
            )

            if user_response in ["y", "yes", "accept"]:
                print("Request accepted")
                # Collect form data based on the schema
                form_data = self._collect_form_data(params.requestedSchema)
                if form_data is not None:
                    print("Form data collected successfully")
                    return ElicitResult(action="accept", content=form_data)
                else:
                    print("Form data collection cancelled")
                    return ElicitResult(action="cancel")
            elif user_response in ["n", "no", "decline"]:
                print("Request declined")
                return ElicitResult(action="decline")
            elif user_response in ["c", "cancel"]:
                print("Request cancelled")
                return ElicitResult(action="cancel")
            else:
                print(
                    "Invalid response. Please enter 'y' (accept), 'n' (decline), or 'c' (cancel)."
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
        connected_server._list_roots_callback = self._handle_roots

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
            logger.debug(
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
