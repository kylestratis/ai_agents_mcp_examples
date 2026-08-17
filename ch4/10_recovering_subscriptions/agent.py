"""
Recovery watcher example. Start the HTTP calculator server first, in a
separate terminal, from the ch4 directory:

    uv run calculator_server_http.py

Then run this agent. Ask it to "install the plugin" to watch a
tools-list change event arrive through the subscription stream.
"""

import asyncio
import json
import logging
import os
from typing import Any

from anthropic import Anthropic
from client import MCPClient
from dotenv import load_dotenv
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
            await self.mcp_client.connect()
            watch_task = asyncio.create_task(
                self.mcp_client.watch_server_changes()
            )
            await self._refresh()

            while True:
                user_input = input("You: ")

                # Rebuild the tool list every turn: a change event from
                # the watcher evicts the cache, so this picks up new
                # tools as soon as the server announces them.
                available_tools = await self.mcp_client.get_available_tools()

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
            watch_task.cancel()
            await self.mcp_client.disconnect()


if __name__ == "__main__":
    mcp_client = MCPClient(
        name="calculator_server_connection",
        server_url=os.environ.get(
            "MCP_SERVER_URL", "http://localhost:8000/mcp"
        ),
        llm_client=anthropic_client,
    )
    agent = Agent(mcp_client, anthropic_client)
    asyncio.run(agent.run())
