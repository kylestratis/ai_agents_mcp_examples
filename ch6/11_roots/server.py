import os
from pathlib import Path
from typing import Annotated
from urllib.request import url2pathname

from mcp.server.mcpserver import Context, ListRoots, MCPServer, Resolve
from mcp_types import ListRootsResult

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
    requested_path = Path(file_path).resolve()
    is_allowed = False

    for root in roots.roots:
        root_path = Path(url2pathname(root.uri.path)).resolve()
        if requested_path.is_relative_to(root_path):
            is_allowed = True
            break

    if not is_allowed:
        error_msg = f"Access denied: {file_path} is not within allowed roots"
        await ctx.error(error_msg)
        raise ValueError(error_msg)

    # Validate directory exists
    if not requested_path.is_dir():
        error_msg = f"Path {file_path} is not a valid directory"
        await ctx.error(error_msg)
        raise NotADirectoryError(error_msg)

    count = len(os.listdir(requested_path))
    await ctx.info(f"Counting files in {file_path} = {count}")
    return f"There are {count} files in {file_path}"


if __name__ == "__main__":
    mcp.run()
