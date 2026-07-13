import os
from typing import Annotated

from mcp.server.mcpserver import Context, ListRoots, MCPServer, Resolve
from mcp_types import ListRootsResult
from pydantic import FileUrl

mcp = MCPServer("roots-server")


def request_roots() -> ListRoots:
    """Resolver: fetch the client's current roots list."""
    return ListRoots()


@mcp.tool()
async def count_files(
    file_path: str,
    roots: Annotated[ListRootsResult, Resolve(request_roots)],
    ctx: Context,
) -> str:
    """Count files in a given directory."""
    root_uris: list[FileUrl] = [root.uri for root in roots.roots]

    file_path_abs = os.path.abspath(file_path)
    is_allowed = False

    for root_uri in root_uris:
        absolute_root_path = os.path.abspath(root_uri.path)
        if file_path_abs.startswith(absolute_root_path):
            is_allowed = True
            break

    if not is_allowed:
        error_msg = (
            f"Access denied: {file_path} is not within allowed roots " f"{root_uris}"
        )
        await ctx.error(error_msg)
        raise ValueError(error_msg)

    # Validate directory exists
    if not os.path.isdir(file_path):
        error_msg = f"Path {file_path} is not a valid directory"
        await ctx.error(error_msg)
        raise NotADirectoryError(error_msg)

    count = len(os.listdir(file_path))
    await ctx.info(f"Counting files in {file_path} = {count}")
    return f"There are {count} files in {file_path}"


if __name__ == "__main__":
    mcp.run()
