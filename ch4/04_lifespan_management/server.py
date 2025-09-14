import asyncio
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import mcp.server.stdio
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool

logs = []


@asynccontextmanager
async def lifespan(server: Server) -> AsyncGenerator[list[str]]:
    logs.append(f"{datetime.now()}: Server started")
    try:
        logs.append(f"{datetime.now()}: logs retrieved")
        yield logs
    finally:
        print("goodbye", file=sys.stderr)


# Create a server instance
server = Server("low-level-server", lifespan=lifespan)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all tools available on the server."""
    ctx = server.request_context
    print(ctx.lifespan_context[-1], file=sys.stderr)
    print(logs[-1], file=sys.stderr)
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
            outputSchema={
                "type": "object",
                "properties": {
                    "augend": {
                        "type": "number",
                        "description": "The first number to add",
                    },
                    "addend": {
                        "type": "number",
                        "description": "The second number to add",
                    },
                    "sum": {
                        "type": "number",
                        "description": "The result of the addition",
                    },
                },
                "required": ["augend", "addend", "sum"],
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
    result = {"augend": args["a"], "addend": args["b"], "sum": args["a"] + args["b"]}
    ctx = server.request_context
    logs = ctx.lifespan_context[-1]
    print(logs, file=sys.stderr)
    return result


async def run():
    print("Running low-level server", file=sys.stderr)
    print(logs, file=sys.stderr)
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
