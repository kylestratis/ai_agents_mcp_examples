import os

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from mcp.types import RootsListChangedNotification
from pydantic import FileUrl

mcp = FastMCP("roots-server")

roots_cache = []


async def handle_roots_list_changed(
    notifications: RootsListChangedNotification,
) -> None:
    roots_cache.clear()


@mcp.tool()
async def count_files(file_path: str, ctx: Context[ServerSession, None]) -> str:
    """Count files in a given directory."""
    if not roots_cache:
        roots_result = await ctx.session.list_roots()
        roots_cache.extend(roots_result.roots)
    root_uris: list[FileUrl] = [root.uri for root in roots_cache]

    file_path_abs = os.path.abspath(file_path)
    is_allowed = False

    for root_uri in root_uris:
        absolute_root_path = os.path.abspath(root_uri.path)
        if file_path_abs.startswith(absolute_root_path):
            is_allowed = True
            break

    if not is_allowed:
        error_msg = (
            f"Access denied: {file_path} is not within allowed roots {root_uris}"
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
    mcp._mcp_server.notification_handlers[RootsListChangedNotification] = (
        handle_roots_list_changed
    )
    mcp.run()
