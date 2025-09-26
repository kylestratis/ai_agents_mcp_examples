from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("resource-template-server")


@mcp.resource("file:///{filename}")
async def resource_template(filename: str) -> str | bytes:
    """A resource that loads one of two files based on the filename parameter."""
    # Get the absolute path to the file relative to this script
    file_to_load = Path(__file__).parent / filename

    # Determine if file is binary based on extension
    if file_to_load.suffix.lower() == ".txt":
        with open(file_to_load, "r", encoding="utf-8") as f:
            return f.read()
    else:
        with open(file_to_load, "rb") as f:
            return f.read()


if __name__ == "__main__":
    mcp.run()
