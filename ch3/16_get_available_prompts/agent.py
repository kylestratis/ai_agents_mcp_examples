import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from client import MCPClient
from dotenv import load_dotenv
from mcp_types import Resource, TextResourceContents

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

    async def _refresh_resources(self) -> None:
        available_resources = await self.mcp_client.get_available_resources()
        self.available_resources = {
            resource.name: resource for resource in available_resources
        }

    async def run(self):
        try:
            print(
                "Welcome to your AI Assistant. Type 'goodbye' to quit or "
                "'refresh' to reload and redisplay available resources."
            )
            await self.mcp_client.connect()
            available_tools = await self.mcp_client.get_available_tools()
            await self._refresh_resources()

            while True:
                prompt = input("You: ")

                if prompt.lower() == "goodbye":
                    print("AI Assistant: Goodbye!")
                    break

                if prompt.lower() == "refresh":
                    await self._refresh_resources()
                    continue

                selected_resource_names = await self._select_resources(prompt)
                context_messages = await self._load_selected_resources(
                    selected_resource_names
                )

                # Build conversation with initial user message and any context
                user_content = [{"type": "text", "text": prompt}]
                if context_messages:
                    user_content.extend(context_messages)

                conversation_messages = [{"role": "user", "content": user_content}]

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


if __name__ == "__main__":
    mcp_client = MCPClient(
        name="calculator_server_connection",
        command="uv",
        server_args=[
            "--directory",
            str(Path(__file__).parent.parent.resolve()),
            "run",
            "calculator_server.py",
        ],
    )
    agent = Agent(mcp_client, anthropic_client)
    asyncio.run(agent.run())
