import asyncio
from typing import Any

import mcp.server.stdio
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool

# Create a server instance
server = Server("low-level-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all tools available on the server."""
    return [
        Tool(
            name="add",
            description="Add two numbers together.",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number to add"},
                    "b": {"type": "number", "description": "The second number to add"},
                },
                "required": ["a", "b"],
            },
        )
    ]


@server.call_tool()
async def add(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number
    """
    if name != "add":
        raise ValueError(f"Unknown tool: {name}")
    result = args["a"] + args["b"]
    return {"type": "text", "text": f"{args['a']} + {args['b']} = {result}"}


async def run():
    print("Running low-level server")
    initialization_options = InitializationOptions(
        server_name="low-level-server",
        server_version="0.1.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream=read_stream,
            write_stream=write_stream,
            initialization_options=initialization_options,
        )


if __name__ == "__main__":
    asyncio.run(run())
