import json
import logging
import webbrowser
from contextlib import AsyncExitStack
from typing import Any, Callable

import httpx
from anthropic import Anthropic
from mcp.client import Client
from mcp.client.session import ClientRequestContext
from mcp.client.streamable_http import streamable_http_client
from mcp_types import (
    BlobResourceContents,
    CreateMessageRequestParams,
    CreateMessageResult,
    ElicitRequestFormParams,
    ElicitRequestURLParams,
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
        server_url: str,
        llm_client: Anthropic,
        file_roots: list[str] | None = None,
    ) -> None:
        self.name = name
        self.server_url = server_url
        self.file_roots = file_roots
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

    async def _handle_roots(
        self,
        context: ClientRequestContext,
    ) -> ListRootsResult | ErrorData:
        """
        Roots handler that returns the file roots, implementing the
        ListRootsFnT protocol.
        """
        roots_result = []
        for root in self.file_roots or []:
            if not root.startswith("file:///"):
                logger.warning(
                    f"Root {root} does not start with file:///, ignoring"
                )
            else:
                roots_result.append(Root(uri=root))
        if not roots_result:
            return ErrorData(code=-32602, message="No valid file roots provided")
        return ListRootsResult(roots=roots_result)

    async def _handle_elicitation(
        self,
        context: ClientRequestContext,
        params: ElicitRequestFormParams | ElicitRequestURLParams,
    ) -> ElicitResult | ErrorData:
        """
        Elicitation handler that displays the server request to the user,
        handles their accept/decline response, and collects form data or
        opens a URL when accepted, implementing the ElicitationFnT protocol.
        """
        # Get the server name from the client instance
        requesting_server = self.name

        # Display the elicitation request to the user
        print(f"\n{'=' * 60}")
        print(f"ELICITATION REQUEST FROM SERVER: {requesting_server}")
        print(f"{'=' * 60}")
        print(f"Message: {params.message}")
        print(f"{'=' * 60}")

        # URL mode: consent first, then hand off to the browser
        if isinstance(params, ElicitRequestURLParams):
            return self._handle_url_elicitation(params)

        # Form mode: get user input for accept/decline
        while True:
            user_response = (
                input("\nDo you want to accept this request? (y/n/c for cancel): ")
                .lower()
                .strip()
            )

            if user_response in ["y", "yes", "accept"]:
                print("Request accepted")
                # Collect form data based on the schema
                form_data = self._collect_form_data(params.requested_schema)
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
                    "Invalid response. Please enter 'y' (accept), "
                    "'n' (decline), or 'c' (cancel)."
                )

    def _handle_url_elicitation(
        self, params: ElicitRequestURLParams
    ) -> ElicitResult:
        """
        Show the user the full URL, get explicit consent, and only
        then open it. The interaction itself happens out of band.
        """
        print("The server is asking you to continue in your browser at:")
        print(f"  {params.url}")
        user_response = input("\nOpen this URL? (y/n): ").lower().strip()
        if user_response in ["y", "yes"]:
            webbrowser.open(str(params.url))
            return ElicitResult(action="accept")
        print("Request declined")
        return ElicitResult(action="decline")

    def _collect_form_data(self, schema: dict[str, Any]) -> dict[str, Any] | None:
        """
        Collect form data from the user based on the provided schema.

        Args:
            schema: The JSON schema defining the required fields

        Returns:
            Dictionary containing the collected form data, or None if cancelled
        """
        print(f"\n{'=' * 60}")
        print("FORM DATA REQUIRED")
        print(f"{'=' * 60}")

        # Display schema information
        if "properties" in schema:
            print("Required fields:")
            for field_name, field_info in schema["properties"].items():
                field_type = field_info.get("type", "string")
                description = field_info.get("description", "")
                required = field_name in schema.get("required", [])
                required_text = " (required)" if required else " (optional)"
                print(
                    f"  • {field_name} ({field_type}){required_text}: {description}"
                )
        else:
            print("Schema:")
            print(json.dumps(schema, indent=2))

        print(f"{'=' * 60}")

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
                        print(
                            f"Error: Invalid {field_type} value. Please try again."
                        )
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

    async def connect(
        self,
        headers: dict[str, str] | None = None,
        auth: httpx.Auth | None = None,
    ) -> None:
        """
        Connect to the server set in the constructor.
        """
        if self._connected:
            raise RuntimeError("Client is already connected")

        try:
            if headers or auth:
                http_client = await self._exit_stack.enter_async_context(
                    httpx.AsyncClient(
                        headers=headers,
                        auth=auth,
                        timeout=httpx.Timeout(30.0, read=300.0),
                        follow_redirects=True,
                    )
                )
                transport = streamable_http_client(
                    url=self.server_url, http_client=http_client
                )
                self._client = Client(
                    transport,
                    logging_callback=self._handle_logs,
                    sampling_callback=self._handle_sampling,
                    list_roots_callback=self._handle_roots,
                    elicitation_callback=self._handle_elicitation,
                )
            else:
                self._client = Client(
                    self.server_url,
                    logging_callback=self._handle_logs,
                    sampling_callback=self._handle_sampling,
                    list_roots_callback=self._handle_roots,
                    elicitation_callback=self._handle_elicitation,
                )

            await self._exit_stack.enter_async_context(self._client)
        except Exception:
            await self._exit_stack.aclose()
            raise
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
