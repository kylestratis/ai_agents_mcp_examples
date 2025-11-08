import asyncio

import mcp.server.stdio
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import AnyUrl, ListResourcesRequest, ListResourcesResult, Resource

# Create a server instance
server = Server("low-level-pagination-server")

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
            mimeType="text/plain",
        )
    )


@server.list_resources()
async def list_resources(request: ListResourcesRequest) -> ListResourcesResult:
    """List resources with pagination support.
    Returns 100 resources at a time from a fixed list of 1000 resources.
    """
    if request.params is not None:
        cursor = request.params.cursor
    else:
        cursor = None

    start_index = 0
    if cursor is not None:
        start_index = int(cursor)
        end_index = min(start_index + PAGE_SIZE, TOTAL_RESOURCES)
    else:
        end_index = TOTAL_RESOURCES

    resources = RESOURCES[start_index:end_index]

    next_cursor = None
    if end_index < TOTAL_RESOURCES:
        next_cursor = str(end_index)

    return ListResourcesResult(resources=resources, nextCursor=next_cursor)


@server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    uri_str = str(uri)
    if not uri_str.startswith("resource://"):
        raise ValueError(f"Invalid resource URI: {uri_str}")

    try:
        resource_num = int(uri_str.replace("resource://", ""))
    except ValueError:
        raise ValueError(f"Invalid resource number in URI: {uri_str}")

    if resource_num < 0 or resource_num >= TOTAL_RESOURCES:
        raise ValueError(f"Resource not found: {uri_str}")

    return RESOURCES[resource_num].description


async def run() -> None:
    """Run the low-level pagination server."""
    print("Running pagination server with 1000 resources")
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
