from pathlib import Path

from mcp.server.fastmcp import FastMCP, Icon

SERVER_DIR = Path(__file__).parent

brain_icon = Icon(
    src=str(SERVER_DIR / "brain.png"), mime_type="image/png", sizes=["128x128"]
)
sloth_icon = Icon(
    src=str(SERVER_DIR / "sloth.png"), mime_type="image/png", sizes=["128x128"]
)
icons = [brain_icon, sloth_icon]

mcp = FastMCP("icons-server", icons=icons)


@mcp.tool(icons=[brain_icon])
async def think() -> str:
    """A tool that makes the server think with an icon."""
    return "I'm thinking..."


@mcp.prompt(icons=[sloth_icon])
async def sloth_prompt() -> str:
    """A prompt that makes the server think slowlywith an icon."""
    return "Think very slowly, like a sloth"


@mcp.resource(uri="file:///{filename}", icons=icons)
async def resource_template(filename: str) -> str | bytes:
    """
    A resource that loads a file based on the filename parameter and has two icons
    """
    return "Here is your file!"


if __name__ == "__main__":
    mcp.run()
