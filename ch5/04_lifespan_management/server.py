import asyncio
import json
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

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


@asynccontextmanager
async def lifespan(server: Server) -> AsyncGenerator[dict[str, list[str]]]:
    logs = []
    logs.append(f"{datetime.now()}: Server started")
    print(logs[-1], file=sys.stderr)
    try:
        logs.append(f"{datetime.now()}: logs yielded")
        yield {"logs": logs}
    finally:
        logs.append(f"{datetime.now()}: Server stopped, printing all logs")
        print(logs, file=sys.stderr)


async def list_tools(
    ctx: ServerRequestContext, params: PaginatedRequestParams | None
) -> ListToolsResult:
    """List all tools available on the server."""
    logs = ctx.lifespan_context["logs"]
    print(logs[-1], file=sys.stderr)
    logs.append(f"{datetime.now()}: list_tools called")
    print(logs[-1], file=sys.stderr)

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
                output_schema={
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
    )


async def add(
    ctx: ServerRequestContext, params: CallToolRequestParams
) -> CallToolResult:
    """Add two numbers together."""
    if params.name != "add":
        raise ValueError(f"Unknown tool: {params.name}")
    args = params.arguments or {}
    result = {
        "augend": args["a"],
        "addend": args["b"],
        "sum": args["a"] + args["b"],
    }
    logs = ctx.lifespan_context["logs"]
    logs.append(f"{datetime.now()}: add called")
    print(logs[-1], file=sys.stderr)
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result))],
        structured_content=result,
    )


# Create a server instance with the lifespan and handlers
server = Server(
    "low-level-server",
    version="0.1.0",
    lifespan=lifespan,
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
