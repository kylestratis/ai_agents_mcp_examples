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
    await mcp_client.connect()
    available_tools = await mcp_client.get_available_tools()
    tool_names = ", ".join(tool["name"] for tool in available_tools)
    print(f"Available tools: {tool_names}")
    while True:
        prompt = input("You: ")
        if prompt.lower() == "goodbye":
            print("AI Assistant: Goodbye!")
            break
        message = anthropic_client.messages.create(
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="claude-sonnet-5",
        )
        for response in message.content:
            print(f"Assistant: {response.text}")
    await mcp_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
