from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP, Icon

SERVER_DIR = Path(__file__).parent

brain_icon = Icon(
    src=str(SERVER_DIR / "brain.png"), mime_type="image/png", sizes=["128x128"]
)
sloth_icon = Icon(
    src=str(SERVER_DIR / "sloth.png"), mime_type="image/png", sizes=["128x128"]
)
icons = [brain_icon, sloth_icon]
server_instructions = "Use this server to get information about the server."

mcp = FastMCP(
    "context-object-server-info-server",
    instructions=server_instructions,
    website_url="https://www.google.com",
    icons=icons,
    debug=True,
    log_level="DEBUG",
)


@mcp.tool()
async def get_server_information(ctx: Context) -> dict:
    """Get information about the server."""
    return {
        "server_name": ctx.fastmcp.name,
        "server_instructions": ctx.fastmcp.instructions,
        "server_website_url": ctx.fastmcp.website_url,
        "server_icon_count": len(ctx.fastmcp.icons),
        "server_debug_mode": ctx.fastmcp.settings.debug,
        "server_log_level": ctx.fastmcp.settings.log_level,
    }


@mcp.tool()
async def get_server_configuration(ctx: Context) -> dict:
    return dict(ctx.fastmcp.settings)


if __name__ == "__main__":
    mcp.run()
