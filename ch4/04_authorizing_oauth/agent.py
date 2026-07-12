import asyncio
import json
import logging
import os
import webbrowser
from typing import Any

from anthropic import Anthropic
from client import MCPClient
from dotenv import load_dotenv
from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import (
    AuthorizationCodeResult,
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)
from mcp_types import (
    Prompt,
    PromptMessage,
    Resource,
    TextContent,
    TextResourceContents,
)

load_dotenv()

LLM_API_KEY = os.environ["LLM_API_KEY"]
anthropic_client = Anthropic(api_key=LLM_API_KEY)
logger = logging.getLogger(__name__)


class InMemoryTokenStorage:
    """
    Simplest possible TokenStorage: holds the tokens and the client's
    registration for the life of this process only. A real host should
    persist both somewhere fit for secrets, one store per server.
    """

    def __init__(self) -> None:
        self._tokens: OAuthToken | None = None
        self._client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        return self._tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self._tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self._client_info

    async def set_client_info(
        self, client_info: OAuthClientInformationFull
    ) -> None:
        self._client_info = client_info


async def open_browser(authorization_url: str) -> None:
    """Redirect handler: send the user to the authorization server."""
    print(f"Opening your browser to authorize: {authorization_url}")
    webbrowser.open(authorization_url)


async def wait_for_callback() -> AuthorizationCodeResult:
    """
    Callback handler: receive the authorization code. A desktop app
    would run a local redirect listener; this CLI asks for a paste.
    """
    code = input("Paste the authorization code: ").strip()
    state = input("Paste the state parameter: ").strip()
    return AuthorizationCodeResult(code=code, state=state)


async def progress_handler(
    progress: float, total: float | None, message: str | None
) -> None:
    if message:
        print(message)
    if total:
        print(f"{progress / total * 100:.0f}% complete")
    else:
        print(f"{progress} complete")


