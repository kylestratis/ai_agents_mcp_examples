import asyncio
import sys

import mcp.server.stdio
from mcp.server import NotificationOptions, Server, ServerRequestContext
from mcp.server.models import InitializationOptions
from mcp_types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)


async def list_tools(
    ctx: ServerRequestContext, params: PaginatedRequestParams | None
) -> ListToolsResult:
    """List all tools available on the server."""
    return ListToolsResult(
        tools=[
            Tool(
                name="add",
                description="Add two numbers together.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "number",
                            "description": "The first number to add",
                        },
                        "b": {
                            "type": "number",
                            "description": "The second number to add",
                        },
                    },
                    "required": ["a", "b"],
                },
            )
        ]
    )


async def add(
    ctx: ServerRequestContext, params: CallToolRequestParams
) -> CallToolResult:
    """Add two numbers together."""
    if params.name != "add":
        raise ValueError(f"Unknown tool: {params.name}")
    args = params.arguments or {}
    result = args["a"] + args["b"]
    return CallToolResult(
        content=[
            TextContent(type="text", text=f"{args['a']} + {args['b']} = {result}")
        ]
    )


# Create a server instance, registering the handlers
server = Server(
    "low-level-server",
    version="0.1.0",
    on_list_tools=list_tools,
    on_call_tool=add,
)


async def run():
    print("Running low-level server", file=sys.stderr)
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
