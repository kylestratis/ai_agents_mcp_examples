import asyncio
import sys

import mcp.server.stdio
from mcp.server import NotificationOptions, Server, ServerRequestContext
from mcp.server.models import InitializationOptions
from mcp_types import (
    ListResourcesResult,
    PaginatedRequestParams,
    ReadResourceRequestParams,
    ReadResourceResult,
    Resource,
    TextResourceContents,
)

# Total number of resources
TOTAL_RESOURCES = 1000
PAGE_SIZE = 100
RESOURCES = []
for i in range(0, TOTAL_RESOURCES):
    RESOURCES.append(
        Resource(
            uri=f"resource://{i}",
            name=f"Resource {i}",
            description=f"This is resource number {i}",
            mime_type="text/plain",
        )
    )


async def list_resources(
    ctx: ServerRequestContext, params: PaginatedRequestParams | None
) -> ListResourcesResult:
    """List resources with pagination support.
    Returns 100 resources at a time from a fixed list of 1000 resources.
    """
    if params is not None:
        cursor = params.cursor
    else:
        cursor = None

    start_index = 0
    if cursor is not None:
        start_index = int(cursor)
    end_index = min(start_index + PAGE_SIZE, TOTAL_RESOURCES)

    resources = RESOURCES[start_index:end_index]

    next_cursor = None
    if end_index < TOTAL_RESOURCES:
        next_cursor = str(end_index)

    return ListResourcesResult(resources=resources, next_cursor=next_cursor)


async def read_resource(
    ctx: ServerRequestContext, params: ReadResourceRequestParams
) -> ReadResourceResult:
    """Read a single resource by its URI."""
    uri = params.uri
    if not uri.startswith("resource://"):
        raise ValueError(f"Invalid resource URI: {uri}")

    try:
        resource_num = int(uri.replace("resource://", ""))
    except ValueError:
        raise ValueError(f"Invalid resource number in URI: {uri}")

    if resource_num < 0 or resource_num >= TOTAL_RESOURCES:
        raise ValueError(f"Resource not found: {uri}")

    return ReadResourceResult(
        contents=[
            TextResourceContents(
                uri=uri,
                mime_type="text/plain",
                text=RESOURCES[resource_num].description,
            )
        ]
    )


# Create a server instance, registering the handlers
server = Server(
    "low-level-pagination-server",
    version="0.1.0",
    on_list_resources=list_resources,
    on_read_resource=read_resource,
)


async def run() -> None:
    """Run the low-level pagination server."""
    print("Running pagination server with 1000 resources", file=sys.stderr)
    initialization_options = InitializationOptions(
        server_name="pagination-server",
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