class Agent:
    def __init__(self, mcp_client: MCPClient, anthropic_client: Anthropic):
        self.mcp_client = mcp_client
        self.anthropic_client = anthropic_client
        self.available_resources: dict[str, Resource] = {}
        self.available_prompts: dict[str, Prompt] = {}

    def display_prompts(self) -> None:
        """Show the user the prompts they can invoke, with their arguments."""
        if not self.available_prompts:
            print("No prompts available on this server.")
            return

        print("\nAvailable prompts:")
        for name, prompt in self.available_prompts.items():
            print(f"  {name}: {prompt.description or '(no description)'}")
            for argument in prompt.arguments or []:
                required = "required" if argument.required else "optional"
                print(
                    f"      - {argument.name} ({required}) "
                    f"{argument.description or ''}"
                )
        print()

    def _collect_prompt_arguments(self, prompt: Prompt) -> dict[str, str]:
        """Ask the user to supply each of the prompt's arguments."""
        arguments: dict[str, str] = {}
        for argument in prompt.arguments or []:
            label = argument.name
            if argument.description:
                label += f" ({argument.description})"
            value = input(f"  {label}: ").strip()
            if not value and argument.required:
                value = input(
                    f"  {argument.name} is required — please provide a value: "
                ).strip()
            if value:
                arguments[argument.name] = value
        return arguments

    async def _use_prompt(self, name: str) -> list[dict[str, Any]]:
        prompt = self.available_prompts[name]
        arguments = self._collect_prompt_arguments(prompt)

        prompt_messages: list[PromptMessage] = await self.mcp_client.load_prompt(
            name=name, arguments=arguments
        )

        conversation_messages: list[dict[str, Any]] = []
        for message in prompt_messages:
            content = message.content
            if isinstance(content, TextContent):
                conversation_messages.append(
                    {"role": message.role, "content": content.text}
                )
            else:
                logger.warning(
                    f"Skipping unsupported prompt content type: {content.type}"
                )
        return conversation_messages

    async def _select_resources(self, prompt: str) -> list[str]:
        """Use LLM to intelligently select relevant resources."""
        if not self.available_resources:
            return []

        resource_descriptions = {
            name: resource.description or f"Resource: {name}"
            for name, resource in self.available_resources.items()
        }

        selection_prompt = f"""
Given this user question: "{prompt}"

And these available resources:
{json.dumps(resource_descriptions, indent=2)}

Which resources (if any) would be helpful to answer the user's question?
Return a JSON array of resource names, or an empty array if no resources are needed.
Only include resources that are directly relevant.

Example: ["math-constants"] or []
"""

        try:
            response = self.anthropic_client.messages.create(
                max_tokens=200,
                messages=[{"role": "user", "content": selection_prompt}],
                model="claude-sonnet-5",
            )

            response_text = response.content[0].text.strip()
            if "[" in response_text and "]" in response_text:
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                json_part = response_text[start:end]
                selected_resources = json.loads(json_part)
                return [
                    r for r in selected_resources if r in self.available_resources
                ]

        except Exception as e:
            logger.warning(f"Failed to select resources with LLM: {e}")

        return []

    async def _load_selected_resources(
        self, resource_names: list[str]
    ) -> list[dict[str, Any]]:
        """Load the specified resources."""
        context_messages = []

        for resource_name in resource_names:
            if resource_name in self.available_resources:
                print(f"LLM selected resource: {resource_name}")
                try:
                    resource = self.available_resources[resource_name]
                    resource_contents = await self.mcp_client.get_resource(
                        uri=resource.uri
                    )
                    for content in resource_contents:
                        if isinstance(content, TextResourceContents):
                            context_messages.append(
                                {
                                    "type": "text",
                                    "text": f"[Resource: {resource_name}]\n"
                                    f"{content.text}",
                                }
                            )
                        elif content.mime_type in [
                            "image/jpeg",
                            "image/png",
                            "image/gif",
                            "image/webp",
                        ]:  # b64-encoded image
                            context_messages.append(
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": content.mime_type,
                                        "data": content.blob,
                                    },
                                }
                            )
                        else:
                            logger.warning(
                                "Unable to process mime_type "
                                f"{content.mime_type} for "
                                f"resource {resource_name}"
                            )
                except Exception as e:
                    logger.warning(f"Error loading resource {resource_name}: {e}")

        return context_messages

    async def _refresh(self) -> None:
        available_resources = await self.mcp_client.get_available_resources()
        self.available_resources = {
            resource.name: resource for resource in available_resources
        }
        available_prompts = await self.mcp_client.get_available_prompts()
        self.available_prompts = {
            prompt.name: prompt for prompt in available_prompts
        }

    async def run(self):
        try:
            print(
                "Welcome to your AI Assistant. Type 'goodbye' to quit or "
                "'refresh' to reload and redisplay available resources."
            )
            available_tools = await self.mcp_client.get_available_tools()
            await self._refresh()

            while True:
                user_input = input("You: ")

                if user_input.lower() == "goodbye":
                    print("AI Assistant: Goodbye!")
                    break
                if user_input.lower() == "refresh":
                    await self._refresh()
                    continue

                if user_input.lower() == "prompts":
                    self.display_prompts()
                    name = input(
                        "Select a prompt by name (Enter to cancel): "
                    ).strip()
                    if not name:
                        continue
                    if name not in self.available_prompts:
                        print(f"No prompt named {name!r}.")
                        continue
                    conversation_messages = await self._use_prompt(name)
                else:
                    selected = await self._select_resources(user_input)
                    context_messages = await self._load_selected_resources(selected)
                    user_content = [{"type": "text", "text": user_input}]
                    if context_messages:
                        user_content.extend(context_messages)
                    conversation_messages = [
                        {"role": "user", "content": user_content}
                    ]

                # Tool use loop - continue until we get a final text response
                while True:
                    current_response = self.anthropic_client.messages.create(
                        max_tokens=4096,
                        messages=conversation_messages,
                        model="claude-sonnet-5",
                        tools=available_tools,
                        tool_choice={"type": "auto"},
                    )
                    conversation_messages.append(
                        {
                            "role": "assistant",
                            "content": current_response.content,
                        }
                    )

                    if current_response.stop_reason == "tool_use":
                        tool_use_blocks = [
                            block
                            for block in current_response.content
                            if block.type == "tool_use"
                        ]
                        tool_results = []
                        for tool_use in tool_use_blocks:
                            print(f"Using tool: {tool_use.name}")
                            tool_result = await self.mcp_client.use_tool(
                                tool_name=tool_use.name,
                                arguments=tool_use.input,
                                progress_callback=progress_handler,
                            )
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use.id,
                                    "content": "\n".join(tool_result),
                                }
                            )
                        conversation_messages.append(
                            {"role": "user", "content": tool_results}
                        )
                        continue
                    else:
                        text_blocks = [
                            content.text
                            for content in current_response.content
                            if hasattr(content, "text") and content.text.strip()
                        ]

                        if text_blocks:
                            print(f"Assistant: {text_blocks[0]}")
                        else:
                            print("Assistant: [No text response available]")
                        break
        finally:
            await self.mcp_client.disconnect()


async def main() -> None:
    server_url = os.environ.get("MCP_OAUTH_SERVER_URL")
    bearer_token = os.environ.get("MCP_SERVER_TOKEN")
    if not server_url:
        print(
            "Set MCP_OAUTH_SERVER_URL to an OAuth-protected MCP server to "
            "run this example. Optionally set MCP_SERVER_TOKEN to use a "
            "static bearer token instead of the full OAuth flow."
        )
        return

    mcp_client = MCPClient(
        name="oauth_server_connection",
        server_url=server_url,
        llm_client=anthropic_client,
    )

    if bearer_token:
        # Simplest case: a static API key or bearer token via headers
        await mcp_client.connect(
            headers={"Authorization": f"Bearer {bearer_token}"}
        )
    else:
        client_metadata = OAuthClientMetadata(
            client_name="Calculator Assistant",
            redirect_uris=["http://localhost:3030/callback"],
            scope="calculator:read calculator:write",
        )

        # Full OAuth: the SDK's provider handles the authorization-code
        # flow with PKCE, token refresh, and client registration for you.
        # Pass client_metadata_url to prefer CIMD registration.
        oauth = OAuthClientProvider(
            server_url=server_url,
            client_metadata=client_metadata,
            storage=InMemoryTokenStorage(),
            redirect_handler=open_browser,
            callback_handler=wait_for_callback,
        )
        await mcp_client.connect(auth=oauth)

    agent = Agent(mcp_client, anthropic_client)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
