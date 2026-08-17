import asyncio
import os
from pathlib import Path

from anthropic import Anthropic
from client import MCPClient
from dotenv import load_dotenv

load_dotenv()

LLM_API_KEY = os.environ["LLM_API_KEY"]
anthropic_client = Anthropic(api_key=LLM_API_KEY)

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


async def progress_handler(
    progress: float, total: float | None, message: str | None
) -> None:
    if message:
        print(message)
    if total:
        print(f"{progress / total * 100:.0f}% complete")
    else:
        print(f"{progress} complete")


print("Welcome to your AI Assistant. Type 'goodbye' to quit.")


async def main():
    """Main async function to run the assistant."""
    try:
        await mcp_client.connect()
        available_tools = await mcp_client.get_available_tools()
        tool_names = ", ".join(tool["name"] for tool in available_tools)
        print(f"Available tools: {tool_names}")

        while True:
            prompt = input("You: ")
            if prompt.lower() == "goodbye":
                print("AI Assistant: Goodbye!")
                break

            conversation_messages = [{"role": "user", "content": prompt}]

            # Tool use loop - continue until we get a final text response
            while True:
                current_response = anthropic_client.messages.create(
                    max_tokens=4096,
                    messages=conversation_messages,
                    model="claude-sonnet-5",
                    tools=available_tools,
                    tool_choice={"type": "auto"},
                )
                conversation_messages.append(
                    {"role": "assistant", "content": current_response.content}
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
                        tool_result = await mcp_client.use_tool(
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
        await mcp_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
