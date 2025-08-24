import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from client import MCPClient
from dotenv import load_dotenv
from internal_tool import InternalTool
from mcp.types import TextResourceContents

load_dotenv()

LLM_API_KEY = os.environ["LLM_API_KEY"]
anthropic_client = Anthropic(api_key=LLM_API_KEY)
logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, mcp_client: MCPClient, anthropic_client: Anthropic):
        self.mcp_client = mcp_client
        self.anthropic_client = anthropic_client
        self.available_resources = {}
        self.available_prompts = {}

    async def _select_resources(self, user_query: str) -> list[str]:
        """Use LLM to intelligently select relevant resources."""
        if not self.available_resources:
            return []

        resource_descriptions = {
            name: resource.description or f"Resource: {name}"
            for name, resource in self.available_resources.items()
        }

        selection_prompt = f"""
Given this user question: "{user_query}"

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
                model="claude-sonnet-4-0",
            )

            response_text = response.content[0].text.strip()
            if "[" in response_text and "]" in response_text:
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                json_part = response_text[start:end]
                selected_resources = json.loads(json_part)
                return [r for r in selected_resources if r in self.available_resources]

        except Exception as e:
            logger.warning(f"Failed to select resources with LLM: {e}")

        return []

    async def _select_prompts(self, user_query: str) -> list[dict[str, Any]]:
        """Use LLM to intelligently select relevant prompts."""
        if not self.available_prompts:
            return []

        prompts = [
            prompt.model_dump_json() for prompt in self.available_prompts.values()
        ]

        selection_prompt = f"""
Given this user question: "{user_query}"

And these available prompt templates:
{json.dumps(prompts, indent=2)}

Which prompts (if any) would provide helpful instructions or guidance for answering this question?
Return a JSON array of prompt objects which have a name (string) and arguments (objects where the 
keys are the named parameter name and value is the argument value), or an empty array if no prompts
are needed. Only include prompts that are directly relevant.

Example: [{{"name": "calculation-helper", "arguments": {{"operation": "addition"}}]}},
 {{"name": "step-by-step-math", "arguments": {{}}}}] or []
"""

        try:
            response = self.anthropic_client.messages.create(
                max_tokens=200,
                messages=[{"role": "user", "content": selection_prompt}],
                model="claude-sonnet-4-0",
            )

            response_text = response.content[0].text.strip()
            if "[" in response_text and "]" in response_text:
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                json_part = response_text[start:end]
                selected_prompts = json.loads(json_part)
                return [
                    p for p in selected_prompts if p["name"] in self.available_prompts
                ]

        except Exception as e:
            logger.warning(f"Failed to select prompts with LLM: {e}")

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
                                    "text": f"[Resource: {resource_name}]\n{content.text}",
                                }
                            )
                        elif content.mimeType in [
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
                                        "media_type": content.mimeType,
                                        "data": content.blob,
                                    },
                                }
                            )
                        else:
                            print(
                                f"WARNING: Unable to process mimeType {resource_contents.mimeType} for resource {resource_name}"
                            )
                except Exception as e:
                    print(f"Error loading resource {resource_name}: {e}")

        return context_messages

    async def _load_selected_prompts(self, prompts: list[dict[str, Any]]) -> str:
        """Load the specified prompts as system instructions."""
        system_instructions = []

        for prompt in prompts:
            if prompt["name"] in self.available_prompts:
                print(f"Using prompt: {prompt['name']}")
                try:
                    prompt_content = await self.mcp_client.load_prompt(
                        name=prompt["name"], arguments=prompt["arguments"]
                    )

                    # Extract the prompt text
                    prompt_text = ""
                    for message in prompt_content:
                        if hasattr(message.content, "text"):
                            prompt_text += message.content.text + "\n"
                        elif isinstance(message.content, str):
                            prompt_text += message.content + "\n"

                    if prompt_text.strip():
                        system_instructions.append(
                            f"[Prompt: {prompt['name']}]\n{prompt_text.strip()}"
                        )

                except Exception as e:
                    print(f"Error loading prompt {prompt['name']}: {e}")

        return "\n\n".join(system_instructions)

    async def _refresh(self) -> None:
        available_resources = await self.mcp_client.get_available_resources()
        self.available_resources = {
            resource.name: resource for resource in available_resources
        }
        available_prompts = await self.mcp_client.get_available_prompts()
        self.available_prompts = {prompt.name: prompt for prompt in available_prompts}

    async def run(self):
        try:
            print(
                "Welcome to your AI Assistant. Type 'goodbye' to quit or 'refresh' to reload and redisplay available resources."
            )
            await self.mcp_client.connect()
            available_tools: list[
                InternalTool
            ] = await self.mcp_client.get_available_tools()
            available_tools: list[dict[str, str]] = [
                tool.translate_to_anthropic() for tool in available_tools
            ]
            await self._refresh()

            print(
                f"Loaded {len(self.available_resources)} resources and {len(self.available_prompts)} prompts"
            )

            while True:
                prompt = input("You: ")

                if prompt.lower() == "goodbye":
                    print("AI Assistant: Goodbye!")
                    break

                if prompt.lower() == "refresh":
                    await self._refresh()
                    continue

                # Select relevant resources and prompts
                selected_resource_names = await self._select_resources(prompt)
                selected_prompt_names = await self._select_prompts(prompt)

                # Load relevant resources and prompts
                context_messages = await self._load_selected_resources(
                    selected_resource_names
                )
                system_instructions = await self._load_selected_prompts(
                    selected_prompt_names
                )

                # Build conversation with initial user message and any context
                user_content = [{"type": "text", "text": prompt}]
                if context_messages:
                    user_content.extend(context_messages)

                conversation_messages = [{"role": "user", "content": user_content}]

                # Tool use loop - continue until we get a final text response
                while True:
                    create_message_args = {
                        "max_tokens": 4096,
                        "messages": conversation_messages,
                        "model": "claude-sonnet-4-0",
                        "tools": available_tools,
                        "tool_choice": {"type": "auto"},
                    }

                    if system_instructions:
                        create_message_args["system"] = system_instructions

                    current_response = self.anthropic_client.messages.create(
                        **create_message_args
                    )

                    # Add assistant message to conversation
                    conversation_messages.append(
                        {"role": "assistant", "content": current_response.content}
                    )

                    # Check if we need to use tools
                    if current_response.stop_reason == "tool_use":
                        # Extract tool use blocks
                        tool_use_blocks = [
                            block
                            for block in current_response.content
                            if block.type == "tool_use"
                        ]

                        # Execute all tools and collect results
                        tool_results = []
                        for tool_use in tool_use_blocks:
                            print(f"Using tool: {tool_use.name}")
                            tool_result = await self.mcp_client.use_tool(
                                tool_name=tool_use.name, arguments=tool_use.input
                            )
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use.id,
                                    "content": "\n".join(tool_result),
                                }
                            )

                        # Add tool results to conversation
                        conversation_messages.append(
                            {"role": "user", "content": tool_results}
                        )

                        # Continue loop to get next LLM response
                        continue

                    else:
                        # No tools needed, extract final text response
                        text_blocks = [
                            content.text
                            for content in current_response.content
                            if hasattr(content, "text") and content.text.strip()
                        ]

                        if text_blocks:
                            print(f"Assistant: {text_blocks[0]}")
                        else:
                            print("Assistant: [No text response available]")

                        # Exit the tool use loop
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
        llm_client=anthropic_client,
        file_roots=[
            f"file:///{str(Path(__file__).parent.resolve())}",
        ],
    )
    agent = Agent(mcp_client, anthropic_client)
    asyncio.run(agent.run())
