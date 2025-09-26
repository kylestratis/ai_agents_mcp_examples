from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.resources import FileResource

# Initialize FastMCP server
mcp = FastMCP("resource-object-server")


@mcp.resource("file:///{filename}")
async def resource_template(filename: str) -> FileResource:
    """A resource that loads one of two files based on the filename parameter."""
    # Get the absolute path to the file relative to this script
    file_to_load = Path(__file__).parent / filename
    if file_to_load.suffix.lower() == ".txt":
        binary_flag = False
    else:
        binary_flag = True
    return FileResource(
        uri=f"file:///{filename}", path=file_to_load, is_binary=binary_flag
    )


filename = "1.txt"
file_resource = FileResource(
    uri=f"file:///{filename}", path=Path(__file__).parent / filename
)
mcp.add_resource(file_resource)

if __name__ == "__main__":
    mcp.run()
